"""Ready-made paths built exclusively from the curated library."""

from src.books import get_hint_for_category


STARTER_PATHS = (
    {
        "id": "python",
        "title": "Learn Python",
        "audience": "Beginner to advanced",
        "goal": "Learn the basics, automate everyday tasks, then explore advanced Python.",
        "category": "coding",
        "subcategory": "python",
        "book_ids": (4, 5, 6),
        "rationale": "Start with Python Crash Course for the fundamentals, then apply them with Automate the Boring Stuff with Python. Fluent Python is an advanced stretch goal to return to after building a few projects.",
    },
    {
        "id": "habits",
        "title": "Build Better Habits",
        "audience": "Beginner",
        "goal": "Understand how habits work and build a small routine you can sustain.",
        "category": "habits",
        "subcategory": None,
        "book_ids": (3, 1, 2),
        "rationale": "The Power of Habit introduces how habits work. Atomic Habits turns those ideas into a practical system, and Tiny Habits helps you start small and practice consistently.",
    },
    {
        "id": "history",
        "title": "Understand World History",
        "audience": "Beginner",
        "goal": "Start with a broad human history, then explore selected eras in more detail.",
        "category": "history",
        "subcategory": None,
        "book_ids": (23, 46, 44, 20),
        "rationale": "Sapiens provides a broad overview before you explore selected eras: the Mongol empire, the American Revolution, and the Second World War. These focused histories progress through time; this is a starting point rather than a complete world history survey.",
    },
)


def build_starter_path(books_df, starter_id):
    """Resolve curated IDs in their editorial order for the editor and exports."""
    starter = next(path for path in STARTER_PATHS if path["id"] == starter_id)
    indexed = books_df.set_index("id", drop=False)
    books = indexed.loc[list(starter["book_ids"])].to_dict("records")
    return {
        "title": starter["title"],
        "category": starter["category"],
        "subcategory": starter["subcategory"],
        "level": "beginner",
        "style": None,
        "depth": "short" if len(books) == 3 else "deep",
        "user_query": starter["goal"],
        "books": books,
        "rationale": starter["rationale"],
        "rationale_stale": False,
        "hint": get_hint_for_category(starter["category"]),
    }
