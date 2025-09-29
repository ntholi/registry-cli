import io
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import qrcode
from PIL import Image
from PyPDF2 import PdfReader, PdfWriter
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
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


def _generate_qr_code(reference: str) -> ImageReader:
    """Generate a QR code for the certificate verification URL.

    Args:
        reference: The certificate reference number

    Returns:
        ImageReader object that can be used in reportlab
    """
    verification_url = f"http://portal.co.ls/verify/certificate/{reference}"

    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,  # Controls the size of the QR Code
        error_correction=qrcode.ERROR_CORRECT_L,  # About 7% or less errors can be corrected
        box_size=10,  # Controls how many pixels each "box" of the QR code is
        border=4,  # Controls how many boxes thick the border should be
    )

    qr.add_data(verification_url)
    qr.make(fit=True)

    # Create QR code image
    qr_img = qr.make_image(fill_color="black", back_color="white")

    # Convert PIL image to ImageReader for reportlab
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, "PNG")
    img_buffer.seek(0)

    return ImageReader(img_buffer)


def _build_overlay(
    name: str, program_name: str, reference: str, issue_date: str, tmp_path: Path
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
    palatino = "palatino"
    _register_font(PALATINO_FONT_PATH, palatino)

    snell_roundhand = "SnellRoundhand"
    _register_font(SNELL_FONT_PATH, snell_roundhand)

    c.setFont(palatino, 8)
    text_width = c.stringWidth(reference, palatino, 8)
    c.drawString(PAGE_WIDTH - text_width, 772, reference)

    draw_text(
        name,
        palatino,
        695,
        32,
        1,
    )

    draw_text(
        program_name,
        snell_roundhand,
        603,
        42,
        2.5,
    )

    draw_text(
        issue_date,
        palatino,
        180,
        12.4,
    )

    # Add QR code
    qr_image = _generate_qr_code(reference)
    qr_size = 50  # Size of the QR code in points
    qr_x = perfect_center_x - (qr_size / 2)  # Align QR code with text centering
    qr_y = 220  # Position from bottom

    c.drawImage(qr_image, qr_x, qr_y, width=qr_size, height=qr_size)

    c.showPage()
    c.save()


def generate_certificate(
    name: str, program_name: str, program_code: str, std_no: int
) -> Optional[str]:
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
    # Generate reference using program code and student number
    reference = f"LSO{program_code}{std_no}"
    _build_overlay(name, program_name, reference, issue_date, overlay_path)

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
