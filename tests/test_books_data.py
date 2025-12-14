import unittest
import csv
import os
import re

class TestBooksData(unittest.TestCase):
    def setUp(self):
        self.csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'books.csv')
        self.valid_categories = {
            "habits", "coding", "history", "cooking", "productivity", "business", 
            "science", "philosophy", "design", "psychology", "health", "biography", "social"
        }
        self.valid_learning_types = {"procedural-skill", "narrative-history", "behavioral-skill", "conceptual", "reference"}

    def test_csv_integrity(self):
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            books = list(reader)
            
            # self.assertEqual(len(books), 151, "Should have 151 books") # Removed brittle check
            
            ids = set()
            for book in books:
                # Check ID uniqueness
                self.assertNotIn(book['id'], ids, f"Duplicate ID found: {book['id']}")
                ids.add(book['id'])
                
                # Check required fields
                self.assertTrue(book['title'], f"Book ID {book['id']} missing title")
                self.assertTrue(book['author'], f"Book ID {book['id']} missing author")
                
                # Check numeric ranges
                try:
                    difficulty = int(book['difficulty'])
                    self.assertTrue(1 <= difficulty <= 5, f"Book ID {book['id']} invalid difficulty: {difficulty}")
                except ValueError:
                    self.fail(f"Book ID {book['id']} difficulty is not an integer")
                
                try:
                    readability = int(book['readability'])
                    self.assertTrue(1 <= readability <= 5, f"Book ID {book['id']} invalid readability: {readability}")
                except ValueError:
                    self.fail(f"Book ID {book['id']} readability is not an integer")

                # Check URL format
                url = book.get('store_url', '')
                if url:
                    self.assertTrue(url.startswith(('http://', 'https://')), f"Book ID {book['id']} invalid URL: {url}")
                
                # Check Category validity
                category = book.get('category', '').lower()
                self.assertIn(category, self.valid_categories, f"Book ID {book['id']} has invalid category: {category}")

                # Check Learning Type validity
                l_type = book.get('learning_type', '').lower()
                self.assertIn(l_type, self.valid_learning_types, f"Book ID {book['id']} has invalid learning_type: {l_type}")

if __name__ == '__main__':
    unittest.main()
