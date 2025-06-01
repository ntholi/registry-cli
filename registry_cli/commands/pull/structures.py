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


def _process_modules_and_prerequisites(
    db: Session, semester: StructureSemester, modules_data: list
) -> None:
    """Helper function to process modules and their prerequisites for a semester."""
    semester_modules_needing_prerequisites = []

    for module_data in modules_data:
        if module_data["code"].isdigit():
            base_module = (
                db.query(Module).filter(Module.id == module_data["code"]).first()
            )
        else:
            base_module = (
                db.query(Module).filter(Module.code == module_data["code"]).first()
            )
        if not base_module:
            raise ValueError(
                f"Module with code '{module_data['code']}' not found in database"
            )

        semester_module = (
            db.query(SemesterModule)
            .filter(SemesterModule.id == module_data["id"])
            .first()
        )
        if not semester_module:
            semester_module = SemesterModule(
                id=module_data["id"],
                module_id=base_module.id,
                type=module_data["type"],
                credits=module_data["credits"],
                semester_id=semester.id,
            )
            db.add(semester_module)
        else:
            semester_module.module_id = base_module.id
            semester_module.type = module_data["type"]
            semester_module.credits = module_data["credits"]
            semester_module.semester_id = semester.id

        if module_data.get("prerequisite_code"):
            semester_modules_needing_prerequisites.append(
                {
                    "semester_module": semester_module,
                    "prerequisite_code": module_data["prerequisite_code"],
                }
            )

    db.commit()

    for item in semester_modules_needing_prerequisites:
        semester_module = item["semester_module"]
        prerequisite_code = item["prerequisite_code"]

        prerequisite = db.query(Module).filter(Module.code == prerequisite_code).first()

        if prerequisite:
            prerequisite_sem_module = (
                db.query(SemesterModule)
                .filter(SemesterModule.module_id == prerequisite.id)
                .first()
            )

            if prerequisite_sem_module:
                existing_prerequisite = (
                    db.query(ModulePrerequisite)
                    .filter(
                        ModulePrerequisite.semester_module_id == semester_module.id,
                        ModulePrerequisite.prerequisite_id
                        == prerequisite_sem_module.id,
                    )
                    .first()
                )
                if not existing_prerequisite:
                    module_prerequisite = ModulePrerequisite(
                        semester_module_id=semester_module.id,
                        prerequisite_id=prerequisite_sem_module.id,
                    )
                    db.add(module_prerequisite)
            else:
                click.secho(
                    f"Warning: Prerequisite semester module for {prerequisite_code} not found in database",
                    fg="yellow",
                )
        else:
            click.secho(
                f"Warning: Prerequisite module {prerequisite_code} not found in database",
                fg="red",
            )

    db.commit()


def _process_semesters(db: Session, structure: Structure, structure_id: int) -> bool:
    """Helper function to process semesters and their modules for a structure."""
    semester_url = (
        f"{BASE_URL}/f_semesterlist.php?showmaster=1&StructureID={structure_id}"
    )
    semester_scraper = SemesterScraper(semester_url)
    semesters_data = semester_scraper.scrape()

    if not semesters_data:
        click.echo("No semesters found for this structure.")
        return False

    for i, semester_data in enumerate(semesters_data, 1):
        try:
            click.echo(
                f"  Processing semester {i}/{len(semesters_data)}: {semester_data['name']}"
            )

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

            db.commit()

            module_url = f"{BASE_URL}/f_semmodulelist.php?showmaster=1&SemesterID={semester_data['id']}"
            module_scraper = SemesterModuleScraper(module_url)
            modules_data = module_scraper.scrape()

            if modules_data:
                click.echo(f"    Processing {len(modules_data)} modules...")
                _process_modules_and_prerequisites(db, semester, modules_data)
                click.echo(
                    f"    Completed modules for semester {semester_data['name']}"
                )

        except Exception as e:
            db.rollback()
            click.secho(
                f"    Error processing semester {semester_data['name']}: {str(e)}",
                fg="red",
            )
            continue

    return True


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

        successful_structures = 0
        total_structures = len(structures_data)

        for i, structure_data in enumerate(structures_data, 1):
            try:
                click.echo(
                    f"Processing structure {i}/{total_structures}: {structure_data['code']}"
                )

                structure = (
                    db.query(Structure)
                    .filter(Structure.id == int(structure_data["id"]))
                    .first()
                )

                if not structure:
                    structure = Structure(
                        id=int(structure_data["id"]),
                        code=structure_data["code"],
                        desc=structure_data["desc"],
                        program_id=program_id,
                    )
                    db.add(structure)
                else:
                    structure.code = structure_data["code"]
                    structure.desc = structure_data["desc"]
                    structure.program_id = program_id

                db.commit()

                if _process_semesters(db, structure, int(structure_data["id"])):
                    successful_structures += 1
                    click.echo(f"Completed structure {structure_data['code']}")
                else:
                    click.secho(
                        f"No semesters found for structure {structure_data['code']}",
                        fg="yellow",
                    )

            except Exception as e:
                db.rollback()
                click.secho(
                    f"Error processing structure {structure_data['code']}: {str(e)}",
                    fg="red",
                )
                continue

        click.echo(
            f"Successfully processed {successful_structures}/{total_structures} program structures."
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
    try:
        structure = db.query(Structure).filter(Structure.id == structure_id).first()

        if not structure:
            click.secho(
                f"Structure {structure_id} not found in database. This will create a new structure record.",
                fg="yellow",
            )
            program_id = click.prompt(
                "Enter the program ID for this structure", type=int
            )

            structure = Structure(
                id=structure_id,
                code=click.prompt("Enter the structure code", type=str),
                program_id=program_id,
            )
            db.add(structure)
            db.commit()

        if _process_semesters(db, structure, structure_id):
            click.echo(
                f"Successfully pulled structure {structure_id} with all semesters and modules."
            )
        else:
            click.secho(f"No semesters found for structure {structure_id}", fg="yellow")

    except Exception as e:
        db.rollback()
        click.secho(f"Error pulling structure: {str(e)}", fg="red")
