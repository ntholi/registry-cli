import json
import os
from typing import Dict, Set

import click
from sqlalchemy.orm import Session

from registry_cli.commands.pull.student import student_pull

PROGRESS_FILE = "students_range_progress.json"


def load_progress() -> Dict:
    """Load progress from the JSON file."""
    if os.path.exists(PROGRESS_FILE):
        try:
            with open(PROGRESS_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
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
    """Save progress to the JSON file."""
    try:
        with open(PROGRESS_FILE, "w") as f:
            json.dump(progress, f, indent=2)
    except IOError as e:
        click.secho(f"Warning: Could not save progress: {e}", fg="yellow")


def students_range_pull(
    db: Session,
    start: int = 901019990,
    end: int = 901000001,
    info_only: bool = False,
    reset: bool = False,
) -> None:
    """Pull student records from start number down to end number with progress persistence."""

    if start < end:
        click.secho("Error: Start number must be greater than end number", fg="red")
        return

    if reset and os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)
        click.echo("Progress file reset")

    progress = load_progress()

    # Update range if different from saved progress
    if progress["start_number"] != start or progress["end_number"] != end:
        progress["start_number"] = start
        progress["end_number"] = end
        progress["current_position"] = start
        click.echo(f"Updated range to {start} -> {end}")

    failed_pulls: Set[int] = set(progress["failed_pulls"])
    current_position: int = progress["current_position"]

    total_range = start - end + 1
    failed_count = len(failed_pulls)

    click.echo(f"Range: {start} -> {end} (Total: {total_range:,} students)")
    click.echo(f"Failed: {failed_count:,}")
    click.echo(f"Current position: {current_position}")

    if current_position < end:
        click.secho("All students in range have been processed!", fg="green")
        return

    try:
        for std_no in range(current_position, end - 1, -1):
            remaining = std_no - end + 1
            processed = total_range - remaining
            progress_percent = (processed / total_range) * 100

            click.echo(
                f"[{processed:,}/{total_range:,}] ({progress_percent:.1f}%) Processing student {std_no}..."
            )

            try:
                success = student_pull(db, std_no, info_only)

                if success:
                    if std_no in failed_pulls:
                        failed_pulls.remove(std_no)
                    click.secho(f"✓ Successfully pulled student {std_no}", fg="green")
                else:
                    failed_pulls.add(std_no)
                    click.secho(f"✗ Failed to pull student {std_no}", fg="red")

            except KeyboardInterrupt:
                click.echo("\nInterrupted by user. Saving progress...")
                break
            except Exception as e:
                failed_pulls.add(std_no)
                click.secho(f"✗ Error pulling student {std_no}: {str(e)}", fg="red")

            # Update progress
            progress["current_position"] = std_no
            progress["failed_pulls"] = list(failed_pulls)
            save_progress(progress)

    finally:
        # Final progress update
        progress["failed_pulls"] = list(failed_pulls)
        save_progress(progress)

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


def show_progress() -> None:
    """Show current progress without pulling any students."""
    if not os.path.exists(PROGRESS_FILE):
        click.secho(
            "No progress file found. Run the students-range command first.", fg="yellow"
        )
        return

    progress = load_progress()

    start = progress["start_number"]
    end = progress["end_number"]
    failed_pulls = set(progress["failed_pulls"])
    current_position = progress["current_position"]

    total_range = start - end + 1
    failed_count = len(failed_pulls)
    remaining = current_position - end + 1
    processed = total_range - remaining
    progress_percent = (processed / total_range) * 100

    click.echo("=" * 50)
    click.echo("PROGRESS STATUS")
    click.echo("=" * 50)
    click.echo(f"Range: {start:,} -> {end:,} (Total: {total_range:,} students)")
    click.echo(f"Current position: {current_position:,}")
    click.echo(f"Progress: {processed:,}/{total_range:,} ({progress_percent:.1f}%)")
    click.secho(f"Failed pulls: {failed_count:,} students", fg="red")

    if current_position < end:
        click.secho("✓ All students completed!", fg="green")
    else:
        click.echo(f"Remaining: {remaining:,} students")

    if failed_pulls:
        click.echo(
            f"\nSample failed student numbers: {sorted(failed_pulls, reverse=True)[:10]}"
        )


def retry_failed(db: Session, info_only: bool = False) -> None:
    """Retry pulling students that previously failed."""
    if not os.path.exists(PROGRESS_FILE):
        click.secho(
            "No progress file found. Run the students-range command first.", fg="yellow"
        )
        return

    progress = load_progress()
    failed_pulls = set(progress["failed_pulls"])

    if not failed_pulls:
        click.secho("No failed pulls to retry!", fg="green")
        return

    click.echo(f"Retrying {len(failed_pulls)} failed student pulls...")

    retry_count = 0

    for std_no in sorted(failed_pulls, reverse=True):
        click.echo(f"Retrying student {std_no}...")

        try:
            success = student_pull(db, std_no, info_only)

            if success:
                failed_pulls.remove(std_no)
                retry_count += 1
                click.secho(f"✓ Successfully pulled student {std_no}", fg="green")
            else:
                click.secho(f"✗ Still failed to pull student {std_no}", fg="red")

        except Exception as e:
            click.secho(f"✗ Error retrying student {std_no}: {str(e)}", fg="red")

    # Update progress
    progress["failed_pulls"] = list(failed_pulls)
    save_progress(progress)

    click.echo(f"\nRetry completed: {retry_count} students now successful")
    click.echo(f"Still failed: {len(failed_pulls)} students")
