import traceback
from typing import List
from pathlib import Path
from backend.api.open_library_api import get_author_details, logger, get_book_details, find_similar_books, \
    diploma_session, OL_AUTHOR_WORKS_URL, OL_AUTHORS_URL, OL_SEARCH_URL
from backend.models import Book, Author, BookDetailSchema
from fastapi import APIRouter, HTTPException, Query
from starlette.responses import FileResponse
from langdetect import detect, LangDetectException
from backend.recommendation.recommender import (
    recommend_by_genre,
    recommend_similar_authors,
    recommend_similar_books
)
from backend.config import (
    BOOKS_MIN_RATING_DEFAULT,
    BOOKS_MIN_REVIEWS_DEFAULT,
    BOOKS_PAGE_LIMIT_DEFAULT,
    BOOKS_OFFSET_DEFAULT,
    AUTHOR_LIMIT_DEFAULT,
    BOOK_PAGE_LIMIT_DEFAULT
)
from pydantic import BaseModel

router = APIRouter(tags=["filters"])

# Absolute path to project root (3 levels up: /project/backend/routers → /project)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

#
#                                   Routers for genre filter
#

@router.get("/genre_filter")
def get_genre_filter():
    return FileResponse(PROJECT_ROOT / "frontend" / "templates" / "genre_based.html")


from typing import List
from fastapi import APIRouter, Query, HTTPException
import logging

from backend.api.open_library_api import search_books_ol
from backend.models import Book  # ваш Pydantic-модель Book


@router.get("/api/genre_filter", response_model=List[Book])
async def genre_filter_api(
    genres: List[str] = Query(..., description="List of genres to filter by"),
    min_rating: float = Query(
        BOOKS_MIN_RATING_DEFAULT, description="Minimum average rating"
    ),
    min_reviews: int = Query(
        BOOKS_MIN_REVIEWS_DEFAULT, description="Minimum number of reviews"
    ),
    offset: int = Query(
        BOOKS_OFFSET_DEFAULT, ge=0, description="Pagination offset"
    ),
    limit: int = Query(
        BOOKS_PAGE_LIMIT_DEFAULT, gt=0, le=100, description="Number of books to return"
    ),
):
    return recommend_by_genre(
        genres=genres,
        min_rating=min_rating,
        min_reviews=min_reviews,
        limit=limit,
        offset=offset,
    )


@router.get("/book/{work_key}")
def book_detail_page(work_key: str):
    # serve the HTML template
    return FileResponse(PROJECT_ROOT / "frontend" / "templates" / "book_details.html")



class BookDetailResponse(BaseModel):
    detail: dict
    recommendations: List[Book]

@router.get("/api/book/{work_key}", response_model=BookDetailResponse)
async def book_detail_api(
        work_key: str,
        limit: int = Query(5, ge=1, le=20),
):
    # 1) full metadata
    meta = get_book_details(work_key)
    if not meta:
        raise HTTPException(404, f"No work found for key {work_key}")

    # 2) recommendations by TITLE (use your existing function)
    raw = find_similar_books(meta["title"], limit=limit)

    recs = [
        Book(
            key=b["key"],
            title=b["title"],
            authors=b.get("authors") or b.get("author_name", []),
            cover_id=b.get("cover_id") or b.get("cover_i"),
            rating=b.get("rating") or b.get("ratings_average"),
            rating_count=b.get("rating_count") or b.get("ratings_count"),
            genres=b.get("subjects") or b.get("subject", [])
        )
        for b in raw
    ]

    return BookDetailResponse(detail=meta, recommendations=recs)

#
#                                   Routers for author filter
#


@router.get("/author_filter")
def get_author_filter():
    return FileResponse(PROJECT_ROOT / "frontend" / "templates" / "author_based.html")


@router.get("/api/author", response_model=List[Author])
async def get_author_recommendations(
    author: str = Query(..., min_length=2),
    limit: int = Query(AUTHOR_LIMIT_DEFAULT, ge=1, le=20)
):
    """Return similar authors, even with score 0."""
    authors = recommend_similar_authors(author, limit=limit)
    return authors[:limit]


@router.get("/api/author_suggest")
async def author_suggestions(
        query: str = Query(..., min_length=2),
        limit: int = Query(5, ge=1, le=10)
):
    """Return author name suggestions based on partial match."""
    try:
        params = {
            'q': query,
            'limit': limit,
            'fields': 'name,key'
        }
        resp = diploma_session.get(OL_AUTHORS_URL, params=params, timeout=5)
        resp.raise_for_status()
        docs = resp.json().get('docs', [])

        return [{'name': doc['name']} for doc in docs if 'name' in doc]
    except Exception as e:
        logger.error(f'Error fetching author suggestions: {e}')
        return []

@router.get("/author/{author_key}")
def author_detail_page(author_key: str):
    return FileResponse(PROJECT_ROOT / "frontend" / "templates" / "author_details.html")


@router.get("/api/author/{author_key}", response_model=Author)
async def get_author_details_api(author_key: str):
    author = get_author_details(author_key)
    if not author:
        raise HTTPException(404, f"No author found for key {author_key}")
    return author


from langdetect import detect, LangDetectException


@router.get("/api/author/{author_key}/works", response_model=List[Book])
async def get_author_works(
        author_key: str,
        limit: int = Query(5, ge=1, le=20),
        languages: str = Query("en,ru", description="Filter by title languages (comma-separated)")
):
    try:
        allowed_langs = [lang.strip() for lang in languages.split(",")]
        url = OL_AUTHOR_WORKS_URL.format(author_key=author_key)
        params = {
            'limit': 50,
            'fields': 'title,key,cover_i,covers,ratings_average,first_publish_year'
        }
        resp = diploma_session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        books = []
        for work in data.get('entries', []):
            title = work.get('title')
            if not title:
                continue

            try:
                title_lang = detect(title)
            except LangDetectException:
                title_lang = None

            if title_lang not in allowed_langs:
                continue

            cover_id = work.get('covers', [None])[0] or work.get('cover_i')

            books.append(Book(
                key=work.get('key', '').split('/')[-1],
                title=title,
                cover_id=cover_id,
                rating=work.get('ratings_average')
            ))

            if len(books) >= limit:
                break

        logger.info(f"Returning {len(books)} books filtered by languages {allowed_langs}")
        return books

    except Exception as e:
        logger.error(f"Error fetching works: {str(e)}", exc_info=True)
        raise HTTPException(500, "Failed to fetch author's works")

#
#                                   Routers for book filter
#

@router.get("/book_filter")
def book_filter():
    return FileResponse(PROJECT_ROOT / "frontend" / "templates" / "book_based.html")


@router.get("/api/book", response_model=List[Book])
async def get_similar_books(
    book: str = Query(..., min_length=2, description="Title of the book to find similar ones"),
    limit: int = Query(20, ge=1, le=20, description="Maximum number of recommendations to return")
) -> List[Book]:
    """
    Return a list of books similar to the given title using TF-IDF similarity.
    """
    recommendations = recommend_similar_books(book, limit=limit)
    if not recommendations:
        raise HTTPException(
            status_code=404,
            detail=f"No recommendations found for title '{book}'"
        )

    return [
        Book(
            key=rec['key'],
            title=rec['title'],
            authors=rec.get('author_name', []),
            genres=rec.get('subject', []),
            cover_id=rec.get('cover_i'),
            rating=rec.get('ratings_average'),
            rating_count=rec.get('ratings_count'),
        )
        for rec in recommendations
    ]


@router.get("/api/book_suggest")
async def book_suggestions(
        query: str = Query(..., min_length=2),
        limit: int = Query(5, ge=1, le=10)
):
    """Return book title suggestions based on partial match."""
    try:
        params = {
            'q': query,
            'limit': limit,
            'fields': 'title,author_name,cover_i'
        }
        resp = diploma_session.get(OL_SEARCH_URL, params=params, timeout=5)
        resp.raise_for_status()
        docs = resp.json().get('docs', [])

        return [{
            'title': doc.get('title'),
            'author_name': doc.get('author_name', []),
            'cover_id': doc.get('cover_i')
        } for doc in docs if doc.get('title')]
    except Exception as e:
        logger.error(f'Error fetching book suggestions: {e}')
        return []