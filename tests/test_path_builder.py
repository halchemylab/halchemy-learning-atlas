"""Verify the manual builder through Streamlit without making AI requests."""

import os
import unittest
from unittest.mock import Mock, patch

from streamlit.testing.v1 import AppTest

from src.books import load_books
from src.exports import build_markdown_export, build_pdf_export
from src.recommendations import execute_recommendation


class TestPathBuilder(unittest.TestCase):
    def setUp(self):
        self.stats = Mock()
        self.client = Mock()
        self.rationale = Mock(return_value="An AI explanation.")
        for mocker in (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            patch("dotenv.load_dotenv"),
            patch("openai.OpenAI", self.client),
            patch("src.utils.fetch_book_cover", return_value=None),
            patch("src.roi.increment_stats"),
            patch("src.llm_client.get_sequence_rationale", self.rationale),
            patch("src.recommendations.execute_recommendation", side_effect=lambda df, args: execute_recommendation(df, args, stats_incrementer=self.stats)),
        ):
            mocker.start()
            self.addCleanup(mocker.stop)

    def submit(self, app):
        next(button for button in app.button if button.label == "Build my path").click().run()
        self.assertEqual(len(app.exception), 0)

    def test_build_edit_export_and_optional_ai(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox(key="builder_category").select("coding").run()
        app.selectbox(key="builder_subcategory_coding").select("python")
        app.selectbox(key="builder_style_coding").select("academic")
        app.selectbox(key="builder_depth").select("deep")
        self.submit(app)
        data = app.session_state["current_path_data"]
        self.assertEqual(data["subcategory"], "python")
        self.assertEqual(data["depth"], "deep")
        self.assertTrue(all(book["is_beginner_friendly"] for book in data["books"]))
        self.assertTrue(any("preferred style" in notice for notice in data["notices"]))
        self.assertTrue(any("expected minimum of 5" in notice for notice in data["notices"]))
        self.assertEqual(len(app.get("download_button")), 2)
        self.assertIn(data["books"][0]["title"], build_markdown_export(data))
        self.assertTrue(build_pdf_export(data).startswith(b"%PDF"))
        self.assertTrue(app.chat_input[0].disabled)
        self.assertTrue(next(b for b in app.button if b.label == "Explain this path with AI").disabled)
        self.stats.assert_called_once_with(num_books=len(data["books"]), category="coding")
        self.client.assert_not_called()
        self.rationale.assert_not_called()

        first_id = data["books"][0]["id"]
        app.button(key=f"move_down_0_{first_id}").click().run()
        self.assertEqual(app.session_state["current_path_data"]["books"][1]["id"], first_id)
        self.assertEqual(len(app.exception), 0)
        app.text_input[0].set_value("test-key").run()
        self.rationale.assert_not_called()
        next(b for b in app.button if b.label == "Refresh rationale").click().run()
        self.assertEqual(len(app.exception), 0)
        self.rationale.assert_called_once()
        self.assertEqual(app.session_state["current_path_data"]["rationale_source"], "ai")

    def test_empty_result_preserves_current_path_and_does_not_count(self):
        books = load_books()
        books.loc[books["category"] == "coding", "is_advanced"] = False
        with patch("src.books.load_books", return_value=books):
            app = AppTest.from_file("app.py").run()
            app.button(key="starter_habits").click().run()
            previous = app.session_state["current_path_data"]
            app.selectbox(key="builder_category").select("coding").run()
            app.selectbox(key="builder_level").select("advanced")
            self.submit(app)
            self.assertEqual(app.session_state["current_path_data"], previous)
            self.assertTrue(any("No books match" in warning.value for warning in app.warning))
            self.stats.assert_not_called()
            self.client.assert_not_called()

    def test_switching_topics_updates_optional_choices(self):
        app = AppTest.from_file("app.py").run()
        app.selectbox(key="builder_category").select("coding").run()
        app.selectbox(key="builder_subcategory_coding").select("python").run()
        app.selectbox(key="builder_category").select("habits").run()
        self.submit(app)
        data = app.session_state["current_path_data"]
        self.assertEqual(data["category"], "habits")
        self.assertIsNone(data["subcategory"])
        self.assertEqual(len(data["books"]), 3)
        self.client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
