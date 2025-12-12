import os
from openai import OpenAI
from typing import List, Dict, Any

from src.books import load_books, get_unique_values

# Load data dynamically to constrain the LLM
try:
    _df = load_books()
    _valid_categories = get_unique_values(_df, 'category')
except Exception:
    _df = None
    _valid_categories = []

# Fallback if data is missing (prevents crash on empty DB)
if not _valid_categories:
    _valid_categories = ["habits", "coding", "history", "cooking", "productivity", "business"]

_categories_str = ", ".join([c.title() for c in _valid_categories])

# Define the tool structure for OpenAI function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_library",
            "description": "Search the Halchemy Library for a curated reading path based on user preferences. Call this ONLY when you have identified the topic, skill level, and style preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": _valid_categories,
                        "description": "The main topic category."
                    },
                    "subcategory": {
                        "type": "string",
                        "description": "Specific niche (e.g., 'python', 'WWII', 'japanese-cooking'). Optional."
                    },
                    "level": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                        "description": "The user's current skill level."
                    },
                    "style": {
                        "type": "string",
                        "enum": ["story-driven", "tactical/how-to", "academic", "reference"],
                        "description": "The preferred writing style of the books."
                    },
                    "depth": {
                        "type": "string",
                        "enum": ["short", "deep"],
                        "description": "Length of the path: 'short' (3 books) or 'deep' (5-7 books)."
                    }
                },
                "required": ["category", "level"]
            }
        }
    }
]

SYSTEM_PROMPT = f"""You are the Halchemy Library Librarian. Your goal is to help users learn new skills by recommending a "book path" (a sequence of books).

You have access to a tool called `query_library`.
To use it, you must first understand the user's:
1. **Topic** (Must map to: {_categories_str}).
2. **Current Level** (Beginner, Intermediate, Advanced).
3. **Style Preference** (Story-driven/Narrative vs. Tactical/How-to).
4. **Depth** (Short path vs. Deep dive).

**Instructions:**
- **Don't hallucinate books.** logic is handled by the tool. Your job is just to gather parameters.
- Be helpful and concise.
- Ask clarifying questions if the user is vague (e.g., if they say "I want to learn", ask "What subject?").
- If the user asks for a topic NOT in your list (like "Gardening"), apologize and say you only have the supported categories for now.
- Once you have enough info, CALL the `query_library` function. Do not just list book titles yourself.
"""

def get_chat_completion(
    client: OpenAI,
    messages: List[Dict[str, Any]],
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> Any:
    """
    Sends the chat history to OpenAI and returns the response.
    The response might be a text message OR a tool call.
    """
    # Ensure system prompt is at the start
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        tools=TOOLS,
        tool_choice="auto",
        temperature=temperature
    )
    
    return response.choices[0].message

def get_sequence_rationale(
    client: OpenAI,
    user_query: str,
    books: List[Dict[str, Any]],
    model: str = "gpt-4o-mini"
) -> str:
    """
    Generates a short explanation for why this specific sequence of books was chosen.
    """
    book_titles = [f"{i+1}. {b['title']} by {b['author']}" for i, b in enumerate(books)]
    book_list_str = "\n".join(book_titles)
    
    prompt = f"""
    The user asked: "{user_query}"
    
    We have curated the following reading path:
    {book_list_str}
    
    Explain in 1-2 sentences why this specific sequence fits their goal. 
    Focus on the progression (e.g., "starts with X, moves to Y").
    """
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful librarian explaining a reading list."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Enjoy your reading path!"
