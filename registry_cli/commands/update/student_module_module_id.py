import time
from typing import List

import click
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.models import (
    Module,
    SemesterModule,
    StudentModule,
    StudentProgram,
    StudentSemester,
)


def search_and_update_module_id(
    db: Session,
    semester_number: int,
    module_name: str,
    x_sem_module_id: int,
    std_nos: List[int],
) -> None:
    """
    Search for a module by name and update x_SemModuleID for specified students.

    This command:
    1. Searches for a module matching the given name in r_stdmodulelist.php context
    2. Updates the x_SemModuleID in r_stdmoduleedit.php for each student
    3. Processes all students in the provided list for the given semester number

    Args:
        db: Database session
        semester_number: Semester number (e.g. 1, 2, 3, 4)
        module_name: Module name to search for
        x_sem_module_id: New x_SemModuleID value to set
        std_nos: List of student numbers to update
    """
    click.echo(
        f"Searching for module '{module_name}' and updating x_SemModuleID to {x_sem_module_id}"
    )
    click.echo(f"Processing {len(std_nos)} students in semester {semester_number}")

    # First verify the x_sem_module_id exists in the database
    semester_module = (
        db.query(SemesterModule).filter(SemesterModule.id == x_sem_module_id).first()
    )

    if not semester_module:
        click.secho(
            f"Error: SemesterModule with ID {x_sem_module_id} not found in database",
            fg="red",
        )
        return

    if semester_module.module:
        click.echo(
            f"Target SemesterModule: {semester_module.module.code} - {semester_module.module.name}"
        )
    else:
        click.echo(
            f"Target SemesterModule ID: {x_sem_module_id} (no associated module)"
        )

    browser = Browser()
    updated_count = 0
    skipped_count = 0
    error_count = 0
    total_modules = 0

    for i, std_no in enumerate(std_nos, 1):
        click.echo(f"\nProcessing student {i}/{len(std_nos)}: {std_no}")

        # Find student's active program
        program = (
            db.query(StudentProgram)
            .filter(StudentProgram.std_no == std_no)
            .where(StudentProgram.status == "Active")
            .first()
        )
        if not program:
            click.secho(f"No active program found for student {std_no}", fg="yellow")
            skipped_count += 1
            continue

        # Find student's semester for the given semester number
        semester = (
            db.query(StudentSemester)
            .filter(
                StudentSemester.student_program_id == program.id,
                StudentSemester.semester_number == semester_number,
            )
            .first()
        )
        if not semester:
            click.secho(
                f"No semester found for student {std_no} in semester {semester_number}",
                fg="yellow",
            )
            skipped_count += 1
            continue

        # Find student modules matching the module name
        student_modules = _find_matching_student_modules(db, semester.id, module_name)

        if not student_modules:
            click.secho(
                f"No modules matching '{module_name}' found for student {std_no} in semester {semester_number}",
                fg="yellow",
            )
            skipped_count += 1
            continue

        total_modules += len(student_modules)
        click.echo(
            f"Found {len(student_modules)} matching modules for student {std_no}"
        )

        # Update each matching module
        for student_module in student_modules:
            try:
                # Get current module info for display
                current_sem_module = (
                    db.query(SemesterModule)
                    .filter(SemesterModule.id == student_module.semester_module_id)
                    .first()
                )

                current_module_info = "Unknown"
                if current_sem_module and current_sem_module.module:
                    current_module_info = f"{current_sem_module.module.code} - {current_sem_module.module.name}"

                click.echo(f"  Updating module: {current_module_info}")

                success = _update_module_ref_on_website(
                    browser,
                    student_module.id,
                    x_sem_module_id,
                    student_module.status,
                    credits=semester_module.credits,
                )

                if success:
                    # Update in database
                    student_module.semester_module_id = x_sem_module_id
                    updated_count += 1
                    click.secho(
                        f"  ✓ Updated StudentModule {student_module.id} for student {std_no}",
                        fg="green",
                    )
                else:
                    click.secho(
                        f"  ✗ Failed to update StudentModule {student_module.id} for student {std_no}",
                        fg="red",
                    )
                    error_count += 1

                # Small delay to avoid overwhelming the server
                time.sleep(1)

            except Exception as e:
                click.secho(
                    f"  Error processing StudentModule {student_module.id} for student {std_no}: {str(e)}",
                    fg="red",
                )
                error_count += 1

    # Commit all database changes
    db.commit()

    # Print summary
    click.echo(f"\n" + "=" * 50)
    click.echo(f"Update Summary:")
    click.echo(f"Total modules found: {total_modules}")
    click.secho(f"Successfully updated: {updated_count} modules", fg="green")
    if skipped_count > 0:
        click.secho(f"Skipped students: {skipped_count}", fg="blue")
    if error_count > 0:
        click.secho(f"Errors: {error_count} modules", fg="red")
    click.echo("=" * 50)


def _find_matching_student_modules(
    db: Session, student_semester_id: int, module_name: str
) -> List[StudentModule]:
    """
    Find student modules that match the given module name.

    Searches in the StudentModule -> SemesterModule -> Module chain.
    """
    # Search by module name using ILIKE for case-insensitive partial matching
    student_modules = (
        db.query(StudentModule)
        .join(SemesterModule, StudentModule.semester_module_id == SemesterModule.id)
        .join(Module, SemesterModule.module_id == Module.id)
        .filter(
            StudentModule.student_semester_id == student_semester_id,
            Module.name.ilike(f"%{module_name}%"),
        )
        .all()
    )

    return student_modules


def _update_module_ref_on_website(
    browser: Browser,
    std_module_id: int,
    new_sem_module_id: int,
    status: str,
    credits: float,
) -> bool:
    """
    Update the x_SemModuleID field on the website using r_stdmoduleedit.php.

    Args:
        browser: Browser instance for making requests
        std_module_id: StudentModule ID to update
        new_sem_module_id: New SemesterModule ID to set
        status: Current status of the student module
        credits: Credits of the new semester module

    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Fetch the edit form
        url = f"{BASE_URL}/r_stdmoduleedit.php?StdModuleID={std_module_id}"
        response = browser.fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the form
        form = soup.find("form", {"name": "fr_stdmoduleedit"})
        if not form or not isinstance(form, Tag):
            click.secho(f"Form not found for StudentModule {std_module_id}", fg="red")
            return False

        # Get form data
        form_data = get_form_payload(form)

        # Update the relevant fields
        form_data["a_edit"] = "U"  # Update action
        form_data["x_SemModuleID"] = str(new_sem_module_id)
        form_data["x_StdModStatCode"] = status
        form_data["x_StdModCredits"] = credits
        form_data["x_StdModFee"] = ""  # Clear fee field

        # Submit the form
        post_url = f"{BASE_URL}/r_stdmoduleedit.php"
        post_response = browser.post(post_url, form_data)

        if post_response.status_code == 200:
            # Check for success indicators in the response
            response_text = post_response.text.lower()
            if "successfully" in response_text or "updated" in response_text:
                return True

            # Check for error messages
            response_soup = BeautifulSoup(post_response.text, "html.parser")
            error_message = response_soup.find("div", class_="error")
            if error_message:
                click.secho(
                    f"Website error: {error_message.get_text(strip=True)}", fg="red"
                )
                return False

            # If no explicit success/error message, assume success if status is 200
            return True
        else:
            click.secho(
                f"HTTP error {post_response.status_code} updating StudentModule {std_module_id}",
                fg="red",
            )
            return False

    except Exception as e:
        click.secho(
            f"Exception updating StudentModule {std_module_id}: {str(e)}", fg="red"
        )
        return False
