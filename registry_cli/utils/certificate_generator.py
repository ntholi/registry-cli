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

PRIMARY_COLOR = HexColor("#000000")

DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT = A4
REFERENCE_RIGHT_MARGIN = 36
TEXT_HORIZONTAL_MARGIN = 60


def expand_program_name(program_name: str) -> str:
    """Expand abbreviated degree names to their full forms.

    Args:
        program_name: The original program name (e.g., "BA in Interior Architecture")

    Returns:
        The expanded program name (e.g., "Bachelor of Arts in Interior Architecture")
    """
    # Dictionary mapping abbreviations to full degree names
    degree_expansions = {
        "BA": "Bachelor of Arts",
        "BSc": "Bachelor of Science",
        "B Bus": "Bachelor of Business",
        "BCom": "Bachelor of Commerce",
        "BEd": "Bachelor of Education",
        "BEng": "Bachelor of Engineering",
        "BFA": "Bachelor of Fine Arts",
        "BIT": "Bachelor of Information Technology",
        "BN": "Bachelor of Nursing",
        "LLB": "Bachelor of Laws",
        "MA": "Master of Arts",
        "MSc": "Master of Science",
        "MBA": "Master of Business Administration",
        "MEd": "Master of Education",
        "MEng": "Master of Engineering",
        "MFA": "Master of Fine Arts",
        "MIT": "Master of Information Technology",
        "LLM": "Master of Laws",
        "PhD": "Doctor of Philosophy",
        "DBA": "Doctor of Business Administration",
        "EdD": "Doctor of Education",
    }

    # Check for (Hons) pattern and handle it specially
    has_hons = "(Hons)" in program_name

    # Remove (Hons) temporarily for processing, but preserve exact spacing
    working_name = program_name.replace(" (Hons)", "").replace("(Hons)", "").strip()

    # Try to find and replace degree abbreviations
    for abbrev, full_name in degree_expansions.items():
        # Case 1: Exact match (e.g., "MBA" -> "Master of Business Administration")
        if working_name.strip() == abbrev:
            result = full_name
            if has_hons:
                result = result + " (Hons)"
            return result

        # Case 2: Match at the start followed by a space (e.g., "BA in...")
        elif working_name.startswith(abbrev + " "):
            # Replace the abbreviation with the full name
            expanded = working_name.replace(abbrev + " ", full_name + " ", 1)
            # Add back (Hons) if it was present, placing it after the degree name
            if has_hons:
                # Insert (Hons) after the degree name but before "in"
                if " in " in expanded:
                    parts = expanded.split(" in ", 1)
                    expanded = parts[0] + " (Hons) in " + parts[1]
                else:
                    expanded = expanded + " (Hons)"
            return expanded

    # If no abbreviation found, return original name
    return program_name


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
    """Generate a QR code for the certificate verification URL with a centered logo.

    Args:
        reference: The certificate reference number

    Returns:
        ImageReader object that can be used in reportlab
    """
    verification_url = f"http://portal.co.ls/verify/certificate/{reference}"

    # Create QR code instance with higher error correction to accommodate logo
    qr = qrcode.QRCode(
        version=1,  # Controls the size of the QR Code
        error_correction=qrcode.ERROR_CORRECT_H,  # High error correction (~30%) to accommodate center logo
        box_size=10,  # Controls how many pixels each "box" of the QR code is
        border=4,  # Controls how many boxes thick the border should be
    )

    qr.add_data(verification_url)
    qr.make(fit=True)

    # Create QR code image and get the underlying PIL Image
    qr_code_img = qr.make_image(fill_color="black", back_color="white")
    qr_img = qr_code_img.get_image().convert("RGBA")

    # Load the center logo
    logo_path = Path("images/fly400x400.jpeg")
    if logo_path.exists():
        # Open and resize the logo
        logo = Image.open(logo_path).convert("RGBA")

        qr_width, qr_height = qr_img.size
        base_size = int(min(qr_width, qr_height) * 0.15)
        if base_size > 0:
            # Resize logo maintaining aspect ratio
            logo = logo.resize((base_size, base_size), Image.Resampling.LANCZOS)

            # Create a padded background to give the logo breathing room inside the QR modules
            padding = max(4, int(base_size * 0.2))
            padded_size = base_size + (padding * 2)
            logo_background = Image.new(
                "RGBA",
                (padded_size, padded_size),
                (255, 255, 255, 255),
            )
            logo_background.paste(logo, (padding, padding), logo)

            # Calculate position to center the padded logo
            logo_x = (qr_width - padded_size) // 2
            logo_y = (qr_height - padded_size) // 2

            # Paste the padded logo onto the QR code
            qr_img.paste(logo_background, (logo_x, logo_y), logo_background)

    # Convert back to RGB for saving as PNG
    qr_img = qr_img.convert("RGB")

    # Convert PIL image to ImageReader for reportlab
    img_buffer = io.BytesIO()
    qr_img.save(img_buffer, "PNG")
    img_buffer.seek(0)

    return ImageReader(img_buffer)


def _build_overlay(
    name: str,
    program_name: str,
    reference: str,
    issue_date: str,
    tmp_path: Path,
    *,
    page_width: float,
    page_height: float,
) -> None:
    c = canvas.Canvas(str(tmp_path), pagesize=(page_width, page_height))
    c.setFillColor(PRIMARY_COLOR)

    perfect_center_x = page_width / 2

    def draw_text(
        text: str,
        font_name: str,
        y_axis: float,
        font_size: float,
        letter_spacing_reduction: float = 0.0,
        max_width: Optional[float] = None,
        line_spacing: float = 1.2,
    ) -> None:
        c.setFont(font_name, font_size)

        effective_max_width = (
            max_width
            if max_width is not None
            else page_width - (2 * TEXT_HORIZONTAL_MARGIN)
        )

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
        if get_text_width(text) <= effective_max_width:
            draw_line(text, y_axis)
            return

        # Split text into multiple lines
        words = text.split()
        lines = []
        current_line = ""

        for word in words:
            test_line = current_line + (" " if current_line else "") + word

            if get_text_width(test_line) <= effective_max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                    current_line = word
                else:
                    # Single word is too long, break it by characters
                    if get_text_width(word) > effective_max_width:
                        char_line = ""
                        for char in word:
                            test_char_line = char_line + char
                            if get_text_width(test_char_line) <= effective_max_width:
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
    c.drawString(page_width - REFERENCE_RIGHT_MARGIN - text_width, 772, reference)

    draw_text(
        name,
        palatino,
        695,
        32,
        1,
    )

    draw_text(program_name, snell_roundhand, 603, 40, 1.6, 550)

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

    # Expand abbreviated program name to full form
    expanded_program_name = expand_program_name(program_name)

    issue_date = "02 October 2025"

    # Prepare output filename
    safe_name = "_".join(name.split())
    output_file = (
        OUTPUT_DIR
        / f"certificate_{safe_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    )

    try:
        base_reader = PdfReader(str(TEMPLATE_PATH))
    except Exception:
        return None

    if not base_reader.pages:
        return None

    media_box = base_reader.pages[0].mediabox
    page_width = float(media_box[2]) - float(media_box[0])
    page_height = float(media_box[3]) - float(media_box[1])

    if not page_width or not page_height:
        page_width, page_height = DEFAULT_PAGE_WIDTH, DEFAULT_PAGE_HEIGHT

    # Create overlay
    overlay_path = OUTPUT_DIR / "_overlay_temp.pdf"
    # Generate reference using program code and student number
    reference = f"LSO{program_code}{std_no}"
    _build_overlay(
        name,
        expanded_program_name,
        reference,
        issue_date,
        overlay_path,
        page_width=page_width,
        page_height=page_height,
    )

    try:
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
