import os
from openai import OpenAI
from typing import List, Dict, Any

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
                        "enum": ["habits", "coding", "history", "cooking", "productivity", "business"],
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

SYSTEM_PROMPT = """You are the Halchemy Library Librarian. Your goal is to help users learn new skills by recommending a "book path" (a sequence of books).

You have access to a tool called `query_library`.
To use it, you must first understand the user's:
1. **Topic** (Must map to: Habits, Coding, History, Cooking, Productivity, Business).
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
