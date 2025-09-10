import click
from bs4 import BeautifulSoup
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, get_form_payload
from registry_cli.commands.enroll.crawler import Crawler
from registry_cli.models import (
    Module,
    Program,
    SemesterModule,
    Structure,
    StructureSemester,
    Student,
    StudentProgram,
    StudentSemester,
    Term,
)
from registry_cli.utils.logging_config import get_logger

logger = get_logger(__name__)


def add_semester_module_to_student(
    db: Session,
    std_no: int,
    term: str,
    semester_module_id: int,
    module_status: str = "Add",
) -> None:
    """
    Add a semester module to a student's term using the web interface.

    Args:
        db: Database session
        std_no: Student number
        term: Term name (e.g., "2024-07")
        semester_module_id: ID of the semester module to add
        module_status: Status of the module (default: "Add")
    """
    # Find the student
    student = db.query(Student).filter(Student.std_no == std_no).first()
    if not student:
        click.secho(f"Student {std_no} not found", fg="red")
        return

    # Find the term
    term_obj = db.query(Term).filter(Term.name == term).first()
    if not term_obj:
        click.secho(f"Term '{term}' not found", fg="red")
        return

    # Find the student's active program
    student_program = (
        db.query(StudentProgram)
        .filter(
            and_(
                StudentProgram.std_no == std_no,
                StudentProgram.status == "Active",
            )
        )
        .first()
    )

    if not student_program:
        click.secho(f"No active program found for student {std_no}", fg="red")
        return

    # Find the student's semester for this term
    student_semester = (
        db.query(StudentSemester)
        .filter(
            and_(
                StudentSemester.student_program_id == student_program.id,
                StudentSemester.term == term,
            )
        )
        .first()
    )

    if not student_semester:
        click.secho(f"No semester found for student {std_no} in term {term}", fg="red")
        return

    # Find the semester module
    semester_module = (
        db.query(SemesterModule).filter(SemesterModule.id == semester_module_id).first()
    )

    if not semester_module:
        click.secho(f"Semester module {semester_module_id} not found", fg="red")
        return

    # Get module details for logging
    module_name = "Unknown"
    if semester_module.module:
        module_name = f"{semester_module.module.code} - {semester_module.module.name}"

    click.echo(f"Adding module '{module_name}' to student {std_no} for term {term}")

    # Use the crawler to add the module
    crawler = Crawler(db)

    # Check if module is already registered
    existing_modules = crawler.get_existing_modules(student_semester.id)
    if semester_module.module and semester_module.module.code in existing_modules:
        click.secho(
            f"Module {semester_module.module.code} is already registered for this student",
            fg="yellow",
        )
        return

    try:
        # Add the single module using the web interface
        success = _add_single_module(
            crawler,
            student_semester.id,
            semester_module_id,
            module_status,
            semester_module.credits,
        )

        if success:
            click.secho(
                f"Successfully added module '{module_name}' to student {std_no}",
                fg="green",
            )
        else:
            click.secho(
                f"Failed to add module '{module_name}' to student {std_no}", fg="red"
            )

    except Exception as e:
        click.secho(f"Error adding module: {str(e)}", fg="red")
        logger.error(
            f"Error adding module {semester_module_id} to student {std_no}: {str(e)}"
        )


def add_semester_module_by_code_to_student(
    db: Session, std_no: int, term: str, module_code: str, module_status: str = "Add"
) -> None:
    """
    Add a semester module to a student's term using module code.

    Args:
        db: Database session
        std_no: Student number
        term: Term name (e.g., "2024-07")
        module_code: Module code (e.g., "CS 101")
        module_status: Status of the module (default: "Add")
    """
    # Find the student and their program
    student = db.query(Student).filter(Student.std_no == std_no).first()
    if not student:
        click.secho(f"Student {std_no} not found", fg="red")
        return

    student_program = (
        db.query(StudentProgram)
        .filter(
            and_(
                StudentProgram.std_no == std_no,
                StudentProgram.status == "Active",
            )
        )
        .first()
    )

    if not student_program:
        click.secho(f"No active program found for student {std_no}", fg="red")
        return

    # Find the module by code
    module = db.query(Module).filter(Module.code == module_code).first()
    if not module:
        click.secho(f"Module with code '{module_code}' not found", fg="red")
        return

    # Find semester modules for this module in the student's structure
    semester_modules = (
        db.query(SemesterModule, StructureSemester, Structure, Program)
        .join(Module, SemesterModule.module_id == Module.id)
        .join(StructureSemester, SemesterModule.semester_id == StructureSemester.id)
        .join(Structure, StructureSemester.structure_id == Structure.id)
        .join(Program, Structure.program_id == Program.id)
        .filter(
            and_(Module.code == module_code, SemesterModule.semester_id.isnot(None))
        )
        .all()
    )

    if not semester_modules:
        click.secho(f"No semester modules found for module '{module_code}'", fg="red")
        return

    if len(semester_modules) == 1:
        # Only one option, use it
        semester_module_id = semester_modules[0][
            0
        ].id  # First element is SemesterModule
    else:
        # Multiple options, let user choose
        click.echo(
            f"Found {len(semester_modules)} semester modules for '{module_code}':"
        )
        for i, (sm, struct_sem, structure, program) in enumerate(semester_modules):
            semester_name = struct_sem.name if struct_sem else "Unknown semester"
            program_name = program.name if program else "Unknown program"
            click.echo(
                f"  {i+1}. ID: {sm.id}, Semester: {semester_name}, Credits: {sm.credits}, Program: {program_name}"
            )

        choice = click.prompt(
            "Select semester module (enter number)",
            type=click.IntRange(1, len(semester_modules)),
        )
        semester_module_id = semester_modules[choice - 1][
            0
        ].id  # First element is SemesterModule

    # Now add the module using the semester module ID
    add_semester_module_to_student(db, std_no, term, semester_module_id, module_status)


def _add_single_module(
    crawler: Crawler,
    std_semester_id: int,
    semester_module_id: int,
    module_status: str,
    module_credits: float,
) -> bool:
    """
    Add a single module to a student semester using the web interface.

    Args:
        crawler: Crawler instance
        std_semester_id: Student semester ID
        semester_module_id: Semester module ID to add
        module_status: Module status (e.g., "Add", "Compulsory")
        module_credits: Module credits

    Returns:
        bool: True if successful, False otherwise
    """
    # Navigate to the module list page first
    url = f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={std_semester_id}"
    crawler.browser.fetch(url)

    # Navigate to the add module page
    add_response = crawler.browser.fetch(f"{BASE_URL}/r_stdmoduleadd1.php")
    page = BeautifulSoup(add_response.text, "lxml")

    # Create the module string in the format: module_id-status-credits-1200
    module_string = f"{semester_module_id}-{module_status}-{module_credits}-1200"

    # Prepare the payload
    payload = get_form_payload(page) | {
        "Submit": "Add+Modules",
        "take[]": [module_string],
    }

    # Submit the form to add the module
    response = crawler.browser.post(f"{BASE_URL}/r_stdmoduleadd1.php", payload)

    # Check if the module was added successfully
    registered_modules = crawler.get_existing_modules(std_semester_id)

    # Return True if we have more modules than before (indicating success)
    return len(registered_modules) > 0
