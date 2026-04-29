import unittest

import pandas as pd

from src.path_editor import (
    get_replacement_candidates,
    move_book,
    remove_book,
    replace_book,
)


class TestPathEditor(unittest.TestCase):
    def setUp(self):
        self.books = [
            {"id": 1, "title": "Book 1"},
            {"id": 2, "title": "Book 2"},
            {"id": 3, "title": "Book 3"},
        ]

        self.df = pd.DataFrame(
            {
                "id": [1, 2, 3, 4, 5],
                "title": ["Book 1", "Book 2", "Book 3", "Book 4", "Book 5"],
                "author": ["A", "B", "C", "D", "E"],
                "category": ["coding"] * 5,
                "subcategory": ["python"] * 5,
                "difficulty": [1, 2, 3, 1, 4],
                "readability": [5, 4, 3, 4, 2],
                "style": ["tactical/how-to"] * 5,
                "learning_type": ["procedural-skill"] * 5,
                "chronology_hint": [0] * 5,
                "short_description": [""] * 5,
                "store_url": ["https://example.com"] * 5,
                "is_beginner_friendly": [True, True, True, True, False],
                "is_intermediate": [True] * 5,
                "is_advanced": [False] * 5,
            }
        )

    def test_move_book_up_and_down(self):
        moved_down = move_book(self.books, 0, 1)
        self.assertEqual([book["id"] for book in moved_down], [2, 1, 3])

        moved_up = move_book(self.books, 2, -1)
        self.assertEqual([book["id"] for book in moved_up], [1, 3, 2])

    def test_move_book_ignores_out_of_bounds(self):
        self.assertEqual(move_book(self.books, 0, -1), self.books)
        self.assertEqual(move_book(self.books, 2, 1), self.books)
        self.assertEqual(move_book(self.books, 99, 1), self.books)

    def test_remove_book(self):
        updated = remove_book(self.books, 1)
        self.assertEqual([book["id"] for book in updated], [1, 3])

    def test_replace_book(self):
        updated = replace_book(self.books, 1, {"id": 4, "title": "Book 4"})
        self.assertEqual([book["id"] for book in updated], [1, 4, 3])

    def test_get_replacement_candidates_excludes_current_path(self):
        candidates = get_replacement_candidates(
            self.df,
            self.books,
            category="coding",
            subcategory="python",
            level="beginner",
            style="tactical/how-to",
        )

        self.assertEqual([book["id"] for book in candidates], [4])


if __name__ == "__main__":
    unittest.main()
