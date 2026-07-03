"""
Cook It — AI-Powered Recipe Discovery and Digital Cookbook
Flask backend: OCR ingredient extraction -> recipe search -> saved cookbook.
"""
import os
import re
import time
from datetime import datetime

import requests
import pytesseract
from PIL import Image, ImageOps
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)

# --- Database -----------------------------------------------------------
# SQLite by default so the prototype runs with zero setup.
# To point this at real MySQL for production, swap the URI below, e.g.:
#   mysql+pymysql://cookit_user:password@localhost/cookit
# and `pip install pymysql`. schema.sql in this folder mirrors these
# models for a native MySQL setup.
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "COOKIT_DB_URI", f"sqlite:///{os.path.join(BASE_DIR, 'cookit.db')}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)


class SavedRecipe(db.Model):
    __tablename__ = "saved_recipes"
    id = db.Column(db.Integer, primary_key=True)
    meal_id = db.Column(db.String(32), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    thumbnail = db.Column(db.String(512))
    source_url = db.Column(db.String(512))
    matched_ingredients = db.Column(db.String(512))
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "meal_id": self.meal_id,
            "title": self.title,
            "thumbnail": self.thumbnail,
            "source_url": self.source_url,
            "matched_ingredients": self.matched_ingredients,
            "saved_at": self.saved_at.strftime("%b %d, %Y %I:%M %p"),
        }


class ScanLog(db.Model):
    __tablename__ = "scan_log"
    id = db.Column(db.Integer, primary_key=True)
    raw_text = db.Column(db.Text)
    parsed_ingredients = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


with app.app_context():
    db.create_all()

# --- Ingredient recognition ----------------------------------------------
# A curated pantry vocabulary. OCR output is noisy (stray characters,
# packaging text, price tags), so we score raw OCR tokens against this
# list rather than trusting every word Tesseract returns.
KNOWN_INGREDIENTS = [
    "chicken", "beef", "pork", "egg", "eggs", "milk", "butter", "cheese",
    "garlic", "onion", "tomato", "tomatoes", "potato", "potatoes", "carrot",
    "carrots", "broccoli", "spinach", "lettuce", "cabbage", "rice", "pasta",
    "noodles", "flour", "sugar", "salt", "pepper", "olive oil", "oil",
    "soy sauce", "vinegar", "lemon", "lime", "ginger", "chili", "basil",
    "cilantro", "parsley", "mushroom", "mushrooms", "shrimp", "fish",
    "tofu", "beans", "corn", "peas", "bell pepper", "cucumber", "yogurt",
    "cream", "bacon", "sausage", "bread", "coconut milk", "honey", "apple",
    "banana", "avocado", "spring onion", "scallion", "chicken breast",
    "ground beef", "salmon", "tuna", "cheddar", "mozzarella", "parmesan",
]


def parse_ingredients_from_text(raw_text: str):
    """Match OCR text against known ingredients (whole-word, case-insensitive)."""
    text = raw_text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    found = []
    for item in KNOWN_INGREDIENTS:
        pattern = r"\b" + re.escape(item) + r"\b"
        if re.search(pattern, text):
            # avoid adding both "chicken" and "chicken breast" duplicately
            if not any(item in f or f in item for f in found):
                found.append(item)
            elif item not in found:
                found.append(item)
    # de-dupe while preserving order
    seen = set()
    ordered = []
    for f in found:
        if f not in seen:
            seen.add(f)
            ordered.append(f)
    return ordered


# --- Recipe API (TheMealDB — free, no key required) -----------------------
MEALDB_FILTER = "https://www.themealdb.com/api/json/v1/1/filter.php"
MEALDB_LOOKUP = "https://www.themealdb.com/api/json/v1/1/lookup.php"


def search_recipes_by_ingredients(ingredients):
    """
    TheMealDB's free tier only supports filtering by ONE ingredient per call.
    We query each ingredient separately, then rank recipes by how many of
    the user's ingredients they actually contain (via a full lookup).
    """
    if not ingredients:
        return []

    candidate_ids = {}
    for ing in ingredients[:5]:  # cap calls for a snappy demo
        try:
            resp = requests.get(MEALDB_FILTER, params={"i": ing}, timeout=6)
            resp.raise_for_status()
            meals = resp.json().get("meals") or []
        except requests.RequestException:
            continue
        for m in meals:
            candidate_ids.setdefault(m["idMeal"], m)

    if not candidate_ids:
        return []

    # Rank top candidates by ingredient overlap using full recipe detail
    scored = []
    for meal_id in list(candidate_ids.keys())[:12]:
        try:
            resp = requests.get(MEALDB_LOOKUP, params={"i": meal_id}, timeout=6)
            resp.raise_for_status()
            meal = (resp.json().get("meals") or [None])[0]
        except requests.RequestException:
            meal = None
        if not meal:
            continue

        meal_ingredients = []
        for i in range(1, 21):
            val = meal.get(f"strIngredient{i}")
            if val and val.strip():
                meal_ingredients.append(val.strip().lower())

        overlap = [
            ing for ing in ingredients
            if any(ing in mi or mi in ing for mi in meal_ingredients)
        ]

        scored.append({
            "meal_id": meal["idMeal"],
            "title": meal["strMeal"],
            "thumbnail": meal["strMealThumb"],
            "category": meal.get("strCategory", ""),
            "area": meal.get("strArea", ""),
            "source_url": meal.get("strSource") or f"https://www.themealdb.com/meal/{meal['idMeal']}",
            "instructions": (meal.get("strInstructions") or "")[:280],
            "matched_ingredients": overlap,
            "match_count": len(overlap),
        })

    scored.sort(key=lambda r: r["match_count"], reverse=True)
    return scored


# --- Routes ---------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/scan", methods=["POST"])
def scan_ingredients():
    if "photo" not in request.files:
        return jsonify({"error": "No photo uploaded."}), 400

    photo = request.files["photo"]
    if photo.filename == "":
        return jsonify({"error": "No photo selected."}), 400

    filename = f"{int(time.time())}_{photo.filename}"
    save_path = os.path.join(UPLOAD_DIR, filename)
    photo.save(save_path)

    try:
        img = Image.open(save_path)
        img = ImageOps.exif_transpose(img)
        img = img.convert("L")  # grayscale improves OCR accuracy
        raw_text = pytesseract.image_to_string(img)
    except Exception as exc:
        return jsonify({"error": f"Could not read image: {exc}"}), 500

    parsed = parse_ingredients_from_text(raw_text)

    log = ScanLog(raw_text=raw_text.strip(), parsed_ingredients=", ".join(parsed))
    db.session.add(log)
    db.session.commit()

    return jsonify({
        "raw_text": raw_text.strip(),
        "ingredients": parsed,
        "image_url": f"/static/uploads/{filename}",
    })


@app.route("/api/recipes", methods=["POST"])
def get_recipes():
    data = request.get_json(force=True)
    ingredients = [i.strip().lower() for i in data.get("ingredients", []) if i.strip()]
    if not ingredients:
        return jsonify({"error": "No ingredients provided."}), 400
    recipes = search_recipes_by_ingredients(ingredients)
    return jsonify({"recipes": recipes})


@app.route("/api/cookbook", methods=["GET"])
def list_cookbook():
    recipes = SavedRecipe.query.order_by(SavedRecipe.saved_at.desc()).all()
    return jsonify({"recipes": [r.to_dict() for r in recipes]})


@app.route("/api/cookbook", methods=["POST"])
def save_to_cookbook():
    data = request.get_json(force=True)
    existing = SavedRecipe.query.filter_by(meal_id=data.get("meal_id")).first()
    if existing:
        return jsonify({"message": "Already in your cookbook.", "recipe": existing.to_dict()})

    recipe = SavedRecipe(
        meal_id=data.get("meal_id"),
        title=data.get("title"),
        thumbnail=data.get("thumbnail"),
        source_url=data.get("source_url"),
        matched_ingredients=", ".join(data.get("matched_ingredients", [])),
    )
    db.session.add(recipe)
    db.session.commit()
    return jsonify({"message": "Saved to your cookbook.", "recipe": recipe.to_dict()})


@app.route("/api/cookbook/<int:recipe_id>", methods=["DELETE"])
def delete_from_cookbook(recipe_id):
    recipe = SavedRecipe.query.get_or_404(recipe_id)
    db.session.delete(recipe)
    db.session.commit()
    return jsonify({"message": "Removed."})


if __name__ == "__main__":
    # Render (and most cloud hosts) inject the port to bind via $PORT.
    # Locally this falls back to 5000, same as before.
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "true").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
