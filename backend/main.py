from fastapi import FastAPI, Depends, status, Header, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
import redis
import json
import models
import schemas
from database import engine, get_db
from datetime import date, timedelta
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=engine)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Library API!"}

@app.post("/api/titles", response_model=schemas.TitleResponse, status_code=status.HTTP_201_CREATED)
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

@app.get("/api/titles", response_model=List[schemas.TitleSummary], status_code=status.HTTP_200_OK)
def get_all_titles(name: Optional[str] = None, db: Session = Depends(get_db)):

    query = db.query(models.Title)
    if name:
        query = query.filter(models.Title.name.ilike(f"%{name}%"))
    return query.all()


# --- CREATE A BOOK FORMAT ---
@app.post("/api/formats/books", response_model=schemas.BookResponse, status_code=status.HTTP_201_CREATED)
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


# --- CREATE A PHYSICAL LIBRARY ITEM ---
@app.post("/api/items", response_model=schemas.LibraryItemResponse, status_code=status.HTTP_201_CREATED)
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


# --- CREATE A BORROWER ---
@app.post("/api/borrowers", response_model=schemas.BorrowerResponse, status_code=status.HTTP_201_CREATED)
def create_borrower(borrower_data: schemas.BorrowerCreate, db: Session = Depends(get_db)):
    new_borrower = models.Borrower(name=borrower_data.name)

    db.add(new_borrower)
    db.commit()
    db.refresh(new_borrower)

    return new_borrower

# --- Search for  a BORROWER ---

@app.get("/api/borrowers", response_model=List[schemas.BorrowerResponse], status_code=status.HTTP_200_OK)
def get_all_borrowers(name: Optional[str] = None, db: Session = Depends(get_db)):

    query = db.query(models.Borrower)
    if name:
        query = query.filter(models.Borrower.name.ilike(f"%{name}%"))
    return query.all()


# --- CHECK OUT AN ITEM ---
# --- CHECK OUT AN ITEM (NESTED ROUTE & IDEMPOTENT) ---
@app.post(
    "/api/borrowers/{borrower_id}/checkoutRecords",
    response_model=schemas.CheckoutNestedResponse,
    status_code=status.HTTP_201_CREATED
)
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

    # 2. Extract the item ID from the nested request body
    item_id = checkout_data.item.id

    # 3. Check if the item is already checked out
    active_checkout = db.query(models.CheckoutRecord).filter(
        models.CheckoutRecord.item_serial_no == item_id,
        models.CheckoutRecord.return_date == None
    ).first()

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
        "id": new_checkout.checkout_id,
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