import unittest
from unittest.mock import MagicMock
import json
from src.llm_client import get_sequence_rationale, get_chat_completion

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

    def test_get_chat_completion_tool_call(self):
        """Test that get_chat_completion correctly returns a message with tool calls."""
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_message = MagicMock()
        
        # Setup the mock to simulate a tool call
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "query_library"
        mock_tool_call.function.arguments = json.dumps({
            "category": "coding",
            "level": "beginner",
            "style": "tactical/how-to",
            "depth": "short"
        })
        
        mock_message.tool_calls = [mock_tool_call]
        mock_message.content = None # content is usually null for tool calls
        
        mock_response.choices = [MagicMock(message=mock_message)]
        mock_client.chat.completions.create.return_value = mock_response

        # Call the function
        messages = [{"role": "user", "content": "I want to learn coding"}]
        result = get_chat_completion(mock_client, messages)
        
        # Verify the result is the message object with tool calls
        self.assertIsNotNone(result.tool_calls)
        self.assertEqual(len(result.tool_calls), 1)
        self.assertEqual(result.tool_calls[0].function.name, "query_library")
        
        # Verify arguments are parseable
        args = json.loads(result.tool_calls[0].function.arguments)
        self.assertEqual(args['category'], 'coding')
        self.assertEqual(args['level'], 'beginner')
        
if __name__ == '__main__':
    unittest.main()
