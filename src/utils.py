import requests
import streamlit as st

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_book_cover(title, author):
    """
    Fetches the book cover image URL from Google Books API.
    Returns a placeholder image if not found.
    """
    try:
        query = f"intitle:{title}+inauthor:{author}"
        url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults=1"
        response = requests.get(url, timeout=5)
        data = response.json()

        if "items" in data:
            volume_info = data["items"][0].get("volumeInfo", {})
            image_links = volume_info.get("imageLinks", {})
            # Prefer thumbnail, fallback to smallThumbnail
            return image_links.get("thumbnail") or image_links.get("smallThumbnail")
    except Exception:
        pass
    
    # Return None or a specific placeholder URL if you have one
    # For now, we'll return None and handle it in the UI
    return None
