import uuid

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json

import models, schemas
from database import get_db, redis_client

router = APIRouter(prefix="/api/titles", tags=["Titles"])

@router.post("", response_model=schemas.TitleResponse, status_code=status.HTTP_201_CREATED)
def create_title(title_data: schemas.TitleCreate, db: Session = Depends(get_db),
                 idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),):

    if idempotency_key:
        cached_response = redis_client.get(idempotency_key)
        if cached_response:
            if cached_response == "processing":
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is currently processing")
            return json.loads(cached_response)
        is_new = redis_client.set(idempotency_key, "processing", nx=True, ex=3600)

        if not is_new:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Request is currently processing")

    new_title = models.Title(
        name=title_data.name,
        description=title_data.description,
        genre=title_data.genre
    )

    db.add(new_title)
    db.commit()
    db.refresh(new_title)

    if idempotency_key:
        response_data = {
            "title_id": new_title.title_id,
            "name": new_title.name,
            "description": new_title.description,
            "genre": new_title.genre
        }
        redis_client.set(idempotency_key, json.dumps(response_data), ex=86400)

    return new_title

@router.post("/{title_id}/book", response_model=schemas.BookResponse, status_code=status.HTTP_200_OK)
def create_book_copies(
        title_id: str,
        book_data: schemas.BookCreate,
        db: Session = Depends(get_db),
):
    # Verify the title exists
    title = db.query(models.Title).filter(models.Title.title_id == title_id).first()
    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    # 2. Save Book metadata (Assuming you have a Book model linked to Title)
    # If author and number_of_pages are just fields on the Title model,
    # you would update the Title object here instead.
    new_book = models.Book(
        title_id=title_id,
        author=book_data.author,
        number_of_pages=book_data.number_of_pages,
    )
    db.add(new_book)
    db.commit()
    db.refresh(new_book)

    # 3. Create the specified number of Item copies
    created_items = []
    for _ in range(book_data.number_of_copies):
        # Generate a serial number. If your DB auto-increments this,
        # you can omit it and retrieve it after db.commit()
        new_serial = str(uuid.uuid4())

        new_library_item = models.LibraryItem(
            serial_no=new_serial,
            format_id=new_book.format_id,
        )
        db.add(new_library_item)
        created_items.append(new_library_item)
    # 4. Commit all changes to the database at once
    db.commit()

    # 5. Extract the serial numbers from the created items
    serial_numbers = [library_item.serial_no for library_item in created_items]

    return schemas.BookResponse(
        title_id=title_id,
        format_id=new_book.format_id,
        author=book_data.author,
        number_of_pages=book_data.number_of_pages,
        created_serial_numbers=serial_numbers
    )




@router.get("", response_model=List[schemas.TitleSummary], status_code=status.HTTP_200_OK)
def get_all_titles(name: Optional[str] = None, db: Session = Depends(get_db)):

    query = db.query(models.Title)
    if name:
        query = query.filter(models.Title.name.ilike(f"%{name}%"))
    return query.all()

@router.get("/{title_id}", response_model=schemas.TitleDetailResponse, status_code=status.HTTP_200_OK)
def get_title_detail(title_id: str, db: Session = Depends(get_db)):

    title = db.query(models.Title).filter(
        models.Title.title_id == title_id
    ).first()

    if not title:
        raise HTTPException(status_code=404, detail="Title not found")

    # 2. Group items by format and count
    format_counts = (
        db.query(
            models.Format.format_type.label("format"),
            func.count(models.LibraryItem.format_id).label("count")  # or whatever primary key LibraryItem uses
        )
        .join(models.LibraryItem, models.LibraryItem.format_id == models.Format.format_id)
        .filter(models.Format.title_id == title_id)
        .group_by(models.Format.format_type)
        .all()
    )
    # return now the details along with a list of formats
    return {
        "title_id": title.title_id,
        "name": title.name,
        "description": title.description,
        "genre": title.genre,
        "formats": [{"format": fc.format, "count": fc.count} for fc in format_counts]
    }