from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.commands.enroll.crawler import Crawler
from registry_cli.models import (
    Program,
    RegistrationClearance,
    RegistrationRequest,
    Structure,
    Student,
    StudentProgram,
)


def enroll_approved(db: Session) -> None:
    crawler = Crawler(db)

    approved_requests = (
        db.query(RegistrationRequest)
        .join(RegistrationClearance)
        .filter(
            and_(
                RegistrationClearance.department == "finance",
                RegistrationClearance.status == "approved",
            )
        )
        .all()
    )

    for request in approved_requests:
        student = db.query(Student).filter(Student.std_no == request.std_no).first()
        if not student:
            continue

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
            continue

        program, structure, program_details = result

        year = (request.semester_number - 1) // 2 + 1
        sem = (request.semester_number - 1) % 2 + 1
        semester_name = f"Year {year} Sem {sem}"

        print(
            "school_id=",
            program_details.school_id,
            ", program_id=",
            program_details.id,
            " structure_id=",
            structure.id,
            ", std_program_id=",
            program.id,
            ", semester=",
            semester_name,
        )
        crawler.add_semester(
            school_id=program_details.school_id,
            program_id=program_details.id,
            structure_id=structure.id,
            std_program_id=program.id,
            semester=semester_name,
        )
