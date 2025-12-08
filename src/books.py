import pandas as pd
import os
from typing import List, Dict, Optional

# Constants for file paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
BOOKS_FILE = os.path.join(DATA_DIR, 'books.csv')

def load_books() -> pd.DataFrame:
    """Loads the books dataset from the CSV file."""
    try:
        df = pd.read_csv(BOOKS_FILE)
        # Ensure boolean columns are actually booleans
        bool_cols = ['is_beginner_friendly', 'is_intermediate', 'is_advanced']
        for col in bool_cols:
            if col in df.columns:
                 df[col] = df[col].astype(bool)
        return df
    except FileNotFoundError:
        # In production, you might log this error
        return pd.DataFrame()

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

    # 1. Filter by Category
    # Case-insensitive matching
    filtered = df[df['category'].str.lower() == category.lower()].copy()
    
    # 2. Filter by Subcategory (if provided and exists in data)
    if subcategory and not filtered.empty:
        # Only filter if the subcategory actually has matches, otherwise stay broad
        sub_matches = filtered[filtered['subcategory'].str.lower() == subcategory.lower()]
        if not sub_matches.empty:
            filtered = sub_matches

    # 3. Filter by Level (inclusive)
    # If beginner, we want is_beginner_friendly = True
    # If intermediate, we want is_intermediate = True
    # If advanced, we want is_advanced = True
    if not filtered.empty:
        if level == "beginner":
            filtered = filtered[filtered['is_beginner_friendly'] == True]
        elif level == "intermediate":
            filtered = filtered[filtered['is_intermediate'] == True]
        elif level == "advanced":
            filtered = filtered[filtered['is_advanced'] == True]

    # 4. Filter by Style (soft filter - prefer if possible, but don't empty the list)
    if style_pref and not filtered.empty:
        style_matches = filtered[filtered['style'].str.lower() == style_pref.lower()]
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
        # Sort chronological if possible
        # Note: chronology_hint might be mixed strings/ints. 
        # For MVP, we'll try to coerce to numeric or just rely on ID/metadata order if complex.
        # Let's try a simple approach: separate 'Ancient' vs years.
        # For now, let's sort by difficulty as a proxy for accessibility, or keep original order
        # if curated well.
        # A better MVP heuristic: Sort by 'chronology_hint' treating it as string for now,
        # or rely on difficulty for entry point.
        candidates = candidates.sort_values(by=['chronology_hint', 'difficulty'], ascending=[True, True])
        
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
    hints = {
        "habits": "Focus on **one small change** at a time. Don't try to read all these at once; pick the first one, implement a single micro-habit (e.g., 'floss one tooth'), and track it for 2 weeks before adding more.",
        "coding": "Reading code is different from reading prose. **Type out the examples** manually (don't copy-paste). Build a tiny project after each chapter to cement the concepts.",
        "history": "Create a **timeline** as you read. Note down the key players and their motivations. History is about cause and effect, not just dates.",
        "cooking": "**Mise en place** is your best friend. Read the whole recipe before you start. Try cooking the same simple dish 3 times in a row to truly master the technique.",
        "productivity": "Productivity isn't about doing *more*, it's about doing the *right* things. Pick **one system** (like GTD or Deep Work) and stick to it for 30 days. consistency beats intensity.",
        "business": "Take notes on **mental models**. Ask yourself: 'How can I apply this principle to my current project or team?' Business books are toolkits, not novels."
    }
    return hints.get(category.lower(), "Read actively. Take notes, highlight key passages, and try to explain the concepts to someone else to test your understanding.")
