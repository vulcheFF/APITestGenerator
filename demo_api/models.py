from pydantic import BaseModel, Field
from datetime import date

class Book(BaseModel):
    id: int
    title: str
    author: str
    isbn: str = Field(pattern = r"^\d{13}$")
    price: float = Field(gt=0, description="Price is positive")
    quantity: int = Field(ge=0, description="Quantity can't be negative")
    published_date: date
    genre: str