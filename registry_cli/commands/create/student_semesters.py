import time
from typing import Optional

import click
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from registry_cli.models import (
    RegistrationClearance,
    RegistrationRequest,
    RequestedModule,
    Student,
    StudentModule,
    StudentProgram,
    StudentSemester,
    Term,
)


def create_student_semester_for_request(
    db: Session, request: RegistrationRequest
) -> Optional[StudentSemester]:
    """
    Create a StudentSemester record based on a RegistrationRequest.

    Args:
        db: Database session
        request: RegistrationRequest to create semester for

    Returns:
        Created StudentSemester or None if student/program not found
    """
    student = db.query(Student).filter(Student.std_no == request.std_no).first()
    if not student:
        click.secho(f"Student {request.std_no} not found", fg="red")
        return None

    term = db.query(Term).filter(Term.id == request.term_id).first()
    if not term:
        click.secho(f"Term with ID {request.term_id} not found", fg="red")
        return None

    # Find the student's active program
    student_program = (
        db.query(StudentProgram)
        .filter(
            and_(
                StudentProgram.std_no == student.std_no,
                StudentProgram.status == "Active",
            )
        )
        .first()
    )

    if not student_program:
        click.secho(f"No active program found for student {student.std_no}", fg="red")
        return None

    # Check if semester already exists
    existing_semester = (
        db.query(StudentSemester)
        .filter(
            and_(
                StudentSemester.student_program_id == student_program.id,
                StudentSemester.term == term.name,
                StudentSemester.semester_number == request.semester_number,
            )
        )
        .first()
    )

    if existing_semester:
        click.secho(
            f"Semester already exists for student {student.std_no}, "
            f"term {term.name}, semester {request.semester_number}",
            fg="yellow",
        )
        # Still create modules if they don't exist
        modules_created = _create_student_modules_for_semester(
            db, existing_semester, request, silent=True
        )

        # Mark all requested modules as registered
        _mark_requested_modules_as_registered(db, request)

        # Mark the registration request as registered if not already
        if request.status != "registered":
            request.status = "registered"
            request.updated_at = int(time.time())
            db.commit()

        return existing_semester

    # Create new StudentSemester
    student_semester = StudentSemester(
        term=term.name,
        semester_number=request.semester_number,
        status="Active",
        student_program_id=student_program.id,
        created_at=int(time.time()),
    )

    db.add(student_semester)
    db.commit()

    # Create StudentModule records for the requested modules
    modules_created = _create_student_modules_for_semester(
        db, student_semester, request, silent=True
    )

    # Mark all requested modules as registered
    _mark_requested_modules_as_registered(db, request)

    # Mark the registration request as registered
    request.status = "registered"
    request.updated_at = int(time.time())
    db.commit()

    click.secho(
        f"Created semester for student {student.std_no}, "
        f"term {term.name}, semester {request.semester_number} "
        f"with {modules_created} modules",
        fg="green",
    )
    return student_semester


def _create_student_modules_for_semester(
    db: Session,
    student_semester: StudentSemester,
    request: RegistrationRequest,
    silent: bool = False,
) -> int:
    """
    Create StudentModule records for the requested modules in a semester.

    Args:
        db: Database session
        student_semester: StudentSemester to create modules for
        request: RegistrationRequest containing requested modules
        silent: If True, suppress detailed output messages

    Returns:
        Number of modules created
    """
    requested_modules = (
        db.query(RequestedModule)
        .filter(RequestedModule.registration_request_id == request.id)
        .all()
    )

    modules_created = 0
    for requested_module in requested_modules:
        # Check if student module already exists
        existing_module = (
            db.query(StudentModule)
            .filter(
                and_(
                    StudentModule.student_semester_id == student_semester.id,
                    StudentModule.semester_module_id
                    == requested_module.semester_module_id,
                )
            )
            .first()
        )

        if existing_module:
            if not silent:
                click.secho(
                    f"Module {requested_module.semester_module.module.code if requested_module.semester_module.module else 'Unknown'} "
                    f"already exists for student semester {student_semester.id}",
                    fg="yellow",
                )
            continue

        # Create new StudentModule
        student_module = StudentModule(
            semester_module_id=requested_module.semester_module_id,
            status=requested_module.module_status,
            marks="NM",  # Default marks
            grade="NM",  # Default grade indicating not yet graded
            student_semester_id=student_semester.id,
            created_at=int(time.time()),
        )

        db.add(student_module)
        modules_created += 1

    if modules_created > 0:
        db.commit()
        if not silent:
            click.secho(
                f"Created {modules_created} student modules for semester {student_semester.id}",
                fg="green",
            )

    return modules_created


def _mark_requested_modules_as_registered(
    db: Session, request: RegistrationRequest
) -> None:
    """
    Mark all requested modules associated with a registration request as registered.

    Args:
        db: Database session
        request: RegistrationRequest containing requested modules to mark as registered
    """
    requested_modules = (
        db.query(RequestedModule)
        .filter(RequestedModule.registration_request_id == request.id)
        .all()
    )

    modules_updated = 0
    for requested_module in requested_modules:
        if requested_module.status != "registered":
            requested_module.status = "registered"
            modules_updated += 1

    if modules_updated > 0:
        db.commit()
        click.secho(
            f"Marked {modules_updated} requested modules as registered for request {request.id}",
            fg="green",
        )


def create_student_semesters_approved(db: Session) -> None:
    """Create student semesters for all approved registration requests."""
    approved_requests = (
        db.query(RegistrationRequest)
        .filter(RegistrationRequest.status == "pending")
        .filter(
            RegistrationRequest.id.in_(
                db.query(RegistrationClearance.registration_request_id)
                .filter(
                    RegistrationClearance.department.in_(["finance", "library"]),
                    RegistrationClearance.status == "approved",
                )
                .group_by(RegistrationClearance.registration_request_id)
                .having(func.count(RegistrationClearance.registration_request_id) == 2)
            )
        )
        .all()
    )

    if len(approved_requests) == 0:
        click.secho("No approved requests found.", fg="red")
        return

    success_count = 0
    for i, request in enumerate(approved_requests):
        click.echo(
            f"\nProcessing request {i + 1}/{len(approved_requests)} for student {request.std_no}"
        )

        try:
            student_semester = create_student_semester_for_request(db, request)
            if student_semester:
                success_count += 1
        except Exception as e:
            click.secho(
                f"Failed to create semester for student {request.std_no}: {str(e)}",
                fg="red",
            )

    click.secho(
        f"\nCompleted! Successfully created {success_count} student semesters out of {len(approved_requests)} requests.",
        fg="green" if success_count == len(approved_requests) else "yellow",
    )


def create_student_semester_by_student_number(db: Session, std_no: int) -> None:
    """Create student semester for a specific approved student."""
    registration_request = (
        db.query(RegistrationRequest)
        .filter(RegistrationRequest.std_no == std_no)
        .filter(
            RegistrationRequest.id.in_(
                db.query(RegistrationClearance.registration_request_id)
                .filter(
                    RegistrationClearance.department.in_(["finance", "library"]),
                    RegistrationClearance.status == "approved",
                )
                .group_by(RegistrationClearance.registration_request_id)
                .having(func.count(RegistrationClearance.registration_request_id) == 2)
            )
        )
        .order_by(RegistrationRequest.id.desc())
        .first()
    )

    if not registration_request:
        click.secho(
            f"No approved registration request found for student {std_no}",
            fg="red",
        )
        return

    click.echo(f"Processing semester creation for student {std_no}")
    try:
        student_semester = create_student_semester_for_request(db, registration_request)
        # The success message is already shown by create_student_semester_for_request
    except Exception as e:
        click.secho(
            f"Failed to create semester for student {std_no}: {str(e)}", fg="red"
        )
