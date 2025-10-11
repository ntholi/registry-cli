"""
Push term modules to website and re-sync with correct IDs.

This module handles pushing existing student modules for a term to the website
and then re-syncing them back to get the correct IDs from the website (single source of truth).
"""

import time
from dataclasses import dataclass
from typing import Optional

import click
from bs4 import BeautifulSoup
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.commands.enroll.crawler import Crawler
from registry_cli.commands.pull.student.common import scrape_and_save_modules
from registry_cli.models import (
    Program,
    SemesterModule,
    Structure,
    StudentModule,
    StudentProgram,
    StudentSemester,
    Term,
)
from registry_cli.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ModuleData:
    """Data class to hold module information before deletion."""

    semester_module_id: int
    status: str
    credits: float


def get_or_create_semester_on_website(
    db: Session,
    crawler: Crawler,
    semester: StudentSemester,
    term: Term,
) -> Optional[int]:
    """
    Get or create student semester on website.

    Uses the Crawler's add_semester method which checks if the semester exists
    and creates it if it doesn't.

    Args:
        db: Database session
        crawler: Crawler instance
        semester: StudentSemester object
        term: Term object

    Returns:
        Student semester ID from website if successful, None otherwise
    """
    # Get the student program and related data
    student_program = (
        db.query(StudentProgram)
        .filter(StudentProgram.id == semester.student_program_id)
        .first()
    )

    if not student_program:
        logger.error(f"Student program {semester.student_program_id} not found")
        return None

    # Get structure and program details
    structure = (
        db.query(Structure).filter(Structure.id == student_program.structure_id).first()
    )

    if not structure:
        logger.error(f"Structure {student_program.structure_id} not found")
        return None

    program = db.query(Program).filter(Program.id == structure.program_id).first()

    if not program:
        logger.error(f"Program {structure.program_id} not found")
        return None

    # Use crawler to add semester (it will check if it exists first)
    semester_id = crawler.add_semester(
        school_id=program.school_id,
        program_id=program.id,
        structure_id=structure.id,
        std_program_id=student_program.id,
        semester_number=semester.semester_number or 1,
        term=term,
    )

    return semester_id


def push_modules_to_website(
    db: Session, browser: Browser, std_semester_id: int, modules_data: list[ModuleData]
) -> list[str]:
    """
    Push student modules to website using r_stdmoduleadd1.php.

    Only pushes modules that don't already exist on the website.

    Args:
        db: Database session
        browser: Browser instance
        std_semester_id: Student semester ID
        modules_data: List of ModuleData objects to push

    Returns:
        List of successfully registered module codes
    """
    if not modules_data:
        logger.info(f"No modules to push for semester {std_semester_id}")
        return []

    # Get existing modules from the website first
    crawler = Crawler(db)
    existing_module_codes = crawler.get_existing_modules(std_semester_id)

    if existing_module_codes:
        click.echo(f"Found {len(existing_module_codes)} modules already on website")
        logger.info(f"Existing modules on website: {existing_module_codes}")

    # Get module codes for the modules we want to push
    modules_to_check = []
    for module_data in modules_data:
        sem_mod = (
            db.query(SemesterModule)
            .filter(SemesterModule.id == module_data.semester_module_id)
            .first()
        )
        if sem_mod and sem_mod.module:
            modules_to_check.append({"data": module_data, "code": sem_mod.module.code})

    # Filter out modules that already exist on the website
    modules_to_push = [
        m for m in modules_to_check if m["code"] not in existing_module_codes
    ]

    if not modules_to_push:
        click.echo("All modules already exist on website, skipping push")
        logger.info("No new modules to push - all already exist on website")
        return existing_module_codes

    click.echo(
        f"Will push {len(modules_to_push)} new modules (skipping {len(modules_to_check) - len(modules_to_push)} already on website)"
    )

    # Navigate to the module list page first
    url = f"{BASE_URL}/r_stdmodulelist.php?showmaster=1&StdSemesterID={std_semester_id}"
    browser.fetch(url)

    # Get the add modules page
    add_response = browser.fetch(f"{BASE_URL}/r_stdmoduleadd1.php")
    page = BeautifulSoup(add_response.text, "lxml")

    # Build the module strings in the format: {semester_module_id}-{status}-{credits}-1200
    modules_with_amounts = []
    for module_info in modules_to_push:
        module_data = module_info["data"]
        module_id = module_data.semester_module_id
        module_status = module_data.status
        module_credits = module_data.credits
        module_string = f"{module_id}-{module_status}-{module_credits}-1200"
        modules_with_amounts.append(module_string)

    if not modules_with_amounts:
        logger.warning("No valid modules to push")
        return existing_module_codes

    # Submit the form
    payload = get_form_payload(page) | {
        "Submit": "Add+Modules",
        "take[]": modules_with_amounts,
    }

    browser.post(f"{BASE_URL}/r_stdmoduleadd1.php", payload)

    # Get the registered modules from the website
    registered_modules = crawler.get_existing_modules(std_semester_id)
    logger.info(
        f"Successfully pushed modules - total on website: {len(registered_modules)}"
    )

    return registered_modules


def push_term_modules(
    db: Session, term: str, std_no: Optional[int] = None, reset: bool = False
) -> None:
    """
    Push all student modules for a term to the website and re-sync.

    This function:
    1. Gets all student semesters for the specified term (optionally filtered by student number)
    2. For each semester, gets or creates the semester on the website
    3. Deletes existing modules from database
    4. Pushes modules to website
    5. Re-syncs modules from website to get correct IDs

    Args:
        db: Database session
        term: Term name (e.g., "2025-02")
        std_no: Optional student number to process only that student
        reset: Whether to reset progress (not used in this implementation)
    """
    browser = Browser()
    crawler = Crawler(db)

    # Get the Term object
    term_obj = db.query(Term).filter(Term.name == term).first()
    if not term_obj:
        click.secho(f"Term {term} not found in database", fg="red")
        return

    # Get all student semesters for the term, optionally filtered by student number
    query = db.query(StudentSemester).filter(StudentSemester.term == term)

    if std_no is not None:
        # Join with StudentProgram to filter by student number
        query = query.join(
            StudentProgram, StudentSemester.student_program_id == StudentProgram.id
        ).filter(
            and_(StudentProgram.std_no == std_no, StudentProgram.status == "Active")
        )

    semesters = query.all()

    if not semesters:
        if std_no is not None:
            click.secho(
                f"No semesters found for student {std_no} in term {term}", fg="yellow"
            )
        else:
            click.secho(f"No semesters found for term {term}", fg="yellow")
        return

    if std_no is not None:
        click.echo(
            f"Found {len(semesters)} semester(s) for student {std_no} in term {term}"
        )
    else:
        click.echo(f"Found {len(semesters)} semesters for term {term}")

    success_count = 0
    failed_count = 0
    skipped_count = 0

    for i, semester in enumerate(semesters, 1):
        click.echo(f"\n[{i}/{len(semesters)}] Processing semester {semester.id}...")

        try:
            # Get or create the semester on the website
            website_semester_id = get_or_create_semester_on_website(
                db, crawler, semester, term_obj
            )

            if not website_semester_id:
                click.secho(
                    f"Could not get/create semester on website for semester {semester.id}",
                    fg="yellow",
                )
                skipped_count += 1
                continue

            # Get modules from database
            modules = list(semester.modules)

            if not modules:
                click.echo(f"No modules found for semester {semester.id}, skipping")
                skipped_count += 1
                continue

            click.echo(f"Found {len(modules)} modules to process")

            # Store module data before deletion (need to query semester modules for credits)
            modules_data = []
            for module in modules:
                sem_mod = (
                    db.query(SemesterModule)
                    .filter(SemesterModule.id == module.semester_module_id)
                    .first()
                )
                if sem_mod:
                    modules_data.append(
                        ModuleData(
                            semester_module_id=module.semester_module_id,
                            status=module.status,
                            credits=sem_mod.credits,
                        )
                    )

            if not modules_data:
                click.secho(
                    "No valid modules found with semester module data", fg="yellow"
                )
                skipped_count += 1
                continue

            # Check if modules exist on website and push only new ones
            click.echo("Checking and pushing modules to website...")
            registered_codes = push_modules_to_website(
                db, browser, website_semester_id, modules_data
            )

            if not registered_codes:
                click.secho("No modules found on website after push", fg="red")
                failed_count += 1
                continue

            # Delete modules from database (now that we know they're on the website)
            for module in modules:
                db.delete(module)
            db.commit()
            click.echo(f"Deleted {len(modules)} modules from database")

            # Update semester ID if different
            if website_semester_id != semester.id:
                old_id = semester.id
                semester.id = website_semester_id
                db.commit()
                click.echo(
                    f"Updated semester ID from {old_id} to {website_semester_id}"
                )

            # Re-sync from website to get correct IDs
            click.echo("Re-syncing modules from website...")
            scrape_and_save_modules(db, semester)

            success_count += 1
            click.secho(
                f"Successfully processed semester {semester.id} ({len(registered_codes)} modules)",
                fg="green",
            )

            # Small delay to avoid overwhelming the server
            time.sleep(0.5)

        except Exception as e:
            click.secho(f"Error processing semester {semester.id}: {str(e)}", fg="red")
            logger.exception(f"Error processing semester {semester.id}")
            failed_count += 1
            continue

    # Summary
    click.echo("\n" + "=" * 50)
    click.secho(f"Processing complete!", fg="green", bold=True)
    click.echo(f"Total semesters: {len(semesters)}")
    click.secho(f"Successful: {success_count}", fg="green")
    click.secho(f"Failed: {failed_count}", fg="red" if failed_count > 0 else "white")
    click.secho(
        f"Skipped: {skipped_count}", fg="yellow" if skipped_count > 0 else "white"
    )
