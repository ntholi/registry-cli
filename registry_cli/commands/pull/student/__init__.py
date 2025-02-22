import click
from sqlalchemy.orm import Session

from registry_cli.models import (
    Student,
    StudentProgram,
    StudentSemester,
)
from registry_cli.scrapers.student import (
    StudentProgramScraper,
    StudentScraper,
    StudentSemesterScraper,
)
from .common import scrape_and_save_modules
from .term import term_pull


def student_pull(db: Session, student_id: int) -> None:
    """Pull a student record from the registry system."""
    scraper = StudentScraper(student_id)

    try:
        student_data = scraper.scrape()
        student = (
            db.query(Student).filter(Student.std_no == student_data["std_no"]).first()
        )
        if student:
            for key, value in student_data.items():
                setattr(student, key, value)
        else:
            student = Student(**student_data)
            db.add(student)

        db.commit()
        click.echo(
            f"Successfully {'updated' if student else 'added'} student: {student}"
        )

        program_scraper = StudentProgramScraper(db, student_id)
        try:
            program_data = program_scraper.scrape()
            for prog in program_data:
                program = (
                    db.query(StudentProgram)
                    .filter(StudentProgram.id == prog["id"])
                    .first()
                )
                if program:
                    program.status = prog["status"]
                    program.structure_id = prog["structure_id"]
                    program.start_term = prog["start_term"]
                    program.stream = prog["stream"]
                    program.assist_provider = prog["assist_provider"]
                    program.std_no = student.std_no
                else:
                    program = StudentProgram(
                        id=prog["id"],
                        start_term=prog["start_term"],
                        structure_id=prog["structure_id"],
                        stream=prog["stream"],
                        status=prog["status"],
                        assist_provider=prog["assist_provider"],
                        std_no=student.std_no,
                    )
                    db.add(program)
                db.commit()

                try:
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
                            student_program_id=program.id,
                        )
                        db.add(semester)
                        db.commit()

                        try:
                            scrape_and_save_modules(db, semester)
                        except Exception as e:
                            click.echo(f"Error scraping modules: {str(e)}", err=True)

                    click.echo(
                        f"Successfully pulled {len(semester_data)} semesters for program: {program.id}"
                    )

                except Exception as e:
                    db.rollback()
                    click.echo(
                        f"Error pulling semester data for program {program.id}: {str(e)}"
                    )

            click.echo(
                f"Successfully pulled {len(program_data)} programs for student: {student}"
            )

        except Exception as e:
            db.rollback()
            click.echo(f"Error pulling student program data: {str(e)}")

    except Exception as e:
        db.rollback()
        click.echo(f"Error pulling student data: {str(e)}")
