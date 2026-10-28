import logging
from concurrent.futures import ThreadPoolExecutor

import requests
import streamlit as st


logger = logging.getLogger(__name__)

def fetch_book_cover(title, author):
    """
    Fetches the book cover image URL from Google Books API.
    Returns a placeholder image if not found.
    """
    query = f"intitle:{title}+inauthor:{author}"
    url = "https://www.googleapis.com/books/v1/volumes"
    params = {"q": query, "maxResults": 1}

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
    except requests.Timeout:
        logger.warning("Timed out fetching cover for %s by %s", title, author)
        return None
    except requests.RequestException as exc:
        logger.warning("Google Books cover request failed for %s by %s: %s", title, author, exc)
        return None
    except ValueError as exc:
        logger.warning("Google Books returned invalid JSON for %s by %s: %s", title, author, exc)
        return None

    items = data.get("items", [])
    if items:
        volume_info = items[0].get("volumeInfo", {})
        image_links = volume_info.get("imageLinks", {})
        # Prefer thumbnail, fallback to smallThumbnail
        return image_links.get("thumbnail") or image_links.get("smallThumbnail")
    
    # Return None or a specific placeholder URL if you have one
    # For now, we'll return None and handle it in the UI
    return None


@st.cache_data(show_spinner=False, ttl=3600, max_entries=128)
def fetch_book_covers(books):
    """Fetch a path's covers concurrently without Streamlit calls in workers."""
    if not books:
        return []
    with ThreadPoolExecutor(max_workers=min(12, len(books))) as executor:
        futures = [executor.submit(fetch_book_cover, title, author) for title, author in books]
        return [future.result() for future in futures]
