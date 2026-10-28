import unittest
from copy import deepcopy
from unittest.mock import patch

from src.exports import build_markdown_export, build_pdf_export


class TestExports(unittest.TestCase):
    def test_goal_and_generation_notices_survive_both_exports(self):
        from io import BytesIO
        from pypdf import PdfReader
        data = {
            "category": "coding", "level": "beginner", "books": [],
            "rationale": "Original explanation.", "hint": "Practice.",
            "user_query": "Learn Python at two hours per week.",
            "notices": ["Only two matching books are available.", "Including other styles."],
            "rationale_stale": True,
        }
        markdown = build_markdown_export(data)
        pdf_text = "\n".join(page.extract_text() for page in PdfReader(BytesIO(build_pdf_export(data))).pages)
        for expected in [data["user_query"], *data["notices"], "predates your edits"]:
            self.assertIn(expected, markdown)
            self.assertIn(expected, pdf_text)

    def test_pdf_cache_reuses_equal_paths_and_invalidates_after_edits(self):
        build_pdf_export.clear()
        self.addCleanup(build_pdf_export.clear)
        data = {
            "books": [{"title": "First Book"}, {"title": "Second Book"}],
            "rationale": "Starts simple.",
            "rationale_stale": False,
        }

        with patch("src.exports.generate_pdf", side_effect=[b"original", b"edited", b"refreshed"]) as generate:
            self.assertEqual(build_pdf_export(data), b"original")
            self.assertEqual(build_pdf_export(deepcopy(data)), b"original")
            self.assertEqual(generate.call_count, 1)

            data["books"].reverse()
            data["rationale_stale"] = True
            self.assertEqual(build_pdf_export(data), b"edited")
            self.assertEqual(generate.call_count, 2)

            data["rationale"] = "Updated explanation."
            data["rationale_stale"] = False
            self.assertEqual(build_pdf_export(data), b"refreshed")
            self.assertEqual(generate.call_count, 3)

    def test_build_markdown_export_includes_path_details(self):
        markdown = build_markdown_export(
            {
                "category": "coding",
                "level": "beginner",
                "rationale": "Starts simple.",
                "hint": "Type examples.",
                "books": [
                    {
                        "title": "Test Book",
                        "author": "Test Author",
                        "short_description": "A short description.",
                        "store_url": "https://example.com",
                        "affiliate_url": "https://affiliate.example.com",
                    }
                ],
            }
        )

        self.assertIn("# Learning Path: Coding (Beginner)", markdown)
        self.assertIn("### 1. Test Book", markdown)
        self.assertIn("[Buy Link](https://affiliate.example.com)", markdown)


if __name__ == "__main__":
    unittest.main()
