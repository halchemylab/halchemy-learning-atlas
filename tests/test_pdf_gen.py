import unittest
from io import BytesIO

from pypdf import PdfReader

from src.pdf_gen import generate_pdf


class TestPdfGeneration(unittest.TestCase):
    def test_long_content_wraps_and_continues_without_losing_text(self):
        author = "A very long author name " * 18 + "AUTHOR_END"
        description = "A detailed learning exercise. " * 450 + "DESCRIPTION_END"
        rationale = "A useful reason to read. " * 450 + "RATIONALE_END"
        content = generate_pdf({
            "category": "coding", "level": "beginner", "rationale": rationale,
            "books": [{"title": "Long title " * 24, "author": author,
                       "short_description": description}],
        })
        reader = PdfReader(BytesIO(content))
        text = "\n".join(page.extract_text() for page in reader.pages)
        self.assertGreater(len(reader.pages), 3)
        for marker in ("AUTHOR_END", "DESCRIPTION_END", "RATIONALE_END", "(CONTINUED)"):
            self.assertIn(marker, text)

    def test_unicode_titles_and_authors_are_preserved(self):
        title = "L’été — Ελληνικά и Русский"
        author = "François Žižek"
        reader = PdfReader(BytesIO(generate_pdf({
            "category": "history", "level": "beginner",
            "rationale": "Read ‘carefully’…", "books": [{"title": title, "author": author}],
        })))
        text = "\n".join(page.extract_text() for page in reader.pages)
        for expected in (title, author, "Read ‘carefully’…"):
            self.assertIn(expected, text)
        fonts = reader.pages[0]["/Resources"]["/Font"]
        self.assertTrue(any("/FontFile2" in font.get_object()["/DescendantFonts"][0].get_object()["/FontDescriptor"]
                            for font in fonts.values() if font.get_object().get("/Subtype") == "/Type0"))

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
