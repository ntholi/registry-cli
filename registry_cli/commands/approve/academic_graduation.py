import time
from typing import Any, Dict, List, Optional

import click
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.models import (
    Clearance,
    GradeType,
    GraduationClearance,
    GraduationRequest,
    Module,
    SemesterModule,
    StructureSemester,
    Student,
    StudentModule,
    StudentProgram,
)


def normalize_grade_symbol(grade: str) -> str:
    """
    Normalize grade symbol by trimming and converting to uppercase.
    """
    return grade.strip().upper()


def is_passing_grade(grade: str) -> bool:
    """
    Check if a grade is considered passing.
    Based on the comprehensive grade system with points > 0.
    """
    normalized_grade = normalize_grade_symbol(grade)

    # Grades with points > 0 are considered passing
    passing_grades = [
        "A+",
        "A",
        "A-",
        "B+",
        "B",
        "B-",
        "C+",
        "C",
        "C-",
        "PC",
        "PX",
        "AP",
    ]
    return normalized_grade in passing_grades


def is_failing_grade(grade: str) -> bool:
    """
    Check if a grade is considered failing.
    """
    failing_grades = ["F", "X", "GNS", "ANN", "FIN", "FX", "DNC", "DNA", "DNS"]
    return normalize_grade_symbol(grade) in failing_grades


def is_supplementary_grade(grade: str) -> bool:
    """
    Check if a grade is supplementary (PP).
    """
    return normalize_grade_symbol(grade) == "PP"


def is_failing_or_sup_grade(grade: str) -> bool:
    """
    Check if a grade is failing or supplementary.
    """
    return is_failing_grade(grade) or is_supplementary_grade(grade)


def normalize_module_name(name: str) -> str:
    """
    Normalize module name for comparison.
    Handles roman numerals, ampersands, and standardizes spacing.
    """
    # Convert roman numerals to arabic numbers
    roman_to_arabic = {
        "i": "1",
        "ii": "2",
        "iii": "3",
        "iv": "4",
        "v": "5",
        "vi": "6",
        "vii": "7",
        "viii": "8",
        "ix": "9",
        "x": "10",
    }

    # Normalize the name
    normalized = name.strip().lower().replace("&", "and")

    # Replace roman numerals with arabic numbers
    words = normalized.split()
    for i, word in enumerate(words):
        if word in roman_to_arabic:
            words[i] = roman_to_arabic[word]

    # Join and clean up spacing
    return " ".join(words).strip()


def get_student_programs(db: Session, std_no: int) -> List[StudentProgram]:
    """
    Get student programs for a given student number.
    """
    programs = db.query(StudentProgram).filter(StudentProgram.std_no == std_no).all()
    return programs


def get_visible_modules_for_structure(
    db: Session, structure_id: int
) -> List[Dict[str, Any]]:
    """
    Get visible modules for a structure, grouped by semester.
    Only returns modules where hidden=False.
    """
    semesters = (
        db.query(StructureSemester)
        .filter(StructureSemester.structure_id == structure_id)
        .order_by(StructureSemester.semester_number)
        .all()
    )

    result = []
    for semester in semesters:
        semester_modules = (
            db.query(SemesterModule)
            .filter(
                and_(
                    SemesterModule.semester_id == semester.id,
                    SemesterModule.hidden == False,  # Only get visible modules
                )
            )
            .all()
        )

        modules_data = []
        for sm in semester_modules:
            if sm.module:  # Ensure module exists
                modules_data.append(
                    {
                        "id": sm.id,
                        "module": sm.module,
                        "type": sm.type,
                        "credits": sm.credits,
                    }
                )

        result.append(
            {
                "semesterNumber": semester.semester_number,
                "semesterModules": modules_data,
            }
        )

    return result


def extract_data(programs: List[StudentProgram]) -> Dict[str, Any]:
    """
    Extract student modules from programs.
    Prioritizes Active programs, then Completed programs if no Active ones exist.
    Filters out certain semester statuses.
    """
    # Sort programs by ID (newest first) and filter for Active status
    active_programs = [
        p
        for p in sorted(programs, key=lambda x: x.id, reverse=True)
        if p.status == "Active"
    ]

    # If no active programs, try completed programs
    if not active_programs:
        active_programs = [
            p
            for p in sorted(programs, key=lambda x: x.id, reverse=True)
            if p.status == "Completed"
        ]

    # If still no programs found, return empty
    if not active_programs:
        return {"studentModules": [], "semesters": []}

    # Use the first (newest) program
    program = active_programs[0]
    semesters = program.semesters or []

    # Filter out certain semester statuses and sort by ID
    filtered_semesters = [
        s
        for s in semesters
        if s.status not in ["Deleted", "Deferred", "DroppedOut", "Withdrawn"]
    ]
    filtered_semesters.sort(key=lambda x: x.id)

    # Extract student modules from filtered semesters
    student_modules = []
    for semester in filtered_semesters:
        for module in semester.modules:
            # Filter out certain module statuses
            if module.status not in ["Delete", "Drop"]:
                student_modules.append(module)

    return {"studentModules": student_modules, "semesters": filtered_semesters}


def get_outstanding_from_structure(
    db: Session, programs: List[StudentProgram]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Get outstanding modules from structure based on student's active program.
    Returns failed never repeated and never attempted modules.
    """
    # Find active program
    program = None
    for p in programs:
        if p.status == "Active":
            program = p
            break

    if not program:
        raise Exception("No active program found for student")

    # Get structure modules (only visible ones)
    structure_modules = get_visible_modules_for_structure(db, program.structure_id)

    # Build required modules list
    required_modules = []
    for semester in structure_modules:
        for sm in semester["semesterModules"]:
            if sm["module"] and not sm.get(
                "hidden", False
            ):  # Ensure module exists and is not hidden
                required_modules.append(
                    {
                        "id": sm["module"].id,
                        "code": sm["module"].code,
                        "name": normalize_module_name(sm["module"].name),
                        "originalName": sm["module"].name,
                        "type": sm["type"],
                        "credits": sm["credits"],
                        "semesterNumber": semester["semesterNumber"],
                    }
                )

    # Extract student modules using improved logic
    data = extract_data(programs)
    student_modules = data["studentModules"]

    # Create map of attempted modules by normalized name
    attempted_modules = {}
    for sm in student_modules:
        if hasattr(sm, "semester_module_id") and sm.semester_module_id:
            # Get the semester module to get the actual module
            semester_module = (
                db.query(SemesterModule)
                .filter(SemesterModule.id == sm.semester_module_id)
                .first()
            )

            if semester_module and semester_module.module:
                name = normalize_module_name(semester_module.module.name)
                if name not in attempted_modules:
                    attempted_modules[name] = []
                attempted_modules[name].append(sm)

    failed_never_repeated = []
    never_attempted = []

    for module in required_modules:
        attempts = attempted_modules.get(module["name"], [])

        if not attempts:
            # Never attempted
            never_attempted.append({**module, "name": module["originalName"]})
        else:
            # Check if any attempt passed
            passed_attempts = [
                attempt for attempt in attempts if is_passing_grade(attempt.grade or "")
            ]

            if not passed_attempts:
                # All attempts failed
                if len(attempts) == 1:
                    # Failed and never repeated
                    failed_never_repeated.append(
                        {**module, "name": module["originalName"]}
                    )

    return {
        "failedNeverRepeated": failed_never_repeated,
        "neverAttempted": never_attempted,
    }


def process_academic_clearance(
    db: Session, graduation_request_id: int, std_no: int
) -> None:
    """
    Process academic clearance for a graduation request.
    """
    programs = get_student_programs(db, std_no)
    if not programs:
        raise Exception("Student not found")

    outstanding = get_outstanding_from_structure(db, programs)

    # Determine status and message
    if (
        len(outstanding["failedNeverRepeated"]) == 0
        and len(outstanding["neverAttempted"]) == 0
    ):
        status = "approved"
        message = None
    else:
        status = "pending"
        reasons = []

        if outstanding["failedNeverRepeated"]:
            failed_list = ", ".join(
                [
                    f"{m['code']} - {m['name']}"
                    for m in outstanding["failedNeverRepeated"]
                ]
            )
            reasons.append(f"Failed modules never repeated: {failed_list}")

        if outstanding["neverAttempted"]:
            never_attempted_list = ", ".join(
                [f"{m['code']} - {m['name']}" for m in outstanding["neverAttempted"]]
            )
            reasons.append(f"Required modules never attempted: {never_attempted_list}")

        message = f"Academic requirements not met. {'; '.join(reasons)}. Please ensure all program modules are completed successfully before applying for graduation."

    # Create clearance record
    current_time = int(time.time())
    clearance = Clearance(
        department="academic",
        status=status,
        message=message,
        created_at=current_time,
    )
    db.add(clearance)
    db.flush()  # Get the ID

    # Create graduation clearance link
    graduation_clearance = GraduationClearance(
        graduation_request_id=graduation_request_id,
        clearance_id=clearance.id,
        created_at=current_time,
    )
    db.add(graduation_clearance)


def approve_academic_graduation(db: Session) -> None:
    """
    Approve pending academic graduation requests that meet the criteria.
    This command goes through all academic pending graduation requests and reviews/approves them
    if they need to be approved.
    """
    # Find all graduation requests that have pending academic clearances
    pending_academic_requests = (
        db.query(GraduationRequest)
        .join(
            GraduationClearance,
            GraduationRequest.id == GraduationClearance.graduation_request_id,
        )
        .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
        .filter(and_(Clearance.department == "academic", Clearance.status == "pending"))
        .all()
    )

    if not pending_academic_requests:
        click.secho("No pending academic graduation requests found.", fg="yellow")
        return

    click.secho(
        f"Found {len(pending_academic_requests)} pending academic graduation requests.",
        fg="blue",
    )

    approved_count = 0
    failed_count = 0

    for i, graduation_request in enumerate(pending_academic_requests, 1):
        click.echo(
            f"\nProcessing {i}/{len(pending_academic_requests)}: Student {graduation_request.std_no}"
        )

        try:
            # Get the existing academic clearance
            academic_clearance = (
                db.query(Clearance)
                .join(
                    GraduationClearance,
                    Clearance.id == GraduationClearance.clearance_id,
                )
                .filter(
                    and_(
                        GraduationClearance.graduation_request_id
                        == graduation_request.id,
                        Clearance.department == "academic",
                    )
                )
                .first()
            )

            if not academic_clearance:
                click.secho(
                    f"  ✗ No academic clearance found for graduation request {graduation_request.id}",
                    fg="red",
                )
                failed_count += 1
                continue

            # Get student programs and check academic requirements
            programs = get_student_programs(db, graduation_request.std_no)
            if not programs:
                click.secho(
                    f"  ✗ No programs found for student {graduation_request.std_no}",
                    fg="red",
                )
                failed_count += 1
                continue

            outstanding = get_outstanding_from_structure(db, programs)

            # Check if requirements are met
            if (
                len(outstanding["failedNeverRepeated"]) == 0
                and len(outstanding["neverAttempted"]) == 0
            ):
                # Requirements met - approve
                academic_clearance.status = "approved"
                academic_clearance.message = None
                academic_clearance.response_date = int(time.time())

                click.secho(
                    f"  ✓ Approved academic clearance for student {graduation_request.std_no}",
                    fg="green",
                )
                approved_count += 1
            else:
                # Requirements not met - update message but keep pending
                reasons = []

                if outstanding["failedNeverRepeated"]:
                    failed_list = ", ".join(
                        [
                            f"{m['code']} - {m['name']}"
                            for m in outstanding["failedNeverRepeated"]
                        ]
                    )
                    reasons.append(f"Failed modules never repeated: {failed_list}")

                if outstanding["neverAttempted"]:
                    never_attempted_list = ", ".join(
                        [
                            f"{m['code']} - {m['name']}"
                            for m in outstanding["neverAttempted"]
                        ]
                    )
                    reasons.append(
                        f"Required modules never attempted: {never_attempted_list}"
                    )

                academic_clearance.message = f"Academic requirements not met. {'; '.join(reasons)}. Please ensure all program modules are completed successfully before applying for graduation."

                click.secho(
                    f"  ⚠ Academic requirements not met for student {graduation_request.std_no}",
                    fg="yellow",
                )
                click.secho(f"    Reasons: {'; '.join(reasons)}", fg="yellow")

            # Commit changes after processing each request
            try:
                db.commit()
            except Exception as commit_error:
                db.rollback()
                click.secho(
                    f"  ✗ Error saving changes for student {graduation_request.std_no}: {str(commit_error)}",
                    fg="red",
                )
                failed_count += 1
                continue

        except Exception as e:
            db.rollback()
            click.secho(
                f"  ✗ Error processing student {graduation_request.std_no}: {str(e)}",
                fg="red",
            )
            failed_count += 1
            continue

    # Final summary
    click.echo("\n" + "=" * 50)
    click.secho(f"Processing complete!", fg="green")
    click.secho(f"Approved: {approved_count}", fg="green")
    click.secho(
        f"Still pending: {len(pending_academic_requests) - approved_count - failed_count}",
        fg="yellow",
    )
    click.secho(f"Failed: {failed_count}", fg="red")
