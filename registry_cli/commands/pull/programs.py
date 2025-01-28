import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models import Program
from registry_cli.scrapers.program import ProgramScraper


def program_pull(db: Session, school_id: int = 3) -> None:
    url = f"{BASE_URL}/f_programlist.php?showmaster=1&SchoolID={school_id}"
    scraper = ProgramScraper(url)

    try:
        programs_data = scraper.scrape()
        if not programs_data:
            click.echo("No programs found.")
            return

        for program_data in programs_data:
            program = Program(
                id=int(program_data["program_id"]),
                code=program_data["code"],
                name=program_data["name"],
            )
            db.add(program)

        db.commit()
        click.echo(f"Successfully added {len(programs_data)} programs to the database.")

    except Exception as e:
        click.echo(f"Error pulling programs: {str(e)}")
