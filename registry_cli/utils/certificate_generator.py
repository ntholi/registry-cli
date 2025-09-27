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
PALATINO_FONT_PATH = Path("fonts/palatino.ttf")  # Custom Palatino Bold font file
SNELL_FONT_PATH = Path(
    "fonts/snellroundhand_black.otf"
)  # Custom Snell Roundhand font file
OUTPUT_DIR = Path("certificates")
OUTPUT_DIR.mkdir(exist_ok=True)

# Get page dimensions for proper centering
PAGE_WIDTH, PAGE_HEIGHT = A4  # A4 is 595.276 x 841.89 points
CENTER_X = PAGE_WIDTH / 2  # Should be ~297.638 points from left edge

# Y-coordinate for student name positioning
NAME_FONT_SIZE = 30.3
NAME_Y = 695  # Student name on the underline after "It is hereby certified that"
PROGRAM_Y = 606  # Program name on the underline after "is awarded"
DATE_Y = 180  # Date positioned in bottom right area

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

    # Register custom fonts if available
    try:
        if PALATINO_FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont("PalatinoBold", str(PALATINO_FONT_PATH)))
            font_name = "PalatinoBold"
    except Exception as e:
        raise RuntimeError(f"Failed to register Snell PalatinoBold font: {e}")

    try:
        if SNELL_FONT_PATH.exists():
            pdfmetrics.registerFont(TTFont("SnellRoundhand", str(SNELL_FONT_PATH)))
            program_font_name = "SnellRoundhand"
    except Exception as e:
        raise RuntimeError(f"Failed to register Snell Roundhand font: {e}")

    c.setFont(font_name, NAME_FONT_SIZE)

    # Perfect centering: Use calculated center with +30 point offset
    # This offset was determined through visual testing to account for template-specific positioning
    perfect_center_x = (PAGE_WIDTH / 2) + 30
    c.drawCentredString(perfect_center_x, NAME_Y, name)

    # Program name - elegant script style using Snell Roundhand, centered on the underline
    c.setFont(program_font_name, 35)
    c.drawCentredString(perfect_center_x, PROGRAM_Y, program_name)

    # Date - small regular font, positioned in bottom right
    c.setFont("Helvetica", 11)
    c.drawCentredString(perfect_center_x, DATE_Y, issue_date)

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
