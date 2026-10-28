from copy import deepcopy
import json
import unittest

from src.books import load_books
from src.saved_sessions import MAX_SESSION_BYTES, export_session, import_session
from src.starter_paths import build_starter_path
from src.workspace import commit_path, edit_books, undo_path


class TestSavedSessions(unittest.TestCase):
    def setUp(self):
        self.catalog = load_books()
        self.state = {"messages": [{"role": "user", "content": "Help me learn Python"}], "api_key": "never-export-this"}
        commit_path(self.state, build_starter_path(self.catalog, "python"), "Opened Python.")
        self.original_ids = [book["id"] for book in self.state["current_path_data"]["books"]]
        edit_books(self.state, list(reversed(self.state["current_path_data"]["books"])))

    def test_round_trip_preserves_conversation_goal_order_and_undo(self):
        content = export_session(self.state)
        self.assertNotIn(b"never-export-this", content)
        restored = import_session(content, self.catalog)
        self.assertEqual(restored["messages"], self.state["messages"])
        current = restored["current_path_data"]
        self.assertEqual(current["user_query"], self.state["current_path_data"]["user_query"])
        self.assertTrue(current["rationale_stale"])
        self.assertEqual([b["id"] for b in current["books"]], self.original_ids[::-1])
        self.assertTrue(undo_path(restored))
        self.assertEqual([b["id"] for b in restored["current_path_data"]["books"]], self.original_ids)
        self.assertTrue(undo_path(restored))
        self.assertIsNone(restored["current_path_data"])

    def test_import_resolves_book_metadata_from_catalog(self):
        data = json.loads(export_session(self.state))
        data["current_path_data"]["books"][0]["title"] = "Altered title"
        restored = import_session(json.dumps(data).encode(), self.catalog)
        self.assertNotEqual(restored["current_path_data"]["books"][0]["title"], "Altered title")

    def test_invalid_files_and_history_are_rejected_without_mutation(self):
        data = json.loads(export_session(self.state))
        bad_version = deepcopy(data)
        bad_version["version"] = 9
        bad_book = deepcopy(data)
        bad_book["path_history"][1]["path"]["books"][0]["id"] = 999999
        duplicate = deepcopy(data)
        duplicate["current_path_data"]["books"] *= 2
        bad_role = deepcopy(data)
        bad_role["messages"][0]["role"] = ["system"]
        before = export_session(self.state)
        for content in [b"not JSON", b"[]", b"x" * (MAX_SESSION_BYTES + 1),
                        *[json.dumps(d).encode() for d in [bad_version, bad_book, duplicate, bad_role]]]:
            with self.subTest(content=content[:50]), self.assertRaises(ValueError):
                import_session(content, self.catalog)
        self.assertEqual(export_session(self.state), before)
