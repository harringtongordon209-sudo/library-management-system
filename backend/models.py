from sqlalchemy import Column, String, Integer, Date, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
import uuid


# -------------------------------------
# 1. TITLE
# -------------------------------------
class Title(Base):
    __tablename__ = "titles"

    title_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, index=True)
    description = Column(String)
    genre = Column(String)

    # Links to the Format table
    formats = relationship("Format", back_populates="title")


# -------------------------------------
# 2. FORMAT (The Polymorphic Base)
# -------------------------------------
class Format(Base):
    __tablename__ = "formats"

    format_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    title_id = Column(String, ForeignKey("titles.title_id"))

    # This column tells SQLAlchemy which child table to look at (book, movie, or audiobook)
    format_type = Column(String)

    title = relationship("Title", back_populates="formats")
    library_items = relationship("LibraryItem", back_populates="format")

    # The magic that makes inheritance work
    __mapper_args__ = {
        "polymorphic_on": format_type,
        "polymorphic_identity": "format",
    }


# --- FORMAT SUB-CLASSES ---

class Book(Format):
    __tablename__ = "books"

    # Links directly to the parent Format table
    format_id = Column(String, ForeignKey("formats.format_id"), primary_key=True)
    author = Column(String)
    number_of_pages = Column(Integer)

    __mapper_args__ = {"polymorphic_identity": "book"}


class Movie(Format):
    __tablename__ = "movies"

    format_id = Column(String, ForeignKey("formats.format_id"), primary_key=True)
    director = Column(String)
    runtime = Column(Integer)  # Runtime in minutes

    __mapper_args__ = {"polymorphic_identity": "movie"}


class Audiobook(Format):
    __tablename__ = "audiobooks"

    format_id = Column(String, ForeignKey("formats.format_id"), primary_key=True)
    narrator = Column(String)
    runtime = Column(Integer)

    __mapper_args__ = {"polymorphic_identity": "audiobook"}


# -------------------------------------
# 3. LIBRARY ITEM
# -------------------------------------
class LibraryItem(Base):
    __tablename__ = "library_items"

    # Using the Barcode as the primary key as defined in your UML
    serial_no = Column(String, primary_key=True)
    format_id = Column(String, ForeignKey("formats.format_id"))

    format = relationship("Format", back_populates="library_items")
    checkouts = relationship("CheckoutRecord", back_populates="library_item")


# -------------------------------------
# 4. BORROWER
# -------------------------------------
class Borrower(Base):
    __tablename__ = "borrowers"

    borrower_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String)

    checkouts = relationship("CheckoutRecord", back_populates="borrower")


# -------------------------------------
# 5. CHECKOUT RECORD
# -------------------------------------
class CheckoutRecord(Base):
    __tablename__ = "checkout_records"

    checkout_id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    item_serial_no = Column(String, ForeignKey("library_items.serial_no"))
    borrower_id = Column(String, ForeignKey("borrowers.borrower_id"))

    check_out_date = Column(Date)
    due_date = Column(Date)
    return_date = Column(Date, nullable=True)  # Null if it hasn't been returned yet

    library_item = relationship("LibraryItem", back_populates="checkouts")
    borrower = relationship("Borrower", back_populates="checkouts")
