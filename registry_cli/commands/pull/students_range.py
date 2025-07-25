import json
import os
import sys
import time
from typing import Dict, Set

import click
from sqlalchemy.orm import Session

from registry_cli.commands.pull.student import student_pull
from registry_cli.utils.logging_config import get_logger

logger = get_logger(__name__)


def _exit_if_session_rollback(exc: Exception) -> None:
    if "transaction has been rolled back" in str(exc).lower():
        click.secho(
            "Fatal SQLAlchemy session rollback error detected. Exiting...", fg="red"
        )
        sys.exit(1)


PROGRESS_FILE = "students_range_progress.json"


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


def load_progress() -> Dict:
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to read progress file {PROGRESS_FILE}: {e}")
            click.secho(
                f"Warning: Could not read progress file {PROGRESS_FILE}, starting fresh",
                fg="yellow",
            )

    return {
        "failed_pulls": [],
        "current_position": 901019990,
        "start_number": 901019990,
        "end_number": 901000001,
    }


def save_progress(progress: Dict) -> None:
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save progress to {PROGRESS_FILE}: {e}")
        click.secho(f"Warning: Could not save progress: {e}", fg="yellow")


def students_range_pull(
    db: Session,
    start: int = 901019990,
    end: int = 901000001,
    info_only: bool = False,
    reset: bool = False,
) -> None:
    if start < end:
        error_msg = "Start number must be greater than end number"
        logger.error(f"Invalid range parameters: start={start}, end={end}. {error_msg}")
        click.secho(f"Error: {error_msg}", fg="red")
        return

    if reset and os.path.exists(PROGRESS_FILE):
        logger.info(f"Resetting progress file: {PROGRESS_FILE}")
        os.remove(PROGRESS_FILE)
        click.echo("Progress file reset")

    progress = load_progress()

    if progress["start_number"] != start or progress["end_number"] != end:
        logger.info(
            f"Range updated from {progress['start_number']} -> {progress['end_number']} to {start} -> {end}"
        )
        progress["start_number"] = start
        progress["end_number"] = end
        progress["current_position"] = start
        click.echo(f"Updated range to {start} -> {end}")

    start_time = time.time()
    total_processing_time = 0
    students_processed = 0

    failed_pulls: Set[int] = set(progress["failed_pulls"])
    current_position: int = progress["current_position"]

    total_range = start - end + 1
    failed_count = len(failed_pulls)

    logger.info(
        f"Starting students range pull: {start} -> {end} (Total: {total_range:,} students)"
    )
    logger.info(
        f"Current position: {current_position}, Previously failed: {failed_count:,}"
    )

    click.echo(f"Range: {start} -> {end} (Total: {total_range:,} students)")
    click.echo(f"Failed: {failed_count:,}")
    click.echo(f"Current position: {current_position}")

    if current_position < end:
        click.secho("All students in range have been processed!", fg="green")
        return

    try:
        failed_students = [
            std_no for std_no in range(start, end - 1, -1) if std_no in failed_pulls
        ]
        remaining_students = [
            std_no
            for std_no in range(current_position, end - 1, -1)
            if std_no not in failed_pulls
        ]

        all_students = failed_students + remaining_students

        for std_no in all_students:
            student_start_time = time.time()

            remaining = std_no - end + 1
            processed = total_range - remaining
            progress_percent = (processed / total_range) * 100

            time_estimate_str = ""
            if students_processed > 0:
                avg_time_per_student = total_processing_time / students_processed
                estimated_remaining_time = avg_time_per_student * remaining
                time_estimate_str = (
                    f" ETA: {format_time_estimate(estimated_remaining_time)}"
                )

            status_indicator = "(RETRY)" if std_no in failed_pulls else ""
            click.echo(
                f"[{processed:,}/{total_range:,}] ({progress_percent:.1f}%){time_estimate_str}"
            )
            click.echo(f"Processing student {std_no} {status_indicator}...")

            try:
                success = student_pull(db, std_no, info_only)

                if success:
                    if std_no in failed_pulls:
                        failed_pulls.remove(std_no)
                    click.secho(f"✓ Successfully pulled student {std_no}", fg="green")
                else:
                    failed_pulls.add(std_no)
                    logger.error(
                        f"Failed to pull student {std_no}: student_pull returned False"
                    )
                    click.secho(f"✗ Failed to pull student {std_no}", fg="red")

            except KeyboardInterrupt:
                logger.info("Process interrupted by user at student %s", std_no)
                click.echo("\nInterrupted by user. Saving progress...")
                break
            except Exception as e:
                _exit_if_session_rollback(e)
                failed_pulls.add(std_no)
                logger.error(
                    f"Exception while pulling student {std_no}: {type(e).__name__}: {str(e)}"
                )
                click.secho(f"✗ Error pulling student {std_no}: {str(e)}", fg="red")

            student_end_time = time.time()
            student_processing_time = student_end_time - student_start_time
            total_processing_time += student_processing_time
            students_processed += 1

            progress["current_position"] = std_no
            progress["failed_pulls"] = list(failed_pulls)
            save_progress(progress)

    finally:
        progress["failed_pulls"] = list(failed_pulls)
        save_progress(progress)

        end_time = time.time()
        total_time = end_time - start_time

        logger.info(
            f"Students range pull completed. Total time: {format_time_estimate(total_time)}"
        )
        logger.info(f"Failed pulls: {len(failed_pulls):,} students")
        logger.info(f"Students processed: {students_processed:,}")

        click.echo("\nSummary:")
        click.secho(f"Failed pulls: {len(failed_pulls):,} students", fg="red")

        if failed_pulls:
            click.echo(
                f"\nFailed student numbers: {sorted(failed_pulls, reverse=True)[:20]}{'...' if len(failed_pulls) > 20 else ''}"
            )
            click.echo("(Run the command again to retry failed students)")

        if progress["current_position"] < end:
            click.secho("✓ All students completed!", fg="green")
        else:
            click.echo(
                f"Next run will continue from student {progress['current_position']}"
            )
