import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd
from streamlit.testing.v1 import AppTest

from src.recommendations import execute_recommendation


class TestRecommendationNotices(unittest.TestCase):
    def setUp(self):
        self.books = pd.DataFrame([
            {
                "id": index,
                "title": f"Book {index}",
                "author": "Author",
                "category": "coding",
                "subcategory": "python",
                "difficulty": index,
                "readability": 5,
                "style": "tactical/how-to" if index <= 3 else "academic",
                "learning_type": "procedural-skill",
                "is_beginner_friendly": True,
                "is_intermediate": True,
                "is_advanced": False,
                "short_description": "A learning resource.",
                "store_url": "",
            }
            for index in range(1, 6)
        ])

    def recommend(self, **overrides):
        args = {"category": "coding", "level": "beginner", "depth": "short"}
        args.update(overrides)
        return execute_recommendation(self.books, args, stats_incrementer=lambda **_: None)

    def test_exact_matches_have_no_notices(self):
        result = self.recommend(subcategory=" PYTHON ", style=" TACTICAL/HOW-TO ")
        self.assertEqual(result.path["id"].tolist(), [1, 2, 3])
        self.assertEqual(result.notices, ())

    def test_missing_subtopic_explains_broader_results(self):
        result = self.recommend(subcategory="rust")
        self.assertEqual(result.path["id"].tolist(), [1, 2, 3])
        self.assertEqual(len(result.notices), 1)
        self.assertIn('subtopic "rust"', result.notices[0])
        self.assertIn("broader coding recommendations", result.notices[0])

    def test_style_fallback_explains_available_count(self):
        for style, count in (("academic", 2), ("story-driven", 0)):
            with self.subTest(style=style):
                result = self.recommend(style=style)
                self.assertEqual(result.path["id"].tolist(), [1, 2, 3])
                self.assertEqual(len(result.notices), 1)
                self.assertIn(f'preferred style "{style}"', result.notices[0])
                self.assertIn(f"({count} available)", result.notices[0])

    def test_small_path_with_all_books_in_style_does_not_claim_style_relaxed(self):
        self.books = self.books.iloc[:2]
        result = self.recommend(style="tactical/how-to")
        self.assertEqual(len(result.notices), 1)
        self.assertIn("Only 2 matching books are available", result.notices[0])

    def test_short_and_deep_minimums(self):
        for depth, count, minimum in (("short", 1, 3), ("short", 2, 3), ("deep", 4, 5)):
            with self.subTest(depth=depth, count=count):
                result = execute_recommendation(
                    self.books.iloc[:count],
                    {"category": "coding", "depth": depth},
                    stats_incrementer=lambda **_: None,
                )
                self.assertEqual(len(result.notices), 1)
                self.assertIn(f"minimum of {minimum} books", result.notices[0])

    def test_deep_path_with_five_books_has_no_shortfall(self):
        self.assertEqual(self.recommend(depth="deep").notices, ())

    def test_empty_results_do_not_claim_broader_recommendations(self):
        result = self.recommend(subcategory="rust", style="academic", level="advanced")
        self.assertTrue(result.path.empty)
        self.assertEqual(result.notices, ())

    def test_combined_notices_survive_app_rerun(self):
        args = {"category": "coding", "subcategory": "rust", "style": "academic", "depth": "deep"}
        books = self.books.iloc[:4]
        response = SimpleNamespace(content=None, tool_calls=[SimpleNamespace(
            id="call_query", function=SimpleNamespace(name="query_library", arguments=json.dumps(args))
        )])
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}),
            patch("dotenv.load_dotenv"),
            patch("openai.OpenAI"),
            patch("src.books.load_books", return_value=books),
            patch("src.utils.fetch_book_cover", return_value=None),
            patch("src.roi.load_stats", return_value={}),
            patch("src.roi.increment_stats"),
            patch("src.llm_client.get_chat_completion", side_effect=[
                response, SimpleNamespace(content="Built your path with broader matches.", tool_calls=None),
            ]),
            patch("src.llm_client.get_sequence_rationale", return_value="Start with the basics."),
            patch("src.exports.build_pdf_export", return_value=b"pdf"),
            patch("src.recommendations.execute_recommendation", side_effect=lambda df, args: execute_recommendation(
                df, args, stats_incrementer=lambda **_: None
            )),
        ):
            app = AppTest.from_file("app.py").run()
            app.chat_input[0].set_value("A deep Rust path, academic style").run()
            self.assertEqual(len(app.exception), 0)
            notices = app.session_state["current_path_data"]["notices"]
            self.assertEqual(len(notices), 3)
            self.assertTrue(set(notices).issubset({warning.value for warning in app.warning}))
            app.run()
            self.assertEqual(len(app.exception), 0)
            self.assertTrue(set(notices).issubset({warning.value for warning in app.warning}))


if __name__ == "__main__":
    unittest.main()
