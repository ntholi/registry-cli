import time

import click
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.commands.enroll.crawler import Crawler
from registry_cli.models import (
    Module,
    Program,
    RegistrationRequest,
    RequestedModule,
    Structure,
    Student,
    StudentProgram,
)


def enroll_student(db: Session, request: RegistrationRequest) -> None:
    student = db.query(Student).filter(Student.std_no == request.std_no).first()
    if not student:
        raise ValueError(f"Student {request.std_no} not found")

    crawler = Crawler(db)
    result = (
        db.query(StudentProgram, Structure, Program)
        .join(Structure, StudentProgram.structure_id == Structure.id)
        .join(Program, Structure.program_id == Program.id)
        .filter(
            and_(
                StudentProgram.std_no == student.std_no,
                StudentProgram.status == "Active",
            )
        )
        .first()
    )
    if not result:
        raise ValueError(f"No active program found for student {student.std_no}")

    program, structure, program_details = result

    year = (request.semester_number - 1) // 2 + 1
    sem = (request.semester_number - 1) % 2 + 1
    semester_name = f"Year {year} Sem {sem}"

    semester_id = crawler.add_semester(
        school_id=program_details.school_id,
        program_id=program_details.id,
        structure_id=structure.id,
        std_program_id=program.id,
        semester=semester_name,
    )

    if not semester_id:
        raise RuntimeError("Failed to add semester")

    requested_modules = (
        db.query(Module)
        .join(RequestedModule)
        .filter(RequestedModule.registration_request_id == request.id)
        .all()
    )

    registered_module_codes = crawler.add_modules(semester_id, requested_modules)

    requested_module_records = (
        db.query(RequestedModule)
        .join(Module)
        .filter(
            RequestedModule.registration_request_id == request.id,
            Module.code.in_(registered_module_codes),
        )
        .all()
    )

    for module in requested_module_records:
        module.status = "registered"

    click.echo(f"Updated status for {len(requested_module_records)} registered modules")

    total_requested_modules = (
        db.query(RequestedModule)
        .filter(RequestedModule.registration_request_id == request.id)
        .count()
    )

    if len(requested_module_records) == total_requested_modules:
        request.status = "registered"
        click.secho("All modules were registered successfully", fg="green")
    elif len(requested_module_records) > 0:
        request.status = "partial"
        click.secho(
            f"Only {len(requested_module_records)} out of {total_requested_modules} modules were registered",
            fg="yellow",
        )

    request.updated_at = int(time.time())
    student.sem = request.semester_number
    db.commit()
