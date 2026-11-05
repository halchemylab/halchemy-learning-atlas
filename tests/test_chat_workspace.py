"""Exercise real chat actions through Streamlit, with only network calls mocked."""

from copy import deepcopy
import json
import os
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from src.exports import build_markdown_export
from src.llm_client import LLMClientError


def action(name, arguments):
    return SimpleNamespace(content=None, tool_calls=[SimpleNamespace(
        id="call_edit", function=SimpleNamespace(name=name, arguments=json.dumps(arguments)),
    )])


def answer(text):
    return SimpleNamespace(content=text, tool_calls=None)


class TestChatWorkspace(unittest.TestCase):
    def test_restore_saved_session_without_key_preserves_undo(self):
        from io import BytesIO
        from src.saved_sessions import export_session
        self.app.button(key="starter_python").click().run()
        self.app.button(key="move_down_0_4").click().run()
        saved = export_session({key: self.app.session_state[key] for key in
                                ("current_path_data", "messages", "path_history")})
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}), patch("streamlit.file_uploader", return_value=BytesIO(saved)):
            resumed = AppTest.from_file("app.py").run()
            next(b for b in resumed.button if b.label == "Restore session").click().run()
            self.assertEqual(len(resumed.exception), 0)
            self.assertEqual([b["id"] for b in resumed.session_state["current_path_data"]["books"]], [5, 4, 6])
            self.assertEqual(resumed.session_state["messages"], self.app.session_state["messages"])
            self.assertTrue(resumed.chat_input[0].disabled)
            resumed.button(key="undo_path").click().run()
            self.assertEqual([b["id"] for b in resumed.session_state["current_path_data"]["books"]], [4, 5, 6])
            self.completion.assert_not_called()

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

    def test_retry_reuses_message_and_replaces_error_until_success(self):
        self.app.button(key="starter_python").click().run()
        before = deepcopy(self.app.session_state["current_path_data"])
        self.send("Move the second book first", [LLMClientError("Connection failed.")])
        failed_messages = deepcopy(self.app.session_state["messages"])
        self.completion.side_effect = [LLMClientError("Still unavailable.")]
        self.app.button(key="retry_chat").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(len(self.app.session_state["messages"]), len(failed_messages))
        self.assertEqual(self.app.session_state["current_path_data"], before)
        self.assertEqual(self.app.session_state["messages"][-1]["content"], "Still unavailable.")
        self.completion.side_effect = [
            action("edit_path", {"book_ids": [5, 4, 6], "reason": "Moved the second book first."}),
            answer("Moved the second book first."),
        ]
        self.app.button(key="retry_chat").click().run()
        self.assertEqual(len(self.app.exception), 0)
        messages = self.app.session_state["messages"]
        self.assertEqual(sum(m["role"] == "user" for m in messages), 1)
        self.assertEqual(len(messages), len(failed_messages))
        self.assertEqual(messages[-1]["content"], "Moved the second book first.")
        self.assertEqual([b["id"] for b in self.app.session_state["current_path_data"]["books"]], [5, 4, 6])
        self.assertFalse(any(b.key == "retry_chat" for b in self.app.button))
        request_messages = self.completion.call_args_list[1].args[1]
        self.assertEqual(request_messages[-1], {"role": "user", "content": "Move the second book first"})
        self.assertFalse(any(m.get("content") == "Connection failed." for m in request_messages))

    def test_retry_clears_after_manual_edit_or_new_message(self):
        self.app.button(key="starter_python").click().run()
        self.send("Move the second book first", [LLMClientError("Connection failed.")])
        self.app.button(key="move_down_0_4").click().run()
        self.assertFalse(any(b.key == "retry_chat" for b in self.app.button))
        self.send("Why this order?", [LLMClientError("Connection failed.")])
        self.send("Explain the first book instead", [answer("It introduces the fundamentals.")])
        self.assertFalse(any(b.key == "retry_chat" for b in self.app.button))

    def test_successful_edit_with_failed_explanation_does_not_offer_retry(self):
        self.app.button(key="starter_python").click().run()
        self.send("Move the second book first", [
            action("edit_path", {"book_ids": [5, 4, 6], "reason": "Moved the second book first."}),
            LLMClientError("Connection failed."),
        ])
        self.assertEqual([b["id"] for b in self.app.session_state["current_path_data"]["books"]], [5, 4, 6])
        self.assertFalse(any(b.key == "retry_chat" for b in self.app.button))

    def test_unexpected_failure_can_be_retried_without_api_key(self):
        self.send("Help me learn Python", [RuntimeError("Unexpected failure")])
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
            self.app.run()
            self.assertTrue(self.app.button(key="retry_chat").disabled)
        self.completion.side_effect = [answer("Let's start with Python fundamentals.")]
        self.app.run()
        self.app.button(key="retry_chat").click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(sum(m["role"] == "user" for m in self.app.session_state["messages"]), 1)

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
