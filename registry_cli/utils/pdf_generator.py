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

            # Create document
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30,
            )

            # Build the document elements
            elements = []

            # Add header
            elements.extend(RegistrationPDFGenerator._build_header(styles))

            # Add registration header
            elements.extend(RegistrationPDFGenerator._build_registration_header(styles))

            # Add student information
            elements.append(
                RegistrationPDFGenerator._build_student_info(
                    student, program, term, request.semester_number, styles
                )
            )
            elements.append(Spacer(1, 0.2 * inch))  # Reduced spacing

            # Add modules table
            elements.extend(
                RegistrationPDFGenerator._build_modules_table(module_details, styles)
            )
            elements.append(Spacer(1, 0.2 * inch))  # Reduced spacing
            elements.append(Spacer(1, 0.3 * inch))  # Reduced spacing

            # Add footer
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
        """Create and return all document styles

        Returns:
            Dict of style names to ParagraphStyle objects
        """
        base_styles = getSampleStyleSheet()

        styles = {
            "title": ParagraphStyle(
                "Title",
                fontSize=16,
                alignment=0,
                spaceAfter=6,
                fontName="Helvetica-Bold",
                textColor=colors.black,
            ),
            "normal": base_styles["Normal"],
            "small": ParagraphStyle("Small", fontSize=8, fontName="Helvetica"),
            "header_text": ParagraphStyle(
                "HeaderText", fontSize=10, fontName="Helvetica"
            ),
            "contact_info": ParagraphStyle(
                "ContactInfo", fontSize=6, fontName="Helvetica"
            ),
            "section_header": ParagraphStyle(
                "SectionHeader",
                fontSize=12,
                fontName="Helvetica-Bold",
                spaceAfter=6,
                textColor=colors.black,
            ),
        }

        return styles

    @staticmethod
    def _build_header(styles: Dict[str, ParagraphStyle]) -> List[Any]:
        """Build the document header

        Args:
            styles: Dictionary of paragraph styles

        Returns:
            List of flowable elements for the header
        """
        elements = []
        logo_path = "resource/logo.jpg"
        has_logo = os.path.exists(logo_path)

        # Title
        title = Paragraph(
            "Limkokwing University of Creative Technology", styles["title"]
        )
        elements.append(title)
        elements.append(Spacer(1, 0.1 * inch))

        # Contact info and logo
        if has_logo:
            # Create contact info paragraph
            contact_info = Paragraph(
                """Moshoeshoe Road Maseru Central<br/>
                P.O. Box 8971<br/>
                Maseru Maseru 0101<br/>
                Lesotho<br/>
                +(266) 22315767<br/>
                registry@limkokwing.ac.ls""",
                styles["contact_info"],
            )

            logo = Image(logo_path, width=1.8 * inch, height=1 * inch)

            header_table = Table(
                [[contact_info, logo]], colWidths=[5.5 * inch, 1.5 * inch]
            )

            # Set styling to ensure proper positioning
            header_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (0, 0), "TOP"),  # Top-align contact info
                        ("VALIGN", (1, 0), (1, 0), "TOP"),  # Top-align logo
                        (
                            "ALIGN",
                            (1, 0),
                            (1, 0),
                            "RIGHT",
                        ),  # Right-align logo in its cell
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (0, 0),
                            0,
                        ),  # No left padding for contact info
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (0, 0),
                            0,
                        ),  # No right padding for contact info
                        ("LEFTPADDING", (1, 0), (1, 0), 0),  # No left padding for logo
                        (
                            "RIGHTPADDING",
                            (1, 0),
                            (1, 0),
                            0,
                        ),  # No right padding for logo
                    ]
                )
            )

            elements.append(header_table)
        else:
            # Fallback without logo
            contact_info = Paragraph(
                """Moshoeshoe Road Maseru Central<br/>
                P.O. Box 8971<br/>
                Maseru Maseru 0101<br/>
                Lesotho<br/>
                +(266) 22315767<br/>
                https://www.limkokwing.net/m/contact/limkokwing_lesotho""",
                styles["contact_info"],
            )
            elements.append(contact_info)

        elements.append(
            HRFlowable(
                width="100%",
                thickness=1,
                color=colors.black,
                spaceBefore=6,
                spaceAfter=12,
            )
        )

        return elements

    @staticmethod
    def _build_registration_header(styles: Dict[str, ParagraphStyle]) -> List[Any]:
        """Build the registration proof header

        Args:
            styles: Dictionary of paragraph styles

        Returns:
            List of flowable elements for the registration header
        """
        elements = []

        reg_header_data = [
            [
                Paragraph("PROOF OF REGISTRATION", styles["title"]),
                Paragraph(
                    f"Date: {datetime.now().strftime('%d %b %Y')}",
                    styles["header_text"],
                ),
            ],
        ]
        reg_header_table = Table(reg_header_data, colWidths=[4 * inch, 2.5 * inch])
        reg_header_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, 0), "LEFT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        elements.append(reg_header_table)
        elements.append(Spacer(1, 0.2 * inch))

        return elements

    @staticmethod
    def _build_student_info(
        student: Student,
        program: Program,
        term: Term,
        semester_number: int,
        styles: Dict[str, ParagraphStyle],
    ) -> Table:
        """Build the student information table

        Args:
            student: Student object
            program: Program object
            term: Term object
            semester_number: Semester number
            styles: Dictionary of paragraph styles

        Returns:
            Table object with student information
        """
        student_info = [
            ["Student Number:", str(student.std_no)],
            ["Student Name:", student.name],
            ["Program:", program.name],
            ["Term:", term.name if term else "N/A"],
            ["Semester:", f"Semester {semester_number}"],
        ]

        student_info_table = Table(student_info, colWidths=[1.5 * inch, 5 * inch])
        student_info_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),  # Reduced padding
                    ("TOPPADDING", (0, 0), (-1, -1), 3),  # Reduced padding
                ]
            )
        )

        return student_info_table

    @staticmethod
    def _build_modules_table(
        modules: List[Module], styles: Dict[str, ParagraphStyle]
    ) -> List[Any]:
        """Build the registered modules table

        Args:
            modules: List of Module objects
            styles: Dictionary of paragraph styles

        Returns:
            List containing module table and total credits table
        """
        elements = []

        elements.append(Paragraph("REGISTERED MODULES", styles["section_header"]))

        module_data = [["#", "Module Code & Description", "Type", "Credits"]]

        for idx, module in enumerate(modules, 1):
            module_data.append(
                [
                    idx,
                    f"{module.code}\n{module.name}",
                    module.type,
                    str(module.credits),
                ]
            )

        # Calculate total credits
        total_credits = sum(module.credits for module in modules)

        modules_table = Table(
            module_data,
            colWidths=[0.3 * inch, 4.7 * inch, 1 * inch, 0.7 * inch],
            repeatRows=1,
        )

        modules_table.setStyle(
            TableStyle(
                [
                    # Header row styling
                    ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    # Cell alignment
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (2, 0), (3, -1), "CENTER"),
                    # General styling
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                    ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                    # Cell padding
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )

        elements.append(modules_table)

        return elements

    @staticmethod
    def _build_footer(doc_id: str, styles: Dict[str, ParagraphStyle]) -> List[Any]:
        """Build the document footer

        Args:
            doc_id: Document ID
            styles: Dictionary of paragraph styles

        Returns:
            List of flowable elements for the footer
        """
        elements = []

        elements.append(
            HRFlowable(
                width="100%",
                thickness=0.5,
                color=colors.lightgrey,
                spaceBefore=6,
                spaceAfter=6,
            )
        )

        footer_text = (
            f"Document ID: {doc_id} | "
            f"This document serves as official proof of registration for the above student. "
            f"Registration processed through the official university system on {datetime.now().strftime('%d %B %Y')}."
        )
        elements.append(Paragraph(footer_text, styles["small"]))

        return elements
