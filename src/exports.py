from src.pdf_gen import generate_pdf


def build_markdown_export(data):
    """Builds the Markdown export content for a reading path."""
    lines = [
        f"# Learning Path: {data['category'].title()} ({data['level'].title()})",
        "",
        f"**Rationale:** {data['rationale']}",
        "",
        "## The Books",
        "",
    ]

    for i, book in enumerate(data["books"], 1):
        lines.extend(
            [
                f"### {i}. {book['title']}",
                f"*Author: {book['author']}*",
                "",
                book["short_description"],
                "",
                f"[Buy Link]({book['store_url']})",
                "",
            ]
        )

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
