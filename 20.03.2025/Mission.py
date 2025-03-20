from enum import Enum as PyEnum
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import re  

app = FastAPI()

DATABASE_URL = "sqlite:///./space_missions.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MissionType(str, PyEnum):
    ORBITAL = "ORBITAL"
    LUNAR = "LUNAR"
    MARS = "MARS"
    DEEP_SPACE = "DEEP_SPACE"

class MissionDB(Base):
    __tablename__ = "missions"
    mission_code = Column(String, primary_key=True, index=True)
    mission_name = Column(String, nullable=False)
    launch_site = Column(String, nullable=False)
    launch_date = Column(DateTime, nullable=False)
    mission_type = Column(SQLAlchemyEnum(MissionType), nullable=False)
    spacecraft = Column(String, nullable=False)
    crew_size = Column(Integer, nullable=False)

Base.metadata.create_all(bind=engine)

class Mission(BaseModel):
    mission_code: str
    mission_name: str
    launch_site: str
    launch_date: datetime
    mission_type: MissionType
    spacecraft: str
    crew_size: int

    @validator("mission_code")
    def validator_mission_code(cls, mission_code):
        pattern = r'^[A-Z]{2}-\d{4}-[A-Z]$'
        if not re.match(pattern, mission_code):
            raise ValueError("Код миссии должен иметь формат XX-YYYY-Z (две буквы, дефис, четыре цифры, дефис, буква)")
        return mission_code

    @validator("mission_name")
    def validator_mission_name(cls, mission_name):
        if len(mission_name.strip()) < 3:
            raise ValueError("Название миссии должно содержать минимум 3 символа")
        return mission_name
    
    @validator("launch_site")
    def validator_launch_site(cls, launch_site):
        if len(launch_site.strip()) < 5:
            raise ValueError("Место запуска должно содержать минимум 5 символов")
        return launch_site
    
    @validator("launch_date")
    def validator_launch_date(cls, launch_date):
        current_date = datetime.now()
        if launch_date < current_date:
            raise ValueError("Дата запуска не может быть в прошлом")
        return launch_date
    
    @validator("spacecraft")
    def validator_spacecraft(cls, spacecraft):
        if len(spacecraft.strip()) < 3:
            raise ValueError("Название космического корабля должно содержать минимум 3 символа")
        return spacecraft
    
    @validator("crew_size")
    def validator_crew_size(cls, crew_size):
        if crew_size < 0:
            raise ValueError("Размер экипажа не может быть отрицательным")
        return crew_size

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/missions")
def get_missions(
    mission_code: str = None,
    mission_type: MissionType = None,
    launch_site: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(MissionDB)
    if mission_code:
        query = query.filter(MissionDB.mission_code == mission_code)
    if mission_type:
        query = query.filter(MissionDB.mission_type == mission_type)
    if launch_site:
        query = query.filter(MissionDB.launch_site == launch_site)
    results = query.all()
    # Преобразование вручную в список словарей
    results_dict = [{
        "mission_code": r.mission_code,
        "mission_name": r.mission_name,
        "launch_site": r.launch_site,
        "launch_date": r.launch_date.isoformat(),
        "mission_type": r.mission_type,
        "spacecraft": r.spacecraft,
        "crew_size": r.crew_size
    } for r in results]
    return {
        "message": f"Найдено {len(results)} миссий",
        "data": results_dict
    }

@app.post("/missions")
def create_mission(mission: Mission, db: Session = Depends(get_db)):
    db_mission = db.query(MissionDB).filter(MissionDB.mission_code == mission.mission_code).first()
    if db_mission:
        raise HTTPException(status_code=400, detail="Миссия с таким кодом уже существует")
    db_mission = MissionDB(**mission.dict())
    db.add(db_mission)
    db.commit()
    db.refresh(db_mission)
    return {
        "message": "Миссия успешно запланирована",
        "data": mission.dict()
    }

@app.put("/missions/{mission_code}")
def update_mission(mission_code: str, mission: Mission, db: Session = Depends(get_db)):
    if mission_code != mission.mission_code:
        raise HTTPException(status_code=400, detail="Код миссии в пути и теле запроса не совпадают")
    db_mission = db.query(MissionDB).filter(MissionDB.mission_code == mission_code).first()
    if not db_mission:
        raise HTTPException(status_code=404, detail="Миссия не найдена")
    for key, value in mission.dict().items():
        setattr(db_mission, key, value)
    db.commit()
    db.refresh(db_mission)
    return {
        "message": "Информация о миссии успешно обновлена",
        "data": mission.dict()
    }

@app.delete("/missions/{mission_code}")
def delete_mission(mission_code: str, db: Session = Depends(get_db)):
    db_mission = db.query(MissionDB).filter(MissionDB.mission_code == mission_code).first()
    if not db_mission:
        raise HTTPException(status_code=404, detail="Миссия не найдена")
    db.delete(db_mission)
    db.commit()
    return {
        "message": "Миссия успешно отменена",
        "data": {"mission_code": mission_code}
    }