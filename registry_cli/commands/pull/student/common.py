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
            # I did this because if a module has been deleted in the program structure
            # that module will not show the code and name of that module when in the
            # student academic/semesters/modules view
            # Ideally this query should just be: filter(Module.code == mod["code"])
            filter_query = Module.code == mod["code"]
            if mod["code"].isdigit():
                filter_query = Module.id == int(mod["code"])
            db_module = db.query(Module).filter(filter_query).first()
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
        click.echo(
            f"Successfully saved {len(module_data)} modules for semester {semester.term}"
        )
        return module_data
    except Exception as e:
        db.rollback()
        click.secho(f"Error scraping modules: {str(e)}", fg="red")
