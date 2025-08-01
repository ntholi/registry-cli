from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.commands.pull.programs import program_pull
from registry_cli.models import (
    Module,
    Program,
    SemesterModule,
    Structure,
    StructureSemester,
)
from registry_cli.scrapers.structure import (
    ConcurrentStructureDataCollector,
    ProgramStructureScraper,
)


@dataclass
class StructureData:
    """Complete structure data including semesters and modules."""

    structure_info: Dict[str, str]
    semesters: List[Dict[str, Any]]
    modules_by_semester: Dict[int, List[Dict[str, Any]]]


class StructureDataProcessor:
    """Processes and validates structure data before database persistence."""

    def __init__(self, db: Session):
        self.db = db

    def validate_and_process_modules(
        self, modules_data: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Validate and process module data, ensuring all referenced modules exist."""
        validated_modules = []

        for module_data in modules_data:
            if module_data["code"].isdigit():
                base_module = (
                    self.db.query(Module)
                    .filter(Module.id == module_data["code"])
                    .first()
                )
            else:
                base_module = (
                    self.db.query(Module)
                    .filter(Module.code == module_data["code"])
                    .first()
                )

            if not base_module:
                click.secho(
                    f"Warning: Module with code '{module_data['code']}' not found in database. Skipping.",
                    fg="yellow",
                )
                continue

            module_data["base_module_id"] = base_module.id
            validated_modules.append(module_data)

        return validated_modules

    def save_structure_data(
        self, structure_data: StructureData, program_id: int
    ) -> bool:
        """Save complete structure data to database in a single transaction."""
        try:
            structure_info = structure_data.structure_info

            structure = (
                self.db.query(Structure)
                .filter(Structure.id == int(structure_info["id"]))
                .first()
            )

            if not structure:
                structure = Structure(
                    id=int(structure_info["id"]),
                    code=structure_info["code"],
                    desc=structure_info.get("desc", ""),
                    program_id=program_id,
                )
                self.db.add(structure)
            else:
                structure.code = structure_info["code"]
                structure.desc = structure_info.get("desc", "")
                structure.program_id = program_id

            self.db.flush()

            for semester_data in structure_data.semesters:
                semester = self._save_semester(structure, semester_data)
                modules_data = structure_data.modules_by_semester.get(
                    semester_data["id"], []
                )

                if modules_data:
                    validated_modules = self.validate_and_process_modules(modules_data)
                    self._save_modules(semester, validated_modules)

            self.db.commit()
            return True

        except Exception as e:
            self.db.rollback()
            click.secho(f"Error saving structure data: {str(e)}", fg="red")
            return False

    def _save_semester(
        self, structure: Structure, semester_data: Dict[str, Any]
    ) -> StructureSemester:
        """Save semester data."""
        semester = (
            self.db.query(StructureSemester)
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
            self.db.add(semester)
        else:
            semester.structure_id = structure.id
            semester.name = semester_data["name"]
            semester.semester_number = semester_data["semester_number"]
            semester.total_credits = semester_data["total_credits"]

        self.db.flush()
        return semester

    def _save_modules(
        self, semester: StructureSemester, modules_data: List[Dict[str, Any]]
    ) -> None:
        """Save modules for a semester."""
        for module_data in modules_data:
            semester_module = (
                self.db.query(SemesterModule)
                .filter(SemesterModule.id == module_data["id"])
                .first()
            )

            if not semester_module:
                semester_module = SemesterModule(
                    id=module_data["id"],
                    module_id=module_data["base_module_id"],
                    type=module_data["type"],
                    credits=module_data["credits"],
                    semester_id=semester.id,
                )
                self.db.add(semester_module)
            else:
                semester_module.module_id = module_data["base_module_id"]
                semester_module.type = module_data["type"]
                semester_module.credits = module_data["credits"]
                semester_module.semester_id = semester.id

        self.db.flush()


class ConcurrentStructurePuller:
    """Main class for concurrent structure data pulling and persistence."""

    def __init__(self, db: Session, max_workers: int = 5):
        self.db = db
        self.data_collector = ConcurrentStructureDataCollector(max_workers)
        self.data_processor = StructureDataProcessor(db)

    def pull_structures_for_program(self, program_id: int) -> None:
        """Pull all structures for a program with concurrent data fetching."""
        program = self.db.query(Program).filter(Program.id == program_id).first()
        if not program:
            click.secho(
                f"Program {program_id} not found in database. Pulling program data first...",
                fg="red",
            )
            school_id = click.prompt("Enter the school ID", type=int)
            program_pull(self.db, school_id=school_id)
            program = self.db.query(Program).filter(Program.id == program_id).first()
            if not program:
                click.secho(
                    f"Error: Program {program_id} not found after pulling programs. Please verify the program ID.",
                    fg="red",
                )
                return

        url = f"{BASE_URL}/f_structurelist.php?showmaster=1&ProgramID={program_id}"
        scraper = ProgramStructureScraper(url)

        try:
            structures_list = scraper.scrape()
            if not structures_list:
                click.echo("No program structures found.")
                return

            successful_structures = 0
            total_structures = len(structures_list)

            for i, structure_info in enumerate(structures_list, 1):
                try:
                    click.echo(
                        f"Processing structure {i}/{total_structures}: {structure_info['code']}"
                    )

                    structure_data = self._collect_and_validate_structure_data(
                        structure_info
                    )

                    if self.data_processor.save_structure_data(
                        structure_data, program_id
                    ):
                        successful_structures += 1
                        click.echo(f"✓ Completed structure {structure_info['code']}")
                    else:
                        click.secho(
                            f"✗ Failed to save structure {structure_info['code']}",
                            fg="red",
                        )

                except Exception as e:
                    click.secho(
                        f"✗ Error processing structure {structure_info['code']}: {str(e)}",
                        fg="red",
                    )
                    continue

            click.echo(
                f"Successfully processed {successful_structures}/{total_structures} program structures."
            )

        except Exception as e:
            click.secho(f"Error pulling program structures: {str(e)}", fg="red")

    def pull_single_structure(self, structure_id: int) -> None:
        """Pull a specific structure by its ID with concurrent data fetching."""
        try:
            structure = (
                self.db.query(Structure).filter(Structure.id == structure_id).first()
            )

            if not structure:
                click.secho(
                    f"Structure {structure_id} not found in database. This will create a new structure record.",
                    fg="yellow",
                )
                program_id = click.prompt(
                    "Enter the program ID for this structure", type=int
                )
                code = click.prompt("Enter the structure code", type=str)
                desc = click.prompt(
                    "Enter the structure description", type=str, default=""
                )

                structure_info = {"id": str(structure_id), "code": code, "desc": desc}
            else:
                structure_info = {
                    "id": str(structure.id),
                    "code": structure.code,
                    "desc": structure.desc or "",
                }
                program_id = structure.program_id

            click.echo(f"Collecting data for structure {structure_id}...")
            collected_data = self.data_collector.collect_structure_data(
                str(structure_id)
            )

            if not collected_data["semesters"]:
                click.secho(
                    f"No semesters found for structure {structure_id}", fg="yellow"
                )
                return

            structure_data = StructureData(
                structure_info=structure_info,
                semesters=collected_data["semesters"],
                modules_by_semester=collected_data["modules_by_semester"],
            )

            if self.data_processor.save_structure_data(structure_data, program_id):
                click.echo(
                    f"✓ Successfully pulled structure {structure_id} with all semesters and modules."
                )
            else:
                click.secho(f"✗ Failed to save structure {structure_id}", fg="red")

        except Exception as e:
            click.secho(f"Error pulling structure: {str(e)}", fg="red")

    def _collect_and_validate_structure_data(
        self, structure_info: Dict[str, str]
    ) -> StructureData:
        """Collect and validate all data for a structure."""
        click.echo(
            f"  Collecting concurrent data for structure {structure_info['code']}..."
        )

        collected_data = self.data_collector.collect_structure_data(
            structure_info["id"]
        )

        total_modules = sum(
            len(modules) for modules in collected_data["modules_by_semester"].values()
        )
        click.echo(
            f"  Found {len(collected_data['semesters'])} semesters and {total_modules} modules"
        )

        return StructureData(
            structure_info=structure_info,
            semesters=collected_data["semesters"],
            modules_by_semester=collected_data["modules_by_semester"],
        )


def structure_pull(db: Session, program_id: int) -> None:
    """Pull all structures for a program using concurrent data fetching."""
    puller = ConcurrentStructurePuller(db)
    puller.pull_structures_for_program(program_id)


def single_structure_pull(db: Session, structure_id: int) -> None:
    """Pull a specific structure by its ID using concurrent data fetching."""
    puller = ConcurrentStructurePuller(db)
    puller.pull_single_structure(structure_id)
