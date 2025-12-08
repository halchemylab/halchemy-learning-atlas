import unittest
from unittest.mock import MagicMock
from src.llm_client import get_sequence_rationale

class TestLLMIntegration(unittest.TestCase):
    def test_get_sequence_rationale(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Because it's good."
        mock_client.chat.completions.create.return_value = mock_response
        
        books = [{'title': 'A', 'author': 'B'}]
        rationale = get_sequence_rationale(mock_client, "query", books)
        
        self.assertEqual(rationale, "Because it's good.")
        
if __name__ == '__main__':
    unittest.main()
