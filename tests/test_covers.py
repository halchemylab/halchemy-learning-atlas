import threading
import unittest
from unittest.mock import patch

from src.utils import fetch_book_covers


class TestCovers(unittest.TestCase):
    def test_covers_run_concurrently_keep_order_and_cache(self):
        fetch_book_covers.clear()
        self.addCleanup(fetch_book_covers.clear)
        barrier = threading.Barrier(3)

        def fetch(title, author):
            barrier.wait(timeout=3)
            return None if title == "Missing" else title

        books = (("First", "A"), ("Missing", "B"), ("Last", "C"))
        with patch("src.utils.fetch_book_cover", side_effect=fetch) as mocked:
            self.assertEqual(fetch_book_covers(books), ["First", None, "Last"])
            self.assertEqual(fetch_book_covers(books), ["First", None, "Last"])
            self.assertEqual(mocked.call_count, 3)
