from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
import models
import schemas
from database import engine, get_db
from typing import List, Optional
import json

router = APIRouter(
    prefix="/api/items", tags=["Items"]
)

# --- CREATE A PHYSICAL LIBRARY ITEM ---
@router.post("", response_model=schemas.LibraryItemResponse, status_code=status.HTTP_201_CREATED)
def create_library_item(item_data: schemas.LibraryItemCreate, db: Session = Depends(get_db)):
    # Register the physical barcode and link it to the format
    new_item = models.LibraryItem(
        serial_no=item_data.serial_no,
        format_id=item_data.format_id
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return new_item
