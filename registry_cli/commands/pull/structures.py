import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.commands.pull.programs import program_pull
from registry_cli.models import (
    Module,
    ModulePrerequisite,
    Program,
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
        click.secho(
            f"Program {program_id} not found in database. Pulling program data first...",
            fg="red",
        )
        school_id = click.prompt("Enter the school ID", type=int)
        program_pull(db, school_id=school_id)
        program = db.query(Program).filter(Program.id == program_id).first()
        if not program:
            click.secho(
                f"Error: Program {program_id} not found after pulling programs. Please verify the program ID.",
                fg="red",
            )
            return

    url = f"{BASE_URL}/f_structurelist.php?showmaster=1&ProgramID={program_id}"
    scraper = ProgramStructureScraper(url)

    try:
        structures_data = scraper.scrape()
        if not structures_data:
            click.echo("No program structures found.")
            return

        modules_needing_prerequisites = []

        for structure_data in structures_data:
            structure = (
                db.query(Structure)
                .filter(Structure.id == int(structure_data["id"]))
                .first()
            )

            if not structure:
                structure = Structure(
                    id=int(structure_data["id"]),
                    code=structure_data["code"],
                    program_id=program_id,
                )
                db.add(structure)
            else:
                structure.code = structure_data["code"]
                structure.program_id = program_id

            semester_url = f"{BASE_URL}/f_semesterlist.php?showmaster=1&StructureID={structure_data['id']}"
            semester_scraper = SemesterScraper(semester_url)
            semesters_data = semester_scraper.scrape()

            for semester_data in semesters_data:
                semester = (
                    db.query(StructureSemester)
                    .filter(StructureSemester.id == semester_data["id"])
                    .first()
                )

                if not semester:
                    semester = StructureSemester(
                        id=semester_data["id"],
                        structure_id=structure.id,
                        name=semester_data["name"],
                        semester_number=semester_data["semester_number"],
                        total_credits=semester_data["total_credits"],
                    )
                    db.add(semester)
                else:
                    semester.structure_id = structure.id
                    semester.name = semester_data["name"]
                    semester.semester_number = semester_data["semester_number"]
                    semester.total_credits = semester_data["total_credits"]

                module_url = f"{BASE_URL}/f_semmodulelist.php?showmaster=1&SemesterID={semester_data['id']}"
                module_scraper = SemesterModuleScraper(module_url)
                modules_data = module_scraper.scrape()

                for module_data in modules_data:
                    module = (
                        db.query(Module).filter(Module.id == module_data["id"]).first()
                    )
                    if not module:
                        module = Module(
                            id=module_data["id"],
                            code=module_data["code"],
                            name=module_data["name"],
                            type=module_data["type"],
                            credits=module_data["credits"],
                            semester_id=semester.id,
                        )
                        db.add(module)
                    else:
                        module.code = module_data["code"]
                        module.name = module_data["name"]
                        module.type = module_data["type"]
                        module.credits = module_data["credits"]
                        module.semester_id = semester.id

                    if module_data.get("prerequisite_code"):
                        modules_needing_prerequisites.append(
                            {
                                "module": module,
                                "prerequisite_code": module_data["prerequisite_code"],
                            }
                        )
        db.flush()

        for item in modules_needing_prerequisites:
            module = item["module"]
            prerequisite_code = item["prerequisite_code"]

            prerequisite = (
                db.query(Module).filter(Module.code == prerequisite_code).first()
            )

            if prerequisite:
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
            else:
                click.secho(
                    f"Warning: Prerequisite module {prerequisite_code} not found in database",
                    fg="red",
                )

        db.commit()
        click.echo(
            f"Successfully added {len(structures_data)} program structures to the database."
        )

    except Exception as e:
        db.rollback()
        click.secho(f"Error pulling program structures: {str(e)}", fg="red")


def single_structure_pull(db: Session, structure_id: int) -> None:
    """
    Pull a specific structure by its ID, including semesters and modules.

    Args:
        db: Database session
        structure_id: ID of the structure to pull
    """
    structure = db.query(Structure).filter(Structure.id == structure_id).first()

    if not structure:
        click.secho(
            f"Structure {structure_id} not found in database. This will create a new structure record.",
            fg="yellow",
        )

    # We don't need to look up by program first since we have the structure ID directly
    semester_url = (
        f"{BASE_URL}/f_semesterlist.php?showmaster=1&StructureID={structure_id}"
    )
    semester_scraper = SemesterScraper(semester_url)

    try:
        semesters_data = semester_scraper.scrape()
        if not semesters_data:
            click.echo("No semesters found for this structure.")
            return

        if not structure:
            program_id = click.prompt(
                "Enter the program ID for this structure", type=int
            )

            structure = Structure(
                id=structure_id,
                code=click.prompt("Enter the structure code", type=str),
                program_id=program_id,
            )
            db.add(structure)
            db.flush()

        modules_needing_prerequisites = []

        for semester_data in semesters_data:
            semester = (
                db.query(StructureSemester)
                .filter(StructureSemester.id == semester_data["id"])
                .first()
            )

            if not semester:
                semester = StructureSemester(
                    id=semester_data["id"],
                    structure_id=structure.id,
                    name=semester_data["name"],
                    semester_number=semester_data["semester_number"],
                    total_credits=semester_data["total_credits"],
                )
                db.add(semester)
            else:
                semester.structure_id = structure.id
                semester.name = semester_data["name"]
                semester.semester_number = semester_data["semester_number"]
                semester.total_credits = semester_data["total_credits"]

            module_url = f"{BASE_URL}/f_semmodulelist.php?showmaster=1&SemesterID={semester_data['id']}"
            module_scraper = SemesterModuleScraper(module_url)
            modules_data = module_scraper.scrape()

            for module_data in modules_data:
                module = db.query(Module).filter(Module.id == module_data["id"]).first()
                if not module:
                    module = Module(
                        id=module_data["id"],
                        code=module_data["code"],
                        name=module_data["name"],
                        type=module_data["type"],
                        credits=module_data["credits"],
                        semester_id=semester.id,
                    )
                    db.add(module)
                else:
                    module.code = module_data["code"]
                    module.name = module_data["name"]
                    module.type = module_data["type"]
                    module.credits = module_data["credits"]
                    module.semester_id = semester.id

                if module_data.get("prerequisite_code"):
                    modules_needing_prerequisites.append(
                        {
                            "module": module,
                            "prerequisite_code": module_data["prerequisite_code"],
                        }
                    )

        db.flush()

        for item in modules_needing_prerequisites:
            module = item["module"]
            prerequisite_code = item["prerequisite_code"]

            prerequisite = (
                db.query(Module).filter(Module.code == prerequisite_code).first()
            )

            if prerequisite:
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
            else:
                click.secho(
                    f"Warning: Prerequisite module {prerequisite_code} not found in database",
                    fg="red",
                )

        db.commit()
        click.echo(
            f"Successfully pulled structure {structure_id} with all semesters and modules."
        )

    except Exception as e:
        db.rollback()
        click.secho(f"Error pulling structure: {str(e)}", fg="red")
