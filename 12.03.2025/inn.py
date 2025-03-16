from enum import Enum, auto
from fastapi import FastAPI, Depends
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

# Подключение к базе данных
DATABASE_URL = "sqlite:///./users.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель таблицы
class UserDB(Base):
    __tablename__ = "users"
    inn = Column(String, primary_key=True, index=True)
    gender = Column(SQLAlchemyEnum("MALE", "FEMALE"), nullable=False)  # Строки "MALE" и "FEMALE"
    name = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    address = Column(String, nullable=False)

Base.metadata.create_all(bind=engine)

# Pydantic модель
class Gender(str, Enum):  # Наследуем от str для строковых значений
    MALE = "MALE"
    FEMALE = "FEMALE"

class User_inn(BaseModel):
    inn: str
    gender: Gender
    name: str
    first_name: str
    last_name: str
    address: str

    @validator("inn")
    def validate_inn(cls, inn):
        if not inn.isdigit():
            raise ValueError("ИНН должен состоять только из цифр")
        if len(inn) not in (10, 12):
            raise ValueError("ИНН должен состоять из 10 или 12 цифр")
        return inn

# Зависимость для сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Эндпоинты
@app.get("/User")
def get_user(
    user_inn: str = None,
    user_name: str = None,
    user_first_name: str = None,
    user_last_name: str = None,
    user_address: str = None,
    user_gender: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(UserDB)
    if user_inn:
        query = query.filter(UserDB.inn == user_inn)
    if user_name:
        query = query.filter(UserDB.name == user_name)
    if user_first_name:
        query = query.filter(UserDB.first_name == user_first_name)
    if user_last_name:
        query = query.filter(UserDB.last_name == user_last_name)
    if user_address:
        query = query.filter(UserDB.address == user_address)
    if user_gender: 
        query = query.filter(UserDB.gender == user_gender)
    return query.all()

@app.post("/User")
def create_user(new_user: User_inn, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.inn == new_user.inn).first()
    if db_user:
        return "Пользователь с таким ИНН уже существует"
    db_user = UserDB(**new_user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return "Пользователь успешно создан"

@app.put("/User/{user_inn}")
def update_user(user_inn: str, new_user: User_inn, db: Session = Depends(get_db)):
    if user_inn != new_user.inn:
        return "ИНН в теле запроса не совпадает с указанным в пути"
    db_user = db.query(UserDB).filter(UserDB.inn == user_inn).first()
    if not db_user:
        return "Пользователя с таким ИНН не существует"
    for key, value in new_user.dict().items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return "Пользователь успешно обновлён"

@app.delete("/User/{user_inn}")
def delete_user(user_inn: str, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.inn == user_inn).first()
    if not db_user:
        return "Пользователя с таким ИНН не существует"
    db.delete(db_user)
    db.commit()
    return "Пользователь с таким ИНН удалён"