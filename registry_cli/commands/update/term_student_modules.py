import json
import os
import time
from typing import Dict, List, Set

import click
from sqlalchemy.orm import Session

from registry_cli.commands.update.student_modules import update_student_modules
from registry_cli.models import StudentProgram, StudentSemester
from registry_cli.utils.logging_config import get_logger

logger = get_logger(__name__)


def format_time_estimate(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f} seconds"

    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"

    hours = seconds / 3600
    if hours < 24:
        return f"{hours:.1f} hours"

    days = int(hours // 24)
    remaining_hours = int((seconds % 86400) // 3600)
    remaining_minutes = int((seconds % 3600) // 60)

    if remaining_hours > 0 and remaining_minutes > 0:
        return f"{days} days {remaining_hours} hours {remaining_minutes} minutes"
    elif remaining_hours > 0:
        return f"{days} days {remaining_hours} hours"
    elif remaining_minutes > 0:
        return f"{days} days {remaining_minutes} minutes"
    else:
        return f"{days} days"


def get_progress_file(term: str) -> str:
    sanitized_term = term.replace("/", "-").replace("\\", "-")
    return f"term_update_progress_{sanitized_term}.json"


def load_progress(term: str) -> Dict:
    progress_file = get_progress_file(term)
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read progress file {progress_file}: {e}")
            click.secho(
                f"Warning: Could not read progress file {progress_file}, starting fresh",
                fg="yellow",
            )

    return {
        "term": term,
        "completed_students": [],
        "failed_students": [],
        "total_students": 0,
        "current_index": 0,
    }


def save_progress(term: str, progress: Dict) -> None:
    progress_file = get_progress_file(term)
    try:
        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save progress to {progress_file}: {e}")
        click.secho(f"Warning: Could not save progress: {e}", fg="yellow")


def update_term_student_modules(db: Session, term: str, reset: bool = False) -> None:
    progress_file = get_progress_file(term)

    if reset and os.path.exists(progress_file):
        logger.info(f"Resetting progress file: {progress_file}")
        os.remove(progress_file)
        click.echo("Progress file reset")

    progress = load_progress(term)

    if progress["term"] != term:
        progress["term"] = term
        progress["completed_students"] = []
        progress["failed_students"] = []
        progress["current_index"] = 0

    click.echo(f"Finding all students with semesters in term {term}...")

    student_semesters = (
        db.query(StudentSemester)
        .join(StudentProgram)
        .filter(StudentSemester.term == term)
        .order_by(StudentProgram.std_no)
        .all()
    )

    if not student_semesters:
        click.secho(f"No student semesters found for term {term}", fg="yellow")
        return

    student_numbers = [semester.program.std_no for semester in student_semesters]

    progress["total_students"] = len(student_numbers)

    completed_students: Set[int] = set(progress["completed_students"])
    failed_students: Set[int] = set(progress["failed_students"])

    remaining_students = [
        std_no
        for std_no in student_numbers
        if std_no not in completed_students and std_no not in failed_students
    ]

    retry_students = [std_no for std_no in student_numbers if std_no in failed_students]

    all_students_to_process = retry_students + remaining_students

    click.echo(f"Found {len(student_numbers)} students in term {term}")
    click.echo(f"Completed: {len(completed_students)}")
    click.echo(f"Failed (will retry): {len(failed_students)}")
    click.echo(f"Remaining: {len(remaining_students)}")
    click.echo(f"Total to process: {len(all_students_to_process)}")

    if not all_students_to_process:
        click.secho("All students have been processed!", fg="green")
        return

    start_time = time.time()
    total_processing_time = 0
    students_processed = 0

    try:
        for i, std_no in enumerate(all_students_to_process):
            student_start_time = time.time()

            processed_count = len(completed_students) + i
            progress_percent = (processed_count / len(student_numbers)) * 100

            time_estimate_str = ""
            if students_processed > 0:
                avg_time_per_student = total_processing_time / students_processed
                estimated_remaining_time = avg_time_per_student * (
                    len(all_students_to_process) - i
                )
                time_estimate_str = (
                    f" ETA: {format_time_estimate(estimated_remaining_time)}"
                )

            status_indicator = "(RETRY)" if std_no in failed_students else ""
            click.echo(
                f"[{processed_count + 1}/{len(student_numbers)}] ({progress_percent:.1f}%){time_estimate_str}"
            )
            click.echo(f"Processing student {std_no} {status_indicator}...")

            try:
                update_student_modules(db, std_no, term)

                if std_no in failed_students:
                    failed_students.remove(std_no)
                completed_students.add(std_no)

                click.secho(f"✓ Successfully updated student {std_no}", fg="green")

            except KeyboardInterrupt:
                logger.info("Process interrupted by user at student %s", std_no)
                click.echo("\nInterrupted by user. Saving progress...")
                break
            except Exception as e:
                if std_no in completed_students:
                    completed_students.remove(std_no)
                failed_students.add(std_no)

                logger.error(
                    f"Exception while updating student {std_no}: {type(e).__name__}: {str(e)}"
                )
                click.secho(f"✗ Error updating student {std_no}: {str(e)}", fg="red")

            student_end_time = time.time()
            student_processing_time = student_end_time - student_start_time
            total_processing_time += student_processing_time
            students_processed += 1

            progress["completed_students"] = list(completed_students)
            progress["failed_students"] = list(failed_students)
            progress["current_index"] = processed_count + 1
            save_progress(term, progress)

    finally:
        progress["completed_students"] = list(completed_students)
        progress["failed_students"] = list(failed_students)
        save_progress(term, progress)

        end_time = time.time()
        total_time = end_time - start_time

        logger.info(
            f"Term update completed. Total time: {format_time_estimate(total_time)}"
        )
        logger.info(f"Failed updates: {len(failed_students)} students")
        logger.info(f"Students processed: {students_processed}")

        click.echo("\nSummary:")
        click.secho(
            f"Successfully updated: {len(completed_students)} students", fg="green"
        )
        click.secho(f"Failed updates: {len(failed_students)} students", fg="red")

        if failed_students:
            failed_list = sorted(failed_students)
            click.echo(
                f"\nFailed student numbers: {failed_list[:20]}{'...' if len(failed_students) > 20 else ''}"
            )
            click.echo("(Run the command again to retry failed students)")

        if len(completed_students) + len(failed_students) >= len(student_numbers):
            click.secho("✓ All students processed!", fg="green")
        else:
            remaining = (
                len(student_numbers) - len(completed_students) - len(failed_students)
            )
            click.echo(f"Next run will continue with {remaining} remaining students")
