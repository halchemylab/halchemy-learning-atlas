"""Exercise the no-key onboarding flow through Streamlit itself."""

import os
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from src.starter_paths import STARTER_PATHS


class TestStarterPaths(unittest.TestCase):
    def setUp(self):
        for mocker in (
            patch.dict(os.environ, {"OPENAI_API_KEY": ""}),
            patch("dotenv.load_dotenv"),
            patch("src.utils.fetch_book_cover", return_value=None),
            patch("src.roi.increment_stats"),
        ):
            mocker.start()
            self.addCleanup(mocker.stop)
        client_patch = patch("openai.OpenAI")
        self.client = client_patch.start()
        self.addCleanup(client_patch.stop)

    def test_all_starters_open_and_export_without_api_key(self):
        app = AppTest.from_file("app.py").run()
        self.assertEqual(len(app.exception), 0)
        self.assertTrue(app.chat_input[0].disabled)

        for starter in STARTER_PATHS:
            with self.subTest(topic=starter["id"]):
                app.button(key=f"starter_{starter['id']}").click().run()
                self.assertEqual(len(app.exception), 0)
                data = app.session_state["current_path_data"]
                self.assertEqual(tuple(book["id"] for book in data["books"]), starter["book_ids"])
                self.assertEqual(len(app.get("download_button")), 2)
                self.assertTrue(app.chat_input[0].disabled)
        self.client.assert_not_called()

    def test_manual_edit_and_ai_enablement(self):
        app = AppTest.from_file("app.py").run()
        app.button(key="starter_python").click().run()
        app.button(key="move_down_0_4").click().run()
        self.assertEqual(len(app.exception), 0)
        self.assertEqual([b["id"] for b in app.session_state["current_path_data"]["books"]], [5, 4, 6])
        self.assertTrue(next(b for b in app.button if b.label == "Refresh rationale").disabled)
        self.client.assert_not_called()

        app.text_input[0].set_value("test-key").run()
        self.assertEqual(len(app.exception), 0)
        self.assertFalse(app.chat_input[0].disabled)
        self.assertFalse(next(b for b in app.button if b.label == "Refresh rationale").disabled)
        self.client.assert_called_once_with(api_key="test-key")


if __name__ == "__main__":
    unittest.main()
