"""Validated library actions and a bounded chat/tool loop, independent of Streamlit."""

from copy import deepcopy
import json

from src import llm_client
from src.books import filter_books, get_hint_for_category
from src.recommendations import execute_recommendation
from src.workspace import commit_path, json_text, undo_path


MAX_TOOL_ROUNDS = 5
MAX_PATH_BOOKS = 12
BOOK_FIELDS = ("id", "title", "author", "category", "subcategory", "difficulty",
               "readability", "style", "short_description", "is_beginner_friendly",
               "is_intermediate", "is_advanced")
MUTATING_TOOLS = {"query_library", "edit_path", "undo_path_change"}


def workspace_context(state):
    path = state.get("current_path_data")
    current = None
    if path is not None:
        current = {key: path.get(key) for key in (
            "title", "category", "subcategory", "level", "style", "depth",
            "user_query", "rationale", "rationale_stale", "notices",
        )}
        current["books"] = [
            {"step": i, **{key: book.get(key) for key in BOOK_FIELDS}}
            for i, book in enumerate(path["books"], 1)
        ]
    return {"current_path": current, "undo_available": bool(state.get("path_history")),
            "last_change": state.get("last_path_change")}


def validate_query(books_df, args):
    if not isinstance(args, dict):
        raise ValueError("Search parameters must be an object.")
    allowed = {"category", "subcategory", "level", "style", "depth"}
    if set(args) - allowed:
        raise ValueError("Search contains unsupported parameters.")
    result = {"level": "beginner", "depth": "short", **args}
    for field, values in (
        ("category", set(books_df["category"].dropna())),
        ("level", {"beginner", "intermediate", "advanced"}),
        ("depth", {"short", "deep"}),
        ("style", {None, "story-driven", "tactical/how-to", "academic", "reference"}),
    ):
        value = result.get(field)
        if not isinstance(value, (str, type(None))) or value not in values:
            raise ValueError(f"Choose a supported {field}.")
    subcategory = result.get("subcategory")
    if subcategory is not None and not isinstance(subcategory, str):
        raise ValueError("Subtopic must be text.")
    return result


def execute_tool(name, args, state, books_df, user_query):
    """Resolve all selected IDs from the catalog; model-provided book text is never stored."""
    if not isinstance(args, dict):
        raise ValueError("Action parameters must be an object.")
    if name in {"search_books", "query_library"}:
        query = validate_query(books_df, args)
        if name == "search_books":
            notices = []
            matches = filter_books(
                books_df, category=query["category"], subcategory=query.get("subcategory"),
                level=query["level"], style_pref=query.get("style"), notices=notices,
            )
            # Return all matches so the model can choose candidates beyond the first path.
            return {"matches": json.loads(matches[list(BOOK_FIELDS)].to_json(orient="records")),
                    "notices": notices}, False
        result = execute_recommendation(books_df, query, stats_incrementer=lambda **_: None)
        if result.path.empty:
            raise ValueError("No books match those preferences. Your current path is unchanged.")
        path = {
            "title": f"{(result.subcategory or result.category).replace('-', ' ').title()} Reading Path",
            "category": result.category, "subcategory": result.subcategory,
            "level": result.level, "style": result.style, "depth": result.depth,
            "user_query": user_query, "books": result.path.to_dict("records"),
            "rationale": "Selected from the curated library and ordered by the recommendation engine.",
            "rationale_source": "criteria", "rationale_stale": False,
            "notices": list(result.notices), "hint": get_hint_for_category(result.category),
        }
        changed = commit_path(state, path, "Built a reading path from your request.")
    elif name == "edit_path":
        if set(args) - {"book_ids", "reason", "goal"}:
            raise ValueError("Edit contains unsupported parameters.")
        current = state.get("current_path_data")
        if current is None:
            raise ValueError("Build a reading path with query_library before editing it.")
        ids = args.get("book_ids")
        if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_PATH_BOOKS:
            raise ValueError(f"Provide an ordered list of 1–{MAX_PATH_BOOKS} book IDs.")
        if any(type(book_id) is not int for book_id in ids):
            raise ValueError("Book IDs must be integers from the catalog.")
        if len(ids) != len(set(ids)):
            raise ValueError("A book can appear only once in a path.")
        indexed = books_df.set_index("id", drop=False)
        if any(book_id not in indexed.index for book_id in ids):
            raise ValueError("A selected book ID is not in the curated library. Search again.")
        reason = args.get("reason")
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 1000:
            raise ValueError("Provide a short explanation of the edit.")
        goal = args.get("goal")
        if goal is not None and (not isinstance(goal, str) or not goal.strip() or len(goal) > 2000):
            raise ValueError("The learning goal must be nonempty text, up to 2000 characters.")
        path = deepcopy(current)
        path["books"] = indexed.loc[ids].to_dict("records")
        if goal is not None:
            path["user_query"] = goal.strip()
        if [book["id"] for book in current["books"]] == ids and path["user_query"] == current["user_query"]:
            return {"message": "The path already matches that edit.", "workspace": workspace_context(state)}, False
        path["rationale_stale"] = True
        changed = commit_path(state, path, reason.strip())
    elif name == "undo_path_change":
        if args:
            raise ValueError("Undo takes no parameters.")
        changed = undo_path(state)
        if not changed:
            raise ValueError("There is no earlier path revision to restore.")
    else:
        raise ValueError("Unsupported library action.")
    return {"changed": changed, "workspace": workspace_context(state)}, changed


def run_chat_turn(client, messages, state, books_df, model="gpt-4o-mini", temperature=0.7):
    """Search, apply at most one revision, then explain the verified result.

    Tool exchanges stay within a turn. Subsequent turns use visible chat history
    plus a fresh authoritative snapshot, including any intervening manual edits.
    """
    draft = {key: deepcopy(state.get(key)) for key in
             ("current_path_data", "last_path_change")}
    draft["path_history"] = deepcopy(state.get("path_history", []))
    exchange = [{"role": message["role"], "content": message["content"]}
                for message in messages if message.get("content") and message["role"] in {"user", "assistant"}]
    user_query = next((message["content"] for message in reversed(exchange) if message["role"] == "user"), "")
    changed = False
    last_error = None
    for round_index in range(MAX_TOOL_ROUNDS + 1):
        final = changed or round_index == MAX_TOOL_ROUNDS
        try:
            response = llm_client.get_chat_completion(
                client, exchange, model=model, temperature=temperature,
                workspace=workspace_context(draft), tool_choice="none" if final else "auto",
            )
        except llm_client.LLMClientError:
            if not changed:
                raise
            # The edit succeeded; an explanation outage must not lose it or invite a retry.
            return _publish(state, draft, "Your path was updated. The explanation is unavailable right now; see What changed.")
        calls = response.tool_calls or []
        if not calls:
            text = response.content or last_error or "Tell me what you'd like to learn or change."
            if changed:
                return _publish(state, draft, text)
            return {"message": text, "changed": False}
        if final:
            break
        exchange.append({"role": "assistant", "content": response.content,
                         "tool_calls": [{"id": call.id, "type": "function", "function": {
                             "name": call.function.name, "arguments": call.function.arguments,
                         }} for call in calls]})
        mutation_count = sum(call.function.name in MUTATING_TOOLS for call in calls)
        for call in calls:
            try:
                if mutation_count > 1:
                    raise ValueError("Apply one complete path change per turn, after searching for books.")
                output, did_change = execute_tool(
                    call.function.name, json.loads(call.function.arguments), draft, books_df, user_query,
                )
                changed = changed or did_change
            except (ValueError, TypeError) as exc:
                last_error = str(exc)
                output = {"error": last_error, "changed": False}
            exchange.append({"role": "tool", "tool_call_id": call.id, "content": json_text(output)})
    if changed:
        return _publish(state, draft, "Updated your path. See What changed for the details.")
    return {"message": last_error or "I couldn't complete that request. Try a more specific change. Your path is unchanged.",
            "changed": False}


def _publish(state, draft, message):
    for key, value in draft.items():
        state[key] = value
    return {"message": message, "changed": True}
