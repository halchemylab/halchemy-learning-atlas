import streamlit as st
import pandas as pd
import time
from src.books import load_books, filter_books, sequence_books, get_hint_for_category

# --- Page Config ---
st.set_page_config(
    page_title="Halchemy Library",
    page_icon="📚",
    layout="centered"
)

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "stage" not in st.session_state:
    st.session_state.stage = "intro"  # stages: intro, ask_level, ask_style, ask_depth, recommendation

if "user_inputs" not in st.session_state:
    st.session_state.user_inputs = {
        "category": None,
        "subcategory": None,
        "level": None,
        "style": None,
        "depth": None
    }

if "books_df" not in st.session_state:
    st.session_state.books_df = load_books()

# --- Helper Functions ---

def add_message(role: str, content: str):
    """Adds a message to the chat history."""
    st.session_state.messages.append({"role": role, "content": content})

def typing_effect(text: str):
    """Simulates typing effect (optional, purely visual)."""
    # In a real app, we might use a placeholder, but for simple Streamlit flow, 
    # we just append the message.
    pass

def reset_conversation():
    st.session_state.messages = []
    st.session_state.stage = "intro"
    st.session_state.user_inputs = {
        "category": None,
        "subcategory": None,
        "level": None,
        "style": None,
        "depth": None
    }
    st.rerun()

# --- parsing logic (simple keyword matching) ---
def parse_category(user_text: str):
    text = user_text.lower()
    # Map keywords to categories
    mapping = {
        "habit": "habits",
        "habits": "habits",
        "python": ("coding", "python"),
        "code": "coding",
        "coding": "coding",
        "web": ("coding", "web-dev"),
        "html": ("coding", "web-dev"),
        "css": ("coding", "web-dev"),
        "history": "history",
        "war": ("history", "WWII"),
        "wwii": ("history", "WWII"),
        "cook": "cooking",
        "cooking": "cooking",
        "food": "cooking",
        "Japanese": ("cooking", "japanese-cooking"),
        "productivity": "productivity",
        "focus": "productivity",
        "business": "business",
        "manage": ("business", "management"),
        "leader": ("business", "leadership"),
        "startup": ("business", "startup")
    }
    
    for key, value in mapping.items():
        if key in text:
            if isinstance(value, tuple):
                return value[0], value[1]
            return value, None
    return None, None

def parse_level(user_text: str):
    text = user_text.lower()
    if "begin" in text or "start" in text or "new" in text:
        return "beginner"
    if "intermed" in text:
        return "intermediate"
    if "advan" in text or "expert" in text or "deep" in text:
        return "advanced"
    return None

def parse_style(user_text: str):
    text = user_text.lower()
    if "story" in text or "narrative" in text:
        return "story-driven"
    if "how-to" in text or "guide" in text or "tactic" in text or "practical" in text:
        return "tactical/how-to"
    return "any" # Default if unclear

def parse_depth(user_text: str):
    text = user_text.lower()
    if "short" in text or "quick" in text or "3" in text:
        return "short"
    if "deep" in text or "long" in text or "5" in text or "7" in text:
        return "deep"
    return "short" # Default

# --- Main App Layout ---

st.title("Halchemy Library 📚")
st.caption("Tell us what you want to learn. We’ll build a reading path that’s actually readable.")

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Conversation Logic ---

# Initial Greeting
if not st.session_state.messages:
    intro_msg = "Hi! I can help you master a new subject with a curated reading path. What do you want to learn today? (e.g., 'habits', 'Python', 'history', 'cooking')"
    add_message("assistant", intro_msg)
    st.rerun()

# User Input Handling
if prompt := st.chat_input("Your answer..."):
    # Display user message
    add_message("user", prompt)
    
    # State Machine
    stage = st.session_state.stage
    
    if stage == "intro":
        cat, subcat = parse_category(prompt)
        if cat:
            st.session_state.user_inputs["category"] = cat
            st.session_state.user_inputs["subcategory"] = subcat
            
            # Move to next stage
            st.session_state.stage = "ask_level"
            response = f"Great, **{cat.capitalize()}** is a fantastic choice."
            if subcat:
                response += f" Specifically regarding **{subcat}**."
            response += "\n\nAre you a **beginner**, **intermediate**, or **advanced** learner in this field?"
            add_message("assistant", response)
        else:
            # Fallback
            response = "I'm not sure I have books on that yet. Currently, I can help with **Habits, Coding (Python/Web), History (WWII), Cooking, Productivity, and Business**. Which of these interests you?"
            add_message("assistant", response)

    elif stage == "ask_level":
        level = parse_level(prompt)
        if level:
            st.session_state.user_inputs["level"] = level
            st.session_state.stage = "ask_style"
            
            response = f"Got it, looking for **{level}** resources.""\n\nDo you prefer books that are **story-driven** (narratives, biographies) or more **tactical/how-to** (guides, manuals)?"
            add_message("assistant", response)
        else:
            add_message("assistant", "Could you clarify? Please type 'beginner', 'intermediate', or 'advanced'.")

    elif stage == "ask_style":
        style = parse_style(prompt)
        st.session_state.user_inputs["style"] = style # even if "any"
        
        st.session_state.stage = "ask_depth"
        response = "Understood.""\nLast question: Would you like a **short path** (3 essential books) or a **deep dive** (5-7 books)?"
        add_message("assistant", response)

    elif stage == "ask_depth":
        depth = parse_depth(prompt)
        st.session_state.user_inputs["depth"] = depth
        
        st.session_state.stage = "recommendation"
        add_message("assistant", "Perfect. Generating your learning path now...")
        st.rerun() # Force rerun to show recommendations immediately

    elif stage == "recommendation":
        add_message("assistant", "If you'd like to start over, just type 'reset' or refresh the page.")
        if prompt.lower() == "reset":
            reset_conversation()

    st.rerun()

# --- Recommendation Rendering ---
if st.session_state.stage == "recommendation":
    inputs = st.session_state.user_inputs
    
    # Get Logic results
    filtered = filter_books(
        st.session_state.books_df,
        category=inputs["category"],
        subcategory=inputs["subcategory"],
        level=inputs["level"],
        style_pref=inputs["style"] if inputs["style"] != "any" else None
    )
    
    path = sequence_books(filtered, depth=inputs["depth"])
    
    # Render Results
    if not path.empty:
        st.markdown("### 🎯 Your Custom Reading Path")
        
        for i, (idx, book) in enumerate(path.iterrows(), 1):
            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**Step {i}: {book['title']}**")
                    st.markdown(f"*by {book['author']}*")
                    st.caption(book['short_description'])
                with col2:
                    st.link_button("Buy Book", book['store_url'])
        
        # Hint Section
        st.markdown("---")
        st.info(f"💡 **Hint for learning {inputs['category'].capitalize()}:**\n\n{get_hint_for_category(inputs['category'])}")
        
        # Add a button to reset at the bottom
        if st.button("Start Over"):
            reset_conversation()
            
    else:
        st.warning("I couldn't find enough books matching your exact criteria. Try restarting and choosing a broader category or different level.")
        if st.button("Try Again"):
            reset_conversation()
