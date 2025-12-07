import unittest
import csv
import os

class TestBooksData(unittest.TestCase):
    def setUp(self):
        self.csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'books.csv')

    def test_csv_integrity(self):
        with open(self.csv_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            books = list(reader)
            
            self.assertEqual(len(books), 151, "Should have 151 books")
            
            ids = set()
            for book in books:
                # Check ID uniqueness
                self.assertNotIn(book['id'], ids, f"Duplicate ID found: {book['id']}")
                ids.add(book['id'])
                
                # Check required fields
                self.assertTrue(book['title'], f"Book ID {book['id']} missing title")
                self.assertTrue(book['author'], f"Book ID {book['id']} missing author")
                
                # Check numeric ranges
                difficulty = int(book['difficulty'])
                self.assertTrue(1 <= difficulty <= 5, f"Book ID {book['id']} invalid difficulty: {difficulty}")
                
                readability = int(book['readability'])
                self.assertTrue(1 <= readability <= 5, f"Book ID {book['id']} invalid readability: {readability}")

if __name__ == '__main__':
    unittest.main()
