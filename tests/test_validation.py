import unittest
import pandas as pd
from src.books import validate_books

class TestBookValidation(unittest.TestCase):
    def setUp(self):
        self.valid_data = {
            'id': [1],
            'title': ['Test Book'],
            'author': ['Author'],
            'category': ['Habits'],
            'subcategory': ['general'],
            'difficulty': [3],
            'readability': [3],
            'style': ['tactical'],
            'learning_type': ['behavioral'],
            'is_beginner_friendly': [True],
            'is_intermediate': [False],
            'is_advanced': [False]
        }

    def test_valid_data(self):
        df = pd.DataFrame(self.valid_data)
        # Should not raise
        validate_books(df)

    def test_missing_column(self):
        data = self.valid_data.copy()
        del data['difficulty']
        df = pd.DataFrame(data)
        with self.assertRaises(ValueError) as cm:
            validate_books(df)
        self.assertIn("missing required columns", str(cm.exception))

    def test_invalid_difficulty_high(self):
        data = self.valid_data.copy()
        data['difficulty'] = [6]
        df = pd.DataFrame(data)
        with self.assertRaises(ValueError) as cm:
            validate_books(df)
        self.assertIn("outside 1-5 range", str(cm.exception))

    def test_invalid_difficulty_low(self):
        data = self.valid_data.copy()
        data['difficulty'] = [0]
        df = pd.DataFrame(data)
        with self.assertRaises(ValueError) as cm:
            validate_books(df)
        self.assertIn("outside 1-5 range", str(cm.exception))

    def test_duplicate_ids(self):
        data = {k: v * 2 for k, v in self.valid_data.items()} # Duplicate rows
        df = pd.DataFrame(data)
        with self.assertRaises(ValueError) as cm:
            validate_books(df)
        self.assertIn("Duplicate book IDs", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
