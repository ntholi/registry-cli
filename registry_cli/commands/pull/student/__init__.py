import click
from sqlalchemy.orm import Session

from registry_cli.models import Student, StudentProgram, StudentSemester
from registry_cli.scrapers.student.concurrent import ConcurrentStudentDataCollector
from registry_cli.scrapers.student.program import StudentProgramScraper
from registry_cli.scrapers.student.semester import StudentSemesterScraper
from registry_cli.scrapers.student.student import StudentScraper

from .common import save_semesters_and_modules_batch, scrape_and_save_modules


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

    if not program_data:
        click.echo("No programs found for student")
        return True

    collector = ConcurrentStudentDataCollector()

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

        click.echo(f"Collecting semester and module data for program: {program.id}")
        program_data_collected = collector.collect_program_data(program.id)

        semesters_data = program_data_collected["semesters"]
        modules_by_semester = program_data_collected["modules_by_semester"]

        if semesters_data:
            save_semesters_and_modules_batch(
                db, program, semesters_data, modules_by_semester
            )
        else:
            click.echo(f"No semesters found for program: {program.id}")

    click.echo(
        f"Successfully pulled {len(program_data)} programs for student: {student}"
    )
    return True
