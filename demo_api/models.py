from pydantic import BaseModel, Field
from datetime import date

class Book(BaseModel):
    id: int
    title: str
    author: str
    isbn: str
    price: float
    quantity: int
    published_date: date
    genre: str