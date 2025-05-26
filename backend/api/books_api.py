import requests
import os
import time
from typing import Optional
from backend.config import GOOGLE_BOOKS_URL, API_KEY

if not GOOGLE_BOOKS_URL or not API_KEY:
    raise RuntimeError("GOOGLE_BOOKS_URL or API_KEY is not set in config")


def parse_volume_item(item: dict) -> dict:
    """
    Normalize a single Google Books API volume item into a consistent dict.
    """
    info = item.get("volumeInfo", {}) or {}
    image_links = info.get("imageLinks", {}) or {}
    thumbnail = image_links.get("thumbnail") or image_links.get("smallThumbnail")

    return {
        "id": item.get("id"),
        "title": info.get("title", ""),
        "authors": info.get("authors", []),
        "publisher": info.get("publisher", ""),
        "description": info.get("description", ""),
        "pageCount": info.get("pageCount"),
        "categories": info.get("categories", []),
        "averageRating": info.get("averageRating"),
        "ratingsCount": info.get("ratingsCount"),
        "language": info.get("language", ""),
        "thumbnail": thumbnail,
        "infoLink": info.get("infoLink", ""),
        "previewLink": info.get("previewLink", ""),
        "canonicalLink": info.get("canonicalVolumeLink", ""),
    }


def search_books(query: str, max_results: int = 20) -> list[dict]:
    """
    Search for books using Google Books API by arbitrary query string.
    Returns a list of normalized book dictionaries.
    """
    params = {
        "q": query,
        "key": API_KEY,
        "maxResults": max_results,
    }
    try:
        response = requests.get(GOOGLE_BOOKS_URL, params=params)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        # On network errors or rate limits, return an empty list
        return []

    data = response.json()
    raw_items = data.get("items", []) or []
    return [parse_volume_item(item) for item in raw_items]


def get_book_by_isbn(isbn: str) -> Optional[dict]:
    """
    Search for a book by ISBN in the Google Books API.
    Returns the first normalized book dict or None.
    Retries once on HTTP 429 Too Many Requests.
    """
    params = {
        "q": f"isbn:{isbn}",
        "key": API_KEY,
        "maxResults": 1,
    }
    for attempt in range(2):
        try:
            response = requests.get(GOOGLE_BOOKS_URL, params=params)
            response.raise_for_status()
            items = response.json().get("items") or []
            if not items:
                return None
            return parse_volume_item(items[0])
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else None
            if status == 429 and attempt == 0:
                # Wait and retry once on rate limit
                time.sleep(1)
                continue
            # On other errors or second failure, abort
            return None
    return None


def get_best_edition(doc: dict) -> Optional[dict]:
    """
    Given an OpenLibrary record with ISBNs and title,
    return the edition with the first non-null averageRating.
    If no rated edition found, fallback to searching by title.
    """
    isbns = doc.get("isbn", []) or []
    first_candidate = None

    # Try each ISBN for a rated edition
    for isbn in isbns:
        book = get_book_by_isbn(isbn)
        if book is None:
            continue
        if first_candidate is None:
            first_candidate = book
        if book.get("averageRating") is not None:
            return book

    # Fallback: search by title if ratings not found by ISBN
    title = doc.get("title") or doc.get("title_suggest")
    if title:
        params = {"q": f'intitle:"{title}"', "key": API_KEY, "maxResults": 1}
        try:
            resp = requests.get(GOOGLE_BOOKS_URL, params=params)
            resp.raise_for_status()
            items = resp.json().get("items") or []
            if items:
                return parse_volume_item(items[0])
        except requests.exceptions.HTTPError:
            pass

    return first_candidate