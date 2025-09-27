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
AGARAMOND_FONT_PATH = Path("fonts/AGaramond-Regular.ttf")  # AGaramond Regular font file
OUTPUT_DIR = Path("certificates")
OUTPUT_DIR.mkdir(exist_ok=True)

# Get page dimensions for proper centering
PAGE_WIDTH, PAGE_HEIGHT = A4  # A4 is 595.276 x 841.89 points
CENTER_X = PAGE_WIDTH / 2  # Should be ~297.638 points from left edge


PRIMARY_COLOR = HexColor("#000000")


def _register_font(font_path: Path, font_name: str) -> bool:
    """Register a font if the file exists.

    Returns True if successfully registered, False otherwise.
    """
    try:
        if font_path.exists():
            pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
            return True
    except Exception as e:
        raise RuntimeError(f"Failed to register {font_name} font: {e}")
    return False


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
        max_width: float = 550.0,
        line_spacing: float = 1.2,
    ) -> None:
        c.setFont(font_name, font_size)

        def get_text_width(text_segment: str) -> float:
            """Calculate width of text considering letter spacing reduction."""
            if letter_spacing_reduction == 0.0:
                return c.stringWidth(text_segment, font_name, font_size)
            else:
                base_width = c.stringWidth(text_segment, font_name, font_size)
                return base_width - (len(text_segment) - 1) * letter_spacing_reduction

        def draw_line(line_text: str, y_pos: float) -> None:
            """Draw a single line of text."""
            if letter_spacing_reduction == 0.0:
                c.drawCentredString(perfect_center_x, y_pos, line_text)
                return

            # Calculate reduced letter spacing for this line
            line_width = get_text_width(line_text)
            start_x = perfect_center_x - (line_width / 2)

            current_x = start_x
            for char in line_text:
                c.drawString(current_x, y_pos, char)
                char_width = c.stringWidth(char, font_name, font_size)
                current_x += char_width - letter_spacing_reduction

        # Check if text fits in one line
        if get_text_width(text) <= max_width:
            draw_line(text, y_axis)
            return

        # Split text into multiple lines
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word

            if get_text_width(test_line) <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Single word is too long, break it by characters
                    if get_text_width(word) > max_width:
                        char_line = ""
                        for char in word:
                            test_char_line = char_line + char
                            if get_text_width(test_char_line) <= max_width:
                                char_line = test_char_line
                            else:
                                if char_line:
                                    lines.append(char_line)
                                char_line = char
                        if char_line:
                            current_line = char_line
                    else:
                        current_line = word

        if current_line:
            lines.append(current_line)

        # Draw lines with proper spacing
        line_height = font_size * line_spacing
        total_height = (len(lines) - 1) * line_height
        start_y = y_axis + (total_height / 2)

        for i, line in enumerate(lines):
            line_y = start_y - (i * line_height)
            draw_line(line, line_y)

    # Register custom fonts if available
    font_name = "PalatinoBold"
    _register_font(PALATINO_FONT_PATH, font_name)

    program_font_name = "SnellRoundhand"
    _register_font(SNELL_FONT_PATH, program_font_name)

    date_font_name = "AGaramondPro"
    _register_font(AGARAMOND_FONT_PATH, date_font_name)

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
        603,
        42,
        2.5,
    )

    draw_text(
        issue_date,
        date_font_name,
        180,
        11,
        0.0,
    )

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
