# api/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

from typing import List
import uuid

app = FastAPI(title="Todo API (training)")

# --- Lägg till detta block direkt efter app = FastAPI(...) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://127.0.0.1:8080"],  # tillåt frontend-origin(s)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ------------------------------------------------------------

class Task(BaseModel):
    id: str | None = None
    title: str

# enkel in-memory store för träning
tasks: dict[str, Task] = {}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/tasks", response_model=List[Task])
async def list_tasks():
    return list(tasks.values())

@app.post("/tasks", response_model=Task)
async def create_task(t: Task):
    tid = str(uuid.uuid4())
    t.id = tid
    tasks[tid] = t
    return t

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    if task_id in tasks:
        del tasks[task_id]
        return {"deleted": task_id}
    raise HTTPException(status_code=404, detail="Task not found")
