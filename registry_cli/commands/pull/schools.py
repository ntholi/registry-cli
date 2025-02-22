import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.commands.pull.programs import program_pull
from registry_cli.commands.pull.structures import structure_pull
from registry_cli.models import Program, School
from registry_cli.scrapers.schools import SchoolScraper


def school_pull(db: Session) -> None:
    url = f"{BASE_URL}/f_schoollist.php?cmd=resetall"
    scraper = SchoolScraper(url)

    try:
        schools_data = scraper.scrape()
        if not schools_data:
            click.echo("No schools found.")
            return

        updated_count = 0
        added_count = 0
        for school_data in schools_data:
            school_id = int(school_data["school_id"])
            school = db.query(School).filter(School.id == school_id).first()

            if school:
                school.code = school_data["code"]
                school.name = school_data["name"]
                updated_count += 1
            else:
                school = School(
                    id=school_id,
                    code=school_data["code"],
                    name=school_data["name"],
                )
                db.add(school)
                added_count += 1

            # Pull programs for this school
            click.echo(f"\nPulling programs for school {school_data['name']}...")
            program_pull(db, school_id)

            # Pull structures for each program
            programs = db.query(Program).filter(Program.school_id == school_id).all()
            for program in programs:
                click.echo(f"\nPulling structures for program {program.name}...")
                structure_pull(db, program.id)

        db.commit()
        click.echo(f"\nSummary:")
        click.echo(f"- Updated {updated_count} and added {added_count} schools")

    except Exception as e:
        db.rollback()
        click.secho(f"Error pulling schools: {str(e)}", fg="red")
