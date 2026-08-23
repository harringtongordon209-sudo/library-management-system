from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
import models
import schemas
from database import engine, get_db

router = APIRouter(
    prefix="/api/formats/books", tags=["Formats"]
)

@router.post("", response_model=schemas.BookResponse, status_code=status.HTTP_201_CREATED)
def create_book_format(book_data: schemas.BookCreate, db: Session = Depends(get_db)):
    # Create the Book model (SQLAlchemy handles linking this to the parent Format table automatically)
    new_book = models.Book(
        title_id=book_data.title_id,
        author=book_data.author,
        number_of_pages=book_data.number_of_pages
    )

    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    return new_book