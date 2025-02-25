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

        if info_only:
            return True

        program_scraper = StudentProgramScraper(db, std_no)
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
                            click.secho(f"Error scraping modules: {str(e)}", fg="red")
                            return False

                    click.echo(
                        f"Successfully pulled {len(semester_data)} semesters for program: {program.id}"
                    )

                except Exception as e:
                    db.rollback()
                    click.secho(
                        f"Error pulling semester data for program {program.id}: {str(e)}",
                        fg="red",
                    )
                    return False

            click.echo(
                f"Successfully pulled {len(program_data)} programs for student: {student}"
            )

        except Exception as e:
            db.rollback()
            click.secho(f"Error pulling student program data: {str(e)}", fg="red")
            return False

    except Exception as e:
        db.rollback()
        click.secho(f"Error pulling student data: {str(e)}", fg="red")
        return False

    return True
