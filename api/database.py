# ~/todo-micro/api/database.py
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:example@db:5432/tododb"
)

# create SQLAlchemy engine
# pool_pre_ping hjälper med återkoppling vid nätverksproblem
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# create a Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def wait_for_db(max_retries=10, delay=2):
    retries = 0
    while True:
        try:
            # Försök att öppna en connection och exekvera ett text-skript
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return
        except OperationalError:
            retries += 1
            if retries > max_retries:
                # Om DB aldrig blir redo så bubbla upp felet
                raise
            print(f"Database not ready, retry {retries}/{max_retries} — waiting {delay}s...")
            time.sleep(delay)

def init_db():
    # Vänta tills DB accepterar anslutningar och skapa tabeller
    wait_for_db()
    Base.metadata.create_all(bind=engine)
