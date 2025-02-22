import click
from sqlalchemy.orm import Session

from registry_cli.models import StudentProgram, StudentSemester
from .common import scrape_and_save_modules

def term_pull(db: Session, student_id: int, term: str) -> None:
    """Pull student modules for a specific term."""
    try:
        program = db.query(StudentProgram).filter(
            StudentProgram.std_no == student_id
        ).first()
        
        if not program:
            raise ValueError(f"No program found for student {student_id}")
            
        semester = db.query(StudentSemester).filter(
            StudentSemester.student_program_id == program.id,
            StudentSemester.term == term
        ).first()
        
        if not semester:
            raise ValueError(f"No semester found for term {term}")
            
        scrape_and_save_modules(db, semester)
        
    except Exception as e:
        db.rollback()
        click.echo(f"Error pulling modules for term {term}: {str(e)}", err=True)