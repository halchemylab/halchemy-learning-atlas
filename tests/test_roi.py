import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.roi import DEFAULT_STATS, increment_stats, load_stats


class TestStats(unittest.TestCase):
    def test_invalid_or_partial_stats_can_still_be_incremented(self):
        cases = [
            ({"paths_generated": 1}, {"paths_generated": 1, "books_recommended": 0}),
            ({"books_recommended": 4}, {"paths_generated": 0, "books_recommended": 4}),
            ({"paths_generated": "2", "books_recommended": -1}, DEFAULT_STATS),
            ({"paths_generated": True, "books_recommended": 1.5}, DEFAULT_STATS),
            ([], DEFAULT_STATS), (None, DEFAULT_STATS),
        ]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stats.json"
            with patch("src.roi.STATS_FILE", str(path)):
                for payload, expected in cases:
                    with self.subTest(payload=payload):
                        path.write_text(json.dumps(payload), encoding="utf-8")
                        self.assertEqual(load_stats(), expected)
                        updated = increment_stats(num_books=3)
                        self.assertEqual(updated, {
                            "paths_generated": expected["paths_generated"] + 1,
                            "books_recommended": expected["books_recommended"] + 3,
                        })
                        self.assertEqual(load_stats(), updated)

    def test_missing_or_unreadable_json_uses_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "stats.json"
            with patch("src.roi.STATS_FILE", str(path)):
                self.assertEqual(load_stats(), DEFAULT_STATS)
                path.write_text("{broken", encoding="utf-8")
                self.assertEqual(load_stats(), DEFAULT_STATS)
