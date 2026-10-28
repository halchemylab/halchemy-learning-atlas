from copy import deepcopy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from src.books import load_books
from src.conversation import MAX_TOOL_ROUNDS, execute_tool, run_chat_turn, workspace_context
from src.llm_client import LLMClientError, get_chat_completion
from src.starter_paths import build_starter_path
from src.workspace import commit_path, edit_books


def tool_response(name, args, call_id="call_1"):
    return SimpleNamespace(content=None, tool_calls=[SimpleNamespace(
        id=call_id, function=SimpleNamespace(name=name, arguments=json.dumps(args)),
    )])


def text_response(text="Done."):
    return SimpleNamespace(content=text, tool_calls=None)


class TestConversation(unittest.TestCase):
    def setUp(self):
        self.books = load_books()
        self.state = {}
        commit_path(self.state, build_starter_path(self.books, "python"), "Started Python")
        self.messages = [{"role": "user", "content": "Move the second book first"}]

    def run_turn(self, responses):
        with patch("src.llm_client.get_chat_completion", side_effect=responses) as completion:
            result = run_chat_turn(Mock(), self.messages, self.state, self.books)
        return result, completion

    def test_manual_edits_are_authoritative_and_tool_results_are_paired(self):
        edit_books(self.state, list(reversed(self.state["current_path_data"]["books"])))
        result, completion = self.run_turn([
            tool_response("edit_path", {"book_ids": [5, 6, 4], "reason": "Moved the second book first."}),
            text_response("Moved it to the first step."),
        ])
        self.assertTrue(result["changed"])
        context = completion.call_args_list[0].kwargs["workspace"]
        self.assertEqual([book["id"] for book in context["current_path"]["books"]], [6, 5, 4])
        exchange = completion.call_args_list[1].args[1]
        self.assertEqual(exchange[-2]["tool_calls"][0]["id"], exchange[-1]["tool_call_id"])
        self.assertEqual(exchange[-1]["role"], "tool")
        self.assertTrue(json.loads(exchange[-1]["content"])["changed"])
        self.assertEqual(completion.call_args_list[1].kwargs["tool_choice"], "none")
        self.assertEqual([book["id"] for book in self.state["current_path_data"]["books"]], [5, 6, 4])

    def test_search_then_replace_preserves_kept_books_and_catalog_metadata(self):
        result, completion = self.run_turn([
            tool_response("search_books", {"category": "coding", "subcategory": "python"}),
            tool_response("edit_path", {"book_ids": [4, 5], "reason": "Removed the advanced stretch book.",
                                        "goal": "Practical Python, two hours each week"}, "call_2"),
            text_response("Kept the practical beginner books."),
        ])
        self.assertTrue(result["changed"])
        self.assertEqual(len(self.state["path_history"]), 2)  # Searching consumes no revision.
        current = self.state["current_path_data"]
        self.assertEqual([book["id"] for book in current["books"]], [4, 5])
        self.assertEqual(current["user_query"], "Practical Python, two hours each week")
        self.assertTrue(current["rationale_stale"])
        self.assertEqual(current["books"][0]["title"], self.books.set_index("id").loc[4, "title"])
        search_result = json.loads(completion.call_args_list[1].args[1][2]["content"])
        self.assertTrue(search_result["matches"])

    def test_invalid_actions_never_mutate_state(self):
        invalid = [
            ("edit_path", {"book_ids": [999999], "reason": "Invented"}),
            ("edit_path", {"book_ids": [4, 4], "reason": "Duplicate"}),
            ("edit_path", {"book_ids": [True], "reason": "Wrong type"}),
            ("edit_path", {"book_ids": [], "reason": "Empty"}),
            ("edit_path", {"book_ids": [4], "reason": ""}),
            ("edit_path", {"book_ids": [4], "reason": "Edit", "books": []}),
            ("query_library", {"category": "coding", "level": "expert"}),
            ("query_library", {"category": "coding", "depth": "huge"}),
            ("query_library", {"category": ["coding"]}),
            ("query_library", []), ("unknown", {}), ("undo_path_change", {"extra": True}),
        ]
        for name, args in invalid:
            with self.subTest(name=name, args=args):
                before = deepcopy(self.state)
                with self.assertRaises(ValueError):
                    execute_tool(name, args, self.state, self.books, "goal")
                self.assertEqual(self.state, before)

    def test_chat_undo_restores_manual_edit_and_goal(self):
        original = deepcopy(self.state["current_path_data"])
        execute_tool("edit_path", {"book_ids": [4], "reason": "Shortened.", "goal": "New goal"},
                     self.state, self.books, "")
        result, _ = self.run_turn([tool_response("undo_path_change", {}), text_response("Restored it.")])
        self.assertTrue(result["changed"])
        self.assertEqual(self.state["current_path_data"], original)

    def test_new_path_no_matches_and_empty_undo(self):
        state = {}
        output, changed = execute_tool("query_library", {"category": "coding"}, state, self.books, "Learn code")
        self.assertTrue(changed)
        self.assertTrue(output["workspace"]["current_path"]["books"])
        self.assertEqual(state["current_path_data"]["user_query"], "Learn code")
        with self.assertRaises(ValueError):
            execute_tool("undo_path_change", {}, {}, self.books, "")
        empty = self.books.copy()
        empty["is_advanced"] = False
        before = deepcopy(state)
        with self.assertRaises(ValueError):
            execute_tool("query_library", {"category": "coding", "level": "advanced"}, state, empty, "")
        self.assertEqual(state, before)

    def test_search_and_questions_do_not_change_path_or_history(self):
        before = deepcopy(self.state)
        result, _ = self.run_turn([text_response("The first book teaches the fundamentals.")])
        self.assertFalse(result["changed"])
        self.assertEqual(self.state, before)
        execute_tool("search_books", {"category": "coding"}, self.state, self.books, "")
        self.assertEqual(self.state, before)

    def test_bad_json_and_repeated_tool_calls_are_bounded(self):
        response = tool_response("edit_path", {})
        response.tool_calls[0].function.arguments = "{bad json"
        before = deepcopy(self.state)
        result, completion = self.run_turn([response] * (MAX_TOOL_ROUNDS + 1))
        self.assertFalse(result["changed"])
        self.assertEqual(completion.call_count, MAX_TOOL_ROUNDS + 1)
        self.assertEqual(self.state, before)

    def test_parallel_mutations_are_rejected_together(self):
        response = tool_response("undo_path_change", {})
        response.tool_calls.append(tool_response("undo_path_change", {}, "call_2").tool_calls[0])
        before = deepcopy(self.state)
        result, completion = self.run_turn([response, text_response("Please specify one change.")])
        self.assertFalse(result["changed"])
        self.assertEqual(self.state, before)
        results = completion.call_args_list[1].args[1][-2:]
        self.assertTrue(all("error" in json.loads(item["content"]) for item in results))

    def test_explanation_failure_preserves_successful_edit(self):
        result, _ = self.run_turn([
            tool_response("edit_path", {"book_ids": [4, 5], "reason": "Shortened."}),
            LLMClientError("Network failure"),
        ])
        self.assertTrue(result["changed"])
        self.assertEqual(len(self.state["current_path_data"]["books"]), 2)
        self.assertIn("explanation is unavailable", result["message"])

    def test_sdk_request_contains_live_state_and_disables_parallel_tools(self):
        client = Mock()
        client.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=text_response())])
        get_chat_completion(client, self.messages, workspace=workspace_context(self.state))
        request = client.chat.completions.create.call_args.kwargs
        self.assertFalse(request["parallel_tool_calls"])
        live = json.loads(request["messages"][1]["content"].split("\n", 1)[1])
        self.assertEqual(live["current_path"]["books"][0]["id"], 4)
        self.assertEqual({tool["function"]["name"] for tool in request["tools"]},
                         {"query_library", "search_books", "edit_path", "undo_path_change"})
