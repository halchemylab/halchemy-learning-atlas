from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

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

    filtered = filter_books(
        books_df,
        category=category,
        subcategory=subcategory,
        level=level,
        style_pref=style,
    )

    path = sequence_books(filtered, depth=depth)
    if not path.empty:
        stats_incrementer(num_books=len(path), category=category)

    return RecommendationResult(
        path=path,
        category=category,
        subcategory=subcategory,
        level=level,
        style=style,
        depth=depth,
    )
