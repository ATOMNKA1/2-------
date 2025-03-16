from enum import Enum as PyEnum
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, Integer, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

DATABASE_URL = "sqlite:///./movies.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class MovieGenre(str, PyEnum):
    ACTION = "ACTION"
    DRAMA = "DRAMA"
    COMEDY = "COMEDY"
    SCI_FI = "SCI_FI"

class MovieDB(Base):
    __tablename__ = "movies"
    movie_id = Column(String, primary_key=True, index=True)
    genre = Column(SQLAlchemyEnum(MovieGenre), nullable=False)
    title = Column(String, nullable=False)
    director = Column(String, nullable=False)
    release_year = Column(Integer, nullable=False)

Base.metadata.create_all(bind=engine)

class Movie(BaseModel):
    movie_id: str
    genre: MovieGenre
    title: str
    director: str
    release_year: int

    @validator("movie_id")
    def validate_movie_id(cls, movie_id):
        if not movie_id.isalnum():
            raise ValueError("ID фильма должен состоять только из букв и цифр")
        if len(movie_id) < 5:
            raise ValueError("ID фильма должен быть длиной не менее 5 символов")
        return movie_id

    @validator("release_year")
    def validate_release_year(cls, release_year):
        if release_year < 1888 or release_year > 2025:
            raise ValueError("Год выпуска должен быть между 1888 и 2025")
        return release_year

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/movies")
def get_movies(
    movie_id: str = None,
    title: str = None,
    director: str = None,
    genre: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(MovieDB)
    if movie_id:
        query = query.filter(MovieDB.movie_id == movie_id)
    if title:
        query = query.filter(MovieDB.title == title)
    if director:
        query = query.filter(MovieDB.director == director)
    if genre:
        query = query.filter(MovieDB.genre == genre)
    return query.all()

@app.post("/movies")
def create_movie(movie: Movie, db: Session = Depends(get_db)):
    db_movie = db.query(MovieDB).filter(MovieDB.movie_id == movie.movie_id).first()
    if db_movie:
        raise HTTPException(status_code=400, detail="Фильм с таким ID уже существует")
    db_movie = MovieDB(**movie.dict())
    db.add(db_movie)
    db.commit()
    db.refresh(db_movie)
    return {"message": "Фильм успешно создан"}

@app.put("/movies/{movie_id}")
def update_movie(movie_id: str, movie: Movie, db: Session = Depends(get_db)):
    if movie_id != movie.movie_id:
        raise HTTPException(status_code=400, detail="ID фильма в пути и теле запроса не совпадают")
    db_movie = db.query(MovieDB).filter(MovieDB.movie_id == movie_id).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    for key, value in movie.dict().items():
        setattr(db_movie, key, value)
    db.commit()
    db.refresh(db_movie)
    return {"message": "Фильм успешно обновлен"}

@app.delete("/movies/{movie_id}")
def delete_movie(movie_id: str, db: Session = Depends(get_db)):
    db_movie = db.query(MovieDB).filter(MovieDB.movie_id == movie_id).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Фильм не найден")
    db.delete(db_movie)
    db.commit()
    return {"message": "Фильм успешно удален"}