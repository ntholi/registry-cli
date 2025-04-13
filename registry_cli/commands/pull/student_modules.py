import click
from sqlalchemy.orm import Session

from registry_cli.models import StudentProgram, StudentSemester

from .student.common import scrape_and_save_modules


def student_modules_pull(db: Session, std_no: int, term: str) -> None:
    """Pull student modules for a specific term."""
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
            raise ValueError(f"No semester found for term {term}")

        scrape_and_save_modules(db, semester)

    except Exception as e:
        db.rollback()
        click.secho(
            f"Error pulling modules for term {term}: {str(e)}", fg="red", err=True
        )
