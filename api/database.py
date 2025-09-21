# ~/todo-micro/api/database.py
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

def build_database_url():
    # Läs env-vars med vettiga defaults för Kubernetes
    host = os.getenv("DB_HOST", os.getenv("DATABASE_HOST", "postgres"))
    port = os.getenv("DB_PORT", os.getenv("DATABASE_PORT", "5432"))
    user = os.getenv("POSTGRES_USER", os.getenv("DB_USER", "postgres"))
    password = os.getenv("POSTGRES_PASSWORD", os.getenv("DB_PASSWORD", "example"))
    dbname = os.getenv("POSTGRES_DB", os.getenv("DB_NAME", "tododb"))
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"

# Använd byggd URL (men tillåt override via DATABASE_URL om du vill)
DATABASE_URL = os.getenv("DATABASE_URL", build_database_url())

# create SQLAlchemy engine (pool_pre_ping hjälper vid nätverksproblem)
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def wait_for_db(max_retries=20, delay=3):
    retries = 0
    while True:
        try:
            # Försök att öppna en connection och exekvera ett litet "ping"
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("[wait_for_db] Database reachable")
            return
        except OperationalError as e:
            retries += 1
            if retries > max_retries:
                print(f"[wait_for_db] Giving up after {retries} retries: {e}")
                raise
            print(f"[wait_for_db] Database not ready, retry {retries}/{max_retries} — waiting {delay}s... ({e})")
            time.sleep(delay)

def init_db():
    # Vänta tills DB accepterar anslutningar och skapa tabeller
    wait_for_db()
    Base.metadata.create_all(bind=engine)
