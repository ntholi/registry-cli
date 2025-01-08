import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models.structure import Structure
from registry_cli.scrapers.structure import ProgramStructureScraper


def structure_pull(db: Session, program_id: int) -> None:
    url = f"{BASE_URL}/f_structurelist.php?showmaster=1&ProgramID={program_id}"
    scraper = ProgramStructureScraper(url)

    try:
        structures_data = scraper.scrape()
        if not structures_data:
            click.echo("No program structures found.")
            return

        for structure_data in structures_data:
            structure = Structure(
                id=int(structure_data["id"]),
                code=structure_data["code"],
                program_id=program_id,
            )
            db.add(structure)

        db.commit()
        click.echo(
            f"Successfully added {len(structures_data)} program structures to the database."
        )

    except Exception as e:
        click.echo(f"Error pulling program structures: {str(e)}")
