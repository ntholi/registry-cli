from typing import Any, Dict, List

import click
from sqlalchemy.orm import Session

from registry_cli.models import Module, SemesterModule, StudentModule, StudentSemester
from registry_cli.scrapers.student import StudentModuleScraper


def scrape_and_save_modules(db: Session, semester: StudentSemester):
    """Scrape and save modules for a given semester."""
    module_scraper = StudentModuleScraper(semester.id)
    module_data = module_scraper.scrape()
    for mod in module_data:
        semester_module = (
            db.query(SemesterModule)
            .filter(SemesterModule.id == mod["semester_module_id"])
            .first()
        )
        if not semester_module:
            click.secho(
                f"SemesterModule with id: {mod['semester_module_id']} not found",
                fg="red",
            )
            raise RuntimeError(
                f"SemesterModule with id: {mod['semester_module_id']} not found"
            )
        existing_module = (
            db.query(StudentModule).filter(StudentModule.id == mod["id"]).first()
        )
        if existing_module:
            existing_module.status = mod["status"]
            existing_module.marks = mod["marks"]
            existing_module.grade = mod["grade"]
            existing_module.semester_module_id = mod["semester_module_id"]
            existing_module.semester = semester
        else:
            module = StudentModule(
                id=mod["id"],
                status=mod["status"],
                marks=mod["marks"],
                grade=mod["grade"],
                semester_module_id=mod["semester_module_id"],
                semester=semester,
            )
            db.add(module)
    db.commit()
    click.echo(f"Successfully saved modules for semester {semester.term}")
    return module_data


def save_semesters_and_modules_batch(
    db: Session,
    program,
    semesters_data: List[Dict[str, Any]],
    modules_by_semester: Dict[int, List[Dict[str, Any]]],
) -> None:
    """Save all semesters and their modules in a batch operation."""
    db.query(StudentSemester).filter(
        StudentSemester.student_program_id == program.id
    ).delete()

    saved_semesters = {}

    for sem in semesters_data:
        semester = StudentSemester(
            id=sem["id"],
            term=sem["term"],
            status=sem["status"],
            semester_number=sem["semester_number"],
            caf_date=sem.get("caf_date"),
            student_program_id=program.id,
        )
        db.add(semester)
        saved_semesters[sem["id"]] = semester

    db.commit()

    for semester_id, semester in saved_semesters.items():
        module_data = modules_by_semester.get(semester_id, [])
        for mod in module_data:
            semester_module = (
                db.query(SemesterModule)
                .filter(SemesterModule.id == mod["semester_module_id"])
                .first()
            )
            if not semester_module:
                click.secho(
                    f"SemesterModule with id: {mod['semester_module_id']} not found",
                    fg="yellow",
                )
                continue

            existing_module = (
                db.query(StudentModule).filter(StudentModule.id == mod["id"]).first()
            )
            if existing_module:
                existing_module.status = mod["status"]
                existing_module.marks = mod["marks"]
                existing_module.grade = mod["grade"]
                existing_module.semester_module_id = mod["semester_module_id"]
                existing_module.semester = semester
            else:
                module = StudentModule(
                    id=mod["id"],
                    status=mod["status"],
                    marks=mod["marks"],
                    grade=mod["grade"],
                    semester_module_id=mod["semester_module_id"],
                    semester=semester,
                )
                db.add(module)

    db.commit()
    click.echo(
        f"Successfully saved {len(semesters_data)} semesters and their modules for program: {program.id}"
    )
