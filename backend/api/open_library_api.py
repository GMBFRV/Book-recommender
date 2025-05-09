import math
from typing import List, Dict, Optional, Union, Set
import requests
import logging
from collections import Counter
from itertools import combinations, islice
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote

from backend.models import Author

logger = logging.getLogger(__name__)

# Global HTTP session for connection pooling
diploma_session = requests.Session()
diploma_session.headers.update({'User-Agent': 'DiplomaProject/1.0'})

# API endpoints
OL_SEARCH_URL = 'https://openlibrary.org/search.json'
OL_AUTHORS_URL = 'https://openlibrary.org/search/authors.json'
OL_AUTHOR_WORKS_URL = 'https://openlibrary.org/authors/{author_key}/works.json'
OL_AUTHOR_DETAILS_URL = 'https://openlibrary.org/authors/{author_key}.json'
OL_SUBJECT_URL = 'https://openlibrary.org/subjects/{subject}.json'


def search_books_ol(
    genres: Union[str, List[str]],
    min_reviews: int = 50,
    limit: int = 100,
) -> List[Dict]:
    if isinstance(genres, str):
        genre_list = [genres]
    else:
        genre_list = genres
    subject_query = ' AND '.join(f'subject:{g}' for g in genre_list)
    params = {
        'q': subject_query,
        'ratings_count': f'[{min_reviews} TO *]',
        'limit': limit,
        'fields': ','.join([
            'key', 'title', 'subtitle', 'author_name',
            'first_publish_year', 'edition_count', 'publisher',
            'language', 'subject', 'cover_i', 'ratings_count',
            'ratings_average', 'isbn'
        ]),
    }
    try:
        resp = requests.get(OL_SEARCH_URL, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json().get('docs', [])
    except Exception as e:
        logger.error(f'Error searching books: {e}')
        return []

@lru_cache(maxsize=128)
def get_subjects_from_works(author_key: str) -> List[str]:
    """Fetch top subjects from an author's works, caching results."""
    try:
        url = OL_AUTHOR_WORKS_URL.format(author_key=author_key)
        params = {'limit': 50, 'fields': 'subjects,edition_count'}
        data = diploma_session.get(url, params=params, timeout=10).json()
        entries = data.get('entries', [])
        # sort by popularity
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
    """Fetch detailed author info and subjects, caching results."""
    try:
        key = author_key.split('/')[-1]
        url = OL_AUTHOR_DETAILS_URL.format(author_key=key)
        data = diploma_session.get(url, timeout=15).json()
        # prefer top_subjects, then subjects, then derive from works
        subs = data.get('top_subjects') or data.get('subjects') or get_subjects_from_works(key) or ['science']
        subjects = [s.lower() for s in subs][:5]
        return Author(
            key=key,
            name=data.get('name', 'Unknown Author'),
            birth_date=data.get('birth_date'),
            death_date=data.get('death_date'),
            bio=(data.get('bio', {}).get('value')
                 if isinstance(data.get('bio'), dict)
                 else data.get('bio')),
            works_count=data.get('works_count'),
            subjects=subjects,
            links=data.get('links', []),
            top_work=data.get('top_work'),
            alternate_names=data.get('alternate_names', []),
            rating=data.get('ratings_average')
        )
    except Exception as e:
        logger.error(f'Error fetching author details for {author_key}: {e}')
        return None


def find_similar_authors(target_author: str, limit: int = 5) -> List[Dict]:
    """
    Find authors similar to target by combining AND-queries on subject pairs
    and ranking by frequency of occurrence.
    """
    try:
        # 1. Fetch primary author
        params = {'q': target_author, 'limit': 1}
        search_data = diploma_session.get(OL_AUTHORS_URL, params=params, timeout=10).json()
        docs = search_data.get('docs', [])
        if not docs:
            return []
        primary = docs[0]
        primary_key = primary.get('key', '').split('/')[-1]

        # 2. Get author subjects
        target_subs = [s.lower() for s in primary.get('top_subjects', [])]
        if not target_subs:
            target_subs = get_subjects_from_works(primary_key)
        if not target_subs:
            target_subs = ['science']
        logger.debug(f"Target subjects for {target_author}: {target_subs}")

        # 3. Prepare subject combinations (pairs)
        combos = list(combinations(target_subs, 2))
        if not combos:
            combos = [(s,) for s in target_subs]

        # 4. Define worker for a combo
        def fetch_combo_authors(combo):
            query = ' AND '.join(f'subject:"{s}"' for s in combo)
            url = OL_SEARCH_URL
            params = {
                'q': query,
                'limit': 50,
                'fields': 'author_key,author_name'
            }
            return diploma_session.get(url, params=params, timeout=10).json().get('docs', [])

        # 5. Parallel fetch
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

        # 6. Build and return top authors
        results = []
        for key, score in author_scores.most_common(limit):
            results.append({'name': author_names.get(key), 'key': key, 'score': score})
        return results

    except Exception as e:
        logger.error(f'Error finding similar authors: {e}')
        return []





def find_similar_books(
    target_book: str,
    limit: int = 10,
    max_subjects: int = 10
) -> List[Dict]:
    """
    Find similar books: ~70% share ≥70% of target subjects,
    ~30% share at least one subject, excluding any whose title
    contains the original query string.
    """
    try:
        # 1. Lookup the target book and its subjects
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
        target_key = target.get('key')
        user_query = target_book.lower().strip()

        raw_subjects = [s for s in target.get('subject', []) if isinstance(s, str)]
        if not raw_subjects:
            return []

        # 2. Limit subjects to avoid overly long URLs
        top_subjects = raw_subjects[:max_subjects]
        target_set = {s.lower() for s in top_subjects}

        # 3. Single OR‐query for broad candidate pool
        or_clause = " OR ".join(f'subject:"{s}"' for s in top_subjects)
        pool_resp = diploma_session.get(
            OL_SEARCH_URL,
            params={
                'q': or_clause,
                'limit': limit * 10,
                'fields': 'key,title,author_name,subject, cover_i,ratings_count,ratings_average'
            },
            timeout=15
        )
        if not pool_resp.ok:
            logger.error(f"Search pool error: {pool_resp.status_code} for query {or_clause}")
            return []
        pool = pool_resp.json().get('docs', [])

        # 4. Compute overlap and filter out same‐titled books
        candidates = []
        seen = set()
        for doc in pool:
            key = doc.get('key')
            title = (doc.get('title') or "").lower()

            # exclude the exact same record or any title containing the original query
            if (
                not key
                or key == target_key
                or key in seen
                or (user_query and user_query in title)
            ):
                continue
            seen.add(key)

            cand_subjects = {s.lower() for s in doc.get('subject', []) if isinstance(s, str)}
            ratio = len(target_set & cand_subjects) / len(target_set) if target_set else 0.0
            candidates.append({**doc, 'ratio': ratio})

        # 5. Split into strict (≥70%) and exploratory (<70%)
        strict = [c for c in candidates if c['ratio'] >= 0.7]
        explore = [c for c in candidates if 0 < c['ratio'] < 0.7]

        # 6. Determine counts for each group
        strict_n = math.ceil(limit * 0.7)
        explore_n = limit - strict_n

        strict.sort(key=lambda x: x['ratio'], reverse=True)
        explore.sort(key=lambda x: x['ratio'], reverse=True)

        # 7. Pick top from each, topping up if necessary
        selected = strict[:strict_n]
        if len(selected) < strict_n:
            # not enough strict → take more from explore
            explore_n += (strict_n - len(selected))
        selected += explore[:explore_n]

        # 8. If still short, draw extras from remaining candidates
        if len(selected) < limit:
            extras = strict[strict_n:] + explore[explore_n:]
            selected += extras[: limit - len(selected)]

        return selected[:limit]

    except Exception as e:
        logger.error(f"Error finding similar books for '{target_book}': {e}", exc_info=True)
        return []
