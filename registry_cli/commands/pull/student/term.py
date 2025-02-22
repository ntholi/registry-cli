import click
from sqlalchemy.orm import Session

from registry_cli.models import (
    Module,
    StudentModule,
    StudentProgram,
    StudentSemester,
)
from registry_cli.scrapers.student import (
    StudentModuleScraper,
    StudentSemesterScraper,
)


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
            
        module_scraper = StudentModuleScraper(semester.id)
        module_data = module_scraper.scrape()
        
        db.query(StudentModule).filter(
            StudentModule.student_semester_id == semester.id
        ).delete()
        db.commit()
        
        for mod in module_data:
            db_module = (
                db.query(Module)
                .filter(
                    # I did this because if a module has been deleted in the program structure
                    # that module will not show the code and name of that module when in the
                    # student academic/semesters/modules view
                    # Ideally this query should just be: filter(Module.code == mod["code"])
                    Module.id == int(mod["code"])
                    if mod["code"].isdigit()
                    else Module.code == mod["code"]
                )
                .first()
            )
            if not db_module:
                raise ValueError(f"Module with code {mod['code']} not found")
                
            module = StudentModule(
                id=mod["id"],
                status=mod["status"],
                marks=mod["marks"],
                grade=mod["grade"],
                module_id=db_module.id,
                semester=semester,
            )
            db.add(module)
        
        db.commit()
        click.echo(f"Successfully saved {len(module_data)} modules for term {term}")
        
    except Exception as e:
        db.rollback()
        click.echo(f"Error pulling modules for term {term}: {str(e)}", err=True)