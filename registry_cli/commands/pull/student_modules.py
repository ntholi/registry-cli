import click
from sqlalchemy.orm import Session

from registry_cli.models import StudentProgram, StudentSemester
from registry_cli.scrapers.student import StudentSemesterScraper

from .student.common import scrape_and_save_modules


def student_modules_pull(db: Session, std_no: int, term: str) -> None:
    """Pull student modules for a specific term and create or update the semester."""
    try:
        program = (
            db.query(StudentProgram).filter(StudentProgram.std_no == std_no).first()
        )

        if not program:
            raise ValueError(f"No program found for student {std_no}")

        semester = (
            db.query(StudentSemester)
            .filter(
                StudentSemester.student_program_id == program.id,
                StudentSemester.term == term,
            )
            .first()
        )

        if not semester:
            click.echo(f"No semester found for term {term}, creating it...")

            semester_scraper = StudentSemesterScraper(program.id)
            semesters_data = semester_scraper.scrape()

            matching_semester = next(
                (s for s in semesters_data if s["term"] == term), None
            )

            if not matching_semester:
                raise ValueError(
                    f"No semester with term {term} found in student program {program.id}"
                )

            semester = StudentSemester(
                id=matching_semester["id"],
                term=matching_semester["term"],
                status=matching_semester["status"],
                semester_number=matching_semester["semester_number"],
                student_program_id=program.id,
            )
            db.add(semester)
            db.commit()
            click.echo(f"Created semester {term} for student {std_no}")
        else:
            click.echo(
                f"Found existing semester {term} for student {std_no}, updating modules..."
            )

        scrape_and_save_modules(db, semester)
        click.echo(f"Successfully updated modules for student {std_no}, term {term}")

    except Exception as e:
        db.rollback()
        click.secho(
            f"Error processing student {std_no}, term {term}: {str(e)}",
            fg="red",
            err=True,
        )
