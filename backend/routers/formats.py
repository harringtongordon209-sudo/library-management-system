import uuid

from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json

from typing_extensions import runtime

import models, schemas
from database import get_db, redis_client

router = APIRouter(prefix="/api/formats", tags=["Formats"])

@router.get("/{format_id}/items", response_model=schemas.FormatItemsResponse, status_code=status.HTTP_200_OK)
def get_format_items(format_id: str, db: Session = Depends(get_db)):

    format = db.query(models.Format).filter(
        models.Format.format_id == format_id
    ).first()

    if not format:
        raise HTTPException(status_code=404, detail="Format not found")

    # 2. Get items for format which are not checked out already (i.e., due_date is None in CheckoutRecord)
    checked_out_subquery = (
        db.query(models.CheckoutRecord.item_serial_no)
        .filter(models.CheckoutRecord.return_date.is_(None))
        .subquery()
    )

    available_items = (
        db.query(models.LibraryItem.serial_no)
        .filter(
            models.LibraryItem.format_id == format_id,
                models.LibraryItem.serial_no.notin_(checked_out_subquery))
        .all()
    )

    # return now the title_id along with a list of formats
    return {
        "format_id": format_id,
        "items": [item.serial_no for item in available_items]
    }
