from enum import Enum as PyEnum
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
import re  

app = FastAPI()  # Исправлено: скобки после FastAPI

DATABASE_URL = "sqlite:///./logins.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class GenderType(str, PyEnum):
    MAN = "MAN"
    WOMEN = "WOMEN"

class UserDB(Base):
    __tablename__ = "Users"
    mail_ID = Column(String, primary_key=True, index=True)
    password = Column(String, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    patronymic = Column(String, nullable=False)
    gender = Column(SQLAlchemyEnum(GenderType), nullable=False)
    age = Column(Integer, nullable=False)

Base.metadata.create_all(bind=engine)

class User(BaseModel):
    mail_ID: str
    password: str
    first_name: str
    last_name: str
    patronymic: str
    gender: GenderType
    age: int


    @validator("age")
    def validator_age(cls, age):
        if age < 18:
            raise ValueError("Ваш возраст не соответствует минимальному, минимальный возраст 18 лет")
        return age
    
    @validator("password")
    def validator_password(cls, password):
        pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*#?&])[A-Za-z\d@$!%*#?&]{8,}$'
        if not re.match(pattern, password):
            raise ValueError(
                "Пароль должен содержать минимум 8 символов, "
                "включая хотя бы одну заглавную букву, одну строчную букву, одну цифру и один спецсимвол (@$!%*#?&)"
            )
        return password
    
    @validator("mail_ID")
    def validator_mail(cls, mail_ID):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, mail_ID):
            raise ValueError("Неверный формат email. Пример: user@example.com")
        return mail_ID
    
    @validator("first_name")
    def validator_first_name(cls, first_name):
        if len(first_name.strip()) < 2:
            raise ValueError("Имя должно содержать минимум 2 символа")
        return first_name
    
    @validator("last_name")
    def validator_last_name(cls, last_name):
        if len(last_name.strip()) < 2:
            raise ValueError("Фамилия должна содержать минимум 2 символа")
        return last_name
    
    @validator("patronymic")
    def validator_patronymic(cls, patronymic):
        if len(patronymic.strip()) < 2:
            raise ValueError("Отчество должно содержать минимум 2 символа")
        return patronymic

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/users")
def get_users(
    mail_ID: str = None,
    first_name: str = None,
    last_name: str = None,
    gender: GenderType = None,
    db: Session = Depends(get_db)
):
    query = db.query(UserDB)
    if mail_ID:
        query = query.filter(UserDB.mail_ID == mail_ID)
    if first_name:
        query = query.filter(UserDB.first_name == first_name)
    if last_name:
        query = query.filter(UserDB.last_name == last_name)
    if gender:
        query = query.filter(UserDB.gender == gender)
    return query.all()

@app.post("/users")
def create_user(user: User, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.mail_ID == user.mail_ID).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    db_user = UserDB(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "Пользователь успешно создан"}

@app.put("/users/{mail_ID}")
def update_user(mail_ID: str, user: User, db: Session = Depends(get_db)):
    if mail_ID != user.mail_ID:
        raise HTTPException(status_code=400, detail="Email в пути и теле запроса не совпадают")
    db_user = db.query(UserDB).filter(UserDB.mail_ID == mail_ID).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    for key, value in user.dict().items():
        setattr(db_user, key, value)
    db.commit()
    db.refresh(db_user)
    return {"message": "Пользователь успешно обновлен"}

@app.delete("/users/{mail_ID}")
def delete_user(mail_ID: str, db: Session = Depends(get_db)):
    db_user = db.query(UserDB).filter(UserDB.mail_ID == mail_ID).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    db.delete(db_user)
    db.commit()
    return {"message": "Пользователь успешно удален"}