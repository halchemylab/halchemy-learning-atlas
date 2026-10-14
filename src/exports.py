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


def build_pdf_export(data):
    """Builds the PDF export content for a reading path."""
    return generate_pdf(data)
