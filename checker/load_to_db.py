# checker/load_to_db.py
import os
from sqlalchemy import create_engine, text
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:example@db:5432/tododb")
engine = create_engine(DATABASE_URL)

HASH_FILE = Path("checker/leaked_password_hashes.txt")

def ensure_table():
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS leaked_passwords (
            sha1 TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        );
        """))

def load_hashes():
    if not HASH_FILE.exists():
        print("No hash file:", HASH_FILE)
        return
    lines = [l.strip().upper() for l in HASH_FILE.read_text().splitlines() if l.strip()]
    inserted = 0
    with engine.begin() as conn:
        for h in lines:
            conn.execute(text("INSERT INTO leaked_passwords (sha1) VALUES (:sha) ON CONFLICT (sha1) DO NOTHING;"), {"sha": h})
            inserted += 1
    print("Attempted insert of", inserted, "hashes")

if __name__ == "__main__":
    ensure_table()
    load_hashes()
