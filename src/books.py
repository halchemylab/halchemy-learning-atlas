import pandas as pd
import os
import re
from typing import List, Mapping, Optional

# Constants for file paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
BOOKS_FILE = os.path.join(DATA_DIR, 'books.csv')
BOOL_COLS = ['is_beginner_friendly', 'is_intermediate', 'is_advanced']

class DataLoadingError(Exception):
    """Exception raised for errors in loading the books dataset."""
    pass


def _parse_bool(value: object) -> bool:
    """Parses CSV-friendly boolean values without treating every string as true."""
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False

    normalized = str(value).strip().lower()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n", ""}:
        return False

    raise ValueError(f"Invalid boolean value: {value}")


def normalize_books(df: pd.DataFrame) -> pd.DataFrame:
    """Normalizes loaded book data into the types expected by the recommender."""
    normalized = df.copy()
    for col in BOOL_COLS:
        if col in normalized.columns:
            normalized[col] = normalized[col].map(_parse_bool)
    return normalized


def validate_books(df: pd.DataFrame) -> None:
    """Validates the books DataFrame schema and content."""
    required_cols = [
        'id', 'title', 'author', 'category', 'subcategory', 
        'difficulty', 'readability', 'style', 'learning_type',
        'short_description', 'store_url',
        'is_beginner_friendly', 'is_intermediate', 'is_advanced'
    ]
    
    # Check missing columns
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Dataset missing required columns: {missing}")

    # Check numeric ranges
    if not df['difficulty'].between(1, 5).all():
        raise ValueError("Column 'difficulty' contains values outside 1-5 range")
        
    if not df['readability'].between(1, 5).all():
        raise ValueError("Column 'readability' contains values outside 1-5 range")

    # Check unique IDs
    if not df['id'].is_unique:
        raise ValueError("Duplicate book IDs found")

    for col in BOOL_COLS:
        if not df[col].map(lambda value: isinstance(value, bool)).all():
            raise ValueError(f"Column '{col}' contains non-boolean values")

def load_books() -> pd.DataFrame:
    """Loads and validates the books dataset from the CSV file."""
    if not os.path.exists(BOOKS_FILE):
        raise DataLoadingError(f"Books data file not found at: {BOOKS_FILE}")

    try:
        df = normalize_books(pd.read_csv(BOOKS_FILE))
        
        validate_books(df)
        return df
    except Exception as e:
        raise DataLoadingError(f"Failed to load books library: {e}")

def filter_books(
    df: pd.DataFrame,
    category: str,
    subcategory: Optional[str] = None,
    level: str = "beginner",
    style_pref: Optional[str] = None
) -> pd.DataFrame:
    """
    Filters the book dataframe based on user criteria.
    
    Args:
        df: The full books DataFrame.
        category: Main topic (e.g., 'habits', 'coding').
        subcategory: Specific topic (e.g., 'python').
        level: User's skill level ('beginner', 'intermediate', 'advanced').
        style_pref: Preferred style (e.g., 'tactical/how-to', 'story-driven').
    """
    if df.empty:
        return df
    if not category:
        return df.iloc[0:0].copy()

    # 1. Filter by Category
    # Case-insensitive matching
    category_key = str(category).strip().lower()
    filtered = df[df['category'].fillna('').str.lower() == category_key].copy()
    
    # 2. Filter by Subcategory (if provided and exists in data)
    if subcategory and not filtered.empty:
        # Only filter if the subcategory actually has matches, otherwise stay broad
        subcategory_key = str(subcategory).strip().lower()
        sub_matches = filtered[filtered['subcategory'].fillna('').str.lower() == subcategory_key]
        if not sub_matches.empty:
            filtered = sub_matches

    # 3. Filter by Level (inclusive)
    # If beginner, we want is_beginner_friendly = True
    # If intermediate, we want is_intermediate = True
    # If advanced, we want is_advanced = True
    if not filtered.empty:
        level_key = str(level or "").strip().lower()
        if level_key == "beginner":
            filtered = filtered[filtered['is_beginner_friendly'] == True]
        elif level_key == "intermediate":
            filtered = filtered[filtered['is_intermediate'] == True]
        elif level_key == "advanced":
            filtered = filtered[filtered['is_advanced'] == True]

    # 4. Filter by Style (soft filter - prefer if possible, but don't empty the list)
    if style_pref and not filtered.empty:
        style_key = str(style_pref).strip().lower()
        style_matches = filtered[filtered['style'].fillna('').str.lower() == style_key]
        # If we have enough matches with the style, use them. 
        # Otherwise, keep the mixed bag so we don't return 0 results.
        if len(style_matches) >= 3:
            filtered = style_matches

    return filtered

def sequence_books(
    df: pd.DataFrame,
    depth: str = "short"
) -> pd.DataFrame:
    """
    Sequences the filtered books into a logical learning path.
    
    Args:
        df: Filtered DataFrame of candidate books.
        depth: 'short' (3 books) or 'deep' (5-7 books).
    """
    if df.empty:
        return df
    
    # Copy to avoid modifying original
    candidates = df.copy()
    
    # Determine sort order based on dominant learning_type in the set
    # (Heuristic: look at the first few rows or mode)
    learning_type = candidates['learning_type'].mode()[0] if not candidates['learning_type'].empty else 'conceptual'
    
    # Sorting Logic
    if learning_type == 'procedural-skill':
        # Sort by difficulty (easier -> harder), then readability (higher -> lower)
        candidates = candidates.sort_values(by=['difficulty', 'readability'], ascending=[True, False])
        
    elif learning_type == 'narrative-history':
        if 'chronology_hint' in candidates.columns:
            candidates = candidates.assign(
                _chronology_sort=candidates['chronology_hint'].map(_chronology_sort_value)
            )
            candidates = candidates.sort_values(
                by=['_chronology_sort', 'difficulty'],
                ascending=[True, True],
            ).drop(columns=['_chronology_sort'])
        else:
            candidates = candidates.sort_values(by=['difficulty', 'readability'], ascending=[True, False])
        
    elif learning_type == 'behavioral-skill':
        # Habits/Leadership: Fundamentals (low difficulty) -> Application (tactical)
        candidates = candidates.sort_values(by=['difficulty', 'readability'], ascending=[True, False])
        
    else:
        # Default: Sort by difficulty then readability
        candidates = candidates.sort_values(by=['difficulty', 'readability'], ascending=[True, False])

    # Limit number of books
    limit = 3 if depth == "short" else 7
    return candidates.head(limit)

def get_unique_values(df: pd.DataFrame, column: str) -> List[str]:
    """Returns sorted unique values for a column, excluding nulls."""
    if df.empty or column not in df.columns:
        return []
    return sorted(df[column].dropna().unique().tolist())

def get_hint_for_category(category: str) -> str:
    """Returns domain-specific advice for the result page."""
    category_key = str(category or "").lower()
    hints = {
        "habits": "Focus on **one small change** at a time. Don't try to read all these at once; pick the first one, implement a single micro-habit (e.g., 'floss one tooth'), and track it for 2 weeks before adding more.",
        "coding": "Reading code is different from reading prose. **Type out the examples** manually (don't copy-paste). Build a tiny project after each chapter to cement the concepts.",
        "history": "Create a **timeline** as you read. Note down the key players and their motivations. History is about cause and effect, not just dates.",
        "cooking": "**Mise en place** is your best friend. Read the whole recipe before you start. Try cooking the same simple dish 3 times in a row to truly master the technique.",
        "productivity": "Productivity isn't about doing *more*, it's about doing the *right* things. Pick **one system** (like GTD or Deep Work) and stick to it for 30 days. consistency beats intensity.",
        "business": "Take notes on **mental models**. Ask yourself: 'How can I apply this principle to my current project or team?' Business books are toolkits, not novels."
    }
    return hints.get(category_key, "Read actively. Take notes, highlight key passages, and try to explain the concepts to someone else to test your understanding.")


def get_purchase_url(book: Mapping[str, object]) -> Optional[str]:
    """Returns the preferred purchase URL, favoring affiliate links when available."""
    for field in ("affiliate_url", "store_url"):
        value = book.get(field)
        if pd.notna(value) and str(value).strip():
            return str(value).strip()
    return None


def _chronology_sort_value(value: object) -> int:
    """Converts chronology hints to sortable values with unknowns at the end."""
    if pd.isna(value) or str(value).strip() == "":
        return 10**9

    text = str(value).strip().lower()
    if text in {"ancient", "prehistory", "prehistoric"}:
        return -10**9

    match = re.search(r"-?\d+", text)
    if not match:
        return 10**9

    year = int(match.group(0))
    if "bc" in text or "bce" in text:
        return -abs(year)
    return year
