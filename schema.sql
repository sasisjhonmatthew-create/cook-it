-- Cook It — MySQL schema
-- Mirrors the SQLAlchemy models in app.py. Use this if you swap the
-- prototype's SQLite database for real MySQL (see README.md).

CREATE DATABASE IF NOT EXISTS cookit CHARACTER SET utf8mb4;
USE cookit;

CREATE TABLE IF NOT EXISTS saved_recipes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    meal_id VARCHAR(32) NOT NULL,
    title VARCHAR(255) NOT NULL,
    thumbnail VARCHAR(512),
    source_url VARCHAR(512),
    matched_ingredients VARCHAR(512),
    saved_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_meal (meal_id)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS scan_log (
    id INT AUTO_INCREMENT PRIMARY KEY,
    raw_text TEXT,
    parsed_ingredients VARCHAR(512),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- Optional next step: a `users` table + foreign key on saved_recipes.user_id
-- to support multiple accounts, once you're ready to add login.
