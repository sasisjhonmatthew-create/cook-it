# Cook It — AI-Powered Recipe Discovery & Digital Cookbook

A working prototype: photograph your ingredients, get real recipe matches, save the ones you like.

## How it works

1. **Scan** — upload/capture a photo (grocery items, a receipt, a handwritten list).
2. **OCR** — the backend runs Tesseract on the image and extracts raw text.
3. **Ingredient matching** — the raw OCR text is matched against a curated pantry
   vocabulary (`KNOWN_INGREDIENTS` in `app.py`), since OCR output is noisy and
   includes packaging text, prices, etc. Results appear as an editable "ticket"
   so you can fix anything the scan missed before searching.
4. **Recipe search** — confirmed ingredients are sent to
   [TheMealDB](https://www.themealdb.com/api.php) (free, no API key needed),
   and results are ranked by how many of your ingredients each recipe actually uses.
5. **Cookbook** — save recipes you like; they're stored in a local database and
   listed on the Cookbook tab.

## Setup

### 1. Install Tesseract (the OCR engine)

- **macOS:** `brew install tesseract`
- **Ubuntu/Debian:** `sudo apt-get install tesseract-ocr`
- **Windows:** [installer here](https://github.com/UB-Mannheim/tesseract/wiki) — after installing, set the path in `app.py` if needed:
  ```python
  pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
  ```

### 2. Install Python dependencies

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run it

```bash
python app.py
```

Open **http://localhost:5000**. A SQLite database (`cookit.db`) is created automatically on first run — no setup needed.

## Deploying to Render (free tier)

This gives you a public URL — same app, works from any phone's browser, no install needed on the phone's end.

### 1. Push the project to GitHub
Render deploys from a Git repo, so this needs to live on GitHub first.
- Create a new repo on [github.com](https://github.com) (public or private, either works)
- In the project folder:
  ```
  git init
  git add .
  git commit -m "Cook It prototype"
  git branch -M main
  git remote add origin https://github.com/<your-username>/<your-repo>.git
  git push -u origin main
  ```

### 2. Create the Render service
- Sign up at [render.com](https://render.com) (free, GitHub login works)
- Click **New +** → **Web Service**
- Connect your GitHub repo
- Render detects the `Dockerfile` automatically — leave environment as **Docker**
- Instance type: **Free**
- Click **Create Web Service**

First deploy takes a few minutes (it's installing Tesseract inside the container). When it's done, Render gives you a URL like `https://cook-it-xxxx.onrender.com` — that's your public app. Open it on your phone's browser and it works exactly like on desktop; tapping "Choose photo" opens the phone's camera directly.

### About the free tier
- The service **spins down after 15 minutes of no traffic**, and the first request after that takes 30–60 seconds to wake back up. That's normal for free hosting, not a bug — worth mentioning if you're demoing live so nobody thinks it's broken.
- The free tier's disk is **not persistent** — anything written to `cookit.db` or `static/uploads/` gets wiped whenever the service restarts or redeploys. For a class demo this is usually fine, but saved cookbook entries won't survive a redeploy.
- If you need saved recipes to persist long-term, the fix is an external database — see the MySQL section below and set `COOKIT_DB_URI` as an environment variable in Render's dashboard (Environment tab) instead of in your code, so your DB password never ends up in GitHub.

## Switching to real MySQL

The prototype uses SQLite so it runs with zero config. To use MySQL instead (as in the original spec):

1. `pip install pymysql`
2. Run `schema.sql` against your MySQL server: `mysql -u root -p < schema.sql`
3. Set the environment variable before running the app:
   ```bash
   export COOKIT_DB_URI="mysql+pymysql://username:password@localhost/cookit"
   python app.py
   ```

The SQLAlchemy models in `app.py` match `schema.sql` exactly, so no code changes are needed.

## Notes on the OCR approach

Reading printed text off a label or receipt is a solved problem for Tesseract.
Recognizing loose ingredients from a photo of an open fridge (no text at all) is
a much harder computer-vision problem — that's object detection/classification,
not OCR, and would need a trained model (e.g. a fine-tuned YOLO or a vision API
like Google Cloud Vision's label detection). This prototype is scoped to
**text-bearing sources**: grocery labels, receipts, or a handwritten/typed list.
That's a reasonable and honest scope for a school project — worth stating
explicitly in your documentation so it reads as a deliberate design decision,
not a limitation you missed.

## Project structure

```
cook-it/
├── app.py              # Flask backend — OCR, ingredient parsing, recipe API, DB
├── schema.sql           # MySQL schema (mirrors the SQLAlchemy models)
├── requirements.txt
├── templates/
│   └── index.html
└── static/
    ├── css/style.css
    ├── js/main.js
    └── uploads/          # scanned photos land here
```

## Ideas for extending this further

- Swap the keyword-matching ingredient parser for a small NER model or an LLM
  call, so it can catch ingredients not in the curated list.
- Add user accounts so the cookbook is per-person, not global.
- Track "ingredients used" over time to actually measure food waste reduction —
  that's the strongest part of your value proposition, worth surfacing as a
  simple stat on the cookbook page (e.g. "12 recipes made from what you already had").
