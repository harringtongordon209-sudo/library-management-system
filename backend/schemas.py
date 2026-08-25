from pydantic import BaseModel
from typing import Optional, List
from datetime import date, time # <-- New import for handling checkout dates

# -------------------------------------
# 1. TITLE SCHEMAS
# -------------------------------------
class TitleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    genre: Optional[str] = None

class TitleResponse(TitleCreate):
    title_id: str

    class Config:
        from_attributes = True

class TitleSummary(BaseModel):
    title_id: str
    name: str
    genre: str

    class Config:
        from_attributes = True

class TitleDetails(BaseModel):
    title_id: str
    name: str
    description: str
    genre: str
    totalNoOfItems: int

    class Config:
        from_attributes = True

# -------------------------------------
# 2. FORMAT SCHEMAS (Example: Book)
# -------------------------------------
# We will start with a schema specifically for creating a Book.
# You can easily duplicate this pattern for Movie and Audiobook later!
class BookCreate(BaseModel):
    author: str
    number_of_pages: int
    number_of_copies: int

class BookResponse(BaseModel):
    title_id: str
    format_id: str
    author: str
    number_of_pages: int
    created_serial_numbers: List[str]

    class Config:
        from_attributes = True


class DvdCreate(BaseModel):
    title_id: str
    director: str
    runtime: time

class DvdResponse(BookCreate):
    format_id: str
    format_type: str # This will automatically say "Dvd" from SQLAlchemy

    class Config:
        from_attributes = True

class AudioBookCreate(BaseModel):
    title_id: str
    narrator: str
    runtime: time

class AudioBookResponse(BookCreate):
    format_id: str
    format_type: str # This will automatically say "Dvd" from SQLAlchemy

    class Config:
        from_attributes = True

# -------------------------------------
# 3. LIBRARY ITEM SCHEMAS
# -------------------------------------
class LibraryItemCreate(BaseModel):
    serial_no: str # The physical barcode
    format_id: str # Links it to a specific book, movie, etc.

class LibraryItemResponse(LibraryItemCreate):
    class Config:
        from_attributes = True

# -------------------------------------
# 4. BORROWER SCHEMAS
# -------------------------------------
class BorrowerCreate(BaseModel):
    name: str

class BorrowerResponse(BorrowerCreate):
    borrower_id: str

    class Config:
        from_attributes = True

# -------------------------------------
# 5. CHECKOUT RECORD SCHEMAS
# -------------------------------------
class CheckoutCreate(BaseModel):
    item_serial_no: str
    borrower_id: str
    # Note: We don't ask the user for dates here; our backend code will generate them!

class CheckoutResponse(BaseModel):
    checkout_id: str
    item_serial_no: str
    borrower_id: str
    check_out_date: date
    due_date: date
    return_date: Optional[date] = None

    class Config:
        from_attributes = True

# --- NEW CHECKOUT REQUEST SCHEMAS ---
class ItemReference(BaseModel):
    id: str

class CheckoutNestedCreate(BaseModel):
    item: ItemReference

# --- NEW CHECKOUT RESPONSE SCHEMAS ---
class ItemDetails(BaseModel):
    id: str
    name: str
    barcode: str

class CheckoutNestedResponse(BaseModel):
    id: str
    startDate: date
    dueDate: date
    returnDate: Optional[date] = None
    item: ItemDetails

class FormatCount(BaseModel):
    format: str
    count: int

class TitleDetailResponse(BaseModel):
    title_id: str
    name: str
    description: str | None = None
    genre: str | None = None
    formats: List[FormatCount]

    class Config:
        from_attributes = True