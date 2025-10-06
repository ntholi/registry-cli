import time
from typing import List, Optional

import click
from bs4 import BeautifulSoup, Tag
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL, Browser, get_form_payload
from registry_cli.models import StudentProgram


def mark_programs_as_completed(
    db: Session, std_nos: List[int], graduation_date: str
) -> None:
    """
    Mark student programs as completed with a graduation date.

    Args:
        db: Database session
        std_nos: List of student numbers
        graduation_date: Graduation date in YYYY-MM-DD format (e.g. "2011-08-20")
    """
    # Validate graduation date format
    if not _validate_date_format(graduation_date):
        click.secho(
            f"Invalid graduation date format: {graduation_date}. Expected YYYY-MM-DD (e.g. '2011-08-20')",
            fg="red",
        )
        return

    browser = Browser()

    total_students = len(std_nos)
    processed = 0
    success_count = 0
    skip_count = 0
    error_count = 0

    click.echo(
        f"\nProcessing {total_students} students to mark programs as completed..."
    )
    click.echo(f"Graduation date: {graduation_date}\n")

    for std_no in std_nos:
        processed += 1
        click.echo(f"[{processed}/{total_students}] Processing student {std_no}...")

        # Get all Active and Completed programs for this student
        all_programs = (
            db.query(StudentProgram)
            .filter(
                StudentProgram.std_no == std_no,
                StudentProgram.status.in_(["Active", "Completed"]),
            )
            .all()
        )

        if not all_programs:
            click.secho(f"  ✗ No programs found for student {std_no}", fg="yellow")
            skip_count += 1
            continue

        if len(all_programs) > 1:
            click.secho(
                f"  ! Student {std_no} has {len(all_programs)} programs:",
                fg="yellow",
            )
            for i, program in enumerate(all_programs, 1):
                structure_code = program.structure.code if program.structure else "N/A"
                program_name = (
                    program.structure.program.name
                    if program.structure and program.structure.program
                    else "Unknown"
                )
                status = program.status or "Unknown"

                # Color the status: green for Completed, yellow for Active, cyan for others
                if status.lower() == "completed":
                    status_colored = click.style(status, fg="green")
                elif status.lower() == "active":
                    status_colored = click.style(status, fg="yellow")
                else:
                    status_colored = click.style(status, fg="cyan")

                click.echo(
                    f"    {i}. ID: {program.id} - {program_name} ({structure_code}) - Status: {status_colored}"
                )

            # Ask user which one to mark as completed
            while True:
                choice = click.prompt(
                    "  Which program should be marked as completed? Enter number (or 's' to skip)",
                    type=str,
                )
                if choice.lower() == "s":
                    click.echo(f"  ⊘ Skipped student {std_no}")
                    skip_count += 1
                    break
                try:
                    index = int(choice) - 1
                    if 0 <= index < len(all_programs):
                        selected_program = all_programs[index]
                        success = _update_program_status(
                            db, browser, selected_program, graduation_date
                        )
                        if success:
                            click.secho(
                                f"  ✓ Successfully marked program {selected_program.id} as completed",
                                fg="green",
                            )
                            success_count += 1
                        else:
                            click.secho(
                                f"  ✗ Failed to update program {selected_program.id}",
                                fg="red",
                            )
                            error_count += 1
                        break
                    else:
                        click.echo(
                            f"  Invalid choice. Please enter 1-{len(all_programs)}"
                        )
                except ValueError:
                    click.echo("  Invalid input. Please enter a number or 's' to skip")
        else:
            # Single program - update it directly
            program = all_programs[0]
            success = _update_program_status(db, browser, program, graduation_date)
            if success:
                click.secho(
                    f"  ✓ Successfully marked program {program.id} as completed",
                    fg="green",
                )
                success_count += 1
            else:
                click.secho(f"  ✗ Failed to update program {program.id}", fg="red")
                error_count += 1

        # Small delay between students
        time.sleep(0.5)

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("SUMMARY")
    click.echo("=" * 60)
    click.secho(f"Total students processed: {total_students}", fg="cyan")
    click.secho(f"Successfully updated: {success_count}", fg="green")
    click.secho(f"Skipped: {skip_count}", fg="yellow")
    click.secho(f"Errors: {error_count}", fg="red")
    click.echo("=" * 60)


def _update_program_status(
    db: Session, browser: Browser, program: StudentProgram, graduation_date: str
) -> bool:
    """
    Update a single student program to Completed status with graduation date.

    Updates both the website and database.

    Args:
        db: Database session
        browser: Browser instance
        program: StudentProgram instance to update
        graduation_date: Graduation date in YYYY-MM-DD format

    Returns:
        bool: True if successful, False otherwise
    """
    # Update on website first
    website_success = _update_program_on_website(browser, program.id, graduation_date)

    if not website_success:
        click.secho(f"  Failed to update website for program {program.id}", fg="red")
        return False

    # Update in database
    try:
        program.status = "Completed"
        program.graduation_date = graduation_date
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        click.secho(f"  Database error for program {program.id}: {str(e)}", fg="red")
        return False


def _update_program_on_website(
    browser: Browser, std_program_id: int, graduation_date: str
) -> bool:
    """
    Update student program status to Completed on the website.

    Args:
        browser: Browser instance
        std_program_id: Student program ID
        graduation_date: Graduation date in YYYY-MM-DD format

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Fetch the edit form
        url = f"{BASE_URL}/r_stdprogramedit.php?StdProgramID={std_program_id}"
        response = browser.fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the form
        form = soup.find("form", {"name": "fr_stdprogramedit"})
        if not form or not isinstance(form, Tag):
            click.secho(
                f"  Form not found for student program {std_program_id}", fg="red"
            )
            return False

        # Get all form data - this extracts all hidden inputs
        form_data = get_form_payload(form)

        # Extract all input fields (text, hidden, checkbox) and their values
        all_inputs = form.find_all("input")
        for input_field in all_inputs:
            if not isinstance(input_field, Tag):
                continue

            input_name = input_field.get("name")
            input_type = input_field.get("type", "text")

            if not input_name:
                continue

            # Skip submit button
            if input_name == "btnAction":
                continue

            if input_type == "hidden":
                # Already handled by get_form_payload
                continue
            elif input_type == "checkbox":
                # Only include if checked (has 'checked' attribute)
                if input_field.get("checked"):
                    form_data[input_name] = input_field.get("value", "Y")
                # If not checked, don't include in form data
            elif input_type in ["text", "number"]:
                # Get the value attribute
                value = input_field.get("value", "")
                form_data[input_name] = value

        # Extract all select fields and their selected values
        all_selects = form.find_all("select")
        for select_field in all_selects:
            if not isinstance(select_field, Tag):
                continue

            select_name = select_field.get("name")
            if not select_name:
                continue

            # Find the selected option
            selected_option = select_field.find("option", selected=True)
            if selected_option and isinstance(selected_option, Tag):
                form_data[select_name] = selected_option.get("value", "")

        # Extract all textarea fields
        all_textareas = form.find_all("textarea")
        for textarea in all_textareas:
            if not isinstance(textarea, Tag):
                continue

            textarea_name = textarea.get("name")
            if textarea_name:
                form_data[textarea_name] = textarea.get_text(strip=False)

        # Now override the fields we want to update
        form_data["a_edit"] = "U"  # Update action
        form_data["x_ProgramStatus"] = "Completed"
        form_data["x_GraduationDate"] = graduation_date

        # Submit the form
        post_url = f"{BASE_URL}/r_stdprogramedit.php"
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
                    f"  Website error: {error_message.get_text(strip=True)}", fg="red"
                )
                return False

            # If no explicit success/error message, assume success if status is 200
            return True
        else:
            click.secho(
                f"  HTTP error {post_response.status_code} updating program {std_program_id}",
                fg="red",
            )
            return False

    except Exception as e:
        click.secho(
            f"  Exception updating program {std_program_id}: {str(e)}", fg="red"
        )
        return False


def _validate_date_format(date_string: str) -> bool:
    """
    Validate that a date string is in YYYY-MM-DD format.

    Args:
        date_string: Date string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    import re

    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(pattern, date_string):
        return False

    # Additional validation - check if it's a valid date
    try:
        year, month, day = date_string.split("-")
        year_int = int(year)
        month_int = int(month)
        day_int = int(day)

        if month_int < 1 or month_int > 12:
            return False

        if day_int < 1 or day_int > 31:
            return False

        # Simple check for months with fewer days
        if month_int in [4, 6, 9, 11] and day_int > 30:
            return False

        if month_int == 2:
            # Leap year check
            is_leap = (year_int % 4 == 0 and year_int % 100 != 0) or (
                year_int % 400 == 0
            )
            if (is_leap and day_int > 29) or (not is_leap and day_int > 28):
                return False

        return True
    except (ValueError, AttributeError):
        return False
