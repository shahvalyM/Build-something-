# Loads password hashes from 'leaked_password_hashes.txt' into PostgreSQL.
# Used by the load-hashes Kubernetes Job during initialization.

import os
from sqlalchemy import create_engine, text
from pathlib import Path
import sys

# Build DB URL from environment (supports DATABASE_URL or individual POSTGRES_* vars)
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    user = os.getenv("POSTGRES_USER")
    pw = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST", "postgres")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB")
    if not all([user, pw, db]):
        print("Missing DB credentials: POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB", file=sys.stderr)
        sys.exit(2)
    DATABASE_URL = f"postgresql://{user}:{pw}@{host}:{port}/{db}"

print("Using DATABASE_URL:", ("<hidden>" if "@" in DATABASE_URL else DATABASE_URL))

engine = create_engine(DATABASE_URL)
HASH_FILE = Path("leaked_password_hashes.txt")

def ensure_table():
    """Creates leaked_passwords table if it doesn't exist."""
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS leaked_passwords (
            sha1 TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        );
        """))

def load_hashes():
    """Inserts hashes from file into DB (ignores duplicates)."""
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