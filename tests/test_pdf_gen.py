import unittest

from src.pdf_gen import generate_pdf


class TestPdfGeneration(unittest.TestCase):
    def test_generate_pdf_returns_bytes(self):
        pdf_bytes = generate_pdf(
            {
                "category": "coding",
                "level": "beginner",
                "rationale": "Starts simple and gets more practical.",
                "hint": "Type out examples as you read.",
                "books": [
                    {
                        "title": "Test Book",
                        "author": "Test Author",
                        "short_description": "A short description.",
                        "store_url": "https://example.com",
                    }
                ],
            }
        )

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
