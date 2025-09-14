# ~/todo-micro/api/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import uuid

import models
import schemas
from database import SessionLocal, engine, init_db

# init DB models/tables at startup (will be harmless if already created)
init_db()

app = FastAPI(title="Todo API (with Postgres)")

# CORS (development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/tasks", response_model=list[schemas.TaskOut])
def list_tasks(db: Session = Depends(get_db)):
    return db.query(models.Task).all()

@app.post("/tasks", response_model=schemas.TaskOut)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    tid = str(uuid.uuid4())
    db_task = models.Task(id=tid, title=task.title)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    t = db.query(models.Task).filter(models.Task.id == task_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(t)
    db.commit()
    return {"deleted": task_id}
