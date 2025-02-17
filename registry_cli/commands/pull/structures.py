import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.commands.pull.programs import program_pull
from registry_cli.models import (
    Module,
    ModulePrerequisite,
    Program,
    SemesterModule,
    Structure,
    StructureSemester,
)
from registry_cli.scrapers.structure import (
    ProgramStructureScraper,
    SemesterModuleScraper,
    SemesterScraper,
)


def structure_pull(db: Session, program_id: int) -> None:
    program = db.query(Program).filter(Program.id == program_id).first()
    if not program:
        click.echo(
            f"Program {program_id} not found in database. Pulling program data first..."
        )
        school_id = click.prompt("Enter the school ID", type=int)
        program_pull(db, school_id=school_id)
        program = db.query(Program).filter(Program.id == program_id).first()
        if not program:
            click.echo(
                f"Error: Program {program_id} not found after pulling programs. Please verify the program ID."
            )
            return

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
                semester = StructureSemester(
                    id=semester_data["id"],
                    structure_id=structure.id,
                    name=semester_data["name"],
                    semester_number=semester_data["semester_number"],
                    total_credits=semester_data["total_credits"],
                )
                db.add(semester)

                # Scrape modules for this semester
                module_url = f"{BASE_URL}/f_semmodulelist.php?showmaster=1&SemesterID={semester_data['id']}"
                module_scraper = SemesterModuleScraper(module_url)
                modules_data = module_scraper.scrape()

                for module_data in modules_data:
                    module = (
                        db.query(Module)
                        .filter(Module.code == module_data["code"])
                        .first()
                    )
                    if not module:
                        module = Module(
                            id=module_data["id"],
                            code=module_data["code"],
                            name=module_data["name"],
                            type=module_data["type"],
                            credits=module_data["credits"],
                        )
                        db.add(module)

                    semester_module = SemesterModule(
                        semester_id=semester.id,
                        module_id=module.id,
                    )
                    db.add(semester_module)

                    # Handle prerequisites
                    if module_data.get("prerequisite_code"):
                        prerequisite = (
                            db.query(Module)
                            .filter(Module.code == module_data["prerequisite_code"])
                            .first()
                        )
                        if prerequisite:
                            # Check if prerequisite already exists
                            existing_prerequisite = (
                                db.query(ModulePrerequisite)
                                .filter(
                                    ModulePrerequisite.module_id == module.id,
                                    ModulePrerequisite.prerequisite_id == prerequisite.id,
                                )
                                .first()
                            )
                            if not existing_prerequisite:
                                module_prerequisite = ModulePrerequisite(
                                    module_id=module.id,
                                    prerequisite_id=prerequisite.id,
                                )
                                db.add(module_prerequisite)

        db.commit()
        click.echo(
            f"Successfully added {len(structures_data)} program structures to the database."
        )

    except Exception as e:
        db.rollback()
        click.echo(f"Error pulling program structures: {str(e)}")
