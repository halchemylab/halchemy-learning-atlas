import re

from fpdf import FPDF
from fpdf.enums import XPos, YPos

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
    """Converts app/LLM text into clean core-font-safe PDF text."""
    if value is None:
        return ""

    text = str(value)
    replacements = {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": "-",
        "\u2014": "-",
        "\u2026": "...",
        "\u2022": "-",
        "\u00a0": " ",
    }
    for source, replacement in replacements.items():
        text = text.replace(source, replacement)

    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip().encode("latin-1", "replace").decode("latin-1")


def _title_case(value: object, fallback: str = "Learning") -> str:
    text = _clean_text(value)
    if not text:
        return fallback
    return text.replace("_", " ").replace("-", " ").title()


def _line_count(pdf: FPDF, text: str, width: float) -> int:
    """Approximates wrapped line count using the active font."""
    paragraphs = text.split("\n") or [""]
    total = 0
    for paragraph in paragraphs:
        words = paragraph.split()
        if not words:
            total += 1
            continue

        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if pdf.get_string_width(candidate) <= width:
                current = candidate
            else:
                total += 1
                current = word
        if current:
            total += 1
    return max(total, 1)


class PDFReport(FPDF):
    def __init__(self):
        super().__init__(orientation="P", unit="mm", format="Letter")
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
        self.set_font("helvetica", "B", 8)
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
        self.set_font("helvetica", "", 8)
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
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*ACCENT_DARK)
    pdf.cell(0, 5, text.upper(), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def _add_hero(pdf: PDFReport, path_data: dict) -> None:
    category = _title_case(path_data.get("category"), "Learning")
    level = _title_case(path_data.get("level"), "Custom")
    books = path_data.get("books", [])
    depth = _title_case(path_data.get("depth"), "")

    pdf.set_fill_color(*DARK)
    pdf.rect(0, 0, pdf.w, 50, style="F")
    pdf.set_xy(pdf.l_margin, 13)

    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(141, 219, 226)
    pdf.cell(0, 5, "HALCHEMY LIBRARY", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    pdf.set_font("helvetica", "B", 24)
    pdf.set_text_color(255, 255, 255)
    pdf.multi_cell(
        pdf.content_width,
        9,
        f"{category} Learning Path",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    meta = f"{level} path | {len(books)} books"
    if depth:
        meta = f"{meta} | {depth} route"
    pdf.set_font("helvetica", "", 10.5)
    pdf.set_text_color(214, 224, 232)
    pdf.cell(0, 6, meta, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    pdf.set_y(58)


def _add_info_card(
    pdf: PDFReport,
    label: str,
    body: object,
    fill_color: tuple[int, int, int] = SOFT_BLUE,
    accent_color: tuple[int, int, int] = ACCENT,
) -> None:
    text = _clean_text(body)
    if not text:
        return

    x = pdf.l_margin
    width = pdf.content_width
    inner = 6
    body_width = width - (inner * 2)
    line_height = 5.2

    pdf.set_font("helvetica", "", 10.5)
    body_height = _line_count(pdf, text, body_width) * line_height
    height = 16 + body_height

    pdf.ensure_space(height + 8)
    y = pdf.get_y()

    pdf.set_fill_color(*fill_color)
    pdf.set_draw_color(*fill_color)
    pdf.rect(x, y, width, height, style="DF", round_corners=True, corner_radius=2)
    pdf.set_fill_color(*accent_color)
    pdf.rect(x, y, 2, height, style="F")

    pdf.set_xy(x + inner, y + 4)
    _draw_label(pdf, label)
    pdf.set_font("helvetica", "", 10.5)
    pdf.set_text_color(*DARK)
    pdf.set_x(x + inner)
    pdf.multi_cell(
        body_width,
        line_height,
        text,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )
    pdf.set_y(y + height + 6)


def _add_section_title(pdf: PDFReport, title: str) -> None:
    pdf.ensure_space(14)
    pdf.set_font("helvetica", "B", 15)
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
    title = _clean_text(book.get("title", "Untitled Book"))
    author = _clean_text(book.get("author", "Unknown Author"))
    description = _clean_text(book.get("short_description", ""))
    metrics = _metric_text(book)
    link = get_purchase_url(book)

    x = pdf.l_margin
    width = pdf.content_width
    inner = 6
    left_col = 21
    text_x = x + inner + left_col
    text_width = width - (inner * 2) - left_col

    pdf.set_font("helvetica", "B", 12.5)
    title_height = _line_count(pdf, title, text_width) * 6
    pdf.set_font("helvetica", "", 9.5)
    description_height = _line_count(pdf, description, text_width) * 4.8 if description else 0
    height = 14 + title_height + description_height
    if metrics:
        height += 5
    if link:
        height += 5
    height = max(height, 34)

    pdf.ensure_space(height + 5)
    y = pdf.get_y()

    pdf.set_fill_color(*CARD)
    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.25)
    pdf.rect(x, y, width, height, style="DF", round_corners=True, corner_radius=2)

    pdf.set_fill_color(*ACCENT)
    pdf.rect(x, y, 2, height, style="F")

    pdf.set_xy(x + inner, y + 7)
    pdf.set_fill_color(*SOFT_BLUE)
    pdf.set_draw_color(*SOFT_BLUE)
    pdf.rect(pdf.get_x(), pdf.get_y(), 15, 8, style="DF", round_corners=True, corner_radius=1.5)
    pdf.set_xy(x + inner, y + 8.2)
    pdf.set_font("helvetica", "B", 8)
    pdf.set_text_color(*ACCENT_DARK)
    pdf.cell(15, 4, f"{index:02d}", align="C")

    pdf.set_xy(text_x, y + 5)
    pdf.set_font("helvetica", "B", 12.5)
    pdf.set_text_color(*DARK)
    pdf.multi_cell(
        text_width,
        6,
        title,
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    pdf.set_x(text_x)
    pdf.set_font("helvetica", "", 9.5)
    pdf.set_text_color(*MUTED)
    pdf.cell(
        text_width,
        5,
        f"by {author}",
        new_x=XPos.LMARGIN,
        new_y=YPos.NEXT,
    )

    if description:
        pdf.ln(1.5)
        pdf.set_x(text_x)
        pdf.set_font("helvetica", "", 9.5)
        pdf.set_text_color(*DARK)
        pdf.multi_cell(
            text_width,
            4.8,
            description,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    if metrics:
        pdf.ln(1.5)
        pdf.set_x(text_x)
        pdf.set_font("helvetica", "B", 8.5)
        pdf.set_text_color(*MUTED)
        pdf.cell(text_width, 4.5, metrics, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    if link:
        pdf.ln(1)
        pdf.set_x(text_x)
        pdf.set_font("helvetica", "B", 9)
        pdf.set_text_color(*ACCENT_DARK)
        pdf.cell(
            30,
            5,
            "Buy book",
            link=link,
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

    pdf.set_y(y + height + 4)


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
