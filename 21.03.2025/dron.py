from enum import Enum as PyEnum
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SQLAlchemyEnum, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import re  

app = FastAPI()

DATABASE_URL = "sqlite:///./drone_flights.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class CargoType(str, PyEnum):
    MEDICAL = "MEDICAL"
    FOOD = "FOOD"
    ELECTRONICS = "ELECTRONICS"
    DOCUMENTS = "DOCUMENTS"

class FlightDB(Base):
    __tablename__ = "flights"
    flight_id = Column(String, primary_key=True, index=True)
    drone_id = Column(String, nullable=False)
    departure_point = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    departure_time = Column(DateTime, nullable=False)
    cargo_type = Column(SQLAlchemyEnum(CargoType), nullable=False)
    cargo_weight_kg = Column(Float, nullable=False)
    max_altitude_m = Column(Integer, nullable=False)

Base.metadata.create_all(bind=engine)

class Flight(BaseModel):
    flight_id: str
    drone_id: str
    departure_point: str
    destination: str
    departure_time: datetime
    cargo_type: CargoType
    cargo_weight_kg: float
    max_altitude_m: int

    @validator("flight_id")
    def validator_flight_id(cls, flight_id):
        pattern = r'^FL-\d{5}-[A-Z]$'
        if not re.match(pattern, flight_id):
            raise ValueError("ID полета должен иметь формат FL-XXXXX-Z (FL, дефис, 5 цифр, дефис, буква)")
        return flight_id

    @validator("drone_id")
    def validator_drone_id(cls, drone_id):
        pattern = r'^DRN-\d{4}$'
        if not re.match(pattern, drone_id):
            raise ValueError("ID дрона должен иметь формат DRN-XXXX (DRN и 4 цифры)")
        return drone_id
    
    @validator("departure_point")
    def validator_departure_point(cls, departure_point):
        if len(departure_point.strip()) < 3:
            raise ValueError("Пункт отправления должен содержать минимум 3 символа")
        return departure_point
    
    @validator("destination")
    def validator_destination(cls, destination):
        if len(destination.strip()) < 3:
            raise ValueError("Пункт назначения должен содержать минимум 3 символа")
        return destination
    
    @validator("departure_time")
    def validator_departure_time(cls, departure_time):
        current_time = datetime.now()
        if departure_time < current_time:
            raise ValueError("Время вылета не может быть в прошлом")
        return departure_time
    
    @validator("cargo_weight_kg")
    def validator_cargo_weight(cls, cargo_weight_kg):
        if cargo_weight_kg <= 0 or cargo_weight_kg > 50:
            raise ValueError("Вес груза должен быть от 0.1 до 50 кг")
        return cargo_weight_kg
    
    @validator("max_altitude_m")
    def validator_altitude(cls, max_altitude_m):
        if max_altitude_m < 10 or max_altitude_m > 400:
            raise ValueError("Максимальная высота должна быть от 10 до 400 метров")
        return max_altitude_m

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/flights")
def get_flights(
    flight_id: str = None,
    drone_id: str = None,
    cargo_type: CargoType = None,
    db: Session = Depends(get_db)
):
    query = db.query(FlightDB)
    if flight_id:
        query = query.filter(FlightDB.flight_id == flight_id)
    if drone_id:
        query = query.filter(FlightDB.drone_id == drone_id)
    if cargo_type:
        query = query.filter(FlightDB.cargo_type == cargo_type)
    results = query.all()
    results_dict = [{
        "flight_id": r.flight_id,
        "drone_id": r.drone_id,
        "departure_point": r.departure_point,
        "destination": r.destination,
        "departure_time": r.departure_time.isoformat(),
        "cargo_type": r.cargo_type,
        "cargo_weight_kg": r.cargo_weight_kg,
        "max_altitude_m": r.max_altitude_m
    } for r in results]
    return {
        "message": f"Найдено {len(results)} полетов",
        "data": results_dict
    }

@app.post("/flights")
def create_flight(flight: Flight, db: Session = Depends(get_db)):
    db_flight = db.query(FlightDB).filter(FlightDB.flight_id == flight.flight_id).first()
    if db_flight:
        raise HTTPException(status_code=400, detail="Полет с таким ID уже существует")
    db_flight = FlightDB(**flight.dict())
    db.add(db_flight)
    db.commit()
    db.refresh(db_flight)
    return {
        "message": "Полет успешно запланирован",
        "data": flight.dict()
    }

@app.put("/flights/{flight_id}")
def update_flight(flight_id: str, flight: Flight, db: Session = Depends(get_db)):
    if flight_id != flight.flight_id:
        raise HTTPException(status_code=400, detail="ID полета в пути и теле запроса не совпадают")
    db_flight = db.query(FlightDB).filter(FlightDB.flight_id == flight_id).first()
    if not db_flight:
        raise HTTPException(status_code=404, detail="Полет не найден")
    for key, value in flight.dict().items():
        setattr(db_flight, key, value)
    db.commit()
    db.refresh(db_flight)
    return {
        "message": "Информация о полете успешно обновлена",
        "data": flight.dict()
    }

@app.delete("/flights/{flight_id}")
def delete_flight(flight_id: str, db: Session = Depends(get_db)):
    db_flight = db.query(FlightDB).filter(FlightDB.flight_id == flight_id).first()
    if not db_flight:
        raise HTTPException(status_code=404, detail="Полет не найден")
    db.delete(db_flight)
    db.commit()
    return {
        "message": "Полет успешно отменен",
        "data": {"flight_id": flight_id}
    }