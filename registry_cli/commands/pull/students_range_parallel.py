import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Set

import click
from sqlalchemy.orm import Session, sessionmaker

from registry_cli.commands.pull.student import student_pull
from registry_cli.db.config import get_engine
from registry_cli.utils.logging_config import get_logger

logger = get_logger(__name__)

PROGRESS_FILE = "students_range_parallel_progress.json"
lock = threading.Lock()


def _exit_if_session_rollback(exc: Exception) -> None:
    if "transaction has been rolled back" in str(exc).lower():
        click.secho(
            "Fatal SQLAlchemy session rollback error detected. Exiting...", fg="red"
        )
        sys.exit(1)


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


def get_db_session(use_local: bool = True):
    engine = get_engine(use_local)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


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
        "current_position": 901013069,
        "start_number": 901013069,
        "end_number": 901000001,
        "processed_students": [],
        "total_processed": 0,
    }


def save_progress(progress: Dict) -> None:
    try:
        with lock:
            with open(PROGRESS_FILE, "w") as f:
                json.dump(progress, f, indent=2)
    except IOError as e:
        logger.error(f"Failed to save progress to {PROGRESS_FILE}: {e}")
        click.secho(f"Warning: Could not save progress: {e}", fg="yellow")


def process_student_worker(
    std_no: int, info_only: bool, use_local: bool, progress: Dict
) -> Dict:
    result = {
        "std_no": std_no,
        "success": False,
        "error": None,
        "processing_time": 0,
    }

    start_time = time.time()
    db = None

    try:
        db = get_db_session(use_local)
        success = student_pull(db, std_no, info_only)
        result["success"] = success

        if success:
            with lock:
                if std_no in progress["failed_pulls"]:
                    progress["failed_pulls"].remove(std_no)
                if std_no not in progress["processed_students"]:
                    progress["processed_students"].append(std_no)
                    progress["total_processed"] += 1
        else:
            with lock:
                if std_no not in progress["failed_pulls"]:
                    progress["failed_pulls"].append(std_no)

    except Exception as e:
        _exit_if_session_rollback(e)
        result["error"] = str(e)
        with lock:
            if std_no not in progress["failed_pulls"]:
                progress["failed_pulls"].append(std_no)
        logger.error(
            f"Exception while pulling student {std_no}: {type(e).__name__}: {str(e)}"
        )

    finally:
        if db:
            db.close()
        result["processing_time"] = time.time() - start_time

    return result


def students_range_parallel_pull(
    start: int = 901013069,
    end: int = 901000001,
    info_only: bool = False,
    reset: bool = False,
    max_workers: int = 10,
    use_local: bool = True,
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
        progress["processed_students"] = []
        progress["total_processed"] = 0
        click.echo(f"Updated range to {start} -> {end}")

    start_time = time.time()
    total_processing_time = 0

    failed_pulls: Set[int] = set(progress["failed_pulls"])
    processed_students: Set[int] = set(progress["processed_students"])

    total_range = start - end + 1
    failed_count = len(failed_pulls)
    completed_count = len(processed_students)

    logger.info(
        f"Starting parallel students range pull: {start} -> {end} (Total: {total_range:,} students)"
    )
    logger.info(
        f"Max workers: {max_workers}, Previously failed: {failed_count:,}, Completed: {completed_count:,}"
    )

    click.echo(f"Range: {start} -> {end} (Total: {total_range:,} students)")
    click.echo(f"Max workers: {max_workers}")
    click.echo(f"Failed: {failed_count:,}")
    click.echo(f"Completed: {completed_count:,}")

    remaining_students = [
        std_no
        for std_no in range(start, end - 1, -1)
        if std_no not in processed_students and std_no not in failed_pulls
    ]

    failed_students = [
        std_no for std_no in range(start, end - 1, -1) if std_no in failed_pulls
    ]

    all_students = failed_students + remaining_students

    if not all_students:
        click.secho("All students in range have been processed!", fg="green")
        return

    click.echo(f"Students to process: {len(all_students):,}")
    click.echo(f"Processing with {max_workers} parallel workers...")

    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            students_processed = completed_count

            for std_no in all_students:
                future = executor.submit(
                    process_student_worker, std_no, info_only, use_local, progress
                )
                futures[future] = std_no

            for completed_future in as_completed(futures):
                std_no = futures[completed_future]
                result = completed_future.result()

                students_processed += 1
                total_processing_time += result["processing_time"]

                remaining = len(all_students) - (students_processed - completed_count)
                processed = total_range - remaining
                progress_percent = (processed / total_range) * 100

                time_estimate_str = ""
                if students_processed > completed_count:
                    avg_time_per_student = total_processing_time / (
                        students_processed - completed_count
                    )
                    estimated_remaining_time = avg_time_per_student * remaining
                    time_estimate_str = (
                        f" ETA: {format_time_estimate(estimated_remaining_time)}"
                    )

                status_indicator = "(RETRY)" if std_no in failed_pulls else ""

                with lock:
                    progress["current_position"] = min(
                        std_no, progress.get("current_position", start)
                    )
                    save_progress(progress)

                if result["success"]:
                    click.secho(
                        f"[{processed:,}/{total_range:,}] ({progress_percent:.1f}%){time_estimate_str} "
                        f"✓ Student {std_no} {status_indicator}",
                        fg="green",
                    )
                else:
                    error_msg = (
                        result["error"]
                        if result["error"]
                        else "student_pull returned False"
                    )
                    click.secho(
                        f"[{processed:,}/{total_range:,}] ({progress_percent:.1f}%){time_estimate_str} "
                        f"✗ Student {std_no} {status_indicator}: {error_msg}",
                        fg="red",
                    )

    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        click.echo("\nInterrupted by user. Saving progress...")
    except Exception as e:
        logger.error(f"Unexpected error in parallel processing: {e}")
        click.secho(f"Error: {e}", fg="red")
    finally:
        save_progress(progress)

        end_time = time.time()
        total_time = end_time - start_time

        final_failed = len(progress["failed_pulls"])
        final_completed = len(progress["processed_students"])

        logger.info(
            f"Parallel students range pull completed. Total time: {format_time_estimate(total_time)}"
        )
        logger.info(f"Failed pulls: {final_failed:,} students")
        logger.info(f"Successfully processed: {final_completed:,} students")

        click.echo("\nSummary:")
        click.secho(f"Successfully processed: {final_completed:,} students", fg="green")
        click.secho(f"Failed pulls: {final_failed:,} students", fg="red")

        if progress["failed_pulls"]:
            failed_sample = sorted(progress["failed_pulls"], reverse=True)[:20]
            click.echo(
                f"\nFailed student numbers: {failed_sample}{'...' if len(progress['failed_pulls']) > 20 else ''}"
            )
            click.echo("(Run the command again to retry failed students)")

        remaining_total = total_range - final_completed
        if remaining_total <= 0:
            click.secho("✓ All students completed!", fg="green")
        else:
            click.echo(f"Remaining students to process: {remaining_total:,}")
