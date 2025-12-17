import streamlit as st
import pandas as pd
import json
import os
import graphviz
from openai import OpenAI
from src.books import load_books, filter_books, sequence_books, get_hint_for_category, DataLoadingError
from src.llm_client import get_chat_completion, get_sequence_rationale
from src.roi import load_stats, increment_stats
from src.utils import fetch_book_cover
from src.pdf_gen import generate_pdf

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
    st.header("Library Stats")
    stats = load_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Paths", f"{stats.get('paths_generated', 0)}")
    with col2:
        st.metric("Books", f"{stats.get('books_recommended', 0)}")
    with col3:
        st.metric("Topics", f"{len(stats.get('topics_explored', []))}")
    
    st.divider()

    # Configuration Section
    st.header("Configuration")
    
    # Try to get key from environment or secrets first
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        api_key = st.text_input("Enter OpenAI API Key", type="password")
        if not api_key:
            st.warning("Please enter your OpenAI API Key to continue.")
            st.stop()
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
client = OpenAI(api_key=api_key)

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
def execute_recommendation(args):
    """Executes the deterministic book logic based on LLM-extracted args."""
    category = args.get("category")
    subcategory = args.get("subcategory")
    level = args.get("level", "beginner")
    style = args.get("style")
    depth = args.get("depth", "short")

    filtered = filter_books(
        st.session_state.books_df,
        category=category,
        subcategory=subcategory,
        level=level,
        style_pref=style
    )
    
    path = sequence_books(filtered, depth=depth)
    
    # Increment stats only if we actually ran a search
    increment_stats(num_books=len(path), category=category)
    
    return path, category, depth, level

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
    
    for i, (idx, book) in enumerate(path.iterrows(), 1):
        with st.container(border=True):
            col0, col1, col2 = st.columns([1, 3, 1])
            
            with col0:
                cover_url = fetch_book_cover(book['title'], book['author'])
                if cover_url:
                    st.image(cover_url, use_container_width=True)
                else:
                    st.markdown("📚") # Placeholder icon

            with col1:
                st.markdown(f"**Step {i}: {book['title']}**")
                st.markdown(f"*by {book['author']}*")
                
                # Metadata Visuals
                diff = int(book.get('difficulty', 1))
                read = int(book.get('readability', 1))
                st.caption(f"Difficulty: {'🌶️' * diff} | Readability: {'📖' * read}")
                
                st.caption(book['short_description'])
            with col2:
                st.link_button("Buy Book", book['store_url'])
    
    # Hint Section
    st.markdown("---")
    hint_text = get_hint_for_category(category)
    st.info(f"💡 **Hint for learning {category.capitalize()}:**\n\n{hint_text}")
    return hint_text


# --- Chat Interface ---

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
    markdown_content = f"# Learning Path: {data['category'].title()} ({data['level'].title()})\n\n"
    markdown_content += f"**Rationale:** {data['rationale']}\n\n"
    markdown_content += "## The Books\n\n"
    
    for i, book in enumerate(data['books'], 1):
        markdown_content += f"### {i}. {book['title']}\n"
        markdown_content += f"*Author: {book['author']}*\n\n"
        markdown_content += f"{book['short_description']}\n\n"
        markdown_content += f"[Buy Link]({book['store_url']})\n\n"
    
    markdown_content += "---\n\n"
    markdown_content += f"## Expert Hint\n{data['hint']}"
    
    st.sidebar.download_button(
        label="Download Curriculum (.md)",
        data=markdown_content,
        file_name=f"halchemy_path_{data['category']}.md",
        mime="text/markdown"
    )

    # Generate PDF on demand
    pdf_bytes = generate_pdf(data)
    st.sidebar.download_button(
        label="Download Curriculum (.pdf)",
        data=pdf_bytes,
        file_name=f"halchemy_path_{data['category']}.pdf",
        mime="application/pdf"
    )

# Initial Greeting
if not st.session_state.messages:
    intro_msg = "Hello! I'm your librarian. Tell me what you want to learn (e.g., 'Python', 'Habits', 'History'), and I'll design a reading path for you."
    st.session_state.messages.append({"role": "assistant", "content": intro_msg})
    st.rerun()

# Handle User Input
if prompt := st.chat_input("What do you want to learn?"):
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
                    args = json.loads(tool_call.function.arguments)
                    
                    # Execute Logic
                    path, category, depth, level = execute_recommendation(args)
                    
                    # Render results immediately
                    hint_text = render_books(path, category)
                    
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
                        st.session_state.current_path_data = {
                            "category": category,
                            "level": level,
                            "books": path.to_dict('records'),
                            "rationale": rationale_text,
                            "hint": hint_text
                        }
                    
                    # Save a summary message to history so context is preserved
                    success_msg = f"I've generated a {depth} reading path for **{category}** ({args.get('level')})."
                    st.session_state.messages.append({"role": "assistant", "content": success_msg})
                    
                else:
                    # Normal text response
                    content = response_message.content
                    st.markdown(content)
                    st.session_state.messages.append({"role": "assistant", "content": content})
            
            except Exception as e:
                st.error(f"An error occurred: {e}")