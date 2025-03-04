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

            # Document with smaller margins for more space
            doc = SimpleDocTemplate(
                pdf_path,
                pagesize=A4,
                rightMargin=30,
                leftMargin=30,
                topMargin=30,
                bottomMargin=30,
            )

            styles = getSampleStyleSheet()
            title_style = ParagraphStyle(
                "Title",
                fontSize=16,
                alignment=0,
                spaceAfter=6,
                fontName="Helvetica-Bold",
                textColor=colors.black,
            )
            normal_style = styles["Normal"]
            small_style = ParagraphStyle("Small", fontSize=8, fontName="Helvetica")
            header_text_style = ParagraphStyle(
                "HeaderText", fontSize=10, fontName="Helvetica"
            )
            section_header_style = ParagraphStyle(
                "SectionHeader",
                fontSize=12,
                fontName="Helvetica-Bold",
                spaceAfter=6,
                textColor=colors.black,
            )

            elements = []

            # Create header table with university info and logo
            logo_path = "path/to/logo.png"
            has_logo = os.path.exists(logo_path)

            if has_logo:
                header_data = [
                    [
                        Paragraph(
                            "Limkokwing University of Creative Technology",
                            title_style,
                        ),
                        Image(logo_path, width=1.5 * inch, height=1.5 * inch),
                    ],
                    [
                        Paragraph(
                            """
                            Moshoeshoe Road Maseru Central<br/>
                            P.O. Box 8971<br/>
                            Maseru Maseru 0101<br/>
                            Lesotho<br/>
                            +(266) 22315767<br/>
                            https://www.limkokwing.net/m/contact/limkokwing_lesotho""",
                            header_text_style,
                        ),
                        Paragraph("LESOTHO", header_text_style),
                    ],
                ]
                header_table = Table(header_data, colWidths=[4.5 * inch, 2 * inch])
                header_table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                            ("ALIGN", (1, 0), (1, 1), "CENTER"),
                        ]
                    )
                )
            else:
                # Fallback if logo is unavailable
                header_data = [
                    [
                        Paragraph(
                            "Limkokwing University of Creative Technology",
                            title_style,
                        ),
                    ],
                    [
                        Paragraph(
                            """Tax ID : 200051832-0<br/>
                            Moshoeshoe Road Maseru Central<br/>
                            P.O. Box 8971<br/>
                            Maseru Maseru 0101<br/>
                            Lesotho<br/>
                            +(266) 22315767<br/>
                            https://www.limkokwing.net/m/contact/limkokwing_lesotho""",
                            header_text_style,
                        ),
                    ],
                ]
                header_table = Table(header_data)
                header_table.setStyle(
                    TableStyle(
                        [
                            ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ]
                    )
                )

            elements.append(header_table)
            elements.append(
                HRFlowable(
                    width="100%",
                    thickness=1,
                    color=colors.black,
                    spaceBefore=6,
                    spaceAfter=12,
                )
            )

            # Registration header - cleaner, with date aligned right
            reg_header_data = [
                [
                    Paragraph("PROOF OF REGISTRATION", title_style),
                    Paragraph(
                        f"Date: {datetime.now().strftime('%d %b %Y')}",
                        header_text_style,
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

            # Student information - cleaner, without the removed fields
            student_info = [
                ["Student Number:", str(student.std_no)],
                ["Student Name:", student.name],
                ["Program:", program.name],
                ["Term:", term.name if term else "N/A"],
                ["Semester:", f"Semester {request.semester_number}"],
            ]
            student_info_table = Table(student_info, colWidths=[1.5 * inch, 5 * inch])
            student_info_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(student_info_table)
            elements.append(Spacer(1, 0.3 * inch))

            # Registered modules with improved styling
            elements.append(Paragraph("REGISTERED MODULES", section_header_style))

            # Add a light gray background to alternate rows for better readability
            module_data = [["#", "Module Code & Description", "Type", "Credits"]]

            for idx, module in enumerate(module_details, 1):
                module_data.append(
                    [
                        idx,
                        f"{module.code}\n{module.name}",
                        module.type,
                        str(module.credits),
                    ]
                )

            # Calculate total credits
            total_credits = sum(module.credits for module in module_details)

            modules_table = Table(
                module_data,
                colWidths=[0.3 * inch, 4.7 * inch, 1 * inch, 0.7 * inch],
                repeatRows=1,
            )

            row_colors = [colors.lightgrey, colors.white]
            for i in range(1, len(module_data)):
                bg_color = row_colors[i % 2]
                modules_table.setStyle(
                    TableStyle([("BACKGROUND", (0, i), (-1, i), bg_color)])
                )

            modules_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.gray),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("ALIGN", (0, 0), (0, -1), "CENTER"),
                        ("ALIGN", (2, 0), (3, -1), "CENTER"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
                        ("LINEBELOW", (0, 0), (-1, 0), 1, colors.black),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )

            elements.append(modules_table)

            # Total credits with stronger visual emphasis
            total_data = [
                ["", "", "Total Credits:", str(total_credits)],
            ]
            total_table = Table(
                total_data, colWidths=[0.3 * inch, 4.7 * inch, 1 * inch, 0.7 * inch]
            )
            total_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
                        ("ALIGN", (3, 0), (3, -1), "CENTER"),
                        ("FONTNAME", (2, 0), (3, -1), "Helvetica-Bold"),
                        ("LINEABOVE", (2, 0), (3, 0), 1, colors.black),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(total_table)
            elements.append(Spacer(1, 0.3 * inch))

            # Registration status - simplified and focused on key information
            status_data = [
                ["Registration Status:", request.status.upper()],
                ["Processed On:", datetime.now().strftime("%d %B %Y")],
            ]
            status_table = Table(status_data, colWidths=[1.5 * inch, 5 * inch])
            status_table.setStyle(
                TableStyle(
                    [
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ]
                )
            )
            elements.append(status_table)
            elements.append(Spacer(1, 0.5 * inch))

            # Signature line with better spacing and formatting
            signature_data = [
                ["_______________________________", "_______________________________"],
                ["Registry Department", "Student Signature"],
            ]
            signature_table = Table(signature_data, colWidths=[3 * inch, 3 * inch])
            signature_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (1, 1), "CENTER"),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                        ("FONTNAME", (0, 1), (1, 1), "Helvetica"),
                        ("FONTSIZE", (0, 1), (1, 1), 9),
                        ("TOPPADDING", (0, 1), (1, 1), 2),
                    ]
                )
            )
            elements.append(signature_table)

            # Footer with document ID and verification text
            elements.append(Spacer(1, 0.5 * inch))
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
                f"Document ID: {pdf_filename.split('.')[0]} | "
                f"This document serves as official proof of registration for the above student. "
                f"Registration processed through the official university system on {datetime.now().strftime('%d %B %Y')}."
            )
            elements.append(Paragraph(footer_text, small_style))

            doc.build(elements)

            logger.info(f"Generated registration PDF: {pdf_path}")
            return pdf_path

        except Exception as e:
            logger.error(f"Failed to generate registration PDF: {str(e)}")
            return None
