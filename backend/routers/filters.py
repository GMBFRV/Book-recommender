import traceback
from typing import List

from backend.api.open_library_api import get_author_details, logger
from backend.models import Book, Author
from fastapi import APIRouter, HTTPException, Query
from starlette.responses import FileResponse
from backend.recommendation.recommender import recommend_by_genre, recommend_similar_authors, recommend_similar_books

router = APIRouter(tags=["filters"])

# Routers for genre filter
@router.get("/genre_filter")
def get_genre_filter():
    return FileResponse("../frontend/templates/genre_filter.html")

@router.get("/api/genre_filter", response_model=List[Book])
async def genre_filter_api(
    genres: List[str] = Query(..., description="Genres to filter"),
    min_rating: float = Query(4.0, description="Minimum average rating"),
    min_reviews: int = Query(5, description="Minimum review count"),
    top_n: int = Query(20, description="Number of results to return")
):
    try:
        # Call the recommender instead of raw API
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



# Routers for author filter
@router.get("/author_filter")
def author_filter():
    return FileResponse("../frontend/templates/author_filter.html")


@router.get("/api/author", response_model=List[Author])
async def get_author_recommendations(
        author: str = Query(..., min_length=2),
        limit: int = Query(10, ge=1, le=20)
):
    """Возвращаем все рекомендованные авторы, даже с 0 баллов."""
    authors = recommend_similar_authors(author, limit=limit)
    return authors[:limit]




@router.get("/book_filter")
def book_filter():
    return FileResponse("../frontend/templates/book_filter.html")

@router.get("/api/book", response_model=List[Book])
async def get_similar_books(
    book: str = Query(..., min_length=2, description="Title of the book to find similar ones"),
    limit: int = Query(20, ge=1, le=20, description="Maximum number of recommendations to return")
) -> List[Book]:
    """
    Return a list of books similar to the given title using TF-IDF similarity.
    """
    # Fetch and rank similar books via TF-IDF
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

