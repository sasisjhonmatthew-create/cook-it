# Cook It — deployment image for Render
FROM python:3.11-slim

# Tesseract is a system-level OCR engine, not a Python package —
# this is why we need Docker instead of Render's plain Python runtime.
RUN apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render sets $PORT at runtime; gunicorn binds to it here.
CMD gunicorn app:app --bind 0.0.0.0:$PORT --timeout 120
