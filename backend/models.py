from typing import List, Optional, Dict, Any
from pydantic import BaseModel

class Book(BaseModel):
    key: str
    title: str
    authors: List[str] = []
    genres: List[str] = []
    rating: Optional[float] = None
    rating_count: Optional[int] = None
    cover_id: Optional[int] = None
    publish_year: Optional[int] = None


    # Explicitly include computed properties in dict/json
    def dict(self, **kwargs):
        data = super().dict(**kwargs)
        return data

class Author(BaseModel):
    key: str
    name: str
    birth_date: Optional[str] = None
    death_date: Optional[str] = None
    bio: Optional[str] = None
    works_count: Optional[int] = None
    subjects: List[str] = []
    links: List[Dict[str, Any]] = []
    top_work: Optional[str] = None
    alternate_names: List[str] = []
    rating: Optional[float] = None
    similarity_score: Optional[float] = None
    photo_id: Optional[int] = None

class BookDetailSchema(BaseModel):
    detail: dict
    recommendations: List[Book]