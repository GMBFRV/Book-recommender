import traceback
from typing import List
from pathlib import Path
from backend.api.open_library_api import get_author_details, logger, get_book_details, find_similar_books, \
    diploma_session, OL_AUTHOR_WORKS_URL, OL_AUTHORS_URL, OL_SEARCH_URL
from backend.models import Book, Author, BookDetailSchema
from fastapi import APIRouter, HTTPException, Query
from starlette.responses import FileResponse
from backend.recommendation.recommender import (
    recommend_by_genre,
    recommend_similar_authors,
    recommend_similar_books
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


@router.get("/api/genre_filter", response_model=List[Book])
async def genre_filter_api(
    genres: List[str] = Query(..., description="Genres to filter"),
    min_rating: float = Query(4.0, description="Minimum average rating"),
    min_reviews: int = Query(5, description="Minimum review count"),
    top_n: int = Query(20, description="Number of results to return")
):
    try:
        return recommend_by_genre(
            genres=genres,
            min_rating=min_rating,
            min_reviews=min_reviews,
            limit=top_n
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Recommendation failed: {str(e)}"
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
    limit: int = Query(10, ge=1, le=20)
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


@router.get("/api/author/{author_key}/works", response_model=List[Book])
async def get_author_works(author_key: str, limit: int = Query(5, ge=1, le=20)):
    try:
        url = OL_AUTHOR_WORKS_URL.format(author_key=author_key)
        params = {'limit': limit, 'fields': 'title,key,cover_i,ratings_average'}
        resp = diploma_session.get(url, params=params, timeout=10)
        resp.raise_for_status()
        works = resp.json().get('entries', [])

        return [
            Book(
                key=work.get('key', '').split('/')[-1],
                title=work.get('title'),
                cover_id=work.get('cover_i'),
                rating=work.get('ratings_average')
            )
            for work in works
        ]
    except Exception as e:
        logger.error(f"Error fetching works for author {author_key}: {e}")
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