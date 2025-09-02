from collections import Counter
from typing import Optional

import click
from sqlalchemy import and_, desc
from sqlalchemy.orm import Session

from registry_cli.models import (
    RegistrationRequest,
    RequestedModule,
    SemesterModule,
    StructureSemester,
    StudentProgram,
    StudentSemester,
)


def update_student_semester_number(db: Session, std_no: int) -> None:
    """
    Update a student's latest semester number and status based on their registered modules.

    This command analyzes the modules in the student's latest registration request,
    determines the semester number that most modules belong to, and updates both
    the registration request and student semester accordingly.

    It also updates the status - if most modules have a "Repeat" status (Repeat1, Repeat2, etc.)
    then the status becomes "Repeat", otherwise it remains "Active".

    Args:
        db: Database session
        std_no: Student number
    """
    # Find the student's active program
    student_program = (
        db.query(StudentProgram)
        .filter(
            and_(
                StudentProgram.std_no == std_no,
                StudentProgram.status == "Active",
            )
        )
        .first()
    )

    if not student_program:
        click.secho(f"No active program found for student {std_no}", fg="red")
        return

    # Get the student's latest registration request
    latest_request = (
        db.query(RegistrationRequest)
        .filter(RegistrationRequest.std_no == std_no)
        .order_by(desc(RegistrationRequest.id))
        .first()
    )

    if not latest_request:
        click.secho(f"No registration request found for student {std_no}", fg="red")
        return

    # Get the student's latest semester for this program
    latest_semester = (
        db.query(StudentSemester)
        .filter(StudentSemester.student_program_id == student_program.id)
        .order_by(desc(StudentSemester.id))
        .first()
    )

    if not latest_semester:
        click.secho(f"No student semester found for student {std_no}", fg="red")
        return

    # Get all requested modules for the latest registration request
    requested_modules = (
        db.query(RequestedModule)
        .join(SemesterModule, RequestedModule.semester_module_id == SemesterModule.id)
        .join(StructureSemester, SemesterModule.semester_id == StructureSemester.id)
        .filter(RequestedModule.registration_request_id == latest_request.id)
        .all()
    )

    if not requested_modules:
        click.secho(f"No requested modules found for student {std_no}", fg="yellow")
        return

    # Analyze semester numbers and statuses
    semester_numbers = []
    module_statuses = []

    for requested_module in requested_modules:
        # Get the semester number from the structure semester
        semester_module = requested_module.semester_module
        if semester_module and semester_module.semester:
            semester_numbers.append(semester_module.semester.semester_number)

        # Collect module statuses
        if requested_module.module_status:
            module_statuses.append(requested_module.module_status)

    if not semester_numbers:
        click.secho(
            f"No semester numbers found for student {std_no} modules", fg="yellow"
        )
        return

    # Determine the majority semester number
    semester_counter = Counter(semester_numbers)
    most_common_semester = semester_counter.most_common(1)[0][0]
    most_common_count = semester_counter.most_common(1)[0][1]
    total_modules = len(semester_numbers)

    # Determine the majority status (Active vs Repeat)
    repeat_statuses = [
        status for status in module_statuses if status.startswith("Repeat")
    ]
    repeat_count = len(repeat_statuses)

    # If more than half of the modules are "Repeat" type, set status to "Repeat"
    new_status = "Repeat" if repeat_count > total_modules / 2 else "Active"

    click.echo(f"\nAnalysis for student {std_no}:")
    click.echo(f"Total modules: {total_modules}")
    click.echo(f"Semester distribution: {dict(semester_counter)}")
    click.echo(
        f"Most common semester: {most_common_semester} ({most_common_count} modules)"
    )
    click.echo(f"Repeat modules: {repeat_count}")
    click.echo(f"Determined status: {new_status}")

    # Update the registration request if semester number has changed
    old_reg_semester = latest_request.semester_number
    if old_reg_semester != most_common_semester:
        latest_request.semester_number = most_common_semester
        click.secho(
            f"Updated registration request semester: {old_reg_semester} -> {most_common_semester}",
            fg="green",
        )
    else:
        click.echo(f"Registration request semester unchanged: {most_common_semester}")

    # Update the registration request status if it has changed
    old_reg_status = latest_request.semester_status
    if old_reg_status != new_status:
        latest_request.semester_status = new_status
        click.secho(
            f"Updated registration request status: {old_reg_status} -> {new_status}",
            fg="green",
        )
    else:
        click.echo(f"Registration request status unchanged: {new_status}")

    # Update the student semester if semester number has changed
    old_sem_number = latest_semester.semester_number
    if old_sem_number != most_common_semester:
        latest_semester.semester_number = most_common_semester
        click.secho(
            f"Updated student semester number: {old_sem_number} -> {most_common_semester}",
            fg="green",
        )
    else:
        click.echo(f"Student semester number unchanged: {most_common_semester}")

    # Update the student semester status if it has changed
    old_sem_status = latest_semester.status
    if old_sem_status != new_status:
        latest_semester.status = new_status
        click.secho(
            f"Updated student semester status: {old_sem_status} -> {new_status}",
            fg="green",
        )
    else:
        click.echo(f"Student semester status unchanged: {new_status}")

    # Commit all changes
    db.commit()
    click.secho(
        f"\nSuccessfully updated semester information for student {std_no}", fg="green"
    )


def update_multiple_students_semester_numbers(
    db: Session, std_nos: list[int], reset_progress: bool = False
) -> None:
    """
    Update semester numbers for multiple students.

    Args:
        db: Database session
        std_nos: List of student numbers
        reset_progress: Whether to reset progress tracking
    """
    total_students = len(std_nos)
    success_count = 0
    error_count = 0

    click.echo(f"Processing {total_students} students...")

    for i, std_no in enumerate(std_nos, 1):
        click.echo(f"\n[{i}/{total_students}] Processing student {std_no}...")

        try:
            update_student_semester_number(db, std_no)
            success_count += 1
        except Exception as e:
            error_count += 1
            click.secho(f"Error processing student {std_no}: {str(e)}", fg="red")

    # Summary
    click.echo(f"\n{'='*50}")
    click.echo(f"Processing complete!")
    click.secho(f"Successfully processed: {success_count} students", fg="green")
    if error_count > 0:
        click.secho(f"Errors encountered: {error_count} students", fg="red")
    else:
        click.secho("No errors encountered!", fg="green")
