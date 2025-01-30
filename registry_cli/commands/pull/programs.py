import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models import Program
from registry_cli.scrapers.program import ProgramScraper


def program_pull(db: Session, school_id: int) -> None:
    if not school_id:
        raise ValueError("School ID is required.")
    url = f"{BASE_URL}/f_programlist.php?showmaster=1&SchoolID={school_id}"
    scraper = ProgramScraper(url)

    try:
        programs_data = scraper.scrape()
        if not programs_data:
            click.echo("No programs found.")
            return

        updated_count = 0
        added_count = 0
        for program_data in programs_data:
            program_id = int(program_data["program_id"])
            program = db.query(Program).filter(Program.id == program_id).first()
            
            if program:
                program.code = program_data["code"]
                program.name = program_data["name"]
                updated_count += 1
            else:
                program = Program(
                    id=program_id,
                    code=program_data["code"],
                    name=program_data["name"],
                )
                db.add(program)
                added_count += 1

        db.commit()
        click.echo(f"Successfully updated {updated_count} and added {added_count} programs to the database.")

    except Exception as e:
        click.echo(f"Error pulling programs: {str(e)}")
