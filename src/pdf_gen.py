import re
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import MethodReturnValue, XPos, YPos

from src.books import get_purchase_url


DARK = (28, 37, 49)
MUTED = (92, 103, 116)
ACCENT = (29, 128, 143)
ACCENT_DARK = (18, 97, 111)
PAPER = (248, 250, 252)
CARD = (255, 255, 255)
BORDER = (222, 228, 235)
SOFT_BLUE = (232, 242, 246)
SOFT_GREEN = (235, 247, 241)


def _clean_text(value: object) -> str:
    """Converts app/LLM text into clean Unicode PDF text."""
    if value is None:
        return ""

    text = str(value)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _title_case(value: object, fallback: str = "Learning") -> str:
    text = _clean_text(value)
    if not text:
        return fallback
    return text.replace("_", " ").replace("-", " ").title()


class PDFReport(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="Letter")
        # Bundle licensed fonts so exports work on any host without system fonts.
        font_dir = Path(__file__).resolve().parent.parent / "assets" / "fonts"
        self.add_font("DejaVu", "", font_dir / "DejaVuSans.ttf")
        self.add_font("DejaVu", "B", font_dir / "DejaVuSans-Bold.ttf")
        self.set_margins(16, 16, 16)
        self.set_auto_page_break(auto=True, margin=18)

    @property
    def content_width(self) -> float:
        return self.w - self.l_margin - self.r_margin

    def ensure_space(self, height: float) -> None:
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()

    def header(self):
        if self.page_no() == 1:
            return

        self.set_y(10)
        self.set_font("DejaVu", "B", 8)
        self.set_text_color(*MUTED)
        self.cell(
            0,
            5,
            "HALCHEMY LIBRARY",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )
        self.set_draw_color(*BORDER)
        self.set_line_width(0.25)
        self.line(self.l_margin, 17, self.w - self.r_margin, 17)
        self.set_y(22)

    def footer(self):
        self.set_y(-13)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*MUTED)
        self.cell(
            0,
            5,
            f"Page {self.page_no()}",
            align="C",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )


def _draw_label(pdf: PDFReport, text: str) -> None:
    pdf.set_font("DejaVu", "B", 8)
    pdf.set_text_color(*ACCENT_DARK)
    pdf.cell(0, 5, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _add_hero(pdf: PDFReport, path_data: dict) -> None:
    category = _title_case(path_data.get("category"), "Learning")
    level = _title_case(path_data.get("level"), "Custom")
    books = path_data.get("books", [])
    depth = _title_case(path_data.get("depth"), "")

    title = _clean_text(path_data.get("title")) or f"{category} Learning Path"
    meta = f"{level} path | {len(books)} books"
    if depth:
        meta = f"{meta} | {depth} route"
    pdf.set_font("DejaVu", "B", 24)
    title_height = pdf.multi_cell(pdf.content_width, 9, title, dry_run=True,
                                  output=MethodReturnValue.HEIGHT)
    pdf.set_font("DejaVu", "", 10.5)
    meta_height = pdf.multi_cell(pdf.content_width, 6, meta, dry_run=True,
                                 output=MethodReturnValue.HEIGHT)
    hero_height = max(50, 28 + title_height + meta_height)
    pdf.set_fill_color(*DARK)
    pdf.rect(0, 0, pdf.w, hero_height, style="F")
    pdf.set_xy(pdf.l_margin, 13)

    pdf.set_font("DejaVu", "B", 8)
    pdf.set_text_color(141, 219, 226)
    pdf.cell(0, 5, "HALCHEMY LIBRARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("DejaVu", "B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(
        pdf.content_width,
        9,
        title,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_font("DejaVu", "", 10.5)
    pdf.set_text_color(214, 224, 232)
    pdf.multi_cell(pdf.content_width, 6, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_y(hero_height + 8)


def _wrapped_rows(pdf, text, width, size, style="", color=DARK, height=5.2, link=""):
    """Measure with the same wrapping engine used to render the PDF."""
    pdf.set_font("DejaVu", style, size)
    lines = pdf.multi_cell(
        width, height, _clean_text(text), dry_run=True,
        output=MethodReturnValue.LINES,
    )
    return [(line, size, style, color, height, link) for line in lines]


def _flow_card(pdf, rows, label, fill_color, accent_color):
    """Keep normal cards together and split oversized cards into labeled panels."""
    width = pdf.content_width
    padding = 6
    overhead = 19
    full_height = overhead + sum(row[4] for row in rows)
    page_capacity = pdf.page_break_trigger - 22
    if full_height <= page_capacity:
        pdf.ensure_space(full_height + 4)
    continued = False
    while rows:
        pdf.ensure_space(overhead + rows[0][4] + 4)
        y = pdf.get_y()
        available = pdf.page_break_trigger - y - overhead - 4
        count, body_height = 0, 0
        for row in rows:
            if body_height + row[4] > available:
                break
            body_height += row[4]
            count += 1
        chunk, rows = rows[:count], rows[count:]
        height = overhead + body_height
        pdf.set_fill_color(*fill_color)
        pdf.set_draw_color(*BORDER)
        pdf.rect(pdf.l_margin, y, width, height, style="DF", round_corners=True, corner_radius=2)
        pdf.set_fill_color(*accent_color)
        pdf.rect(pdf.l_margin, y, 2, height, style="F")
        pdf.set_xy(pdf.l_margin + padding, y + 4)
        _draw_label(pdf, label + (" (continued)" if continued else ""))
        pdf.set_y(y + 12)
        for text, size, style, color, line_height, link in chunk:
            pdf.set_x(pdf.l_margin + padding)
            pdf.set_font("DejaVu", style, size)
            pdf.set_text_color(*color)
            pdf.cell(width - 2 * padding, line_height, text, link=link,
                     new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pdf.set_y(y + height + 4)
        if rows:
            pdf.add_page()
            continued = True


def _add_info_card(
    pdf: PDFReport, label: str, body: object,
    fill_color: tuple[int, int, int] = SOFT_BLUE,
    accent_color: tuple[int, int, int] = ACCENT,
) -> None:
    if not _clean_text(body):
        return
    rows = _wrapped_rows(pdf, body, pdf.content_width - 12, 10.5)
    _flow_card(pdf, rows, label, fill_color, accent_color)


def _add_section_title(pdf: PDFReport, title: str) -> None:
    pdf.ensure_space(45)
    pdf.set_font("DejaVu", "B", 15)
    pdf.set_text_color(*DARK)
    pdf.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.25)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(4)


def _metric_text(book: dict) -> str:
    difficulty = _clean_text(book.get("difficulty", ""))
    readability = _clean_text(book.get("readability", ""))
    metrics = []
    if difficulty:
        metrics.append(f"Difficulty {difficulty}/5")
    if readability:
        metrics.append(f"Readability {readability}/5")
    return "  |  ".join(metrics)


def _add_book_card(pdf: PDFReport, index: int, book: dict) -> None:
    width = pdf.content_width - 12
    rows = _wrapped_rows(pdf, book.get("title", "Untitled Book"), width, 12.5, "B", height=6)
    rows += _wrapped_rows(pdf, f"by {book.get('author', 'Unknown Author')}", width, 9.5, color=MUTED)
    if book.get("short_description"):
        rows += _wrapped_rows(pdf, book["short_description"], width, 9.5, height=4.8)
    metrics = _metric_text(book)
    if metrics:
        rows += _wrapped_rows(pdf, metrics, width, 8.5, "B", MUTED)
    link = get_purchase_url(book)
    if link:
        rows += _wrapped_rows(pdf, "Buy book", width, 9, "B", ACCENT_DARK, link=link)
    _flow_card(pdf, rows, f"Step {index:02d}", CARD, ACCENT)


def generate_pdf(path_data):
    """
    Generates a polished PDF report for the given learning path.

    Args:
        path_data (dict): Contains category, level, rationale, hint, and books.

    Returns:
        bytes: The PDF content in bytes.
    """
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_fill_color(*PAPER)
    pdf.rect(0, 50, pdf.w, pdf.h - 50, style="F")

    _add_hero(pdf, path_data)
    _add_info_card(pdf, "Your Goal", path_data.get("user_query", ""))
    if path_data.get("notices"):
        _add_info_card(
            pdf, "When This Path Was Generated",
            "\n\n".join(path_data["notices"]),
            fill_color=(255, 247, 225), accent_color=(168, 109, 20),
        )
    if path_data.get("rationale_stale"):
        _add_info_card(
            pdf, "Explanation needs updating",
            "The explanation below predates your edits. The reading sequence reflects your current path.",
            fill_color=(255, 247, 225), accent_color=(168, 109, 20),
        )
    _add_info_card(pdf, "Why this path", path_data.get("rationale", ""))

    books = path_data.get("books", [])
    if books:
        _add_section_title(pdf, "Reading Sequence")
        for index, book in enumerate(books, 1):
            _add_book_card(pdf, index, book)

    _add_info_card(
        pdf,
        "Expert Hint",
        path_data.get("hint", ""),
        fill_color=SOFT_GREEN,
        accent_color=(42, 145, 95),
    )

    return bytes(pdf.output())
