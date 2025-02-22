import time

from sqlalchemy import and_
from sqlalchemy.orm import Session
import click

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


def enroll_student(db: Session, request: RegistrationRequest) -> bool:
    student = db.query(Student).filter(Student.std_no == request.std_no).first()
    if not student:
        click.secho(f"Student {request.std_no} not found", fg="red")
        return False

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
        click.secho(f"No active program found for student {student.std_no}", fg="red")
        return False

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

    if semester_id:
        requested_modules = (
            db.query(Module)
            .join(RequestedModule)
            .filter(RequestedModule.registration_request_id == request.id)
            .all()
        )
        crawler.add_modules(semester_id, requested_modules)

        # TODO: Update Semester Number
        request.status = "registered"
        request.updated_at = int(time.time())
        db.commit()
        return True

    return False
