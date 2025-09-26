import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

TEMPLATE_PATH = Path("sample.pdf")  # Provided template file
PALATINO_FONT_PATH = Path("palatino_bold.ttf")  # Custom Palatino Bold font file
OUTPUT_DIR = Path("certificates")
OUTPUT_DIR.mkdir(exist_ok=True)

# Get page dimensions for proper centering
PAGE_WIDTH, PAGE_HEIGHT = A4
CENTER_X = PAGE_WIDTH / 2  # Exact horizontal center

NAME_COORDS = (
    CENTER_X,
    695,
)  # Student name on the underline after "It is hereby certified that"
NAME_FONT_SIZE = 32
NAME_MIN_FONT_SIZE = 16
NAME_HORIZONTAL_PADDING = 60  # leave breathing room on both sides of the page
PROGRAM_COORDS = (CENTER_X, 460)  # Program name on the underline after "is awarded"
DATE_COORDS = (430, 290)  # Date positioned in bottom right area

PRIMARY_COLOR = HexColor("#000000")


def _build_overlay(
    name: str, program_name: str, issue_date: str, tmp_path: Path
) -> None:
    """Create a temporary PDF overlay with the dynamic certificate fields.

    Args:
        name: Student full name
        program_name: Program name
        issue_date: Date string to display
        tmp_path: Path to write the overlay PDF
    """
    c = canvas.Canvas(str(tmp_path), pagesize=A4)
    c.setFillColor(PRIMARY_COLOR)

    # Register custom Palatino Bold font if available
    try:
        if PALATINO_FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont("PalatinoBold", str(PALATINO_FONT_PATH)))
            font_name = "PalatinoBold"
        else:
            # Fallback to built-in font
            font_name = "Helvetica-Bold"
    except Exception:
        font_name = "Helvetica-Bold"

    # Student name - Palatino bold, dynamically centered and scaled if needed
    font_size = NAME_FONT_SIZE
    c.setFont(font_name, font_size)

    def _string_width(text: str, font: str, size: float) -> float:
        try:
            return pdfmetrics.stringWidth(text, font, size)
        except KeyError:
            # If the selected font isn't registered, fall back to a built-in font for width
            return pdfmetrics.stringWidth(text, "Helvetica-Bold", size)

    name_width = _string_width(name, font_name, font_size)
    max_name_width = max(PAGE_WIDTH - (NAME_HORIZONTAL_PADDING * 2), 1)

    if name_width > max_name_width:
        scale = max_name_width / name_width
        adjusted_size = max(NAME_MIN_FONT_SIZE, font_size * scale)
        if adjusted_size != font_size:
            font_size = adjusted_size
            c.setFont(font_name, font_size)
            name_width = _string_width(name, font_name, font_size)

    name_x = (PAGE_WIDTH - name_width) / 2
    c.drawString(name_x, NAME_COORDS[1], name)

    # Program name - elegant italic script style, centered on the underline
    c.setFont("Helvetica-Oblique", 18)
    c.drawCentredString(PROGRAM_COORDS[0], PROGRAM_COORDS[1], program_name)

    # Date - small regular font, positioned in bottom right
    c.setFont("Helvetica", 11)
    c.drawString(DATE_COORDS[0], DATE_COORDS[1], issue_date)

    c.showPage()
    c.save()


def generate_certificate(name: str, program_name: str) -> Optional[str]:
    """Generate a graduation certificate PDF based on sample template.

    This overlays the student's name and program on the first page of sample.pdf.

    Returns path to generated PDF or None on failure.
    """
    if not TEMPLATE_PATH.exists():
        return None

    issue_date = datetime.now().strftime("%d %B %Y")

    # Prepare output filename
    safe_name = "_".join(name.split())
    output_file = (
        OUTPUT_DIR
        / f"certificate_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    # Create overlay
    overlay_path = OUTPUT_DIR / "_overlay_temp.pdf"
    _build_overlay(name, program_name, issue_date, overlay_path)

    try:
        base_reader = PdfReader(str(TEMPLATE_PATH))
        overlay_reader = PdfReader(str(overlay_path))
        writer = PdfWriter()

        # Merge only first page (assuming single-page template)
        base_page = base_reader.pages[0]
        overlay_page = overlay_reader.pages[0]
        base_page.merge_page(overlay_page)
        writer.add_page(base_page)

        # Copy remaining pages if any
        for page in base_reader.pages[1:]:
            writer.add_page(page)

        with open(output_file, "wb") as f_out:
            writer.write(f_out)

        return str(output_file)
    except Exception:
        return None
    finally:
        # Cleanup overlay
        if overlay_path.exists():
            try:
                overlay_path.unlink()
            except Exception:
                pass
