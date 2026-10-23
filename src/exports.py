import streamlit as st

from src.pdf_gen import generate_pdf
from src.books import get_purchase_url


def build_markdown_export(data):
    """Builds the Markdown export content for a reading path."""
    path_title = data.get("title", f"{data['category'].title()} ({data['level'].title()})")
    lines = [
        f"# Learning Path: {path_title}",
        "",
        f"**Rationale:** {data['rationale']}",
        "",
        "## The Books",
        "",
    ]
    if data.get("rationale_stale"):
        lines.insert(2, "*The explanation below predates your edits.*\n")

    for i, book in enumerate(data["books"], 1):
        lines.extend(
            [
                f"### {i}. {book['title']}",
                f"*Author: {book['author']}*",
                "",
                book["short_description"],
                "",
            ]
        )
        purchase_url = get_purchase_url(book)
        if purchase_url:
            lines.extend([f"[Buy Link]({purchase_url})", ""])

    lines.extend(
        [
            "---",
            "",
            f"## Expert Hint\n{data['hint']}",
        ]
    )
    return "\n".join(lines)


@st.cache_data(show_spinner=False, ttl=3600, max_entries=32)
def build_pdf_export(data):
    """Caches PDF bytes by path contents, regenerating them after edits."""
    return generate_pdf(data)
