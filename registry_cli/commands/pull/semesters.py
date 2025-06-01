from typing import Optional

import click
from sqlalchemy.orm import Session

from registry_cli.models import Program, Structure, StudentProgram, StudentSemester
from registry_cli.scrapers.student import StudentSemesterScraper

from .student.common import scrape_and_save_modules


def semesters_pull(
    db: Session, std_no: int, program_code: Optional[str] = None
) -> None:
    query = db.query(StudentProgram).filter(StudentProgram.std_no == std_no)

    if program_code:
        structure = (
            db.query(Structure)
            .join(Program, Structure.program_id == Program.id)
            .filter(Structure.code.like(f"{program_code}%"))
            .first()
        )
        if not structure:
            raise ValueError(f"Structure with code '{program_code}' not found")
        query = query.filter(StudentProgram.structure_id == structure.id)

    program = query.first()
    if not program:
        error_msg = f"No program found for student {std_no}"
        if program_code:
            error_msg += f" with structure code '{program_code}'"
        raise ValueError(error_msg)

    semester_scraper = StudentSemesterScraper(program.id)
    semester_data = semester_scraper.scrape()

    if not semester_data:
        click.secho("No semesters found.", fg="red")
        return

    db.query(StudentSemester).filter(
        StudentSemester.student_program_id == program.id
    ).delete()
    db.commit()

    for sem in semester_data:
        semester = StudentSemester(
            id=sem["id"],
            term=sem["term"],
            status=sem["status"],
            semester_number=sem["semester_number"],
            student_program_id=program.id,
        )
        db.add(semester)
        db.commit()

        scrape_and_save_modules(db, semester)

    click.echo(
        f"Successfully pulled {len(semester_data)} semesters for student {std_no}"
    )
