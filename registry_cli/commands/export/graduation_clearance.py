import os
from datetime import datetime
from typing import List, Optional

import click
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from registry_cli.models import (
    Clearance,
    GraduationClearance,
    GraduationRequest,
    PaymentReceipt,
    Program,
    School,
    Structure,
    Student,
    StudentProgram,
)


def export_approved_graduation_students(db: Session) -> None:
    """
    Export students who have been approved for graduation requests clearance by all departments.

    This command exports students who have:
    1. A graduation request
    2. All existing departments have approved their clearance
    3. Their information includes: student number, student names, faculty, program, and receipt numbers

    The exported file includes: student number, name, faculty (school), program name, and receipt numbers.
    """
    click.echo(
        "Finding students with approved graduation clearances from all departments..."
    )

    # First, find which actual departments exist with graduation clearances (exclude invalid entries)
    valid_departments = ["finance", "registry", "library", "resource", "academic"]
    existing_departments = (
        db.query(Clearance.department)
        .join(GraduationClearance, Clearance.id == GraduationClearance.clearance_id)
        .filter(Clearance.department.in_(valid_departments))
        .distinct()
        .all()
    )
    required_departments = [dept[0] for dept in existing_departments]

    click.echo(f"Departments with graduation clearances: {required_departments}")
    if not required_departments:
        click.secho("No departments found with graduation clearances.", fg="yellow")
        return

    # Find graduation requests that have approved clearances from ALL required departments
    # We need to count approved clearances per graduation request and ensure it equals the number of required departments
    graduation_requests_with_full_approval = (
        db.query(GraduationRequest.id, GraduationRequest.student_program_id)
        .join(
            GraduationClearance,
            GraduationRequest.id == GraduationClearance.graduation_request_id,
        )
        .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
        .filter(
            and_(
                Clearance.status == "approved",
                Clearance.department.in_(required_departments),
            )
        )
        .group_by(GraduationRequest.id, GraduationRequest.student_program_id)
        .having(
            func.count(func.distinct(Clearance.department)) == len(required_departments)
        )
        .all()
    )

    if not graduation_requests_with_full_approval:
        click.secho(
            "No students found with approved graduation clearances from all departments.",
            fg="yellow",
        )
        return

    click.echo(
        f"Found {len(graduation_requests_with_full_approval)} students with full departmental approval"
    )

    # Collect detailed information for approved students
    approved_students = []

    for i, (graduation_request_id, student_program_id) in enumerate(
        graduation_requests_with_full_approval, 1
    ):
        if i % 10 == 0:
            click.echo(
                f"Processed {i}/{len(graduation_requests_with_full_approval)} students..."
            )

        try:
            # Get student program with related information
            student_program = (
                db.query(StudentProgram)
                .join(Student, StudentProgram.std_no == Student.std_no)
                .join(Structure, StudentProgram.structure_id == Structure.id)
                .join(Program, Structure.program_id == Program.id)
                .join(School, Program.school_id == School.id)
                .filter(StudentProgram.id == student_program_id)
                .first()
            )

            if not student_program or not student_program.student:
                continue

            # Get payment receipts for this graduation request
            payment_receipts = (
                db.query(PaymentReceipt)
                .filter(PaymentReceipt.graduation_request_id == graduation_request_id)
                .all()
            )

            # Organize receipt numbers by payment type
            graduation_fee_receipts = []
            graduation_gown_receipts = []

            for receipt in payment_receipts:
                if receipt.payment_type == "graduation_fee":
                    graduation_fee_receipts.append(receipt.receipt_no)
                elif receipt.payment_type == "graduation_gown":
                    graduation_gown_receipts.append(receipt.receipt_no)

            # Format receipt numbers
            graduation_fee_receipt_nos = (
                ", ".join(graduation_fee_receipts) if graduation_fee_receipts else "N/A"
            )
            graduation_gown_receipt_nos = (
                ", ".join(graduation_gown_receipts)
                if graduation_gown_receipts
                else "N/A"
            )
            all_receipt_nos = (
                ", ".join([r.receipt_no for r in payment_receipts])
                if payment_receipts
                else "N/A"
            )

            approved_students.append(
                {
                    "student_number": student_program.std_no,
                    "student_name": student_program.student.name,
                    "faculty": student_program.structure.program.school.name,
                    "program_name": student_program.structure.program.name,
                    "graduation_fee_receipts": graduation_fee_receipt_nos,
                    "graduation_gown_receipts": graduation_gown_receipt_nos,
                    "all_receipts": all_receipt_nos,
                    "graduation_request_id": graduation_request_id,
                }
            )

        except Exception as e:
            click.echo(
                f"Error processing graduation request {graduation_request_id}: {str(e)}"
            )
            continue

    if not approved_students:
        click.secho("No valid students found after processing.", fg="yellow")
        return

    # Sort students by graduation request ID
    approved_students.sort(key=lambda x: x["graduation_request_id"])

    # Export to Excel
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"approved_graduation_clearance_{timestamp}.xlsx"
    excel_path = os.path.join(output_dir, excel_filename)

    wb = Workbook()
    ws = wb.active
    if ws is None:
        ws = wb.create_sheet("Approved Graduation Students")
    else:
        ws.title = "Approved Graduation Students"

    # Set up headers
    headers = [
        "Student Number",
        "Student Name",
        "Faculty",
        "Program",
        "Graduation Fee Receipts",
        "Graduation Gown Receipts",
        "All Receipt Numbers",
        "Graduation Request ID",
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
    for row, student in enumerate(approved_students, 2):
        ws.cell(row=row, column=1, value=student["student_number"])
        ws.cell(row=row, column=2, value=student["student_name"])
        ws.cell(row=row, column=3, value=student["faculty"])
        ws.cell(row=row, column=4, value=student["program_name"])
        ws.cell(row=row, column=5, value=student["graduation_fee_receipts"])
        ws.cell(row=row, column=6, value=student["graduation_gown_receipts"])
        ws.cell(row=row, column=7, value=student["all_receipts"])
        ws.cell(row=row, column=8, value=student["graduation_request_id"])

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
        f"Successfully exported approved graduation students to: {excel_path}",
        fg="green",
    )

    # Display summary
    click.echo(f"\nSummary:")
    click.echo(
        f"- Total students with full departmental approval: {len(approved_students)}"
    )

    # Show breakdown by faculty
    from collections import Counter

    faculty_counts = Counter(student["faculty"] for student in approved_students)
    click.echo(f"\nFaculty breakdown:")
    for faculty, count in faculty_counts.most_common():
        click.echo(f"- {faculty}: {count} students")

    # Show breakdown by program
    program_counts = Counter(student["program_name"] for student in approved_students)
    click.echo(f"\nProgram breakdown:")
    for program, count in program_counts.most_common():
        click.echo(f"- {program}: {count} students")

    # Show payment receipt statistics
    students_with_fee_receipts = sum(
        1 for s in approved_students if s["graduation_fee_receipts"] != "N/A"
    )
    students_with_gown_receipts = sum(
        1 for s in approved_students if s["graduation_gown_receipts"] != "N/A"
    )
    students_with_any_receipts = sum(
        1 for s in approved_students if s["all_receipts"] != "N/A"
    )

    click.echo(f"\nPayment receipt statistics:")
    click.echo(f"- Students with graduation fee receipts: {students_with_fee_receipts}")
    click.echo(
        f"- Students with graduation gown receipts: {students_with_gown_receipts}"
    )
    click.echo(f"- Students with any payment receipts: {students_with_any_receipts}")
    click.echo(
        f"- Students without payment receipts: {len(approved_students) - students_with_any_receipts}"
    )
