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
SNELL_FONT_PATH = Path("fonts/Roundhand Bold.ttf")  # Custom Snell Roundhand font file
OUTPUT_DIR = Path("certificates")
OUTPUT_DIR.mkdir(exist_ok=True)

# Get page dimensions for proper centering
PAGE_WIDTH, PAGE_HEIGHT = A4  # A4 is 595.276 x 841.89 points
CENTER_X = PAGE_WIDTH / 2  # Should be ~297.638 points from left edge


DATE_Y = 180  # Date positioned in bottom right area

PRIMARY_COLOR = HexColor("#000000")


def _build_overlay(
    name: str, program_name: str, issue_date: str, tmp_path: Path
) -> None:
    c = canvas.Canvas(str(tmp_path), pagesize=A4)
    c.setFillColor(PRIMARY_COLOR)

    perfect_center_x = (PAGE_WIDTH / 2) + 30

    def draw_text(
        text: str,
        font_name: str,
        y_axis: float,
        font_size: float,
        letter_spacing_reduction: float = 0.0,
    ) -> None:
        c.setFont(font_name, font_size)

        if letter_spacing_reduction == 0.0:
            c.drawCentredString(perfect_center_x, y_axis, text)
            return

        # Calculate reduced letter spacing
        total_width = c.stringWidth(text, font_name, font_size)
        reduced_width = total_width - (len(text) - 1) * letter_spacing_reduction

        start_x = perfect_center_x - (reduced_width / 2)

        current_x = start_x
        for char in text:
            c.drawString(current_x, y_axis, char)
            char_width = c.stringWidth(char, font_name, font_size)
            current_x += char_width - letter_spacing_reduction

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

    draw_text(
        name,
        font_name,
        695,
        32,
        1,
    )

    draw_text(
        program_name,
        program_font_name,
        606,
        42,
        2.5,
    )
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
