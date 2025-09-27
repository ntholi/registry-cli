import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

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
from registry_cli.grade_definitions import (
    calculate_cgpa_from_semesters,
    get_grade_points,
    is_passing_grade,
    normalize_grade_symbol,
)
from registry_cli.models import (
    Clearance,
    GraduationClearance,
    GraduationRequest,
    Program,
    School,
    SemesterModule,
    Structure,
    Student,
    StudentModule,
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


def calculate_cgpa_and_classification_for_program(
    db: Session, std_no: int, program: StudentProgram
) -> Tuple[Optional[float], str]:
    """
    Calculate CGPA and determine classification for a student based on a specific program.
    Uses the same logic as the JavaScript implementation.

    Returns:
        Tuple of (CGPA, Classification)
    """
    try:
        if not program:
            return None, "No Program Provided"

        # Get all semesters for the specified program (excluding deleted/deferred/etc)
        semesters = (
            db.query(StudentSemester)
            .filter(StudentSemester.student_program_id == program.id)
            .filter(
                StudentSemester.status.notin_(
                    ["Deleted", "Deferred", "DroppedOut", "Withdrawn"]
                )
            )
            .order_by(StudentSemester.id)
            .all()
        )

        if not semesters:
            return None, "No Semesters Found"

        # Prepare semester data for CGPA calculation
        semesters_data = []
        for semester in semesters:
            # Get all student modules for this semester (excluding Delete/Drop status)
            modules = (
                db.query(StudentModule, SemesterModule.credits)
                .join(
                    SemesterModule,
                    StudentModule.semester_module_id == SemesterModule.id,
                )
                .filter(StudentModule.student_semester_id == semester.id)
                .filter(StudentModule.status.notin_(["Delete", "Drop"]))
                .all()
            )

            modules_data = []
            for student_module, credits in modules:
                grade = student_module.grade or ""

                modules_data.append(
                    {
                        "grade": grade,
                        "status": student_module.status,
                        "credits": float(credits),
                    }
                )

            semesters_data.append({"id": semester.id, "modules": modules_data})

        # Calculate CGPA using the comprehensive calculation
        grade_points, final_cgpa = calculate_cgpa_from_semesters(semesters_data)

        if final_cgpa == 0:
            return None, "No Valid Grades"

        # Determine classification based on CGPA using grade descriptions
        if final_cgpa >= 3.5:  # A+, A, A- range (Pass with Distinction)
            classification = "Distinction"
        elif final_cgpa >= 3.0:  # B+, B, B- range (Pass with Merit)
            classification = "Merit"
        elif final_cgpa >= 1.7:  # C+, C, C- range (Pass)
            classification = "Pass"
        else:
            classification = "Failed"

        return round(final_cgpa, 2), classification

    except Exception as e:
        click.echo(f"Error calculating CGPA for student {std_no}: {str(e)}")
        return None, "Calculation Error"


def calculate_cgpa_and_classification(
    db: Session, std_no: int
) -> Tuple[Optional[float], str]:
    """
    Calculate CGPA and determine classification for a student based on their active program.
    Uses the same logic as the JavaScript implementation.

    Returns:
        Tuple of (CGPA, Classification)
    """
    try:
        # Get active program
        active_program = (
            db.query(StudentProgram)
            .filter(
                and_(StudentProgram.std_no == std_no, StudentProgram.status == "Active")
            )
            .first()
        )

        if not active_program:
            return None, "No Active Program"

        # Get all semesters for the active program (excluding deleted/deferred/etc)
        semesters = (
            db.query(StudentSemester)
            .filter(StudentSemester.student_program_id == active_program.id)
            .filter(
                StudentSemester.status.notin_(
                    ["Deleted", "Deferred", "DroppedOut", "Withdrawn"]
                )
            )
            .order_by(StudentSemester.id)
            .all()
        )

        if not semesters:
            return None, "No Semesters Found"

        # Prepare semester data for CGPA calculation
        semesters_data = []
        for semester in semesters:
            # Get all student modules for this semester (excluding Delete/Drop status)
            modules = (
                db.query(StudentModule, SemesterModule.credits)
                .join(
                    SemesterModule,
                    StudentModule.semester_module_id == SemesterModule.id,
                )
                .filter(StudentModule.student_semester_id == semester.id)
                .filter(StudentModule.status.notin_(["Delete", "Drop"]))
                .all()
            )

            modules_data = []
            for student_module, credits in modules:
                grade = student_module.grade or ""

                modules_data.append(
                    {
                        "grade": grade,
                        "status": student_module.status,
                        "credits": float(credits),
                    }
                )

            semesters_data.append({"id": semester.id, "modules": modules_data})

        # Calculate CGPA using the comprehensive calculation
        grade_points, final_cgpa = calculate_cgpa_from_semesters(semesters_data)

        if final_cgpa == 0:
            return None, "No Valid Grades"

        # Determine classification based on CGPA using grade descriptions
        if final_cgpa >= 3.5:  # A+, A, A- range (Pass with Distinction)
            classification = "Distinction"
        elif final_cgpa >= 3.0:  # B+, B, B- range (Pass with Merit)
            classification = "Merit"
        elif final_cgpa >= 1.7:  # C+, C, C- range (Pass)
            classification = "Pass"
        else:
            classification = "Failed"

        return round(final_cgpa, 2), classification

    except Exception as e:
        click.echo(f"Error calculating CGPA for student {std_no}: {str(e)}")
        return None, "Calculation Error"


def get_student_classification(db: Session, std_no: int) -> Optional[str]:
    """
    Get the student's classification based on CGPA calculation.

    Deprecated: Use calculate_cgpa_and_classification instead.
    """
    _, classification = calculate_cgpa_and_classification(db, std_no)
    return classification


def export_graduating_students(
    db: Session, additional_std_nos: Optional[List[int]] = None
) -> None:
    """
    Export graduating students to Excel file.

    Graduating students are those who either:
    1. Have approved academic graduation clearances, OR
    2. Have active programs with semesters containing '2024-07' or '2025-02' terms
       AND have no pending academic issues (using approve_academic_graduation logic), OR
    3. Are explicitly provided in additional_std_nos (bypassing the pending issues check)

    The exported file includes: student number, name, program name, school name, CGPA, classification, and criteria met.
    CGPA and classification are calculated from student's module grades in their active program.

    Args:
        db: Database session
        additional_std_nos: Optional list of student numbers to include without pending issues check
    """
    graduating_students = []

    # Criterion 1: Students with approved academic graduation clearances
    click.echo("Finding students with approved academic graduation clearances...")

    approved_graduation_students = (
        db.query(StudentProgram.std_no)
        .join(
            GraduationRequest,
            StudentProgram.id == GraduationRequest.student_program_id,
        )
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

    # Add additional student numbers if provided (these bypass pending issues check)
    additional_std_nos_set = set()
    if additional_std_nos:
        additional_std_nos_set = set(additional_std_nos)
        all_graduating_std_nos |= additional_std_nos_set
        click.echo(
            f"Additional student numbers provided: {len(additional_std_nos_set)}"
        )

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

            # Check if student has an approved graduation request
            graduation_request_program = None
            if std_no in approved_std_nos:
                graduation_request_program = (
                    db.query(StudentProgram)
                    .join(Structure, StudentProgram.structure_id == Structure.id)
                    .join(Program, Structure.program_id == Program.id)
                    .join(School, Program.school_id == School.id)
                    .join(
                        GraduationRequest,
                        StudentProgram.id == GraduationRequest.student_program_id,
                    )
                    .join(
                        GraduationClearance,
                        GraduationRequest.id
                        == GraduationClearance.graduation_request_id,
                    )
                    .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
                    .filter(
                        and_(
                            StudentProgram.std_no == std_no,
                            Clearance.department == "academic",
                            Clearance.status == "approved",
                        )
                    )
                    .order_by(
                        GraduationRequest.created_at.desc()
                    )  # Get the most recent approved request
                    .first()
                )

            # Use graduation request program if available, otherwise get active program
            if graduation_request_program:
                target_program = graduation_request_program
            else:
                target_program = (
                    db.query(StudentProgram)
                    .join(Structure, StudentProgram.structure_id == Structure.id)
                    .join(Program, Structure.program_id == Program.id)
                    .join(School, Program.school_id == School.id)
                    .filter(
                        and_(
                            StudentProgram.std_no == std_no,
                            StudentProgram.status == "Active",
                        )
                    )
                    .first()
                )

            if not target_program:
                continue

            program_name = (
                target_program.structure.program.name
                if target_program.structure
                else "Unknown Program"
            )

            school_name = (
                target_program.structure.program.school.name
                if target_program.structure and target_program.structure.program.school
                else "Unknown School"
            )

            # Calculate CGPA using the target program (graduation request program or active program)
            cgpa, classification = calculate_cgpa_and_classification_for_program(
                db, std_no, target_program
            )

            # Determine graduation criteria met
            criteria_met = []
            if std_no in approved_std_nos:
                criteria_met.append("Approved Clearance")
            if std_no in qualifying_semester_std_nos:
                criteria_met.append("2024-07/2025-02 + No Issues")
            if std_no in additional_std_nos_set:
                criteria_met.append("Provided List")

            graduating_students.append(
                {
                    "student_number": std_no,
                    "student_name": student.name,
                    "school_name": school_name,
                    "program_name": program_name,
                    "cgpa": cgpa if cgpa is not None else "N/A",
                    "classification": classification,
                    "criteria_met": " & ".join(criteria_met),
                }
            )

        except Exception as e:
            click.echo(f"Error processing student {std_no}: {str(e)}")
            continue

    if not graduating_students:
        click.secho("No valid graduating students found after processing.", fg="yellow")
        return

    # Filter out students with "Failed" classification
    initial_count = len(graduating_students)
    graduating_students = [
        s for s in graduating_students if s["classification"] != "Failed"
    ]
    failed_count = initial_count - len(graduating_students)

    if failed_count > 0:
        click.echo(f"Excluded {failed_count} students with 'Failed' classification")

    if not graduating_students:
        click.secho(
            "No graduating students remaining after filtering out failed classifications.",
            fg="yellow",
        )
        return

    # Sort students by school name, program name, then CGPA (descending)
    graduating_students.sort(
        key=lambda x: (
            x["school_name"],
            x["program_name"],
            -(
                x["cgpa"] if isinstance(x["cgpa"], (int, float)) else 0
            ),  # Negative for descending CGPA
        )
    )

    # Export to Excel
    output_dir = "exports"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    excel_filename = f"graduating_students_{timestamp}.xlsx"
    excel_path = os.path.join(output_dir, excel_filename)

    wb = Workbook()
    ws = wb.active
    if ws is None:
        # This should never happen with a new workbook, but let's handle it
        ws = wb.create_sheet("Graduating Students")
    else:
        ws.title = "Graduating Students"

    # Set up headers
    headers = [
        "Student Number",
        "Student Name",
        "School Name",
        "Program Name",
        "CGPA",
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
        ws.cell(row=row, column=3, value=student["school_name"])
        ws.cell(row=row, column=4, value=student["program_name"])
        ws.cell(row=row, column=5, value=student["cgpa"])
        ws.cell(row=row, column=6, value=student["classification"])
        ws.cell(row=row, column=7, value=student["criteria_met"])

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

    # Create breakdown sheet
    breakdown_ws = wb.create_sheet("School & Program Breakdown")

    # Prepare breakdown data
    from collections import defaultdict

    school_program_stats = defaultdict(lambda: defaultdict(int))
    school_totals = defaultdict(int)

    # Calculate statistics
    for student in graduating_students:
        school = student["school_name"]
        program = student["program_name"]
        school_program_stats[school][program] += 1
        school_totals[school] += 1

    # Set up breakdown sheet headers
    breakdown_headers = ["School/Faculty", "Program", "Student Count"]
    for col, header in enumerate(breakdown_headers, 1):
        cell = breakdown_ws.cell(row=1, column=col)
        cell.value = header
        cell.font = header_font
        cell.fill = header_fill

    # Add breakdown data
    row = 2
    for school in sorted(school_program_stats.keys()):
        # Add school header row
        school_cell = breakdown_ws.cell(row=row, column=1)
        school_cell.value = school
        school_cell.font = Font(bold=True, color="000080")
        school_cell.fill = PatternFill(
            start_color="E6E6FA", end_color="E6E6FA", fill_type="solid"
        )

        breakdown_ws.cell(row=row, column=2, value="")
        breakdown_ws.cell(row=row, column=3, value="")
        row += 1

        # Add programs for this school
        programs = sorted(school_program_stats[school].keys())
        for program in programs:
            count = school_program_stats[school][program]
            breakdown_ws.cell(row=row, column=1, value="")  # Indent for program
            breakdown_ws.cell(row=row, column=2, value=program)
            breakdown_ws.cell(row=row, column=3, value=count)
            row += 1

        # Add school total
        total_cell = breakdown_ws.cell(row=row, column=2)
        total_cell.value = f"TOTAL - {school}"
        total_cell.font = Font(bold=True, color="800000")

        total_count_cell = breakdown_ws.cell(row=row, column=3)
        total_count_cell.value = school_totals[school]
        total_count_cell.font = Font(bold=True, color="800000")

        row += 2  # Add space between schools

    # Add grand total
    grand_total_row = row
    breakdown_ws.cell(row=grand_total_row, column=2, value="GRAND TOTAL")
    breakdown_ws.cell(row=grand_total_row, column=3, value=len(graduating_students))

    for col in [2, 3]:
        cell = breakdown_ws.cell(row=grand_total_row, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(
            start_color="366092", end_color="366092", fill_type="solid"
        )

    # Auto-size columns for breakdown sheet
    for col in range(1, len(breakdown_headers) + 1):
        column_letter = get_column_letter(col)
        max_length = 0
        for row_cells in breakdown_ws[column_letter]:
            try:
                if len(str(row_cells.value)) > max_length:
                    max_length = len(str(row_cells.value))
            except:
                pass
        adjusted_width = min(max_length + 2, 60)  # Slightly wider for school names
        breakdown_ws.column_dimensions[column_letter].width = adjusted_width

    # Save the file
    wb.save(excel_path)

    click.secho(
        f"Successfully exported graduating students to: {excel_path}", fg="green"
    )

    # Display summary
    click.echo(f"\nSummary:")
    click.echo(
        f"- Total graduating students (excluding failed): {len(graduating_students)}"
    )
    if failed_count > 0:
        click.echo(
            f"- Students excluded due to 'Failed' classification: {failed_count}"
        )
    click.echo(f"- Students with approved clearances: {len(approved_std_nos)}")
    click.echo(
        f"- Students with 2025 semesters and no issues: {len(qualifying_semester_std_nos)}"
    )
    if additional_std_nos_set:
        click.echo(f"- Students from provided list: {len(additional_std_nos_set)}")
    click.echo(
        f"- Students meeting both criteria: {len(approved_std_nos & qualifying_semester_std_nos)}"
    )

    # Show breakdown by school
    from collections import Counter

    school_counts = Counter(student["school_name"] for student in graduating_students)

    click.echo(f"\nSchool breakdown:")
    for school, count in school_counts.most_common():
        click.echo(f"- {school}: {count} students")

    # Show breakdown by program
    program_counts = Counter(student["program_name"] for student in graduating_students)

    click.echo(f"\nProgram breakdown:")
    for program, count in program_counts.most_common():
        click.echo(f"- {program}: {count} students")
