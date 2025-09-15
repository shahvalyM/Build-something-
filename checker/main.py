# checker/main.py (exempel med CORS)
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import hashlib

from database import SessionLocal, engine, Base
import models

# Create DB tables if missing
Base.metadata.create_all(bind=engine)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Checker (DB backed)")

# Konfigurera vilken origin som får anropa API:t
origins = [
    "http://localhost:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

class CheckRequest(BaseModel):
    password: str

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health(db: Session = Depends(get_db)):
    cnt = db.query(models.LeakedPassword).count()
    return {"status": "ok", "leaked_count": cnt}

@app.post("/check")
def check(req: CheckRequest, db: Session = Depends(get_db)):
    pwd = req.password
    if not pwd:
        raise HTTPException(status_code=400, detail="Password required")
    sha1 = hashlib.sha1(pwd.encode("utf-8")).hexdigest().upper()
    found = db.query(models.LeakedPassword).filter(models.LeakedPassword.sha1 == sha1).first()
    return {"leaked": bool(found)}
