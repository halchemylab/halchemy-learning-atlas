from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Tuple

import pandas as pd

from src.books import filter_books, sequence_books
from src.roi import increment_stats


@dataclass(frozen=True)
class RecommendationResult:
    path: pd.DataFrame
    category: Optional[str]
    subcategory: Optional[str]
    level: str
    style: Optional[str]
    depth: str
    notices: Tuple[str, ...] = ()


def execute_recommendation(
    books_df: pd.DataFrame,
    args: Dict[str, Any],
    stats_incrementer: Callable[..., object] = increment_stats,
) -> RecommendationResult:
    """Executes deterministic recommendation logic from LLM-extracted args."""
    category = args.get("category")
    subcategory = args.get("subcategory")
    level = args.get("level", "beginner")
    style = args.get("style")
    depth = args.get("depth", "short")
    notices = []

    filtered = filter_books(
        books_df,
        category=category,
        subcategory=subcategory,
        level=level,
        style_pref=style,
        notices=notices,
    )

    path = sequence_books(filtered, depth=depth)
    if not path.empty:
        minimum_books = 3 if depth == "short" else 5
        if len(path) < minimum_books:
            count = len(path)
            notices.append(
                f'Only {count} matching {"book is" if count == 1 else "books are"} available. '
                f'This {depth} path has fewer than the expected minimum of {minimum_books} books.'
            )
        stats_incrementer(num_books=len(path), category=category)
    else:
        # There is no broader path to show when filtering yields no results.
        notices.clear()

    return RecommendationResult(
        path=path,
        category=category,
        subcategory=subcategory,
        level=level,
        style=style,
        depth=depth,
        notices=tuple(notices),
    )
