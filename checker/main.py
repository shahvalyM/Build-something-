# checker/main.py
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
import hashlib

from database import SessionLocal, engine, Base
import models

# Ensure models are created (safe-guard; uses engine)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Checker (DB backed)")

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
