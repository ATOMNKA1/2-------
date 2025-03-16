from enum import Enum, auto
from fastapi import FastAPI, Depends
from pydantic import BaseModel, validator
from sqlalchemy import create_engine, Column, String, Integer, Enum as SQLAlchemyEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

app = FastAPI()

# Подключение к базе данных
DATABASE_URL = "sqlite:///./library.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Модель таблицы
class BookDB(Base):
    __tablename__ = "books"
    isbn = Column(String, primary_key=True, index=True)  # Уникальный идентификатор книги
    genre = Column(SQLAlchemyEnum("FICTION", "NON_FICTION", "SCIENCE"), nullable=False)  # Жанр
    title = Column(String, nullable=False)  # Название книги
    author = Column(String, nullable=False)  # Автор
    pages = Column(Integer, nullable=False)  # Количество страниц

Base.metadata.create_all(bind=engine)

# Pydantic модель
class Genre(str, Enum):  # Жанры как строки
    FICTION = "FICTION"
    NON_FICTION = "NON_FICTION"
    SCIENCE = "SCIENCE"

class Book(BaseModel):
    isbn: str
    genre: Genre
    title: str
    author: str
    pages: int

    @validator("isbn")
    def validate_isbn(cls, isbn):
        if not isbn.isdigit():
            raise ValueError("ISBN должен состоять только из цифр")
        if len(isbn) not in (10, 13):  # ISBN бывает 10 или 13 цифр
            raise ValueError("ISBN должен состоять из 10 или 13 цифр")
        return isbn

    @validator("pages")
    def validate_pages(cls, pages):
        if pages <= 0:
            raise ValueError("Количество страниц должно быть больше 0")
        return pages

# Зависимость для сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Эндпоинты
@app.get("/Book")
def get_book(
    book_isbn: str = None,
    book_title: str = None,
    book_author: str = None,
    book_genre: str = None,
    db: Session = Depends(get_db)
):
    query = db.query(BookDB)
    if book_isbn:
        query = query.filter(BookDB.isbn == book_isbn)
    if book_title:
        query = query.filter(BookDB.title == book_title)
    if book_author:
        query = query.filter(BookDB.author == book_author)
    if book_genre:
        query = query.filter(BookDB.genre == book_genre)
    return query.all()

@app.post("/Book")
def create_book(new_book: Book, db: Session = Depends(get_db)):
    db_book = db.query(BookDB).filter(BookDB.isbn == new_book.isbn).first()
    if db_book:
        return "Книга с таким ISBN уже существует"
    db_book = BookDB(**new_book.dict())
    db.add(db_book)
    db.commit()
    db.refresh(db_book)
    return "Книга успешно добавлена"

@app.put("/Book/{book_isbn}")
def update_book(book_isbn: str, new_book: Book, db: Session = Depends(get_db)):
    if book_isbn != new_book.isbn:
        return "ISBN в теле запроса не совпадает с указанным в пути"
    db_book = db.query(BookDB).filter(BookDB.isbn == book_isbn).first()
    if not db_book:
        return "Книги с таким ISBN не существует"
    for key, value in new_book.dict().items():
        setattr(db_book, key, value)
    db.commit()
    db.refresh(db_book)
    return "Книга успешно обновлена"

@app.delete("/Book/{book_isbn}")
def delete_book(book_isbn: str, db: Session = Depends(get_db)):
    db_book = db.query(BookDB).filter(BookDB.isbn == book_isbn).first()
    if not db_book:
        return "Книги с таким ISBN не существует"
    db.delete(db_book)
    db.commit()
    return "Книга успешно удалена"