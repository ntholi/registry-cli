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

        # If all returned programs are already Completed AND have a graduation_date set, skip this student
        if all(
            p.status
            and p.status.lower() == "completed"
            and p.graduation_date
            and p.graduation_date.strip()
            for p in all_programs
        ):
            click.secho(
                f"  ⊘ All programs for student {std_no} are already Completed with graduation dates set. Skipping.",
                fg="yellow",
            )
            skip_count += 1
            continue

        if len(all_programs) > 1:
            # Check if any programs meet auto-completion criteria
            auto_complete_programs = [
                p
                for p in all_programs
                if p.status
                and p.status.lower() == "active"
                and _should_auto_complete(p, all_programs)
            ]

            if auto_complete_programs:
                # Automatically mark programs that meet criteria
                click.secho(
                    f"  ! Student {std_no} has {len(auto_complete_programs)} program(s) meeting auto-completion criteria",
                    fg="cyan",
                )

                for program in auto_complete_programs:
                    program_name = (
                        program.structure.program.name
                        if program.structure and program.structure.program
                        else "Unknown"
                    )
                    level = (
                        program.structure.program.level
                        if program.structure and program.structure.program
                        else "Unknown"
                    )
                    semester_count = len(program.semesters)

                    click.echo(
                        f"    Auto-completing: {program_name} ({level}, {semester_count} semesters)"
                    )

                    success = _update_program_status(
                        db, browser, program, graduation_date
                    )
                    if success:
                        click.secho(
                            f"  ✓ Successfully marked program {program.id} as completed",
                            fg="green",
                        )
                        success_count += 1
                    else:
                        click.secho(
                            f"  ✗ Failed to update program {program.id}",
                            fg="red",
                        )
                        error_count += 1
            else:
                # No programs meet auto-completion criteria - check if any are active
                active_programs = [
                    p for p in all_programs if p.status and p.status.lower() == "active"
                ]

                if not active_programs:
                    # All programs are completed or in other status
                    # Check if any completed programs are missing graduation dates
                    completed_without_date = [
                        p
                        for p in all_programs
                        if p.status
                        and p.status.lower() == "completed"
                        and (not p.graduation_date or not p.graduation_date.strip())
                    ]

                    if completed_without_date:
                        # Don't skip - these completed programs need graduation dates
                        click.secho(
                            f"  ! Student {std_no} has {len(completed_without_date)} completed program(s) missing graduation dates",
                            fg="cyan",
                        )

                        for program in completed_without_date:
                            program_name = (
                                program.structure.program.name
                                if program.structure and program.structure.program
                                else "Unknown"
                            )
                            click.echo(f"    Updating: {program_name}")

                            success = _update_program_status(
                                db, browser, program, graduation_date
                            )
                            if success:
                                click.secho(
                                    f"  ✓ Successfully updated program {program.id} with graduation date",
                                    fg="green",
                                )
                                success_count += 1
                            else:
                                click.secho(
                                    f"  ✗ Failed to update program {program.id}",
                                    fg="red",
                                )
                                error_count += 1
                    else:
                        # All programs have graduation dates set, skip
                        click.secho(
                            f"  ⊘ Student {std_no} has no active programs and all completed programs have graduation dates. Skipping.",
                            fg="yellow",
                        )
                        skip_count += 1
                else:
                    # There are active programs but none meet auto-completion criteria
                    # Display the programs for information, then auto-skip
                    click.secho(
                        f"  ⊘ Student {std_no} has {len(all_programs)} programs, but none meet auto-completion criteria. Auto-skipping.",
                        fg="yellow",
                    )
                    for i, program in enumerate(all_programs, 1):
                        program_name = (
                            program.structure.program.name
                            if program.structure and program.structure.program
                            else "Unknown"
                        )
                        status = program.status or "Unknown"
                        semester_count = len(program.semesters)
                        level = (
                            program.structure.program.level
                            if program.structure and program.structure.program
                            else "Unknown"
                        )

                        # Color the status
                        if status.lower() == "completed":
                            status_colored = click.style(status, fg="green")
                        elif status.lower() == "active":
                            status_colored = click.style(status, fg="yellow")
                        else:
                            status_colored = click.style(status, fg="cyan")

                        click.echo(
                            f"    {i}. {program_name} ({level}, {semester_count} semesters) - Status: {status_colored}"
                        )
                    skip_count += 1
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
    website_success = _update_program_on_website(
        browser, program.id, program.std_no, graduation_date
    )

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
    browser: Browser, std_program_id: int, std_no: int, graduation_date: str
) -> bool:
    """
    Update student program status to Completed on the website.

    Args:
        browser: Browser instance
        std_program_id: Student program ID
        std_no: Student number
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
                continue
            elif input_type == "checkbox":
                if input_field.get("checked"):
                    form_data[input_name] = input_field.get("value", "Y")
            elif input_type in ["text", "number"]:
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
        # CRITICAL: Explicitly set these IDs to ensure we're updating the correct program for the correct student
        form_data["x_StdProgramID"] = str(std_program_id)
        form_data["x_StudentID"] = str(std_no)

        # Debug output to verify the correct IDs are being sent
        click.echo(
            f"  → Sending update: StudentID={std_no}, ProgramID={std_program_id}, Status=Completed, Date={graduation_date}"
        )

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


def _should_auto_complete(
    program: StudentProgram, all_programs: List[StudentProgram]
) -> bool:
    """
    Check if a program should be automatically marked as completed based on criteria.

    Criteria:
    - Certificate: Must have semester 1 AND semester 2 (not just any 2 semesters)
    - Diploma: Must have semesters 1, 2, 3, 4, 5, AND 6 (consecutive from 1 to 6)
    - Degree: Must have semesters 1-8 (consecutive) OR if only 3 semesters, must have semesters 6, 7, AND 8

    Args:
        program: StudentProgram instance to check
        all_programs: All programs for this student (to check for completed diploma)

    Returns:
        bool: True if program meets auto-completion criteria, False otherwise
    """
    if not program.structure or not program.structure.program:
        return False

    level = program.structure.program.level.lower()

    # Get the set of semester numbers for this program
    semester_numbers = {
        sem.semester_number
        for sem in program.semesters
        if sem.semester_number is not None
    }

    if level == "certificate":
        # Must have semester 1 AND semester 2
        required_semesters = {1, 2}
        return required_semesters.issubset(semester_numbers)

    elif level == "diploma":
        # Must have semesters 1, 2, 3, 4, 5, and 6
        required_semesters = {1, 2, 3, 4, 5, 6}
        return required_semesters.issubset(semester_numbers)

    elif level == "degree":
        # Check if it's a 3-semester top-up degree (semesters 6, 7, 8)
        topup_semesters = {6, 7, 8}
        if topup_semesters.issubset(semester_numbers) and len(semester_numbers) == 3:
            # For top-up degrees, verify student has a completed diploma
            has_completed_diploma = any(
                p.structure
                and p.structure.program
                and p.structure.program.level.lower() == "diploma"
                and p.status
                and p.status.lower() == "completed"
                for p in all_programs
            )
            return has_completed_diploma

        # Check for full degree (semesters 1-8)
        full_degree_semesters = {1, 2, 3, 4, 5, 6, 7, 8}
        return full_degree_semesters.issubset(semester_numbers)

    return False


def mark_graduated_programs_as_completed(db: Session) -> None:
    """
    Mark all Active student programs with a graduation_date as Completed.

    This command finds all student programs that:
    - Have status = "Active"
    - Have a graduation_date set

    And updates them to status = "Completed" in both the database and website.

    Args:
        db: Database session
    """
    browser = Browser()

    # Query for all Active programs with a graduation_date
    programs_to_complete = (
        db.query(StudentProgram)
        .filter(
            StudentProgram.status == "Active",
            StudentProgram.graduation_date.isnot(None),
            StudentProgram.graduation_date != "",
        )
        .all()
    )

    total_programs = len(programs_to_complete)

    if total_programs == 0:
        click.secho("\nNo Active programs with graduation dates found.", fg="yellow")
        return

    click.echo(
        f"\nFound {total_programs} Active program(s) with graduation dates to mark as Completed.\n"
    )

    # Confirm before proceeding
    if not click.confirm("Do you want to proceed?"):
        click.secho("Operation cancelled.", fg="yellow")
        return

    processed = 0
    success_count = 0
    error_count = 0

    for program in programs_to_complete:
        processed += 1
        graduation_date = program.graduation_date or ""

        # Get student and program info for display
        student_name = program.student.name if program.student else "Unknown"
        program_name = (
            program.structure.program.name
            if program.structure and program.structure.program
            else "Unknown"
        )

        click.echo(
            f"[{processed}/{total_programs}] Processing: {program.std_no} - {student_name}"
        )
        click.echo(f"  Program: {program_name}")
        click.echo(f"  Graduation Date: {graduation_date}")

        success = _update_program_status(db, browser, program, graduation_date)

        if success:
            click.secho(
                f"  ✓ Successfully marked program {program.id} as Completed",
                fg="green",
            )
            success_count += 1
        else:
            click.secho(f"  ✗ Failed to update program {program.id}", fg="red")
            error_count += 1

        # Small delay between updates
        time.sleep(0.5)

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("SUMMARY")
    click.echo("=" * 60)
    click.secho(f"Total programs processed: {total_programs}", fg="cyan")
    click.secho(f"Successfully updated: {success_count}", fg="green")
    click.secho(f"Errors: {error_count}", fg="red")
    click.echo("=" * 60)


def repair_student_programs(db: Session, std_nos: List[int]) -> None:
    """
    Repair student programs by re-syncing them with the website.

    This command goes through each student's programs and ensures the website
    has the correct data by submitting the complete form with ALL fields including:
    - x_StdProgramID (program ID)
    - x_StudentID (student number)
    - x_ProgramIntakeDate (intake date)
    - And all other program fields

    This is useful for fixing data corruption issues where programs were incorrectly
    associated with the wrong students.

    Args:
        db: Database session
        std_nos: List of student numbers to repair
    """
    browser = Browser()

    total_students = len(std_nos)
    processed = 0
    success_count = 0
    error_count = 0
    total_programs = 0

    click.echo(f"\nRepairing student programs for {total_students} students...")
    click.echo("This will re-sync all program data with the website.\n")

    for std_no in std_nos:
        processed += 1
        click.echo(f"[{processed}/{total_students}] Processing student {std_no}...")

        # Get all programs for this student
        programs = (
            db.query(StudentProgram).filter(StudentProgram.std_no == std_no).all()
        )

        if not programs:
            click.secho(f"  ⊘ No programs found for student {std_no}", fg="red")
            continue

        click.echo(f"  Found {len(programs)} program(s)")

        for program in programs:
            total_programs += 1

            # Get program details for display
            program_name = (
                program.structure.program.name
                if program.structure and program.structure.program
                else "Unknown"
            )

            click.echo(f"  → Program ID {program.id}: {program_name}")
            click.echo(f"     Status: {program.status}")
            click.echo(f"     Intake Date: {program.intake_date or 'N/A'}")
            click.echo(f"     Graduation Date: {program.graduation_date or 'N/A'}")

            # Repair this program on the website
            success = _repair_program_on_website(browser, program)

            if success:
                click.secho(
                    f"  ✓ Successfully repaired program {program.id}", fg="green"
                )
                success_count += 1
            else:
                click.secho(f"  ✗ Failed to repair program {program.id}", fg="red")
                error_count += 1

            # Small delay between updates
            time.sleep(0.3)

        # Delay between students
        time.sleep(0.5)

    # Summary
    click.echo("\n" + "=" * 60)
    click.echo("SUMMARY")
    click.echo("=" * 60)
    click.secho(f"Total students processed: {total_students}", fg="cyan")
    click.secho(f"Total programs processed: {total_programs}", fg="cyan")
    click.secho(f"Successfully repaired: {success_count}", fg="green")
    click.secho(f"Errors: {error_count}", fg="red")
    click.echo("=" * 60)


def _repair_program_on_website(browser: Browser, program: StudentProgram) -> bool:
    """
    Repair a single student program by re-submitting all its data to the website.

    This fetches the current form, extracts all fields, and re-submits them
    with explicit values for critical fields to ensure data integrity.

    Args:
        browser: Browser instance
        program: StudentProgram instance to repair

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Fetch the edit form
        url = f"{BASE_URL}/r_stdprogramedit.php?StdProgramID={program.id}"
        response = browser.fetch(url)
        soup = BeautifulSoup(response.text, "html.parser")

        # Find the form
        form = soup.find("form", {"name": "fr_stdprogramedit"})
        if not form or not isinstance(form, Tag):
            click.secho(f"  Form not found for program {program.id}", fg="red")
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
            elif input_type in ["text", "number", "date"]:
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

        # CRITICAL: Now explicitly set all the important fields from our database
        # to ensure they match and are correct
        form_data["a_edit"] = "U"  # Update action
        form_data["x_StdProgramID"] = str(program.id)
        form_data["x_StudentID"] = str(program.std_no)

        # Set all program fields from the database using CORRECT field names from the HTML form
        if program.intake_date:
            form_data["x_ProgramIntakeDate"] = program.intake_date
        if program.reg_date:
            form_data["x_StdProgRegDate"] = (
                program.reg_date
            )  # CORRECT: x_StdProgRegDate, NOT x_RegDate
        if program.start_term:
            form_data["x_TermCode"] = (
                program.start_term
            )  # CORRECT: x_TermCode, NOT x_StartTerm
        if program.stream:
            form_data["x_ProgStreamCode"] = (
                program.stream
            )  # CORRECT: x_ProgStreamCode, NOT x_Stream
        if program.graduation_date:
            form_data["x_GraduationDate"] = program.graduation_date
        if program.status:
            form_data["x_ProgramStatus"] = program.status
        if program.assist_provider:
            form_data["x_AssistProviderCode"] = (
                program.assist_provider
            )  # CORRECT: x_AssistProviderCode, NOT x_AssistProvider

        # Set structure ID
        form_data["x_StructureID"] = str(program.structure_id)

        # Debug output to verify what's being sent
        click.echo(
            f"     → Syncing: Student={program.std_no}, ProgramID={program.id}, Status={program.status}"
        )

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
                f"  HTTP error {post_response.status_code} repairing program {program.id}",
                fg="red",
            )
            return False

    except Exception as e:
        click.secho(f"  Exception repairing program {program.id}: {str(e)}", fg="red")
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
