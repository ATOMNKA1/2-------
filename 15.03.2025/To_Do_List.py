from enum import Enum as PyEnum
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, Integer, Enum as SQLAlchemyEnum, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

app = FastAPI()

DATABASE_URL = "sqlite:///./tasks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class TaskStatus(str, PyEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"

class TaskPriority(str, PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class TaskDB(Base):
    __tablename__ = "tasks"
    task_id = Column(String, primary_key=True, index=True)
    status = Column(SQLAlchemyEnum(TaskStatus), nullable=False)
    description = Column(String, nullable=False)
    priority = Column(SQLAlchemyEnum(TaskPriority), nullable=False)
    created_at = Column(DateTime, nullable=False)

Base.metadata.create_all(bind=engine)

class Task(BaseModel):
    task_id: str
    status: TaskStatus
    description: str
    priority: TaskPriority
    created_at: datetime

    @validator("task_id")
    def validate_task_id(cls, task_id):
        if not task_id.isalnum():
            raise ValueError("ID задачи должен состоять только из букв и цифр")
        if len(task_id) < 3:
            raise ValueError("ID задачи должен быть длиной не менее 3 символов")
        return task_id

    @validator("description")
    def validate_description(cls, description):
        if len(description.strip()) < 5:
            raise ValueError("Описание задачи должно быть длиной не менее 5 символов")
        return description

    @validator("created_at")
    def validate_created_at(cls, created_at):
        if created_at > datetime.now():
            raise ValueError("Дата создания не может быть в будущем")
        return created_at

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/tasks")
def get_tasks(
    task_id: str = None,
    status: str = None,
    priority: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(TaskDB)
    if task_id:
        query = query.filter(TaskDB.task_id == task_id)
    if status:
        query = query.filter(TaskDB.status == status)
    if priority:
        query = query.filter(TaskDB.priority == priority)
    return query.all()

@app.post("/tasks")
def create_task(task: Task, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.task_id == task.task_id).first()
    if db_task:
        raise HTTPException(status_code=400, detail="Задача с таким ID уже существует")
    db_task = TaskDB(**task.dict())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return {"message": "Задача успешно создана"}

@app.put("/tasks/{task_id}")
def update_task(task_id: str, task: Task, db: Session = Depends(get_db)):
    if task_id != task.task_id:
        raise HTTPException(status_code=400, detail="ID задачи в пути и теле запроса не совпадают")
    db_task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    for key, value in task.dict().items():
        setattr(db_task, key, value)
    db.commit()
    db.refresh(db_task)
    return {"message": "Задача успешно обновлена"}

@app.delete("/tasks/{task_id}")
def delete_task(task_id: str, db: Session = Depends(get_db)):
    db_task = db.query(TaskDB).filter(TaskDB.task_id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
    db.delete(db_task)
    db.commit()
    return {"message": "Задача успешно удалена"}