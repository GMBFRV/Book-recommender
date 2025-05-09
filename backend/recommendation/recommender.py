# Content-based recommendation system
from typing import List, Dict, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.api.open_library_api import (search_books_ol, get_author_details, find_similar_authors, find_similar_books)
from backend.models import Book, Author
import logging
import time

logger = logging.getLogger(__name__)

def recommend_by_genre(
        genres: List[str],
        min_rating: float = 4.0,
        min_reviews: int = 50,
        limit: int = 20
) -> List[Book]:
    """
    Recommends books in specified genres with rating >= min_rating.
    Returns List[Book] ordered by rating (highest first).
    """
    # 1. Fetch books from Open Library API
    raw_books = search_books_ol(
        genres=genres,
        min_reviews=min_reviews,
        limit=limit
    )

    # 2. Convert to Book objects and apply rating filter
    books = []
    for b in raw_books:
        book = Book(
            key=b['key'],
            title=b.get('title', 'Unknown'),
            authors=b.get('author_name', []),
            genres=b.get('subject', []),
            rating=b.get('ratings_average'),
            rating_count=b.get('ratings_count'),
            cover_id=b.get('cover_i'),
            publish_year=b.get('first_publish_year')
        )
        if book.rating and book.rating >= min_rating:
            books.append(book)

    # 3. Sort by rating (descending)
    return sorted(books, key=lambda x: x.rating, reverse=True)[:limit]


def calculate_similarity(target_subjects: Set[str], candidate_subjects: List[str]) -> float:
    """Calculate meaningful similarity score (0-1)"""
    if not target_subjects:
        return 0.4  # Default base score

    candidate_set = set(candidate_subjects)
    intersection = target_subjects & candidate_set

    # Base score weighted by subject matches
    base_score = min(1.0, len(intersection) / len(target_subjects))

    return min(1.0, base_score)


def recommend_similar_authors(target_author: str, limit: int) -> List[Author]:
    start_time = time.time()
    """Get similar authors with proper scoring"""
    try:
        logger.info(f"Starting recommendation for author: {target_author}")

        # 1. Get initial candidates
        candidates = find_similar_authors(target_author, limit=limit * 2)
        logger.debug(f"Initial candidates count: {len(candidates)}")

        if not candidates:
            logger.warning("No candidates found")
            return []

        # 2. Get target author's subjects
        target_author_data = get_author_details(candidates[0]['key'])
        if not target_author_data:
            logger.warning("Failed to get target author details")
            return []

        target_subjects = set(s.lower() for s in target_author_data.subjects)
        logger.debug(f"Target subjects: {target_subjects}")

        # 3. Score and filter candidates
        results = []
        for candidate in candidates:
            author = get_author_details(candidate['key'])
            if author:
                similarity = calculate_similarity(
                    target_subjects,
                    [s.lower() for s in author.subjects]
                )
                author.similarity_score = similarity
                results.append(author)
                logger.debug(f"Processed author: {author.name} (score: {similarity})")

        end_time = time.time()
        print("Time of recommender system work:", end_time - start_time)
        # Return sorted by score (at least 0.3 similarity)
        return sorted(
            results,
            key=lambda x: x.similarity_score,
            reverse=True
        )[:limit]


    except Exception as e:
        logger.error(f"Error in recommend_similar_authors: {str(e)}", exc_info=True)
        return []


def recommend_similar_books(
    target_book: str,
    limit: int = 5
) -> List[Dict]:
    """
    Takes raw books from find_similar_books, builds a TF-IDF on
    [title + subjects + author_name], calculates cosine similarity with the target book,
    sorts and returns the top-N.
    """
    raw = find_similar_books(target_book)
    if not raw:
        return []

    # 1) Строим тексты: первая запись — целевая книга
    def doc_to_text(doc: Dict) -> str:
        parts = []
        if t := doc.get('title'): parts.append(t)
        for s in doc.get('subject', []):
            if isinstance(s, str): parts.append(s)
        for a in doc.get('author_name', []):
            if isinstance(a, str): parts.append(a)
        return " ".join(parts)

    texts = [doc_to_text(raw[0])] + [doc_to_text(d) for d in raw[1:]]
    # 2) Векторизуем и считаем косинус
    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(texts)
    sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()
    # 3) Собираем и сортируем
    scored = []
    for doc, sim in zip(raw[1:], sims):
        scored.append({**doc, 'score': float(sim)})
    return sorted(scored, key=lambda x: x['score'], reverse=True)[:limit]