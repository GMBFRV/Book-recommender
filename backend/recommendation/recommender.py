# ----------------------------------------------------------------------------------------------------------------------
#                                               Content-based recommender
# ----------------------------------------------------------------------------------------------------------------------
import math
from typing import List, Dict, Set
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.api.open_library_api import (search_books_ol, get_author_details, find_similar_authors, find_similar_books)
from backend.models import Book, Author
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
logger = logging.getLogger(__name__)
from backend.config import (
    BOOKS_MIN_RATING_DEFAULT,
    BOOKS_MIN_REVIEWS_DEFAULT,
    BOOKS_PAGE_LIMIT_DEFAULT,
    BOOKS_OFFSET_DEFAULT,
    AUTHOR_LIMIT_DEFAULT,
    BOOK_PAGE_LIMIT_DEFAULT
)


# ----------------------------------------------------------------------------------------------------------------------
#                                               Genre-based
# ----------------------------------------------------------------------------------------------------------------------

def recommend_by_genre(
    genres: List[str],
    min_rating: float = BOOKS_MIN_RATING_DEFAULT,
    min_reviews: int = BOOKS_MIN_REVIEWS_DEFAULT,
    limit: int = BOOKS_PAGE_LIMIT_DEFAULT,
    offset: int = BOOKS_OFFSET_DEFAULT
) -> List[Book]:
    """
    Recommend books based on genre filters, average rating, and number of reviews.

    This function retrieves books from OpenLibrary matching the specified genres,
    then filters them based on minimum rating and review count. It continues querying
    in batches until the required number of books is collected or no more are found.
    Results are sorted in descending order by rating.

    Args:
        genres (List[str]): List of genres (subjects) to filter by.
        min_rating (float): Minimum average rating required for a book to be included.
        min_reviews (int): Minimum number of reviews required.
        limit (int): Maximum number of books to return.
        offset (int): Starting point for pagination in the search results.

    Returns:
        List[Book]: A list of Book objects that match the filtering criteria,
                    sorted by rating in descending order.
    """

    collected: List[Book] = []
    current_offset = offset

    while len(collected) < limit:
        raw_batch = search_books_ol(
            genres=genres,
            min_reviews=min_reviews,
            limit=limit,
            offset=current_offset
        )
        if not raw_batch:
            break

        for item in raw_batch:
            avg = item.get("ratings_average") or 0
            if avg >= min_rating:
                collected.append(Book(
                    key=item["key"],
                    title=item.get("title", "Unknown"),
                    authors=item.get("author_name", []),
                    cover_id=item.get("cover_i"),
                    rating=avg,
                    rating_count=item.get("ratings_count", 0),
                    genres=item.get("subject", []),
                    publish_year=item.get("first_publish_year")
                ))
                if len(collected) == limit:
                    break

        if len(collected) < limit:
            current_offset += len(raw_batch)

    collected.sort(key=lambda x: x.rating or 0, reverse=True)
    return collected[:limit]


# ----------------------------------------------------------------------------------------------------------------------
#                                               Author-based
# ----------------------------------------------------------------------------------------------------------------------

def calculate_similarity(target_subjects: Set[str], candidate_subjects: List[str]) -> float:
    """
    Calculate the similarity score between two authors based on overlapping subjects.

    This function compares the set of subjects from a target author with the subjects
    of a candidate author and returns a normalized similarity score based on the proportion
    of shared subjects. If the target author has no subjects, a default base score is returned.

    Args:
        target_subjects (Set[str]): A set of subject tags associated with the target author.
        candidate_subjects (List[str]): A list of subject tags from the candidate author.

    Returns:
        float: A similarity score between 0.0 and 1.0 representing thematic overlap.
               Returns 0.4 if the target has no subjects.
    """
    if not target_subjects:
        return 0.4  # Default base score

    candidate_set = set(candidate_subjects)
    intersection = target_subjects & candidate_set

    base_score = min(1.0, len(intersection) / len(target_subjects))

    return min(1.0, base_score)


def recommend_similar_authors(target_author: str, limit: AUTHOR_LIMIT_DEFAULT) -> List[Author]:
    """
    Recommend authors similar to the given target author based on subject overlap.

    This function first retrieves a set of candidate authors that are thematically related
    to the target author (via shared subject tags). It then calculates a similarity score
    for each candidate using subject intersection and ranks them accordingly.
    Only the top 'limit' most similar authors are returned.

    Steps:
    1. Fetch a set of initial candidates (2 * limit) using subject-based lookup.
    2. Retrieve detailed information for the target author (including subjects).
    3. In parallel, retrieve full data for all candidates.
    4. For each candidate, compute a similarity score based on overlapping subjects.
    5. Sort candidates by score and return the top N results.

    Args:
        target_author (str): Name of the author for whom similar authors are to be recommended.
        limit (int): Number of similar authors to return.

    Returns:
        List[Author]: List of Author objects, each with an assigned similarity_score.
    """
    start = time.perf_counter()
    logger.info(f"Starting recommendation for author: {target_author}")

    candidates = find_similar_authors(target_author, limit=limit * 2)
    logger.debug(f"Initial candidates count: {len(candidates)}")
    if not candidates:
        return []

    target_data = get_author_details(candidates[0]['key'])
    if not target_data:
        return []
    target_subjects = set(s.lower() for s in target_data.subjects)

    results: List[Author] = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_key = {executor.submit(get_author_details, c['key']): c['key'] for c in candidates}
        for future in as_completed(future_to_key):
            author = future.result()
            if not author:
                continue
            score = calculate_similarity(target_subjects, [s.lower() for s in author.subjects])
            author.similarity_score = score
            results.append(author)

    duration = time.perf_counter() - start
    logger.info(f"recommend_similar_authors took {duration:.2f}s")
    return sorted(results, key=lambda x: x.similarity_score, reverse=True)[:limit]



# ----------------------------------------------------------------------------------------------------------------------
#                                               Book-based
# ----------------------------------------------------------------------------------------------------------------------

def recommend_similar_books(
    target_book: str,
    limit: int = 10
) -> List[Dict]:
    """
    Recommend books similar to the given target title based on textual similarity.

    This function finds a list of candidate books using subject overlap with the target book,
    then calculates similarity scores using TF-IDF vectorization and cosine similarity
    between the textual representations of books (title + subjects + author names).

    Args:
        target_book (str): The title of the book to find similar ones for.
        limit (int): Number of similar books to return.

    Returns:
        List[Dict]: A list of books (as dictionaries) sorted by similarity score in descending order.
                    Each result includes a 'score' field indicating the level of similarity (0.0–1.0).
    """
    def doc_to_text(doc: Dict) -> str:
        parts = []
        if t := doc.get('title'):
            parts.append(t)
        for s in doc.get('subject', []):
            if isinstance(s, str):
                parts.append(s)
        for a in doc.get('author_name', []):
            if isinstance(a, str):
                parts.append(a)
        return " ".join(parts)

    offset = 0
    all_candidates = []
    seen_keys = set()
    target_doc = None

    while len(all_candidates) < limit:
        batch = find_similar_books(target_book, limit=limit, offset=offset)
        if not batch:
            break

        if offset == 0 and batch:
            target_doc = getattr(find_similar_books, "_target_cache", None)

        for doc in batch:
            key = doc.get("key")
            if key and key not in seen_keys:
                seen_keys.add(key)
                all_candidates.append(doc)
                if len(all_candidates) == limit:
                    break

        offset += len(batch)

    if not target_doc or not all_candidates:
        return []

    texts = [doc_to_text(target_doc)] + [doc_to_text(doc) for doc in all_candidates]
    vectorizer = TfidfVectorizer()
    tfidf = vectorizer.fit_transform(texts)

    sims = cosine_similarity(tfidf[0:1], tfidf[1:]).flatten()

    scored = []
    for doc, sim in zip(all_candidates, sims):
        scored.append({**doc, "score": float(sim)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]
