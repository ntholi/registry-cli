import os
from datetime import datetime
from typing import Dict, List, Optional

import click
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from registry_cli.commands.approve.academic_graduation import (
    get_outstanding_from_structure,
    get_student_programs,
)
from registry_cli.models import (
    Clearance,
    GraduationClearance,
    GraduationRequest,
    Program,
    StatementOfResultsPrint,
    Structure,
    Student,
    StudentProgram,
    StudentSemester,
)


def has_no_pending_issues(db: Session, std_no: int) -> bool:
    """
    Check if a student has no pending academic issues using the same logic as approve_academic_graduation.

    Returns True if the student has no failed never repeated modules and no never attempted modules.
    """
    try:
        programs = get_student_programs(db, std_no)
        if not programs:
            return False

        outstanding = get_outstanding_from_structure(db, programs)

        # No pending issues if both lists are empty
        return (
            len(outstanding["failedNeverRepeated"]) == 0
            and len(outstanding["neverAttempted"]) == 0
        )
    except Exception as e:
        click.echo(f"Error checking pending issues for student {std_no}: {str(e)}")
        return False


def get_student_classification(db: Session, std_no: int) -> Optional[str]:
    """
    Get the student's classification from the most recent statement of results print.
    """
    statement = (
        db.query(StatementOfResultsPrint)
        .filter(StatementOfResultsPrint.std_no == std_no)
        .order_by(StatementOfResultsPrint.printed_at.desc())
        .first()
    )

    if statement:
        return statement.classification
    return None


def export_graduating_students(db: Session) -> None:
    """
    Export graduating students to Excel file.

    Graduating students are those who either:
    1. Have approved academic graduation clearances, OR
    2. Have active programs with semesters containing '2024-07' or '2025-02' terms
       AND have no pending academic issues (using approve_academic_graduation logic)
    """
    graduating_students = []

    # Criterion 1: Students with approved academic graduation clearances
    click.echo("Finding students with approved academic graduation clearances...")

    approved_graduation_students = (
        db.query(GraduationRequest.std_no)
        .join(
            GraduationClearance,
            GraduationRequest.id == GraduationClearance.graduation_request_id,
        )
        .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
        .filter(
            and_(Clearance.department == "academic", Clearance.status == "approved")
        )
        .all()
    )

    approved_std_nos = {row.std_no for row in approved_graduation_students}
    click.echo(
        f"Found {len(approved_std_nos)} students with approved academic clearances"
    )

    # Criterion 2: Students with active programs having 2024-07 or 2025-02 semesters and no pending issues
    click.echo(
        "Finding students with 2024-07 or 2025-02 semesters and no pending issues..."
    )

    semester_students = (
        db.query(StudentSemester.id, StudentProgram.std_no)
        .join(StudentProgram, StudentSemester.student_program_id == StudentProgram.id)
        .filter(
            and_(
                StudentProgram.status == "Active",
                or_(
                    StudentSemester.term == "2024-07", StudentSemester.term == "2025-02"
                ),
            )
        )
        .all()
    )

    semester_std_nos = {row.std_no for row in semester_students}
    click.echo(
        f"Found {len(semester_std_nos)} students with 2024-07 or 2025-02 semesters"
    )

    # Filter semester students by pending issues
    qualifying_semester_std_nos = set()
    click.echo("Checking for pending academic issues...")

    for i, std_no in enumerate(semester_std_nos, 1):
        if i % 50 == 0:
            click.echo(f"Checked {i}/{len(semester_std_nos)} students...")

        if has_no_pending_issues(db, std_no):
            qualifying_semester_std_nos.add(std_no)

    click.echo(
        f"Found {len(qualifying_semester_std_nos)} students with no pending issues"
    )

    # Combine both sets of graduating students
    all_graduating_std_nos = approved_std_nos | qualifying_semester_std_nos
    click.echo(f"Total graduating students: {len(all_graduating_std_nos)}")

    if not all_graduating_std_nos:
        click.secho("No graduating students found.", fg="yellow")
        return

    # Get detailed information for all graduating students
    click.echo("Collecting student details...")

    for i, std_no in enumerate(all_graduating_std_nos, 1):
        if i % 50 == 0:
            click.echo(f"Processed {i}/{len(all_graduating_std_nos)} students...")

        try:
            # Get student basic info
            student = db.query(Student).filter(Student.std_no == std_no).first()
            if not student:
                continue

            # Get active program
            active_program = (
                db.query(StudentProgram)
                .join(Structure, StudentProgram.structure_id == Structure.id)
                .join(Program, Structure.program_id == Program.id)
                .filter(
                    and_(
                        StudentProgram.std_no == std_no,
                        StudentProgram.status == "Active",
                    )
                )
                .first()
            )

            if not active_program:
                continue

            program_name = (
                active_program.structure.program.name
                if active_program.structure
                else "Unknown Program"
            )
            classification = get_student_classification(db, std_no)

            # Determine graduation criteria met
            criteria_met = []
            if std_no in approved_std_nos:
                criteria_met.append("Approved Clearance")
            if std_no in qualifying_semester_std_nos:
                criteria_met.append("2025 Semester + No Issues")

            graduating_students.append(
                {
                    "student_number": std_no,
                    "student_name": student.name,
                    "program_name": program_name,
                    "classification": classification or "Not Available",
                    "criteria_met": " & ".join(criteria_met),
                }
            )

        except Exception as e:
            click.echo(f"Error processing student {std_no}: {str(e)}")
            continue

    if not graduating_students:
        click.secho("No valid graduating students found after processing.", fg="yellow")
        return

    # Sort students by student number
    graduating_students.sort(key=lambda x: x["student_number"])

    # Export to Excel
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"graduating_students_{timestamp}.xlsx"
    excel_path = os.path.join(output_dir, excel_filename)

    wb = Workbook()
    ws = wb.active
    ws.title = "Graduating Students"

    # Set up headers
    headers = [
        "Student Number",
        "Student Name",
        "Program Name",
        "Classification",
        "Criteria Met",
    ]
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(
        start_color="366092", end_color="366092", fill_type="solid"
    )

    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill

    # Add data rows
    for row, student in enumerate(graduating_students, 2):
        ws.cell(row=row, column=1, value=student["student_number"])
        ws.cell(row=row, column=2, value=student["student_name"])
        ws.cell(row=row, column=3, value=student["program_name"])
        ws.cell(row=row, column=4, value=student["classification"])
        ws.cell(row=row, column=5, value=student["criteria_met"])

    # Auto-size columns
    for col in range(1, len(headers) + 1):
        column_letter = get_column_letter(col)
        max_length = 0
        for row in ws[column_letter]:
            try:
                if len(str(row.value)) > max_length:
                    max_length = len(str(row.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 50)
        ws.column_dimensions[column_letter].width = adjusted_width

    # Save the file
    wb.save(excel_path)

    click.secho(
        f"Successfully exported graduating students to: {excel_path}", fg="green"
    )

    # Display summary
    click.echo(f"\nSummary:")
    click.echo(f"- Total graduating students: {len(graduating_students)}")
    click.echo(f"- Students with approved clearances: {len(approved_std_nos)}")
    click.echo(
        f"- Students with 2025 semesters and no issues: {len(qualifying_semester_std_nos)}"
    )
    click.echo(
        f"- Students meeting both criteria: {len(approved_std_nos & qualifying_semester_std_nos)}"
    )

    # Show breakdown by program
    from collections import Counter

    program_counts = Counter(student["program_name"] for student in graduating_students)

    click.echo(f"\nProgram breakdown:")
    for program, count in program_counts.most_common():
        click.echo(f"- {program}: {count} students")
