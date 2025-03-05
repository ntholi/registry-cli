import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from registry_cli.models import (
    Module,
    Program,
    RegistrationRequest,
    RequestedModule,
    Structure,
    Student,
    StudentProgram,
    Term,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

OUTPUT_DIR = Path("registration_pdfs")
OUTPUT_DIR.mkdir(exist_ok=True)


class RegistrationPDFGenerator:
    """Class for generating registration confirmation PDFs"""

    # Define university brand colors
    BRAND_PRIMARY = colors.HexColor("#212121")
    BRAND_SECONDARY = colors.HexColor("#333333")
    BRAND_GRAY = colors.HexColor("#333333")

    @staticmethod
    def generate_registration_pdf(
        db: Session,
        request: RegistrationRequest,
        student: Student,
        registered_modules: List[str],
    ) -> Optional[str]:
        """Generate a PDF proof of registration

        Args:
            db: Database session
            request: The registration request
            student: The student
            registered_modules: List of registered module codes

        Returns:
            str: Path to the generated PDF file, or None if generation failed
        """
        try:
            # Fetch required data
            term = db.query(Term).filter(Term.id == request.term_id).first()

            program_info = (
                db.query(StudentProgram, Structure, Program)
                .join(Structure, StudentProgram.structure_id == Structure.id)
                .join(Program, Structure.program_id == Program.id)
                .filter(
                    StudentProgram.std_no == student.std_no,
                    StudentProgram.status == "Active",
                )
                .first()
            )

            if not program_info:
                logger.error(f"No active program found for student {student.std_no}")
                return None

            student_program, structure, program = program_info

            module_details = (
                db.query(Module)
                .join(RequestedModule)
                .filter(
                    RequestedModule.registration_request_id == request.id,
                    Module.code.in_(registered_modules),
                )
                .all()
            )

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"registration_{student.std_no}_{timestamp}.pdf"
            pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

            # Create document styles
            styles = RegistrationPDFGenerator._create_styles()

            # Create document with enhanced margins
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=0.75 * inch,
                leftMargin=0.75 * inch,
                topMargin=0.5 * inch,
                bottomMargin=0.5 * inch,
                title=f"Registration Confirmation - {student.name}",
                author="Limkokwing University",
            )

            # Build the document elements
            elements = []

            # Add header
            elements.extend(RegistrationPDFGenerator._build_header(styles))

            # Add registration header with enhanced styling
            elements.extend(RegistrationPDFGenerator._build_registration_header(styles))

            # Add student information
            elements.append(
                RegistrationPDFGenerator._build_student_info(
                    student, program, term, request.semester_number, styles
                )
            )
            elements.append(Spacer(1, 0.3 * inch))

            # Add modules table with enhanced styling
            elements.extend(
                RegistrationPDFGenerator._build_modules_table(module_details, styles)
            )
            elements.append(Spacer(1, 0.5 * inch))

            # Add footer with enhanced styling
            elements.extend(
                RegistrationPDFGenerator._build_footer(
                    pdf_filename.split(".")[0], styles
                )
            )

            # Generate PDF
            doc.build(elements)

            logger.info(f"Generated registration PDF: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(f"Failed to generate registration PDF: {str(e)}")
            return None

    @staticmethod
    def _create_styles() -> Dict[str, ParagraphStyle]:
        """Create and return all document styles with enhanced typography

        Returns:
            Dict of style names to ParagraphStyle objects
        """
        base_styles = getSampleStyleSheet()

        styles = {
            "title": ParagraphStyle(
                "Title",
                fontSize=15,
                alignment=0,
                spaceAfter=8,
                fontName="Helvetica-Bold",
                textColor=RegistrationPDFGenerator.BRAND_PRIMARY,
                leading=17,
            ),
            "subtitle": ParagraphStyle(
                "Subtitle",
                fontSize=11,
                alignment=0,
                spaceAfter=6,
                fontName="Helvetica-Bold",
                textColor=RegistrationPDFGenerator.BRAND_GRAY,
                leading=13,
            ),
            "normal": ParagraphStyle(
                "Normal",
                fontSize=9,
                fontName="Helvetica",
                leading=11,
            ),
            "small": ParagraphStyle(
                "Small",
                fontSize=7,
                fontName="Helvetica",
                leading=9,
                textColor=RegistrationPDFGenerator.BRAND_GRAY,
            ),
            "header_text": ParagraphStyle(
                "HeaderText",
                fontSize=9,
                fontName="Helvetica",
                textColor=RegistrationPDFGenerator.BRAND_GRAY,
            ),
            "contact_info": ParagraphStyle(
                "ContactInfo",
                fontSize=7,
                fontName="Helvetica",
                leading=9,
                textColor=RegistrationPDFGenerator.BRAND_GRAY,
            ),
            "section_header": ParagraphStyle(
                "SectionHeader",
                fontSize=11,
                fontName="Helvetica-Bold",
                spaceAfter=8,
                textColor=RegistrationPDFGenerator.BRAND_PRIMARY,
                leading=13,
            ),
            "data_label": ParagraphStyle(
                "DataLabel",
                fontSize=9,
                fontName="Helvetica-Bold",
                textColor=RegistrationPDFGenerator.BRAND_GRAY,
            ),
            "data_value": ParagraphStyle(
                "DataValue",
                fontSize=9,
                fontName="Helvetica",
            ),
        }

        return styles

    @staticmethod
    def _build_header(styles: Dict[str, ParagraphStyle]) -> List[Any]:
        """Build the document header with enhanced styling

        Args:
            styles: Dictionary of paragraph styles

        Returns:
            List of flowable elements for the header
        """
        elements = []
        logo_path = "resource/logo.jpg"

        # University name with brand color
        title = Paragraph(
            "Limkokwing University of Creative Technology", styles["title"]
        )
        elements.append(title)
        elements.append(Spacer(1, 0.1 * inch))

        # Create contact info paragraph with enhanced formatting and increased left padding
        contact_info_style = ParagraphStyle(
            "ContactInfoIndented",
            parent=styles["contact_info"],
            leftIndent=0.2 * inch,
        )

        contact_info = Paragraph(
            """Moshoeshoe Road Maseru Central<br/>
            P.O. Box 8971<br/>
            Maseru Maseru 0101<br/>
            Lesotho<br/>
            +(266) 22315767 | Ext. 116<br/>
            registry@limkokwing.ac.ls""",
            contact_info_style,
        )

        # Logo with maintained aspect ratio
        logo = Image(logo_path, width=1.8 * inch, height=1 * inch)

        # Create header table with better spacing
        header_table = Table([[contact_info, logo]], colWidths=[5 * inch, 2 * inch])

        # Set styling for better alignment
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (0, 0), "TOP"),
                    ("VALIGN", (1, 0), (1, 0), "TOP"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0),
                    ("RIGHTPADDING", (0, 0), (0, 0), 0),
                    ("LEFTPADDING", (1, 0), (1, 0), 0),
                    ("RIGHTPADDING", (1, 0), (1, 0), 0),
                ]
            )
        )

        elements.append(header_table)

        # Add decorative separator with brand color
        elements.append(
            HRFlowable(
                width="100%",
                thickness=2,
                color=RegistrationPDFGenerator.BRAND_PRIMARY,
                spaceBefore=8,
                spaceAfter=16,
            )
        )

        return elements

    @staticmethod
    def _build_registration_header(styles: Dict[str, ParagraphStyle]) -> List[Any]:
        """Build the registration proof header with enhanced styling

        Args:
            styles: Dictionary of paragraph styles

        Returns:
            List of flowable elements for the registration header
        """
        elements = []

        # Create registration header - removed date row
        elements.append(
            Paragraph("<b>PROOF OF REGISTRATION</b>", styles["section_header"])
        )
        elements.append(Spacer(1, 0.3 * inch))

        return elements

    @staticmethod
    def _build_student_info(
        student: Student,
        program: Program,
        term: Term,
        semester_number: int,
        styles: Dict[str, ParagraphStyle],
    ) -> Table:
        """Build the student information table with enhanced styling

        Args:
            student: Student object
            program: Program object
            term: Term object
            semester_number: Semester number
            styles: Dictionary of paragraph styles

        Returns:
            Table object with student information
        """
        # Calculate year and semester based on semester_number
        year = ((semester_number - 1) // 2) + 1
        semester = ((semester_number - 1) % 2) + 1
        semester_display = f"Year {year} Semester {semester}"

        # Create formatted student info with styling
        student_info = [
            [
                Paragraph("Student Number:", styles["data_label"]),
                Paragraph(str(student.std_no), styles["data_value"]),
            ],
            [
                Paragraph("Student Name:", styles["data_label"]),
                Paragraph(student.name, styles["data_value"]),
            ],
            [
                Paragraph("Program:", styles["data_label"]),
                Paragraph(program.name, styles["data_value"]),
            ],
            [
                Paragraph("Term:", styles["data_label"]),
                Paragraph(term.name if term else "N/A", styles["data_value"]),
            ],
            [
                Paragraph("Semester:", styles["data_label"]),
                Paragraph(semester_display, styles["data_value"]),
            ],
        ]

        # Create student info table with better styling, removed background color
        student_info_table = Table(
            student_info,
            colWidths=[1.5 * inch, 5 * inch],
            style=TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (0, 0), (0, -1), 10),
                    ("LEFTPADDING", (1, 0), (1, -1), 10),
                    # Removed background color
                    # Added more defined borders for structure without background
                    ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.lightgrey),
                    (
                        "LINEBELOW",
                        (0, -1),
                        (-1, -1),
                        1,
                        RegistrationPDFGenerator.BRAND_PRIMARY,
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ]
            ),
        )

        return student_info_table

    @staticmethod
    def _build_modules_table(
        modules: List[Module], styles: Dict[str, ParagraphStyle]
    ) -> List[Any]:
        """Build the registered modules table with enhanced styling

        Args:
            modules: List of Module objects
            styles: Dictionary of paragraph styles

        Returns:
            List containing module table and total credits table
        """
        elements = []

        # Add section header with enhanced styling
        elements.append(Paragraph("REGISTERED MODULES", styles["section_header"]))
        elements.append(Spacer(1, 0.1 * inch))

        # Create module data table with styled headers
        module_data = [["#", "Module Code & Description", "Type", "Credits"]]

        # Add modules with improved formatting
        for idx, module in enumerate(modules, 1):
            module_data.append(
                [
                    idx,
                    f"<b>{module.code}</b><br/>{module.name}",
                    module.type,
                    str(module.credits),
                ]
            )

        # Calculate total credits
        total_credits = sum(module.credits for module in modules)

        # Convert module data to paragraphs for better styling
        formatted_module_data = []
        # Create a specific style for table headers with white text
        header_style = ParagraphStyle(
            "HeaderStyle",
            parent=styles["data_label"],
            textColor=colors.white,
        )

        formatted_module_data.append(
            [
                Paragraph("#", header_style),
                Paragraph("Module Code & Description", header_style),
                Paragraph("Type", header_style),
                Paragraph("Credits", header_style),
            ]
        )

        for row in module_data[1:]:
            formatted_module_data.append(
                [
                    Paragraph(str(row[0]), styles["normal"]),
                    Paragraph(row[1], styles["normal"]),
                    Paragraph(row[2], styles["normal"]),
                    Paragraph(str(row[3]), styles["normal"]),
                ]
            )

        # Create enhanced modules table - keeping header row background for readability
        modules_table = Table(
            formatted_module_data,
            colWidths=[0.4 * inch, 4.6 * inch, 1 * inch, 0.7 * inch],
            repeatRows=1,
            style=TableStyle(
                [
                    # Header row styling with brand colors
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        RegistrationPDFGenerator.BRAND_PRIMARY,
                    ),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    # Cell alignment
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 0), (3, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    # Border styling
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                    # Removed alternating row colors for cleaner appearance
                    # Padding
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ]
            ),
        )

        elements.append(modules_table)

        # Add total credits row without background color
        total_data = [
            [
                "",
                "",
                Paragraph("<b>Credits:</b>", styles["data_label"]),
                Paragraph(f"<b>{total_credits}</b>", styles["data_value"]),
            ]
        ]

        total_table = Table(
            total_data,
            colWidths=[0.4 * inch, 4.6 * inch, 1 * inch, 0.7 * inch],
            style=TableStyle(
                [
                    ("ALIGN", (2, 0), (2, 0), "CENTER"),
                    ("ALIGN", (3, 0), (3, 0), "CENTER"),
                    # Removed background color
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("LEFTPADDING", (2, 0), (3, 0), 8),
                    ("RIGHTPADDING", (2, 0), (3, 0), 8),
                    # Add border for definition
                    (
                        "LINEABOVE",
                        (2, 0),
                        (3, 0),
                        1,
                        RegistrationPDFGenerator.BRAND_PRIMARY,
                    ),
                ]
            ),
        )

        elements.append(total_table)

        return elements

    @staticmethod
    def _build_footer(doc_id: str, styles: Dict[str, ParagraphStyle]) -> List[Any]:
        """Build the document footer with enhanced styling

        Args:
            doc_id: Document ID
            styles: Dictionary of paragraph styles

        Returns:
            List of flowable elements for the footer
        """
        elements = []

        # Add decorative separator before footer
        elements.append(
            HRFlowable(
                width="100%",
                thickness=1,
                color=RegistrationPDFGenerator.BRAND_PRIMARY,
                spaceBefore=8,
                spaceAfter=8,
            )
        )

        # Create styled footer text
        footer_text = (
            f"<b>Document ID:</b> {doc_id} | "
            f"This document serves as official proof of registration for the above student. "
            f"Registration processed through the official university system on <b>{datetime.now().strftime('%d %B %Y')}</b>."
        )

        # Create footer with single column, explicitly aligned left
        footer_table = Table(
            [
                [
                    Paragraph(footer_text, styles["small"]),
                ]
            ],
            colWidths=[7 * inch],  # Use full width for a single column
            style=TableStyle(
                [
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),  # Force left alignment
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (0, 0), 0.2 * inch),
                    ("RIGHTPADDING", (0, 0), (0, 0), 0),
                ]
            ),
        )

        elements.append(footer_table)

        return elements
