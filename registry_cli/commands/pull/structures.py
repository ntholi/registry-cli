import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models.structure import Semester, Structure
from registry_cli.scrapers.structure import ProgramStructureScraper, SemesterScraper


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

            # Scrape semesters for this structure
            semester_url = f"{BASE_URL}/f_semesterlist.php?showmaster=1&StructureID={structure_data['id']}"
            semester_scraper = SemesterScraper(semester_url)
            semesters_data = semester_scraper.scrape()

            for semester_data in semesters_data:
                semester = Semester(
                    id=semester_data["id"],
                    structure_id=structure.id,
                    year=semester_data["year"],
                    semester_number=semester_data["semester_number"],
                    total_credits=semester_data["total_credits"],
                )
                db.add(semester)

        db.commit()
        click.echo(
            f"Successfully added {len(structures_data)} program structures to the database."
        )

    except Exception as e:
        click.echo(f"Error pulling program structures: {str(e)}")
