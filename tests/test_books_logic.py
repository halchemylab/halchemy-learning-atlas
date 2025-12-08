import unittest
import pandas as pd
from src.books import filter_books, sequence_books

class TestBooksLogic(unittest.TestCase):
    def setUp(self):
        # Create a sample DataFrame for testing
        data = {
            'id': range(1, 11),
            'title': [f'Book {i}' for i in range(1, 11)],
            'category': ['Habits'] * 5 + ['Coding'] * 5,
            'subcategory': ['general', 'general', 'general', 'general', 'general', 
                            'python', 'python', 'rust', 'rust', 'python'],
            'difficulty': [1, 2, 3, 4, 5, 1, 2, 3, 4, 5],
            'readability': [5, 4, 3, 2, 1, 5, 4, 3, 2, 1],
            'is_beginner_friendly': [True, True, False, False, False, True, True, False, False, False],
            'is_intermediate': [False, True, True, True, False, False, True, True, True, False],
            'is_advanced': [False, False, False, True, True, False, False, False, True, True],
            'style': ['tactical/how-to'] * 3 + ['story-driven'] * 2 + ['tactical/how-to'] * 5,
            'learning_type': ['behavioral-skill'] * 5 + ['procedural-skill'] * 5,
            'chronology_hint': [0] * 10
        }
        self.df = pd.DataFrame(data)

    def test_filter_category(self):
        # Pass level="all" to bypass level filtering for this test
        filtered = filter_books(self.df, category="Habits", level="all")
        self.assertEqual(len(filtered), 5)
        self.assertTrue(all(filtered['category'] == 'Habits'))
        
        filtered_lower = filter_books(self.df, category="habits", level="all")
        self.assertEqual(len(filtered_lower), 5)

    def test_filter_subcategory_success(self):
        filtered = filter_books(self.df, category="Coding", subcategory="python", level="all")
        # Should match IDs 6, 7, 10
        self.assertEqual(len(filtered), 3)
        self.assertTrue(all(filtered['subcategory'] == 'python'))

    def test_filter_subcategory_fallback(self):
        # Subcategory 'java' doesn't exist, should return all 'Coding' books (fallback logic)
        filtered = filter_books(self.df, category="Coding", subcategory="java", level="all")
        self.assertEqual(len(filtered), 5)

    def test_filter_level_beginner(self):
        filtered = filter_books(self.df, category="Habits", level="beginner")
        # Beginner friendly habits books: ID 1, 2
        self.assertEqual(len(filtered), 2)
        self.assertTrue(all(filtered['is_beginner_friendly']))

    def test_filter_style_soft_filter(self):
        # Habits books: 3 tactical, 2 story-driven
        # Request 'tactical/how-to' -> matches 3, should filter
        filtered = filter_books(self.df, category="Habits", style_pref="tactical/how-to", level="all")
        self.assertEqual(len(filtered), 3)
        self.assertTrue(all(filtered['style'] == 'tactical/how-to'))

        # Request 'story-driven' -> matches 2, which is < 3. 
        # Logic says: if len(style_matches) >= 3 use it, else keep all.
        # So it should return all 5 Habits books.
        filtered = filter_books(self.df, category="Habits", style_pref="story-driven", level="all")
        self.assertEqual(len(filtered), 5)

    def test_sequence_short_vs_deep(self):
        filtered = filter_books(self.df, category="Coding", level="all") # 5 books
        
        seq_short = sequence_books(filtered, depth="short")
        self.assertEqual(len(seq_short), 3)
        
        seq_deep = sequence_books(filtered, depth="deep")
        self.assertEqual(len(seq_deep), 5) # max available is 5

    def test_sequence_ordering_procedural(self):
        # Coding = procedural-skill. 
        # Logic: sort by difficulty (asc), then readability (desc)
        # IDs: 6(diff 1, read 5), 7(2, 4), 8(3, 3), 9(4, 2), 10(5, 1)
        # Expected order: 6, 7, 8, 9, 10
        filtered = filter_books(self.df, category="Coding", level="all")
        sequenced = sequence_books(filtered, depth="deep")
        
        result_ids = sequenced['id'].tolist()
        self.assertEqual(result_ids, [6, 7, 8, 9, 10])

    def test_sequence_ordering_behavioral(self):
        # Habits = behavioral-skill
        # Logic: sort by difficulty (asc), then readability (desc)
        # IDs: 1(diff 1), 2(diff 2), 3(diff 3), 4(diff 4), 5(diff 5)
        filtered = filter_books(self.df, category="Habits", level="all")
        sequenced = sequence_books(filtered, depth="deep")
        
        result_ids = sequenced['id'].tolist()
        self.assertEqual(result_ids, [1, 2, 3, 4, 5])

if __name__ == '__main__':
    unittest.main()
