from enum import Enum as PyEnum
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime

app = FastAPI()

DATABASE_URL = "sqlite:///./events.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class EventType(str, PyEnum):
    CONFERENCE = "CONFERENCE"
    WORKSHOP = "WORKSHOP"
    PARTY = "PARTY"
    SEMINAR = "SEMINAR"

class EventDB(Base):
    __tablename__ = "events"
    event_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    date = Column(DateTime, nullable=False)
    location = Column(String, nullable=False)
    event_type = Column(SQLAlchemyEnum(EventType), nullable=False)

Base.metadata.create_all(bind=engine)

class Event(BaseModel):
    event_id: str
    name: str
    date: datetime
    location: str
    event_type: EventType

    @validator("event_id")
    def validate_event_id(cls, event_id):
        if not event_id.isalnum():
            raise ValueError("ID события должен состоять только из букв и цифр")
        if len(event_id) < 4:
            raise ValueError("ID события должен быть длиной не менее 4 символов")
        return event_id

    @validator("name")
    def validate_name(cls, name):
        if len(name.strip()) < 3:
            raise ValueError("Название события должно быть длиной не менее 3 символов")
        return name

    @validator("date")
    def validate_date(cls, date):
        if date < datetime.now():
            raise ValueError("Дата события не может быть в прошлом")
        return date

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/events")
def get_events(
    event_id: str = None,
    name: str = None,
    location: str = None,
    event_type: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(EventDB)
    if event_id:
        query = query.filter(EventDB.event_id == event_id)
    if name:
        query = query.filter(EventDB.name == name)
    if location:
        query = query.filter(EventDB.location == location)
    if event_type:
        query = query.filter(EventDB.event_type == event_type)
    return query.all()

@app.post("/events")
def create_event(event: Event, db: Session = Depends(get_db)):
    db_event = db.query(EventDB).filter(EventDB.event_id == event.event_id).first()
    if db_event:
        raise HTTPException(status_code=400, detail="Событие с таким ID уже существует")
    db_event = EventDB(**event.dict())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return {"message": "Событие успешно создано"}

@app.put("/events/{event_id}")
def update_event(event_id: str, event: Event, db: Session = Depends(get_db)):
    if event_id != event.event_id:
        raise HTTPException(status_code=400, detail="ID события в пути и теле запроса не совпадают")
    db_event = db.query(EventDB).filter(EventDB.event_id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    for key, value in event.dict().items():
        setattr(db_event, key, value)
    db.commit()
    db.refresh(db_event)
    return {"message": "Событие успешно обновлено"}

@app.delete("/events/{event_id}")
def delete_event(event_id: str, db: Session = Depends(get_db)):
    db_event = db.query(EventDB).filter(EventDB.event_id == event_id).first()
    if not db_event:
        raise HTTPException(status_code=404, detail="Событие не найдено")
    db.delete(db_event)
    db.commit()
    return {"message": "Событие успешно удалено"}