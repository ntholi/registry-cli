from typing import Any, Dict, List

import click
from sqlalchemy.orm import Session

from registry_cli.models import Module, StudentModule, StudentSemester
from registry_cli.scrapers.student import StudentModuleScraper


def scrape_and_save_modules(db: Session, semester: StudentSemester):
    """Scrape and save modules for a given semester."""
    module_scraper = StudentModuleScraper(semester.id)
    try:
        module_data = module_scraper.scrape()
        db.query(StudentModule).filter(
            StudentModule.student_semester_id == semester.id
        ).delete()
        db.commit()

        for mod in module_data:
            try:
                module = StudentModule(
                    id=mod["id"],
                    status=mod["status"],
                    marks=mod["marks"],
                    grade=mod["grade"],
                    semester_module_id=mod["semester_module_id"],
                    semester=semester,
                )
                db.add(module)
            except Exception as e:
                db.rollback()
                click.secho(
                    f"Error processing module {mod.get('code', 'unknown')}: {str(e)}",
                    fg="red",
                )
                continue

        db.commit()
        click.echo(f"Successfully saved modules for semester {semester.term}")
        return module_data
    except Exception as e:
        db.rollback()
        click.secho(f"Error scraping modules: {str(e)}", fg="red")
