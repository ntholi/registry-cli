from typing import Optional

import click
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.models import (
    Clearance,
    GraduationClearance,
    GraduationRequest,
    Program,
    Student,
    StudentProgram,
)
from registry_cli.utils.certificate_generator import generate_certificate


def _get_active_or_completed_program(
    db: Session, std_no: int
) -> Optional[StudentProgram]:
    return (
        db.query(StudentProgram)
        .filter(
            StudentProgram.std_no == std_no,
            StudentProgram.status.in_(["Active", "Completed"]),
        )
        .order_by(StudentProgram.id.desc())
        .first()
    )


def _has_approved_academic_graduation(db: Session, student_program_id: int) -> bool:
    result = (
        db.query(GraduationRequest)
        .join(
            GraduationClearance,
            GraduationRequest.id == GraduationClearance.graduation_request_id,
        )
        .join(Clearance, GraduationClearance.clearance_id == Clearance.id)
        .filter(
            GraduationRequest.student_program_id == student_program_id,
            and_(Clearance.department == "academic", Clearance.status == "approved"),
        )
        .first()
    )
    return result is not None


def create_student_certificate(db: Session, std_no: int) -> Optional[str]:
    """Create a graduation certificate for a student if graduation request is approved academically."""
    student = db.query(Student).filter(Student.std_no == std_no).first()
    if not student:
        click.secho(f"Student {std_no} not found", fg="red")
        return None

    graduation_request = (
        db.query(GraduationRequest)
        .join(StudentProgram, GraduationRequest.student_program_id == StudentProgram.id)
        .filter(StudentProgram.std_no == std_no)
        .order_by(GraduationRequest.id.desc())
        .first()
    )
    if not graduation_request:
        click.secho("No graduation request found for student", fg="red")
        return None

    student_program: StudentProgram = graduation_request.student_program  # type: ignore

    if not _has_approved_academic_graduation(db, student_program.id):
        click.secho(
            "Student's graduation request does not have an approved academic clearance.",
            fg="yellow",
        )
        return None

    program = (
        db.query(Program)
        .filter(Program.id == student_program.structure.program_id)
        .first()
    )
    if not program:
        click.secho("Program not found", fg="red")
        return None

    path = generate_certificate(student.name, program.name)
    if path:
        click.secho(f"Certificate generated: {path}", fg="green")
    else:
        click.secho("Failed to generate certificate", fg="red")
    return path


@click.command(name="certificate")
@click.argument("std_no", type=int)
def certificate_cmd(std_no: int) -> None:
    from registry_cli.main import get_db

    db = get_db()
    create_student_certificate(db, std_no)
