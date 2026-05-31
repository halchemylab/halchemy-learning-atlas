import unittest

import pandas as pd

from src.recommendations import execute_recommendation


class TestRecommendations(unittest.TestCase):
    def test_execute_recommendation_returns_path_and_updates_stats(self):
        df = pd.DataFrame(
            {
                "id": [1, 2, 3],
                "title": ["Book 1", "Book 2", "Book 3"],
                "author": ["A", "B", "C"],
                "category": ["coding"] * 3,
                "subcategory": ["python"] * 3,
                "difficulty": [1, 2, 3],
                "readability": [5, 4, 3],
                "style": ["tactical/how-to"] * 3,
                "learning_type": ["procedural-skill"] * 3,
                "chronology_hint": [0] * 3,
                "is_beginner_friendly": [True] * 3,
                "is_intermediate": [True] * 3,
                "is_advanced": [False] * 3,
            }
        )
        stats_calls = []

        result = execute_recommendation(
            df,
            {"category": "coding", "level": "beginner", "depth": "short"},
            stats_incrementer=lambda **kwargs: stats_calls.append(kwargs),
        )

        self.assertEqual(result.category, "coding")
        self.assertEqual(result.level, "beginner")
        self.assertEqual(result.depth, "short")
        self.assertEqual(result.path["id"].tolist(), [1, 2, 3])
        self.assertEqual(stats_calls, [{"num_books": 3, "category": "coding"}])


if __name__ == "__main__":
    unittest.main()
