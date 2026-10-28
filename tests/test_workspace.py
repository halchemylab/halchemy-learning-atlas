import unittest
from copy import deepcopy

from src.workspace import MAX_REVISIONS, commit_path, edit_books, undo_path


class TestWorkspace(unittest.TestCase):
    def setUp(self):
        self.original = {
            "books": [{"id": 1, "title": "First"}, {"id": 2, "title": "Second"}],
            "user_query": "Learn Python", "rationale": "Original explanation",
            "rationale_stale": False, "category": "coding",
        }
        self.state = {}
        commit_path(self.state, self.original, "Built a path")

    def test_manual_edit_and_undo_restore_full_snapshot(self):
        edit_books(self.state, list(reversed(self.original["books"])))
        self.assertTrue(self.state["current_path_data"]["rationale_stale"])
        self.assertTrue(any("Moved First" in detail for detail in self.state["last_path_change"]["details"]))
        self.state["current_path_data"]["user_query"] = "Changed goal"
        undo_path(self.state)
        self.assertEqual(self.state["current_path_data"], self.original)
        undo_path(self.state)
        self.assertIsNone(self.state["current_path_data"])
        self.assertFalse(undo_path(self.state))

    def test_noop_does_not_consume_history_and_snapshots_are_independent(self):
        self.assertFalse(edit_books(self.state, self.original["books"]))
        self.assertEqual(len(self.state["path_history"]), 1)
        self.original["books"][0]["title"] = "External mutation"
        self.assertEqual(self.state["current_path_data"]["books"][0]["title"], "First")

    def test_history_is_bounded(self):
        for i in range(MAX_REVISIONS + 5):
            path = deepcopy(self.original)
            path["user_query"] = str(i)
            commit_path(self.state, path, "Changed goal")
        self.assertEqual(len(self.state["path_history"]), MAX_REVISIONS)
