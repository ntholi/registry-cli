import click
from sqlalchemy.orm import Session

from registry_cli.models import Student, StudentProgram, StudentSemester
from registry_cli.scrapers.student import (
    StudentProgramScraper,
    StudentScraper,
    StudentSemesterScraper,
)

from .common import scrape_and_save_modules


def student_pull(db: Session, std_no: int, info_only: bool = False) -> bool:
    """Pull a student record from the registry system."""
    scraper = StudentScraper(std_no)
    student_data = scraper.scrape()
    student = db.query(Student).filter(Student.std_no == student_data["std_no"]).first()
    if student:
        for key, value in student_data.items():
            setattr(student, key, value)
    else:
        student = Student(**student_data)
        db.add(student)
    db.commit()
    click.echo(f"Successfully {'updated' if student else 'added'} student: {student}")
    if info_only:
        return True
    program_scraper = StudentProgramScraper(db, std_no)
    program_data = program_scraper.scrape()
    for prog in program_data:
        program = (
            db.query(StudentProgram).filter(StudentProgram.id == prog["id"]).first()
        )
        if program:
            program.std_no = student.std_no
            for key, value in prog.items():
                setattr(program, key, value)
        else:
            program = StudentProgram(**prog)
            program.std_no = student.std_no
            db.add(program)
        db.commit()
        semester_scraper = StudentSemesterScraper(program.id)
        semester_data = semester_scraper.scrape()
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
                caf_date=sem["caf_date"],
                student_program_id=program.id,
            )
            db.add(semester)
            db.commit()
            scrape_and_save_modules(db, semester)
        click.echo(
            f"Successfully pulled {len(semester_data)} semesters for program: {program.id}"
        )
    click.echo(
        f"Successfully pulled {len(program_data)} programs for student: {student}"
    )
    return True
