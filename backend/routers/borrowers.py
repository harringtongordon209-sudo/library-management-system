from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date, timedelta
import json

import models, schemas
from database import get_db, redis_client # Import redis_client from database!

# Prefix removes the need to write /api/borrowers on every route
router = APIRouter(prefix="/api/borrowers", tags=["Borrowers"])

@router.post("", response_model=schemas.BorrowerResponse, status_code=status.HTTP_201_CREATED)
def create_borrower(borrower_data: schemas.BorrowerCreate, db: Session = Depends(get_db),
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

    new_borrower = models.Borrower(name=borrower_data.name)

    db.add(new_borrower)
    db.commit()
    db.refresh(new_borrower)

    if idempotency_key:
        response_data = {
            "borrower_id": new_borrower.borrower_id,
            "name": new_borrower.name
        }
        redis_client.set(idempotency_key, json.dumps(response_data), ex=86400)

    return new_borrower

@router.get("", response_model=List[schemas.BorrowerResponse], status_code=status.HTTP_200_OK)
def get_all_borrowers(name: Optional[str] = None, db: Session = Depends(get_db)):
    query = db.query(models.Borrower)
    if name:
        query = query.filter(models.Borrower.name.ilike(f"%{name}%"))
    return query.all()


@router.patch("/{borrower_id}/checkoutRecords/{checkout_id}", response_model=schemas.CheckoutNestedResponse,status_code=status.HTTP_200_OK)
def checkin_item(
    borrower_id: str,
    checkout_id: str,
    db: Session = Depends(get_db)
):


    # Find the specific checkout record
    checkout_record = db.query(models.CheckoutRecord).filter(
        models.CheckoutRecord.checkout_id == checkout_id,
        models.CheckoutRecord.borrower_id == borrower_id
    ).first()

    # Guardrails: Does it exist? is it already checked in

    if not checkout_record:
        raise HTTPException(status_code=404, detail="Checkout Record not found")

    if checkout_record.return_date is not None:
        raise HTTPException(status_code=400, detail="This Item has already been checked in")


    # Update the return date to todays date

    checkout_record.return_date = date.today()

    # Save to database

    db.commit()
    db.refresh(checkout_record)

    library_item = db.query(models.LibraryItem).filter(
        models.LibraryItem.serial_no == checkout_record.item_serial_no
    ).first()

    return {
        "checkout_id": checkout_record.checkout_id,
        "startDate": checkout_record.check_out_date.isoformat(),
        "dueDate": checkout_record.due_date.isoformat(),
        "returnDate": checkout_record.return_date.isoformat(),
        "item": {
            "id": library_item.format_id,  # Linking the format ID
            "name": library_item.format.title.name,  # Using SQLAlchemy relationships to get the name
            "barcode": library_item.serial_no
        }
    }


@router.post("/{borrower_id}/checkoutRecords", response_model=schemas.CheckoutNestedResponse, status_code=status.HTTP_201_CREATED)
def checkout_item_nested(
        borrower_id: str,  # FastAPI automatically pulls this from the URL!
        checkout_data: schemas.CheckoutNestedCreate,
        db: Session = Depends(get_db),
        idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key")
):
    # 1. Handle Redis Idempotency (Same as we did for Titles)
    if idempotency_key:
        cached = redis_client.get(idempotency_key)
        if cached:
            if cached == "processing":
                raise HTTPException(status_code=409, detail="Request is processing")
            return json.loads(cached)

        is_new = redis_client.set(idempotency_key, "processing", nx=True, ex=3600)
        if not is_new:
            raise HTTPException(status_code=409, detail="Request is processing")

    borrower_record = db.query(models.Borrower).filter(
        models.Borrower.borrower_id == borrower_id
    ).first()
    print(borrower_record)
    if not borrower_record:
        raise HTTPException(status_code=400, detail="Borrower does not exist!")

    # 2. Extract the item ID from the nested request body
    item_id = checkout_data.item.id

    # 3. Check if the item is already checked out
    active_checkout = db.query(models.CheckoutRecord).filter(
        models.CheckoutRecord.item_serial_no == item_id,
        models.CheckoutRecord.return_date == None
    ).first()
    print("got here")

    if active_checkout:
        raise HTTPException(status_code=400, detail="Item is already checked out!")

    # 4. Fetch the library item to get its Title Name for the response
    library_item = db.query(models.LibraryItem).filter(models.LibraryItem.serial_no == item_id).first()
    if not library_item:
        raise HTTPException(status_code=404, detail="Item not found")

    # 5. Calculate dates (Your example response showed a 7-day checkout period)
    start_date = date.today()
    due_date = start_date + timedelta(days=7)

    # 6. Create the Database Record
    new_checkout = models.CheckoutRecord(
        item_serial_no=item_id,
        borrower_id=borrower_id,
        check_out_date=start_date,
        due_date=due_date
    )
    db.add(new_checkout)
    db.commit()
    db.refresh(new_checkout)

    # 7. Construct the exact nested response you requested
    response_data = {
        "checkout_id": new_checkout.checkout_id,
        "startDate": new_checkout.check_out_date.isoformat(),
        "dueDate": new_checkout.due_date.isoformat(),
        "item": {
            "id": library_item.format_id,  # Linking the format ID
            "name": library_item.format.title.name,  # Using SQLAlchemy relationships to get the name
            "barcode": library_item.serial_no
        }
    }

    # 8. Cache the final result in Redis
    if idempotency_key:
        redis_client.set(idempotency_key, json.dumps(response_data), ex=86400)

    return response_data