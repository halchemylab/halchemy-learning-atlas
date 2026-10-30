import unittest
from unittest.mock import MagicMock
import json
from src.llm_client import get_sequence_rationale, get_chat_completion
from src.llm_client import (
    bounded_chat_history, LLMClientError, MAX_HISTORY_CHARS,
    MAX_HISTORY_MESSAGES, MAX_REQUEST_BYTES,
)
from copy import deepcopy


class TestChatLimits(unittest.TestCase):
    def test_long_history_keeps_recent_messages_without_mutating_saved_chat(self):
        messages = [{"role": role, "content": f"{i}: {role}"}
                    for i in range(20) for role in ("user", "assistant")]
        messages.append({"role": "user", "content": "Keep the first book"})
        original = deepcopy(messages)
        result = bounded_chat_history(messages)
        self.assertLessEqual(len(result), MAX_HISTORY_MESSAGES)
        self.assertEqual(result[0]["role"], "user")
        self.assertEqual(result[-1], messages[-1])
        self.assertNotIn(messages[0], result)
        self.assertEqual(messages, original)

    def test_character_budget_keeps_latest_instructions_whole(self):
        messages = [{"role": "user", "content": "old"},
                    {"role": "assistant", "content": "x" * MAX_HISTORY_CHARS},
                    {"role": "user", "content": "Move book two first"}]
        self.assertEqual(bounded_chat_history(messages), messages[-1:])

    def test_oversized_user_message_is_rejected_before_api_call(self):
        from src.conversation import run_chat_turn
        client = MagicMock()
        state = {"current_path_data": None, "path_history": []}
        before = deepcopy(state)
        with self.assertRaisesRegex(LLMClientError, "4,000"):
            run_chat_turn(client, [{"role": "user", "content": "x" * 4001}], state, None)
        client.chat.completions.create.assert_not_called()
        self.assertEqual(state, before)

    def test_total_payload_guard_includes_workspace_and_utf8_bytes(self):
        client = MagicMock()
        with self.assertRaisesRegex(LLMClientError, "context limit"):
            get_chat_completion(client, [{"role": "user", "content": "Hi"}],
                                workspace={"goal": "界" * (MAX_REQUEST_BYTES // 3)})
        client.chat.completions.create.assert_not_called()

    def test_output_limits_and_timeout_apply_to_chat_and_explanations(self):
        client = MagicMock()
        client.chat.completions.create.return_value.choices[0].message.content = "A short explanation."
        get_chat_completion(client, [{"role": "user", "content": "Hi"}])
        request = client.chat.completions.create.call_args.kwargs
        self.assertEqual(request["max_completion_tokens"], 600)
        self.assertEqual(request["timeout"], 30)
        get_sequence_rationale(client, "Learn", [{"title": "A", "author": "B"}])
        self.assertEqual(client.chat.completions.create.call_args.kwargs["max_completion_tokens"], 200)

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
