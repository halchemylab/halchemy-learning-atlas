"""Exercise real chat actions through Streamlit, with only network calls mocked."""

from copy import deepcopy
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from src.exports import build_markdown_export


def action(name, arguments):
    return SimpleNamespace(content=None, tool_calls=[SimpleNamespace(
        id="call_edit", function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )])


def answer(text):
    return SimpleNamespace(content=text, tool_calls=None)


class TestChatWorkspace(unittest.TestCase):
    def setUp(self):
        self.completion = Mock()
        self.stats = Mock()
        for mocker in (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch("dotenv.load_dotenv"),
            patch("openai.OpenAI"),
            patch("src.utils.fetch_book_cover", return_value=None),
            patch("src.roi.load_stats", return_value={}),
            patch("src.roi.increment_stats", self.stats),
            patch("src.llm_client.get_chat_completion", self.completion),
            patch("src.exports.build_pdf_export", return_value=b"pdf"),
        ):
            mocker.start()
            self.addCleanup(mocker.stop)
        self.app = AppTest.from_file("app.py").run()

    def send(self, message, responses):
        self.completion.side_effect = responses
        self.app.chat_input[0].set_value(message).run()
        self.assertEqual(len(self.app.exception), 0)

    def test_manual_edit_chat_edit_export_and_both_kinds_of_undo(self):
        self.app.button(key="starter_python").click().run()
        original = deepcopy(self.app.session_state["current_path_data"])
        self.app.button(key="move_down_0_4").click().run()
        manually_edited = deepcopy(self.app.session_state["current_path_data"])
        self.send("Remove the advanced book; keep the first two", [
            action("edit_path", {"book_ids": [5, 4], "reason": "Kept the first two books and removed the advanced stretch goal."}),
            answer("Removed Fluent Python; kept your first two books in order."),
        ])
        context = self.completion.call_args_list[0].kwargs["workspace"]["current_path"]
        self.assertEqual([book["id"] for book in context["books"]], [5, 4, 6])
        current = self.app.session_state["current_path_data"]
        self.assertEqual([book["id"] for book in current["books"]], [5, 4])
        export = build_markdown_export(current)
        self.assertNotIn("### 3. Fluent Python", export)
        self.assertIn("### 1. Automate the Boring Stuff", export)
        self.assertTrue(any("Removed Fluent Python" in item.value for item in self.app.markdown))
        self.assertEqual(len(self.app.get("download_button")), 2)
        self.assertTrue(any(item.label == "What changed" for item in self.app.expander))
        self.send("Undo that", [action("undo_path_change", {}), answer("Restored the previous three books.")])
        self.assertEqual(self.app.session_state["current_path_data"], manually_edited)
        self.app.button(key="undo_path").click().run()
        self.assertEqual(self.app.session_state["current_path_data"], original)
        self.stats.assert_called_once()  # Edits and undo are not new recommendations.

    def test_chat_can_create_a_path_from_empty_workspace(self):
        self.send("Help me learn Python", [
            action("query_library", {"category": "coding", "subcategory": "python"}),
            answer("Built a beginner Python path."),
        ])
        self.assertIsNone(self.completion.call_args_list[0].kwargs["workspace"]["current_path"])
        current = self.app.session_state["current_path_data"]
        self.assertEqual(current["subcategory"], "python")
        self.assertTrue(current["books"])
        self.stats.assert_called_once_with(num_books=len(current["books"]), category="coding")
        self.app.button(key="undo_path").click().run()
        self.assertIsNone(self.app.session_state["current_path_data"])
        self.assertEqual(len(self.app.get("download_button")), 0)

    def test_search_replace_and_question_preserve_goal_and_order(self):
        self.app.button(key="starter_python").click().run()
        self.send("Make this manageable at two hours per week", [
            action("search_books", {"category": "coding", "subcategory": "python"}),
            action("edit_path", {"book_ids": [4, 5], "reason": "Kept the practical beginner books.",
                                 "goal": "Learn practical Python at two hours per week"}),
            answer("Kept two practical books; work through them at your own pace."),
        ])
        before = deepcopy(self.app.session_state["current_path_data"])
        history = deepcopy(self.app.session_state["path_history"])
        self.send("Why this order?", [answer("Start with the fundamentals, then practice automation.")])
        self.assertEqual(self.app.session_state["current_path_data"], before)
        self.assertEqual(self.app.session_state["path_history"], history)
        self.assertEqual(self.completion.call_args.kwargs["workspace"]["current_path"]["user_query"],
                         "Learn practical Python at two hours per week")

    def test_invalid_edit_preserves_path_and_exports(self):
        self.app.button(key="starter_python").click().run()
        before = deepcopy(self.app.session_state["current_path_data"])
        self.send("Replace it", [
            action("edit_path", {"book_ids": [999999], "reason": "Invalid edit"}),
            answer("That book is unavailable; your path is unchanged."),
        ])
        self.assertEqual(self.app.session_state["current_path_data"], before)
        self.assertEqual(len(self.app.session_state["path_history"]), 1)
        self.assertEqual(len(self.app.get("download_button")), 2)

    def test_undo_button_works_without_an_api_key(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            app = AppTest.from_file("app.py").run()
            app.button(key="starter_habits").click().run()
            original = deepcopy(app.session_state["current_path_data"])
            book_id = original["books"][0]["id"]
            app.button(key=f"remove_0_{book_id}").click().run()
            app.button(key="undo_path").click().run()
            self.assertEqual(app.session_state["current_path_data"], original)
            self.assertTrue(app.chat_input[0].disabled)
            self.assertEqual(len(app.exception), 0)
            self.completion.assert_not_called()
