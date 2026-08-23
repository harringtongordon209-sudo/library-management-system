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

from routers import borrowers, titles, items, formats

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
app.include_router(borrowers.router)
app.include_router(titles.router)
app.include_router(items.router)

app.include_router(formats.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Library API!"}