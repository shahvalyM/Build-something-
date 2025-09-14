from pydantic import BaseModel

class TaskCreate(BaseModel):
    title: str

class TaskOut(BaseModel):
    id: str
    title: str

    class Config:
        orm_mode = True
