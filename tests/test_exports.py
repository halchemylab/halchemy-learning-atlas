import unittest

from src.exports import build_markdown_export


class TestExports(unittest.TestCase):
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
