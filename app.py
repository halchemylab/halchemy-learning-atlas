from dotenv import load_dotenv

# Load environment variables
load_dotenv()

import streamlit as st
import pandas as pd
import json
import logging
import os
import graphviz
from copy import deepcopy
from html import escape
from openai import OpenAI
from src.books import load_books, get_hint_for_category, get_purchase_url, get_unique_values, DataLoadingError
from src.exports import build_markdown_export, build_pdf_export
from src.llm_client import LLMClientError, get_chat_completion, get_sequence_rationale
from src.path_editor import get_replacement_candidates, move_book, remove_book, replace_book
from src.recommendations import execute_recommendation
from src.roi import load_stats, increment_stats
from src.utils import fetch_book_cover
from src.starter_paths import STARTER_PATHS, build_starter_path
from src.workspace import commit_path, edit_books, undo_path


logger = logging.getLogger(__name__)

# --- Page Config ---
st.set_page_config(
    page_title="Halchemy Library (AI-Powered)",
    page_icon="📚",
    layout="centered"
)

# --- Setup & API Key ---
st.title("Halchemy Library 📚")
st.caption("Your AI Librarian for curated learning paths.")

# --- Sidebar: ROI & Config ---
with st.sidebar:
    # Library Stats Section
    st.header("📊 Library Stats")
    
    # Create placeholders for dynamic updates
    with st.container(border=True):
        paths_placeholder = st.empty()
    
    with st.container(border=True):
        books_placeholder = st.empty()
        
    def update_stats_display():
        """Reloads stats and updates the sidebar placeholders."""
        current_stats = load_stats()
        paths_placeholder.metric("Paths", f"{current_stats.get('paths_generated', 0)} linked")
        books_placeholder.metric("Books", f"{current_stats.get('books_recommended', 0)} recommended")

    # Initial render
    update_stats_display()
    
    st.divider()

    # Configuration Section
    st.header("⚙️ Configuration")
    
    # Try to get key from environment or secrets first
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = st.text_input("Enter OpenAI API Key", type="password")
        if not api_key:
            st.info("Build, edit, and download reading paths without a key. Add an API key for chat and AI explanations.")
    else:
        st.success("API Key loaded from environment.")

    # Model and Temperature selectors
    # Ensure default model is set in session state if not already present
    if "model" not in st.session_state:
        st.session_state.model = "gpt-4o-mini"
    
    st.session_state.model = st.selectbox(
        "Select LLM Model",
        ["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"],
        index=["gpt-4o-mini", "gpt-4", "gpt-3.5-turbo"].index(st.session_state.model),
        key="model_selector"
    )

    # Ensure default temperature is set in session state if not already present
    if "temperature" not in st.session_state:
        st.session_state.temperature = 0.7
        
    st.session_state.temperature = st.slider(
        "Temperature (creativity)",
        min_value=0.0,
        max_value=1.5,
        value=st.session_state.temperature,
        step=0.1,
        key="temperature_slider"
    )

# Initialize OpenAI Client
client = OpenAI(api_key=api_key) if api_key else None

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = []

try:
    if "books_df" not in st.session_state:
        st.session_state.books_df = load_books()
except DataLoadingError as e:
    st.error(f"🚨 System Error: {e}")
    st.info("Please ensure 'data/books.csv' exists and is correctly formatted.")
    st.stop()

if "current_path_data" not in st.session_state:
    st.session_state.current_path_data = None

# --- Helper Functions ---
@st.cache_data(show_spinner=False)
def books_to_dataframe(books):
    """Converts stored book records back into a DataFrame for rendering."""
    return pd.DataFrame(books)

def update_current_path_books(books):
    """Persist manual edits with a reversible snapshot."""
    edit_books(st.session_state, books)

def render_roadmap(path):
    """Generates a Graphviz visualization of the learning path."""
    if path.empty:
        return None

    graph = graphviz.Digraph()
    graph.attr(rankdir='LR') # Left to Right layout
    
    # Define node styles
    graph.attr('node', shape='box', style='filled', fillcolor='lightblue', fontname='Arial')
    
    previous_node_id = None
    
    for i, (idx, book) in enumerate(path.iterrows(), 1):
        # Create a unique ID for the node
        node_id = f"book_{i}"
        
        # Label with wrapping for better readability
        label = f"Step {i}\n{book['title']}\n({book['author']})"
        
        graph.node(node_id, label)
        
        # Connect to previous node
        if previous_node_id:
            graph.edge(previous_node_id, node_id)
            
        previous_node_id = node_id
        
    return graph

def render_books(path, category):
    """Renders the book cards and hint."""
    if path.empty:
        st.warning("I couldn't find enough books matching those exact criteria. Try a broader category.")
        return

    st.markdown("### 🎯 Your Custom Reading Path")
    
    # 1. Render Visual Roadmap
    roadmap = render_roadmap(path)
    if roadmap:
        with st.expander("🗺️ View Learning Map", expanded=True):
            st.graphviz_chart(roadmap)
    
    st.caption("Ratings use a 1–5 scale. Higher difficulty means more challenging; higher readability means easier to read.")

    for i, (idx, book) in enumerate(path.iterrows(), 1):
        with st.container(border=True):
            cover_column, details_column = st.columns([1, 4])
            
            with cover_column:
                cover_url = fetch_book_cover(book['title'], book['author'])
                cover_frame_style = (
                    "width:112px;max-width:100%;aspect-ratio:2/3;"
                    "display:flex;align-items:center;justify-content:center;"
                    "background:var(--secondary-background-color);"
                    "border:1px solid rgba(128,128,128,0.25);border-radius:6px;"
                    "overflow:hidden;"
                )
                if cover_url:
                    st.html(
                        f'<div style="{cover_frame_style}">'
                        f'<img src="{escape(str(cover_url), quote=True)}" '
                        f'alt="{escape(str(book["title"]), quote=True)} cover" '
                        'loading="lazy" style="width:100%;height:100%;object-fit:contain;">'
                        '</div>'
                    )
                else:
                    st.html(
                        f'<div style="{cover_frame_style}">'
                        '<div style="text-align:center;padding:12px;font-size:0.8rem;">'
                        '<span aria-hidden="true" style="font-size:2rem;">📚</span>'
                        '<br>Cover unavailable</div></div>'
                    )

            with details_column:
                st.html(
                    f'<p style="margin:0 0 4px;font-size:0.8rem;font-weight:600;">STEP {i}</p>'
                    f'<h3 style="margin:0 0 6px;padding:0;font-size:1.25rem;line-height:1.35;">'
                    f'{escape(str(book["title"]))}</h3>'
                    f'<p style="margin:0 0 12px;font-size:0.95rem;">by {escape(str(book["author"]))}</p>'
                )

                st.write(book['short_description'])
                
                diff = int(book.get('difficulty', 1))
                read = int(book.get('readability', 1))
                st.caption(f"Difficulty: **{diff}/5** · Readability: **{read}/5**")
                
                purchase_url = get_purchase_url(book)
                if purchase_url:
                    st.link_button("Buy Book", purchase_url)
                else:
                    st.caption("No purchase link")
    
    # Hint Section
    st.markdown("---")
    hint_text = get_hint_for_category(category)
    st.info(f"💡 **Hint for learning {category.capitalize()}:**\n\n{hint_text}")
    return hint_text

def render_path_editor(data):
    """Renders manual controls for editing the current reading path."""
    books = data["books"]
    replacement_candidates = get_replacement_candidates(
        st.session_state.books_df,
        books,
        category=data["category"],
        subcategory=data.get("subcategory"),
        level=data.get("level", "beginner"),
        style=data.get("style"),
    )
    st.markdown("### Edit Path")

    if len(books) < 3:
        st.warning("Reading paths work best with at least 3 books.")

    with st.expander("Reorder, remove, or replace books", expanded=False):
        for index, book in enumerate(books):
            cols = st.columns([5, 1, 1, 1])
            with cols[0]:
                st.markdown(f"**{index + 1}. {book['title']}**")
                st.caption(f"by {book['author']}")
            with cols[1]:
                if st.button("Up", key=f"move_up_{index}_{book['id']}", disabled=index == 0):
                    update_current_path_books(move_book(books, index, -1))
                    st.rerun()
            with cols[2]:
                if st.button("Down", key=f"move_down_{index}_{book['id']}", disabled=index == len(books) - 1):
                    update_current_path_books(move_book(books, index, 1))
                    st.rerun()
            with cols[3]:
                if st.button("Remove", key=f"remove_{index}_{book['id']}"):
                    update_current_path_books(remove_book(books, index))
                    st.rerun()

            if replacement_candidates:
                selected_label = st.selectbox(
                    "Replacement",
                    options=list(range(len(replacement_candidates))),
                    format_func=lambda candidate_index: (
                        f"{replacement_candidates[candidate_index]['title']} by "
                        f"{replacement_candidates[candidate_index]['author']} "
                        f"| Difficulty {replacement_candidates[candidate_index]['difficulty']} "
                        f"| Readability {replacement_candidates[candidate_index]['readability']}"
                    ),
                    key=f"replacement_{index}_{book['id']}",
                    label_visibility="collapsed",
                )
                if st.button("Replace this step", key=f"replace_{index}_{book['id']}"):
                    replacement = replacement_candidates[selected_label]
                    update_current_path_books(replace_book(books, index, replacement))
                    st.rerun()
            else:
                st.caption("No replacement candidates available for this step.")

            st.divider()

    if data.get("rationale_stale"):
        st.warning("The path explanation was written before your edits.")
    if data.get("rationale_stale") or data.get("rationale_source") == "criteria":
        if not client:
            st.caption("Add an API key in the sidebar for an AI explanation of this path.")
        explanation_label = "Refresh rationale" if data.get("rationale_stale") else "Explain this path with AI"
        if st.button(explanation_label, disabled=client is None):
            with st.spinner("Refreshing rationale..."):
                data = deepcopy(data)
                data["rationale"] = get_sequence_rationale(
                    client,
                    data.get("user_query", "this learning goal"),
                    data["books"],
                    model=st.session_state.model,
                )
                data["rationale_stale"] = False
                data["rationale_source"] = "ai"
                commit_path(st.session_state, data, "Refreshed the path explanation.")
                st.rerun()


# --- Chat Interface ---

# Starter paths are available before any AI configuration or conversation.
st.markdown("### Start with a ready-made path")
st.caption("Choose a topic to explore 3–4 curated books. No API key needed.")
for column, starter in zip(st.columns(3), STARTER_PATHS):
    with column:
        with st.container(border=True):
            st.markdown(f"**{starter['title']}**")
            st.caption(f"{starter['audience']} · {len(starter['book_ids'])} books")
            st.write(starter["goal"])
            if st.button("Explore this path", key=f"starter_{starter['id']}"):
                new_path = build_starter_path(
                    st.session_state.books_df, starter["id"]
                )
                commit_path(st.session_state, new_path, f"Opened {starter['title']}.")
                # Keep the AI conversation aligned with the newly selected path.
                st.session_state.messages = [{
                    "role": "assistant",
                    "content": f"You're exploring {starter['title']}. Your current books, in order, are: "
                    + "; ".join(book["title"] for book in st.session_state.current_path_data["books"])
                    + ". You can edit the path below or tell me how you'd like to customize it.",
                }]
                increment_stats(num_books=len(starter["book_ids"]), category=starter["category"])
                st.rerun()

# The topic sits outside the form so subtopic/style choices update immediately.
st.markdown("### Build your own path")
st.caption("Choose your preferences to build a curated reading path. No API key needed.")
builder_category = st.selectbox(
    "Topic", get_unique_values(st.session_state.books_df, "category"),
    format_func=str.title, key="builder_category",
)
topic_books = st.session_state.books_df[
    st.session_state.books_df["category"] == builder_category
]
with st.form("path_builder"):
    builder_level = st.selectbox(
        "Experience", ["beginner", "intermediate", "advanced"],
        format_func=str.title, key="builder_level",
    )
    builder_depth = st.selectbox(
        "Depth", ["short", "deep"],
        format_func=lambda value: "Short path (3 books)" if value == "short" else "Deep dive (5–7 books)",
        key="builder_depth",
    )
    builder_subcategory = st.selectbox(
        "Subtopic (optional)", [None] + get_unique_values(topic_books, "subcategory"),
        format_func=lambda value: "Any subtopic" if value is None else value.replace("-", " ").title(),
        key=f"builder_subcategory_{builder_category}",
    )
    builder_style = st.selectbox(
        "Reading style (optional)", [None] + get_unique_values(topic_books, "style"),
        format_func=lambda value: "Any style" if value is None else value.title(),
        key=f"builder_style_{builder_category}",
    )
    build_requested = st.form_submit_button("Build my path")

if build_requested:
    result = execute_recommendation(st.session_state.books_df, {
        "category": builder_category,
        "subcategory": builder_subcategory,
        "level": builder_level,
        "depth": builder_depth,
        "style": builder_style,
    })
    if result.path.empty:
        st.warning("No books match this topic and experience level. Try another level or topic. Your current path is still available below.")
    else:
        goal = f"Learn {builder_subcategory or builder_category} at {builder_level} level with a {builder_depth} reading path."
        if builder_style:
            goal += f" Preferred reading style: {builder_style}."
        new_path = {
            "title": f"{(builder_subcategory or builder_category).replace('-', ' ').title()} Reading Path",
            "category": result.category,
            "subcategory": result.subcategory,
            "level": result.level,
            "style": result.style,
            "depth": result.depth,
            "user_query": goal,
            "books": result.path.to_dict("records"),
            "rationale": f"Requested goal: {goal} This path uses matching books from the curated library, sequenced by the recommendation engine. Any adjustments to your preferences are listed with the path.",
            "rationale_source": "criteria",
            "rationale_stale": False,
            "notices": list(result.notices),
            "hint": get_hint_for_category(result.category),
        }
        commit_path(st.session_state, new_path, "Built a reading path.")
        st.session_state.messages = [{
            "role": "assistant",
            "content": f"Your reading goal: {goal} Your current books, in order, are: "
            + "; ".join(book["title"] for book in st.session_state.current_path_data["books"])
            + ". You can edit and download this path, or optionally customize it with the AI librarian.",
        }]
        st.rerun()

# Display Chat History
for msg in st.session_state.messages:
    # We only display user and assistant text messages, not tool calls/results
    if msg["role"] in ["user", "assistant"] and msg.get("content"):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# Export Button (Sidebar)
if st.session_state.current_path_data:
    st.sidebar.divider()
    st.sidebar.header("📥 Export")
    
    data = st.session_state.current_path_data
    markdown_content = build_markdown_export(data)
    
    st.sidebar.download_button(
        label="Download Curriculum (.md)",
        data=markdown_content,
        file_name=f"halchemy_path_{data['category']}.md",
        mime="text/markdown"
    )

    st.sidebar.download_button(
        label="Download Curriculum (.pdf)",
        data=build_pdf_export(data),
        file_name=f"halchemy_path_{data['category']}.pdf",
        mime="application/pdf"
    )

# Initial Greeting
if not st.session_state.messages:
    intro_msg = "Hello! I'm your librarian. Explore a ready-made path or build your own above. Add an API key for optional chat and AI explanations."
    st.session_state.messages.append({"role": "assistant", "content": intro_msg})
    st.rerun()

# Current editable path
if st.session_state.get("last_path_change"):
    change = st.session_state.last_path_change
    st.success(change["summary"])
    with st.expander("What changed", expanded=False):
        for detail in change["details"]:
            st.write(detail)
if st.session_state.get("path_history"):
    if st.button("Undo last change", key="undo_path"):
        undo_path(st.session_state)
        st.rerun()

if st.session_state.current_path_data:
    current_data = st.session_state.current_path_data
    if current_data.get("title"):
        st.markdown(f"## {current_data['title']}")
    current_path = books_to_dataframe(current_data["books"])
    if current_data.get("notices"):
        st.caption("When this path was generated:")
        for notice in current_data["notices"]:
            st.warning(notice)
    render_books(current_path, current_data["category"])
    if current_data.get("rationale"):
        st.info(f"🤔 **Why this path?**\n\n{current_data['rationale']}")
    render_path_editor(current_data)
    st.caption("Customize this path using the editor above, or describe your goals to the AI librarian below.")

# Handle User Input
if not client:
    st.info("Add an OpenAI API key in the sidebar to chat with the librarian. Building paths, manual edits, and downloads work without a key.")
if prompt := st.chat_input("What do you want to learn or change about this path?", disabled=client is None):
    # 1. Add User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Call LLM
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Prepare messages for API (exclude tool_output artifacts if we were strictly adhering to history, 
                # but for this simple loop, we send the full conversation state)
                # We need to be careful about serializing the history correctly if we had previous tool calls.
                # For MVP simplicity, we'll just send the text messages to keep context clear, 
                # or we need to handle the full tool-call/tool-response lifecycle.
                # Let's use a simplified history for the context window to avoid "invalid role" errors 
                # if we don't strictly pair tool calls with tool outputs in the list.
                
                # Actually, let's just filter for text for the context to be safe, 
                # unless we strictly manage the tool lifecycle.
                
                api_messages = [
                    {"role": m["role"], "content": m["content"]} 
                    for m in st.session_state.messages 
                    if m.get("content") is not None
                ]
                
                response_message = get_chat_completion(client, api_messages, model=st.session_state.model, temperature=st.session_state.temperature)

                # 3. Handle Response
                if response_message.tool_calls:
                    # The LLM wants to run the search!
                    tool_call = response_message.tool_calls[0]
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError as exc:
                        logger.warning("Invalid tool arguments from LLM: %s", tool_call.function.arguments, exc_info=True)
                        st.error("I couldn't read the model's search parameters. Please try rephrasing your request.")
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": "I couldn't read the model's search parameters. Please try rephrasing your request."
                        })
                        st.stop()
                    
                    # Execute Logic
                    result = execute_recommendation(st.session_state.books_df, args)
                    path = result.path
                    category = result.category
                    depth = result.depth
                    level = result.level
                    
                    # Update sidebar stats immediately
                    update_stats_display()
                    
                    hint_text = get_hint_for_category(category)
                    
                    # Generate Rationale
                    rationale_text = ""
                    if not path.empty:
                        with st.spinner("Analyzing your path..."):
                            rationale_text = get_sequence_rationale(
                                client, 
                                prompt, 
                                path.to_dict('records'), 
                                model=st.session_state.model
                            )
                            st.info(f"🤔 **Why this path?**\n\n{rationale_text}")

                        # Save to session state for export
                        new_path = {
                            "category": category,
                            "subcategory": args.get("subcategory"),
                            "level": level,
                            "style": result.style,
                            "depth": depth,
                            "user_query": prompt,
                            "books": path.to_dict('records'),
                            "rationale": rationale_text,
                            "rationale_stale": False,
                            "notices": list(result.notices),
                            "hint": hint_text
                        }
                        commit_path(st.session_state, new_path, "Generated a reading path in chat.")
                    else:
                        no_results_msg = (
                            "I couldn't find enough books matching those exact criteria. "
                            "Try a broader category, level, or style."
                        )
                        st.warning(no_results_msg)
                        st.session_state.messages.append({"role": "assistant", "content": no_results_msg})
                        st.stop()
                    
                    # Save a summary message to history so context is preserved
                    success_msg = f"I've generated a {depth} reading path for **{category}** ({args.get('level')})."
                    st.session_state.messages.append({"role": "assistant", "content": success_msg})
                    st.rerun()
                    
                else:
                    # Normal text response
                    content = response_message.content
                    st.markdown(content)
                    st.session_state.messages.append({"role": "assistant", "content": content})
            
            except LLMClientError as e:
                st.error(e.user_message)
                st.session_state.messages.append({"role": "assistant", "content": e.user_message})
            except Exception as e:
                logger.exception("Unexpected app error while handling chat input")
                st.error("An unexpected error occurred. Check the app logs for details.")
