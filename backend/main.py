import requests
import fastapi
import uvicorn
from fastapi import FastAPI
from starlette.responses import FileResponse

app = FastAPI()
# ---------------------------------------------- Тестові ендпоінти -----------------------------------------------------

@app.get("/")
def main():
    return FileResponse("../frontend/index.html")

# ------------------------------------------------- Користувачі --------------------------------------------------------

@app.get("/registration")
def registration():
    return {"Registration form"}

@app.get("/login")
def login():
    return {"Login"}

@app.get("/user")
def user():
    return {"User information"}

# ------------------------------------------------ Пошук по жанру ------------------------------------------------------

@app.get("/genrefilter")
def genre_filter():
    return {"On this page user can filter books by genre"}

# -------------------------------------------- Пошук по автору (???)----------------------------------------------------

@app.get("/authorfilter")
def author_filter():
    return {"On this page user can filter books by author"}

# ----------------------------------------------- Пошук по книзі ------------------------------------------------------

@app.get("/book")
def book_filter():
    return {"On this page user can filter books by books"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)



