import math
from typing import List, Dict, Optional, Union, Set, Literal
import requests
import logging
from collections import Counter
from itertools import combinations, islice
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
import re
from backend.models import Author
logger = logging.getLogger(__name__)

from backend.config import (
    BOOKS_MIN_REVIEWS_DEFAULT,
    BOOKS_PAGE_LIMIT_DEFAULT,
    BOOKS_OFFSET_DEFAULT,
    AUTHOR_LIMIT_DEFAULT
)

# Global HTTP session for connection pooling
diploma_session = requests.Session()
diploma_session.headers.update({'User-Agent': 'DiplomaProject/1.0'})

# API endpoints
OL_SEARCH_URL = 'https://openlibrary.org/search.json'
OL_AUTHORS_URL = 'https://openlibrary.org/search/authors.json'
OL_AUTHOR_WORKS_URL = 'https://openlibrary.org/authors/{author_key}/works.json'
OL_AUTHOR_DETAILS_URL = 'https://openlibrary.org/authors/{author_key}.json'
OL_SUBJECT_URL = 'https://openlibrary.org/subjects/{subject}.json'


# ----------------------------------------------------------------------------------------------------------------------
#                                               General
# ----------------------------------------------------------------------------------------------------------------------

def get_book_details(work_key: str) -> Dict:
    """
    Retrieve detailed information about a book using its work key.

    This function fetches metadata for a book from the OpenLibrary API, including title,
    subjects, authors, and cover images. Additionally, it queries the Wikipedia REST API
    to extract a short description of the book based on its title.

    Args:
        work_key (str): The unique work identifier of the book (e.g., 'OL12345W').

    Returns:
        Dict: A dictionary containing book metadata including 'key', 'title', 'description',
              'subjects', 'authors', and 'covers'.
    """
    url  = f"https://openlibrary.org/works/{work_key}.json"
    resp = diploma_session.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    authors = []
    for a in data.get("authors", []):
        auth_key = a.get("author", {}).get("key", "").split("/")[-1]
        det = get_author_details(auth_key)
        if det:
            authors.append(det.name)

    raw_wiki    = fetch_wikipedia_summary(data.get("title", ""))
    description = raw_wiki.strip() if raw_wiki else None

    return {
        "key":         work_key,
        "title":       data.get("title"),
        "description": description,
        "subjects":    data.get("subjects", []),
        "authors":     authors,
        "covers":      data.get("covers", []),
    }


def fetch_wikipedia_summary(name: str) -> Optional[str]:
    """
    Fetch a short summary description of a book or author from the Wikipedia REST API.

    This function takes a name (title or author), formats it for a Wikipedia URL,
    and retrieves the corresponding summary text from Wikipedia's REST API.

    Args:
        name (str): The title of the book or name of the author to search for.

    Returns:
        Optional[str]: A short summary text extracted from Wikipedia, or None if the request fails.
    """
    title = name.replace(' ', '_')
    url   = f'https://en.wikipedia.org/api/rest_v1/page/summary/{title}'
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.json().get('extract')
    except Exception:
        return None


# ----------------------------------------------------------------------------------------------------------------------
#                                               Genre-based
# ----------------------------------------------------------------------------------------------------------------------

def search_books_ol(
    genres: Union[str, List[str]],
    min_reviews: int = BOOKS_MIN_REVIEWS_DEFAULT,
    limit: int = BOOKS_PAGE_LIMIT_DEFAULT,
    offset: int = BOOKS_OFFSET_DEFAULT,
) -> List[Dict]:
    """
    Search for books in the OpenLibrary API by genre and minimum number of reviews.

    This function constructs a subject-based query using one or more genre keywords
    and fetches a list of books that have at least the specified number of user ratings.
    Results are filtered and paginated using the given parameters.

    Args:
        genres (Union[str, List[str]]): One or more genre keywords to include in the subject query.
        min_reviews (int): Minimum number of user reviews required to include a book.
        limit (int): Maximum number of results to return per request.
        offset (int): Pagination offset for the search results.

    Returns:
        List[Dict]: A list of raw book data dictionaries returned by the OpenLibrary API.
    """
    if isinstance(genres, str):
        genre_list = [genres]
    else:
        genre_list = genres

    subject_query = ' AND '.join(f'subject:{g}' for g in genre_list)
    params = {
        'q': subject_query,
        'ratings_count': f'[{min_reviews} TO *]',
        'limit': limit,
        'offset': offset,
        'fields': ','.join([
            'key','title','subtitle','author_name',
            'first_publish_year','edition_count','publisher',
            'language','subject','cover_i','ratings_count',
            'ratings_average','isbn'
        ]),
    }

    try:
        resp = requests.get(OL_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get('docs', [])
    except Exception as e:
        logger.error(f"Error searching books: {e}")
        return []


# ----------------------------------------------------------------------------------------------------------------------
#                                               Author-based
# ----------------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=128)
def get_subjects_from_works(author_key: str) -> List[str]:
    """
    Fetch the most frequent subjects from an author's most popular works using the OpenLibrary API.

    This function retrieves up to 50 works by the specified author, sorts them by edition count
    to estimate popularity, and analyzes the top 20 works to extract their subjects.
    It returns the 5 most common subjects across those works. Results are cached for efficiency.

    Args:
        author_key (str): The unique key of the author (e.g., 'OL123A').

    Returns:
        List[str]: A list of the top 5 most frequent subject keywords from the author's works.
    """
    try:
        url = OL_AUTHOR_WORKS_URL.format(author_key=author_key)
        params = {'limit': 50, 'fields': 'subjects,edition_count'}
        data = diploma_session.get(url, params=params, timeout=10).json()
        entries = data.get('entries', [])
        entries.sort(key=lambda x: x.get('edition_count', 0), reverse=True)
        subjects = [s.lower()
                    for work in entries[:20]
                    for s in work.get('subjects', [])
                    if isinstance(s, str)]
        return [subj for subj, _ in Counter(subjects).most_common(5)]
    except Exception as e:
        logger.error(f'Error fetching works subjects for {author_key}: {e}')
        return []


@lru_cache(maxsize=128)
def get_author_details(author_key: str) -> Optional[Author]:
    """
    Retrieve detailed metadata for an author using the OpenLibrary API and Wikipedia.

    This function fetches author information such as name, birth/death dates, subjects,
    biography (from Wikipedia), and other metadata using the author's unique key.
    The result is cached for performance optimization.

    Args:
        author_key (str): The unique key or full URI of the author (e.g., 'OL123A' or '/authors/OL123A').

    Returns:
        Optional[Author]: An Author object with detailed information if successful; otherwise, None.
    """
    try:
        key  = author_key.split('/')[-1]
        url  = OL_AUTHOR_DETAILS_URL.format(author_key=key)
        data = diploma_session.get(url, timeout=15).json()
        raw_wiki = fetch_wikipedia_summary(data.get('name', ''))
        bio = raw_wiki.strip() if raw_wiki else None
        photos   = data.get('photos', [])
        photo_id = photos[0] if photos else None

        return Author(
            key=key,
            name=data.get('name', 'Unknown Author'),
            birth_date=data.get('birth_date'),
            death_date=data.get('death_date'),
            bio=bio,
            works_count=data.get('works_count'),
            subjects=data.get('top_subjects', [])[:5],
            links=data.get('links', []),
            top_work=data.get('top_work'),
            alternate_names=data.get('alternate_names', []),
            rating=data.get('ratings_average'),
            photo_id=photo_id
        )
    except Exception as e:
        logger.error(f'Error fetching author details for {author_key}: {e}')
        return None



def find_similar_authors(target_author: str, limit: AUTHOR_LIMIT_DEFAULT) -> List[Dict]:
    """
    Find authors similar to a target author based on shared subject combinations.

    This function extracts the top subjects associated with the target author and generates
    all possible subject pairs. For each combination, it performs an AND-query search via
    the OpenLibrary API to retrieve authors whose works match those subjects. Authors are scored
    by how frequently they appear across all combinations, and the top results are returned.

    Args:
        target_author (str): The name of the target author for whom similar authors are to be found.
        limit (int): Maximum number of similar authors to return.

    Returns:
        List[Dict]: A list of author dictionaries containing 'name', 'key', and 'score',
                    sorted by descending relevance.
    """
    try:
        params = {'q': target_author, 'limit': 1}
        search_data = diploma_session.get(OL_AUTHORS_URL, params=params, timeout=10).json()
        docs = search_data.get('docs', [])
        if not docs:
            return []
        primary = docs[0]
        primary_key = primary.get('key', '').split('/')[-1]

        target_subs = [s.lower() for s in primary.get('top_subjects', [])]
        if not target_subs:
            target_subs = get_subjects_from_works(primary_key)
        if not target_subs:
            target_subs = ['science']
        logger.debug(f"Target subjects for {target_author}: {target_subs}")

        combos = list(combinations(target_subs, 2))
        if not combos:
            combos = [(s,) for s in target_subs]

        def fetch_combo_authors(combo):
            """
            Fetch authors whose works match a specific combination of subjects.

            This function constructs an AND-based subject query and sends a request to the OpenLibrary API
            to find authors who have written works that match all subjects in the given combination.

            Args:
                combo (Tuple[str, ...]): A tuple containing one or more subject keywords.

            Returns:
                List[Dict]: A list of raw author data dictionaries matching the subject combination.
            """
            query = ' AND '.join(f'subject:"{s}"' for s in combo)
            url = OL_SEARCH_URL
            params = {
                'q': query,
                'limit': 50,
                'fields': 'author_key,author_name'
            }
            return diploma_session.get(url, params=params, timeout=10).json().get('docs', [])

        author_scores = Counter()
        author_names: Dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(fetch_combo_authors, combo): combo for combo in combos}
            for future in as_completed(futures):
                try:
                    docs = future.result()
                    for doc in docs:
                        keys = doc.get('author_key') or []
                        names = doc.get('author_name') or []
                        if not keys or not names:
                            continue
                        key = keys[0].split('/')[-1]
                        if key.lower() == primary_key.lower():
                            continue
                        author_scores[key] += 1
                        author_names[key] = names[0]
                except Exception as e:
                    logger.error(f"Error fetching combo result: {e}")

        results = []
        for key, score in author_scores.most_common(limit):
            results.append({'name': author_names.get(key), 'key': key, 'score': score})
        return results

    except Exception as e:
        logger.error(f'Error finding similar authors: {e}')
        return []


# ----------------------------------------------------------------------------------------------------------------------
#                                               Book-based
# ----------------------------------------------------------------------------------------------------------------------

def find_similar_books(
    target_book: str,
    limit: int = 10,
    offset: int = 0,
    max_subjects: int = 10
) -> List[Dict]:
    """
    Find books similar to a given title based on shared subjects from OpenLibrary.

    This function first retrieves the target book and extracts its top subjects.
    It then searches for books that share those subjects using OR-based queries and ranks
    them by subject overlap. About 70% of the returned results are required to share at least
    70% of the target's subjects (strict match), and the remaining 30% may share fewer subjects
    (exploratory match). Books with the same title or key as the original are excluded.

    Args:
        target_book (str): Title of the book to base the similarity search on.
        limit (int): Maximum number of similar books to return.
        offset (int): Offset for paginated API requests.
        max_subjects (int): Maximum number of subjects to consider from the target book.

    Returns:
        List[Dict]: A list of dictionaries representing similar books,
                    each including a 'ratio' field indicating subject overlap.
    """
    try:
        if offset == 0:
            resp = diploma_session.get(
                OL_SEARCH_URL,
                params={'q': target_book, 'limit': 1, 'fields': 'key,title,subject'},
                timeout=10
            )
            if not resp.ok:
                logger.error(f"Lookup error for '{target_book}': {resp.status_code}")
                return []
            docs = resp.json().get('docs', [])
            if not docs:
                return []

            target = docs[0]
            find_similar_books._target_cache = target
        else:
            target = getattr(find_similar_books, "_target_cache", None)
            if target is None:
                logger.error("Offset > 0 but target book metadata not cached.")
                return []

        target_key = target.get('key')
        user_query = target_book.lower().strip()

        raw_subjects = [s for s in target.get('subject', []) if isinstance(s, str)]
        if not raw_subjects:
            return []

        top_subjects = raw_subjects[:max_subjects]
        target_set = {s.lower() for s in top_subjects}

        or_clause = " OR ".join(f'subject:"{s}"' for s in top_subjects)
        pool_resp = diploma_session.get(
            OL_SEARCH_URL,
            params={
                'q': or_clause,
                'limit': limit * 10,
                'offset': offset,
                'fields': 'key,title,author_name,subject,cover_i,ratings_count,ratings_average'
            },
            timeout=15
        )
        if not pool_resp.ok:
            logger.error(f"Search pool error: {pool_resp.status_code} for query {or_clause}")
            return []
        pool = pool_resp.json().get('docs', [])

        candidates = []
        seen = set()
        for doc in pool:
            key = doc.get('key')
            title = (doc.get('title') or "").lower()

            if not key or key == target_key or key in seen or (user_query and user_query in title):
                continue
            seen.add(key)

            cand_subjects = {s.lower() for s in doc.get('subject', []) if isinstance(s, str)}
            ratio = len(target_set & cand_subjects) / len(target_set) if target_set else 0.0
            candidates.append({**doc, 'ratio': ratio})

        strict = [c for c in candidates if c['ratio'] >= 0.7]
        explore = [c for c in candidates if 0 < c['ratio'] < 0.7]

        strict_n = math.ceil(limit * 0.7)
        explore_n = limit - strict_n

        strict.sort(key=lambda x: x['ratio'], reverse=True)
        explore.sort(key=lambda x: x['ratio'], reverse=True)

        selected = strict[:strict_n]
        if len(selected) < strict_n:
            explore_n += (strict_n - len(selected))
        selected += explore[:explore_n]

        if len(selected) < limit:
            extras = strict[strict_n:] + explore[explore_n:]
            selected += extras[: limit - len(selected)]

        return selected[:limit]

    except Exception as e:
        logger.error(f"Error finding similar books for '{target_book}': {e}", exc_info=True)
        return []