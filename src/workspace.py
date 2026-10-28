"""Session-local path revisions shared by buttons and conversational actions."""

from copy import deepcopy
import json
import math


MAX_REVISIONS = 20


def json_text(value):
    """Encode catalog NaNs as null in workspace snapshots and tool results."""
    def clean(item):
        if isinstance(item, dict):
            return {key: clean(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            return [clean(val) for val in item]
        if isinstance(item, float) and not math.isfinite(item):
            return None
        return item
    return json.dumps(clean(value), ensure_ascii=False, allow_nan=False)


def describe_changes(previous, current):
    """Describe actual book changes without relying on a model's claims."""
    before = (previous or {}).get("books", [])
    after = (current or {}).get("books", [])
    old = {str(book["id"]): (i, book) for i, book in enumerate(before, 1)}
    new = {str(book["id"]): (i, book) for i, book in enumerate(after, 1)}
    changes = []
    for key, (position, book) in old.items():
        if key not in new:
            changes.append(f"Removed: {book['title']}")
    for key, (position, book) in new.items():
        if key not in old:
            changes.append(f"Added at step {position}: {book['title']}")
        elif old[key][0] != position:
            changes.append(f"Moved {book['title']}: step {old[key][0]} → {position}")
    if previous and current and previous.get("user_query") != current.get("user_query"):
        changes.append("Updated your learning goal.")
    return changes


def commit_path(state, path, summary):
    """Snapshot the entire old path before publishing a new independent value."""
    previous = state.get("current_path_data")
    if previous == path:
        return False
    history = list(state.get("path_history", []))
    history.append({"path": deepcopy(previous), "summary": summary})
    state["path_history"] = history[-MAX_REVISIONS:]
    state["current_path_data"] = deepcopy(path)
    state["last_path_change"] = {
        "summary": summary,
        "details": describe_changes(previous, path),
    }
    return True


def edit_books(state, books, summary="Updated your reading path."):
    """Route manual edits through the same revision boundary as chat edits."""
    current = deepcopy(state.get("current_path_data"))
    if current is None:
        raise ValueError("Build a reading path before editing it.")
    if current["books"] == books:
        return False
    current["books"] = deepcopy(books)
    current["rationale_stale"] = True
    return commit_path(state, current, summary)


def undo_path(state):
    """Restore books, goal, metadata, and explanation together."""
    history = list(state.get("path_history", []))
    if not history:
        return False
    revision = history.pop()
    previous = state.get("current_path_data")
    restored = deepcopy(revision["path"])
    state["current_path_data"] = restored
    state["path_history"] = history
    state["last_path_change"] = {
        "summary": f"Undid: {revision['summary']}",
        "details": describe_changes(previous, restored),
    }
    return True
