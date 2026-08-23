from fastapi import FastAPI, Query
from fastapi import HTTPException
from demo_api.models import Book

app = FastAPI(title="Library API")

#(дб) лист...
books_db: list[Book] = [
    Book(
        id=1,
        title="1984",
        author = "G. Orwell",
        isbn = "9780451524935",
        price = 23.99,
        quantity = 10,
        published_date= "1949-06-08",
        genre="Dystopian",
        author_info={"name": "George Orwell", "nationality": "British"}

    ),
    Book(
        id=2,
        title="Brave New World",
        author = "Aldos Huxley",
        isbn = "9780060850524",
        price = 13.99,
        quantity = 5,
        published_date= "1932-01-01",
        genre="Dystopian",
        author_info={"name": "Aldous Huxley", "nationality": "British"}
        
    )
]

@app.get("/books")
def get_books() -> list[Book]:
    return books_db



@app.get("/books/search")
def search_books(tags: list[str] = Query(...)) -> list[Book]:
    return [book for book in books_db if book.genre in tags]

@app.get("/books/{book_id}")
def get_books(book_id: int) -> Book | dict:
    for book in books_db:
        if book.id == book.id:
            return book
        # 404 , not 200
    return {}


@app.post("/books")
def create_book(book: Book) -> Book:
    books_db.append(book)
    #добавяме без проверки дали има наличност
    return book

@app.put("/books/{book_id}")
def update_book(book_id: int, updated_book: Book)  -> Book:
    for index, book in enumerate(books_db):
        if book.id == book.id:
            #няма проверки пак
            books_db[index] = updated_book
            return updated_book
    raise HTTPException(status_code=404, detail = "Book not found!")

@app.delete("/books/{book_id}")
def delete_book(book_id: int) -> dict:
    for index, book in enumerate(books_db):
        if book.id == book.id:
            del books_db[index]
            return {"msg":"Book deleted!"}
    raise HTTPException(status_code=404, detail = "Book not found!")     