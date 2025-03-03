import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, inch
from reportlab.platypus import (
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

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pdf_filename = f"registration_{student.std_no}_{timestamp}.pdf"
            pdf_path = os.path.join(OUTPUT_DIR, pdf_filename)

            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
            )

            styles = getSampleStyleSheet()
            title_style = styles["Heading1"]
            subtitle_style = styles["Heading2"]
            normal_style = styles["Normal"]

            header_style = ParagraphStyle(
                "Header",
                parent=styles["Heading1"],
                fontSize=16,
                alignment=1,  # Center alignment
                spaceAfter=12,
            )

            elements = []

            # Add university logo if available
            # logo_path = "path/to/logo.png"  # Update with the actual logo path
            # if os.path.exists(logo_path):
            #     logo = Image(logo_path, width=2*inch, height=1*inch)
            #     elements.append(logo)

            # Add header
            elements.append(
                Paragraph("LIMKOKWING UNIVERSITY OF CREATIVE TECHNOLOGY", header_style)
            )
            elements.append(Paragraph("PROOF OF REGISTRATION", header_style))
            elements.append(Spacer(1, 0.5 * inch))

            data = [
                ["STUDENT INFORMATION", ""],
                ["Student Number:", str(student.std_no)],
                ["Student Name:", student.name],
                ["National ID:", student.national_id],
                ["Program:", program.name],
                ["Structure Code:", structure.code],
                ["Term:", term.name if term else "N/A"],
                ["Semester:", f"Semester {request.semester_number}"],
                ["Registration Status:", request.status.upper()],
            ]

            student_table = Table(data, colWidths=[2.5 * inch, 3 * inch])
            student_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (1, 0), colors.lightgrey),
                        ("TEXTCOLOR", (0, 0), (1, 0), colors.black),
                        ("ALIGN", (0, 0), (1, 0), "CENTER"),
                        ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (1, 0), 12),
                        ("BOTTOMPADDING", (0, 0), (1, 0), 12),
                        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )

            elements.append(student_table)
            elements.append(Spacer(1, 0.25 * inch))

            elements.append(Paragraph("REGISTERED MODULES", subtitle_style))
            elements.append(Spacer(1, 0.1 * inch))

            module_data = [["Module Code", "Module Name", "Type", "Credits"]]

            for module in module_details:
                module_data.append(
                    [module.code, module.name, module.type, str(module.credits)]
                )

            total_credits = sum(module.credits for module in module_details)
            module_data.append(["", "", "Total Credits:", str(total_credits)])

            modules_table = Table(
                module_data, colWidths=[1 * inch, 3 * inch, 1 * inch, 1 * inch]
            )
            modules_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                        ("GRID", (0, 0), (-1, -2), 1, colors.black),
                        ("ALIGN", (0, -1), (1, -1), "RIGHT"),
                        ("FONTNAME", (2, -1), (3, -1), "Helvetica-Bold"),
                        ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )

            elements.append(modules_table)
            elements.append(Spacer(1, 0.25 * inch))

            verification_text = (
                "This document serves as official proof of registration for the above student. "
                "This registration was processed through the official university registration system "
                f"on {datetime.now().strftime('%d %B %Y at %H:%M')}."
            )
            elements.append(Paragraph(verification_text, normal_style))

            elements.append(Spacer(1, 0.5 * inch))
            elements.append(Paragraph("_______________________________", normal_style))
            elements.append(Paragraph("Registry Department", normal_style))

            elements.append(Spacer(1, 0.25 * inch))
            elements.append(
                Paragraph(
                    "Document ID: " + pdf_filename.split(".")[0],
                    ParagraphStyle("Small", parent=normal_style, fontSize=8),
                )
            )

            doc.build(elements)

            logger.info(f"Generated registration PDF: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(f"Failed to generate registration PDF: {str(e)}")
            return None
