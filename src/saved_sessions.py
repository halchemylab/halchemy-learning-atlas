"""Portable, versioned reading sessions; credentials are never serialized."""

import json

from src.workspace import MAX_REVISIONS, json_text


MAX_SESSION_BYTES = 2 * 1024 * 1024
PATH_TEXT_FIELDS = (
    "title", "category", "subcategory", "level", "style", "depth",
    "user_query", "rationale", "rationale_source", "hint",
)


def export_session(state):
    """Export only reading workspace data, excluding API keys and UI state."""
    payload = {
        "format": "halchemy-reading-session", "version": 1,
        "current_path_data": state.get("current_path_data"),
        "messages": state.get("messages", []),
        "path_history": state.get("path_history", []),
    }
    content = json_text(payload).encode("utf-8")
    if len(content) > MAX_SESSION_BYTES:
        raise ValueError("This session exceeds the 2 MB save limit. Download your curriculum instead.")
    return content


def _text(value, label, limit=20000):
    if not isinstance(value, str) or len(value) > limit:
        raise ValueError(f"Invalid {label} in saved session.")
    return value


def _restore_path(value, catalog):
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("Invalid path in saved session.")
    books = value.get("books")
    if not isinstance(books, list) or len(books) > 12:
        raise ValueError("Saved paths must contain at most 12 books.")
    ids = []
    for book in books:
        book_id = book.get("id") if isinstance(book, dict) else None
        if type(book_id) is not int or book_id not in catalog:
            raise ValueError("A saved book is no longer in this library. The current session is unchanged.")
        ids.append(book_id)
    if len(ids) != len(set(ids)):
        raise ValueError("A saved path contains duplicate books.")
    path = {}
    for field in PATH_TEXT_FIELDS:
        item = value.get(field)
        if item is not None:
            path[field] = _text(item, field)
    for field in ("category", "level", "user_query", "rationale", "hint"):
        if field not in path:
            raise ValueError(f"Saved path is missing {field}.")
    if path["category"] not in {book["category"] for book in catalog.values()}:
        raise ValueError("Saved topic is no longer available.")
    if path["level"] not in {"beginner", "intermediate", "advanced"}:
        raise ValueError("Invalid experience level in saved session.")
    stale = value.get("rationale_stale", False)
    if type(stale) is not bool:
        raise ValueError("Invalid explanation status in saved session.")
    notices = value.get("notices", [])
    if not isinstance(notices, list) or len(notices) > 50:
        raise ValueError("Invalid recommendation notices in saved session.")
    path["notices"] = [_text(item, "notice") for item in notices]
    path["rationale_stale"] = stale
    # Catalog metadata, purchase links, and descriptions come from the local library.
    path["books"] = [dict(catalog[book_id]) for book_id in ids]
    return path


def import_session(content, books_df):
    """Validate the entire upload before returning any state to publish."""
    if not isinstance(content, bytes) or len(content) > MAX_SESSION_BYTES:
        raise ValueError("Choose a saved session JSON file smaller than 2 MB.")
    try:
        data = json.loads(content.decode("utf-8"))
    except (UnicodeDecodeError, ValueError, RecursionError) as exc:
        raise ValueError("This file is not valid session JSON.") from exc
    if (not isinstance(data, dict) or data.get("format") != "halchemy-reading-session"
            or type(data.get("version")) is not int or data["version"] != 1):
        raise ValueError("Unsupported saved session format or version.")
    if "current_path_data" not in data:
        raise ValueError("Saved session is missing its path.")
    catalog = {int(book["id"]): book for book in books_df.to_dict("records")}
    path = _restore_path(data["current_path_data"], catalog)
    messages = data.get("messages", [])
    if not isinstance(messages, list):
        raise ValueError("Invalid conversation in saved session.")
    restored_messages = []
    for message in messages:
        if not isinstance(message, dict) or message.get("role") not in ("user", "assistant"):
            raise ValueError("Invalid conversation message in saved session.")
        restored_messages.append({"role": message["role"], "content": _text(message.get("content"), "message", MAX_SESSION_BYTES)})
    history = data.get("path_history", [])
    if not isinstance(history, list) or len(history) > MAX_REVISIONS:
        raise ValueError("Invalid undo history in saved session.")
    restored_history = []
    for revision in history:
        if not isinstance(revision, dict) or "path" not in revision:
            raise ValueError("Invalid undo revision in saved session.")
        restored_history.append({
            "path": _restore_path(revision["path"], catalog),
            "summary": _text(revision.get("summary"), "revision summary"),
        })
    return {
        "current_path_data": path, "messages": restored_messages,
        "path_history": restored_history,
        "last_path_change": {"summary": "Restored your saved session.", "details": []},
    }
