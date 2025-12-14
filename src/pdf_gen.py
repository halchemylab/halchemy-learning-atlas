from fpdf import FPDF
import tempfile

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'Halchemy Library - Learning Path', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

def generate_pdf(path_data):
    """
    Generates a PDF report for the given learning path.
    Args:
        path_data (dict): Contains 'category', 'level', 'rationale', 'hint', and 'books' (list).
    Returns:
        bytes: The PDF content in bytes.
    """
    pdf = PDFReport()
    pdf.add_page()
    
    # Title Section
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, f"Topic: {path_data['category'].title()} ({path_data['level'].title()})", 0, 1)
    pdf.ln(5)
    
    # Rationale
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Why this path?", 0, 1)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, path_data['rationale'])
    pdf.ln(5)
    
    # Books
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "The Books", 0, 1)
    
    for i, book in enumerate(path_data['books'], 1):
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, f"{i}. {book['title']}", 0, 1)
        
        pdf.set_font("Arial", 'I', 10)
        pdf.cell(0, 6, f"Author: {book['author']}", 0, 1)
        
        pdf.set_font("Arial", '', 10)
        # Handle description text wrapping and clean up
        desc = book.get('short_description', '')
        # Simple sanitization for latin-1 encoding issues often found in FPDF
        desc = desc.encode('latin-1', 'replace').decode('latin-1')
        pdf.multi_cell(0, 6, desc)
        
        link = book.get('store_url', '')
        if link:
            pdf.set_text_color(0, 0, 255)
            pdf.cell(0, 6, "Buy Link", link=link, ln=1)
            pdf.set_text_color(0, 0, 0)
            
        pdf.ln(3)

    # Hint Section
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Expert Hint", 0, 1)
    pdf.set_font("Arial", '', 11)
    hint = path_data.get('hint', '')
    hint = hint.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 6, hint)

    return pdf.output(dest='S').encode('latin-1')
