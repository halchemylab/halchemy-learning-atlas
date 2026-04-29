from typing import Dict, List, Optional

import pandas as pd

from src.books import filter_books


Book = Dict[str, object]


def move_book(books: List[Book], index: int, direction: int) -> List[Book]:
    """Returns a copy of books with one item moved up or down."""
    updated = list(books)
    target_index = index + direction

    if index < 0 or index >= len(updated):
        return updated
    if target_index < 0 or target_index >= len(updated):
        return updated

    updated[index], updated[target_index] = updated[target_index], updated[index]
    return updated


def remove_book(books: List[Book], index: int) -> List[Book]:
    """Returns a copy of books with the requested index removed."""
    if index < 0 or index >= len(books):
        return list(books)

    return [book for i, book in enumerate(books) if i != index]


def replace_book(books: List[Book], index: int, replacement: Book) -> List[Book]:
    """Returns a copy of books with one item replaced."""
    updated = list(books)
    if index < 0 or index >= len(updated):
        return updated

    updated[index] = replacement
    return updated


def get_replacement_candidates(
    df: pd.DataFrame,
    current_books: List[Book],
    category: str,
    subcategory: Optional[str] = None,
    level: str = "beginner",
    style: Optional[str] = None,
) -> List[Book]:
    """Finds matching books that are not already in the current path."""
    if df.empty:
        return []

    candidates = filter_books(
        df,
        category=category,
        subcategory=subcategory,
        level=level,
        style_pref=style,
    )

    if candidates.empty:
        return []

    current_ids = {str(book.get("id")) for book in current_books}
    available = candidates[~candidates["id"].astype(str).isin(current_ids)].copy()
    if available.empty:
        return []

    available = available.sort_values(
        by=["difficulty", "readability"],
        ascending=[True, False],
    )
    return available.to_dict("records")
