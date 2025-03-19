from enum import Enum as PyEnum
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, Integer, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import re  

app = FastAPI()

DATABASE_URL = "sqlite:///./antique_clocks.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MechanismType(str, PyEnum):
    MECHANICAL = "MECHANICAL"
    QUARTZ = "QUARTZ"
    PENDULUM = "PENDULUM"
    SPRING_DRIVEN = "SPRING_DRIVEN"

class ClockDB(Base):
    __tablename__ = "clocks"
    serial_number = Column(String, primary_key=True, index=True)
    brand = Column(String, nullable=False)
    model = Column(String, nullable=False)
    manufacture_year = Column(Integer, nullable=False)
    mechanism = Column(SQLAlchemyEnum(MechanismType), nullable=False)
    material = Column(String, nullable=False)
    condition_grade = Column(Integer, nullable=False)  # Оценка состояния от 1 до 10

Base.metadata.create_all(bind=engine)

class Clock(BaseModel):
    serial_number: str
    brand: str
    model: str
    manufacture_year: int
    mechanism: MechanismType
    material: str
    condition_grade: int

    class Config:
        orm_mode = True  # Поддержка преобразования из SQLAlchemy объектов

    @validator("serial_number")
    def validator_serial_number(cls, serial_number):
        pattern = r'^[A-Z0-9]{6,12}$'
        if not re.match(pattern, serial_number):
            raise ValueError("Серийный номер должен содержать от 6 до 12 букв и цифр")
        return serial_number

    @validator("brand")
    def validator_brand(cls, brand):
        if len(brand.strip()) < 2:
            raise ValueError("Бренд должен содержать минимум 2 символа")
        return brand
    
    @validator("model")
    def validator_model(cls, model):
        if len(model.strip()) < 2:
            raise ValueError("Модель должна содержать минимум 2 символа")
        return model
    
    @validator("manufacture_year")
    def validator_year(cls, manufacture_year):
        current_year = 2025  # Фиксируем текущий год для примера
        if manufacture_year < 1600 or manufacture_year > current_year:
            raise ValueError(f"Год изготовления должен быть между 1600 и {current_year}")
        return manufacture_year
    
    @validator("material")
    def validator_material(cls, material):
        if len(material.strip()) < 3:
            raise ValueError("Материал должен содержать минимум 3 символа")
        return material
    
    @validator("condition_grade")
    def validator_condition(cls, condition_grade):
        if condition_grade < 1 or condition_grade > 10:
            raise ValueError("Оценка состояния должна быть от 1 до 10")
        return condition_grade

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/clocks")
def get_clocks(
    serial_number: str = None,
    brand: str = None,
    mechanism: MechanismType = None,
    db: Session = Depends(get_db)
):
    query = db.query(ClockDB)
    if serial_number:
        query = query.filter(ClockDB.serial_number == serial_number)
    if brand:
        query = query.filter(ClockDB.brand == brand)
    if mechanism:
        query = query.filter(ClockDB.mechanism == mechanism)
    results = query.all()
    results_dict = [Clock.from_orm(r).dict() for r in results]
    return {
        "message": f"Найдено {len(results)} часов",
        "data": results_dict
    }

@app.post("/clocks")
def create_clock(clock: Clock, db: Session = Depends(get_db)):
    db_clock = db.query(ClockDB).filter(ClockDB.serial_number == clock.serial_number).first()
    if db_clock:
        raise HTTPException(status_code=400, detail="Часы с таким серийным номером уже существуют")
    db_clock = ClockDB(**clock.dict())
    db.add(db_clock)
    db.commit()
    db.refresh(db_clock)
    return {
        "message": "Часы успешно добавлены в коллекцию",
        "data": Clock.from_orm(db_clock).dict()
    }

@app.put("/clocks/{serial_number}")
def update_clock(serial_number: str, clock: Clock, db: Session = Depends(get_db)):
    if serial_number != clock.serial_number:
        raise HTTPException(status_code=400, detail="Серийный номер в пути и теле запроса не совпадают")
    db_clock = db.query(ClockDB).filter(ClockDB.serial_number == serial_number).first()
    if not db_clock:
        raise HTTPException(status_code=404, detail="Часы не найдены")
    for key, value in clock.dict().items():
        setattr(db_clock, key, value)
    db.commit()
    db.refresh(db_clock)
    return {
        "message": "Информация о часах успешно обновлена",
        "data": Clock.from_orm(db_clock).dict()
    }

@app.delete("/clocks/{serial_number}")
def delete_clock(serial_number: str, db: Session = Depends(get_db)):
    db_clock = db.query(ClockDB).filter(ClockDB.serial_number == serial_number).first()
    if not db_clock:
        raise HTTPException(status_code=404, detail="Часы не найдены")
    db.delete(db_clock)
    db.commit()
    return {
        "message": "Часы успешно удалены из коллекции",
        "data": {"serial_number": serial_number}
    }
