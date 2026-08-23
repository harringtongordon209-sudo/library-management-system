from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Generator
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
SQLALCHEMY_DATABASE_URL = "postgresql://library_admin:local_password_123@localhost:5432/library_db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()