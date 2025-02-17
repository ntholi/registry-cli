import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models import Program, School
from registry_cli.scrapers.program import ProgramScraper
from registry_cli.scrapers.schools import SchoolScraper


def program_pull(db: Session, school_id: int) -> None:
    if not school_id:
        raise ValueError("School ID is required.")

    # school = read_or_create_school(db, school_id)
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

            program_name: str = program_data["name"]
            program_level = None

            if program_name.lower().startswith("certificate"):
                program_level = "certificate"
            elif program_name.lower().startswith(
                "diploma"
            ) or program_name.lower().startswith("associate"):
                program_level = "diploma"
            else:
                program_level = "degree"

            if program:
                program.code = program_data["code"]
                program.name = program_name
                program.school_id = school_id
                program.level = program_level
                updated_count += 1
            else:
                program = Program(
                    id=program_id,
                    code=program_data["code"],
                    name=program_name,
                    school_id=school_id,
                    level=program_level,
                )
                db.add(program)
                added_count += 1

        db.commit()
        click.echo(
            f"Successfully updated {updated_count} and added {added_count} programs to the database."
        )

    except Exception as e:
        db.rollback()  # Rollback on error
        click.echo(f"Error pulling programs: {str(e)}")


def read_or_create_school(db: Session, school_id: int) -> School:
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        scraper = SchoolScraper(f"{BASE_URL}/f_schoollist.php?cmd=resetall")
        schools_data = scraper.scrape()
        if not schools_data:
            click.echo("No schools found.")
            return
        for school_data in schools_data:
            school = School(
                id=int(school_data["school_id"]),
                code=school_data["code"],
                name=school_data["name"],
            )
            db.add(school)
        db.commit()
        click.echo(f"Successfully added {len(schools_data)} schools.")
    school = db.query(School).filter(School.id == school_id).first()
    if not school:
        raise ValueError(f"School with ID {school_id} not found. even after scraping")
    return school
