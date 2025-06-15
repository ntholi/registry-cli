import json
import multiprocessing
import os
import signal
import sys
import time
from typing import Dict, List, Tuple

import click
from sqlalchemy.orm import Session, sessionmaker

from registry_cli.commands.pull.student import student_pull
from registry_cli.db.config import get_engine


def _exit_if_session_rollback(exc: Exception) -> None:
    """Terminate the process immediately if a SQLAlchemy session rollback is detected."""
    if "transaction has been rolled back" in str(exc).lower():
        click.secho(
            "Fatal SQLAlchemy session rollback error detected. Exiting...",
            fg="red",
        )
        sys.exit(1)



def get_db_session(use_local: bool = True):
    engine = get_engine(use_local)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


def format_time_estimate(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f} seconds"
    minutes = seconds / 60
    if minutes < 60:
        return f"{minutes:.1f} minutes"
    hours = minutes / 60
    if hours < 24:
        return f"{hours:.1f} hours"
    days = hours / 24
    if days < 7:
        return f"{days:.1f} days"
    weeks = days / 7
    return f"{weeks:.1f} weeks"


def load_chunk_progress(chunk_id: int) -> Dict:
    progress_file = f"students_range_chunk_{chunk_id}_progress.json"
    if os.path.exists(progress_file):
        try:
            with open(progress_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {
        "failed_pulls": [],
        "current_position": None,
        "start_number": None,
        "end_number": None,
        "chunk_id": chunk_id,
        "completed": False,
    }


def save_chunk_progress(chunk_id: int, progress: Dict) -> None:
    progress_file = f"students_range_chunk_{chunk_id}_progress.json"
    try:
        with open(progress_file, "w") as f:
            json.dump(progress, f, indent=2)
    except IOError:
        pass


def worker_process(
    chunk_id: int,
    start: int,
    end: int,
    info_only: bool,
    use_local: bool,
    reset: bool,
) -> None:
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    try:
        db = get_db_session(use_local)

        if reset:
            progress_file = f"students_range_chunk_{chunk_id}_progress.json"
            if os.path.exists(progress_file):
                os.remove(progress_file)

        progress = load_chunk_progress(chunk_id)

        if (
            progress["start_number"] != start
            or progress["end_number"] != end
            or progress["current_position"] is None
        ):
            progress["start_number"] = start
            progress["end_number"] = end
            progress["current_position"] = start
            progress["completed"] = False

        failed_pulls = set(progress["failed_pulls"])
        current_position = progress["current_position"]

        if progress["completed"] or current_position < end:
            progress["completed"] = True
            save_chunk_progress(chunk_id, progress)
            return

        start_time = time.time()
        total_processing_time = 0
        students_processed = 0
        total_range = start - end + 1
        
        click.echo(f"[Chunk {chunk_id}] Range: {start} -> {end} (Total: {total_range:,} students)")
        click.echo(f"[Chunk {chunk_id}] Failed: {len(failed_pulls):,}")
        click.echo(f"[Chunk {chunk_id}] Current position: {current_position}")

        for std_no in range(current_position, end - 1, -1):
            student_start_time = time.time()

            try:
                success = student_pull(db, std_no, info_only)

                if success:
                    if std_no in failed_pulls:
                        failed_pulls.remove(std_no)
                else:
                    failed_pulls.add(std_no)

            except Exception as e:
                _exit_if_session_rollback(e)
                failed_pulls.add(std_no)

            student_end_time = time.time()
            student_processing_time = student_end_time - student_start_time
            total_processing_time += student_processing_time
            students_processed += 1

            if students_processed % 10 == 0 or std_no in failed_pulls:
                elapsed_time = time.time() - start_time
                remaining = current_position - end
                avg_time_per_student = total_processing_time / students_processed if students_processed > 0 else 0
                estimated_remaining_time = remaining * avg_time_per_student
                progress_percent = (students_processed / total_range) * 100 if total_range > 0 else 0
                
                chunk_total = start - end + 1
                chunk_processed = start - std_no
                
                click.echo(
                    f"[Chunk {chunk_id}] {std_no:,} | "
                    f"{chunk_processed:,}/{chunk_total:,} ({progress_percent:.1f}%) | "
                    f"Avg: {avg_time_per_student:.2f}s | "
                    f"Est: {format_time_estimate(estimated_remaining_time)} | "
                    f"Failed: {len(failed_pulls):,}"
                )

            progress["current_position"] = std_no
            progress["failed_pulls"] = list(failed_pulls)

            if std_no <= end:
                progress["completed"] = True

            save_chunk_progress(chunk_id, progress)
        
        if students_processed > 0:
            elapsed_time = time.time() - start_time
            avg_time_per_student = total_processing_time / students_processed
            click.echo(f"\n[Chunk {chunk_id}] Completed {students_processed:,} students in {format_time_estimate(elapsed_time)}")
            click.echo(f"[Chunk {chunk_id}] Average time per student: {avg_time_per_student:.2f}s")
            
            if failed_pulls:
                click.echo(
                    f"[Chunk {chunk_id}] Failed student numbers: {sorted(failed_pulls, reverse=True)[:10]}{'...' if len(failed_pulls) > 10 else ''}"
                )

    except Exception as e:
        _exit_if_session_rollback(e)
        pass
    finally:
        try:
            db.close()
        except:
            pass


def monitor_progress(chunk_count: int, start: int, end: int) -> None:
    total_range = start - end + 1

    while True:
        time.sleep(5)

        total_processed = 0
        total_failed = 0
        completed_chunks = 0
        all_completed = True

        chunk_statuses = []

        for i in range(chunk_count):
            progress = load_chunk_progress(i)

            if progress["completed"]:
                completed_chunks += 1
                chunk_start = progress.get("start_number", 0)
                chunk_end = progress.get("end_number", 0)
                chunk_range = chunk_start - chunk_end + 1
                chunk_processed = chunk_range
                chunk_remaining = 0
            else:
                all_completed = False
                chunk_start = progress.get("start_number", 0)
                chunk_end = progress.get("end_number", 0)
                current_pos = progress.get("current_position", chunk_start)

                if chunk_start and chunk_end and current_pos:
                    chunk_range = chunk_start - chunk_end + 1
                    chunk_remaining = current_pos - chunk_end + 1
                    chunk_processed = chunk_range - chunk_remaining
                else:
                    chunk_processed = 0
                    chunk_remaining = 0

            chunk_failed = len(progress.get("failed_pulls", []))
            total_processed += chunk_processed
            total_failed += chunk_failed

            chunk_statuses.append(
                {
                    "chunk_id": i,
                    "processed": chunk_processed,
                    "remaining": chunk_remaining,
                    "failed": chunk_failed,
                    "completed": progress["completed"],
                }
            )

        progress_percent = (
            (total_processed / total_range) * 100 if total_range > 0 else 0
        )

        click.clear()
        click.echo("=" * 60)
        click.echo("PARALLEL STUDENTS RANGE PULL - LIVE MONITORING")
        click.echo("=" * 60)
        click.echo(f"Total Range: {start:,} -> {end:,} ({total_range:,} students)")
        click.echo(
            f"Progress: {total_processed:,}/{total_range:,} ({progress_percent:.1f}%)"
        )
        click.echo(f"Failed: {total_failed:,} students")
        click.echo(f"Completed Chunks: {completed_chunks}/{chunk_count}")
        click.echo("-" * 60)

        for status in chunk_statuses:
            chunk_percent = 0
            if status["processed"] + status["remaining"] > 0:
                chunk_percent = (
                    status["processed"] / (status["processed"] + status["remaining"])
                ) * 100

            status_indicator = "✓" if status["completed"] else "⚠"
            click.echo(
                f"Chunk {status['chunk_id']:2d}: {status_indicator} "
                f"{status['processed']:,} processed, {status['remaining']:,} remaining, "
                f"{status['failed']:,} failed ({chunk_percent:.1f}%)"
            )

        if all_completed:
            click.echo("\n" + "=" * 60)
            click.secho("✓ ALL CHUNKS COMPLETED!", fg="green", bold=True)
            click.echo(f"Total processed: {total_processed:,}")
            click.echo(f"Total failed: {total_failed:,}")
            break


def students_range_parallel_pull(
    start: int = 901019990,
    end: int = 901000001,
    chunk_size: int = 500,
    max_workers: int = 10,
    info_only: bool = False,
    use_local: bool = True,
    reset: bool = False,
) -> None:
    if start < end:
        click.secho("Error: Start number must be greater than end number", fg="red")
        return

    if chunk_size <= 0:
        click.secho("Error: Chunk size must be greater than 0", fg="red")
        return

    if max_workers <= 0:
        click.secho("Error: Max workers must be greater than 0", fg="red")
        return

    total_range = start - end + 1

    chunks = []
    current_start = start
    chunk_id = 0

    while current_start > end:
        current_end = max(current_start - chunk_size + 1, end)
        chunks.append((chunk_id, current_start, current_end))
        current_start = current_end - 1
        chunk_id += 1

    actual_workers = min(max_workers, len(chunks))

    click.echo(f"Range: {start} -> {end} (Total: {total_range:,} students)")
    click.echo(f"Chunk size: {chunk_size:,} students per chunk")
    click.echo(f"Total chunks: {len(chunks)}")
    click.echo(f"Workers: {actual_workers}")
    click.echo(f"Environment: {'Local' if use_local else 'Production'}")

    if not click.confirm("\nDo you want to start the parallel pull?", default=True):
        return

    click.echo("\nStarting parallel pull...")

    processes = []

    try:
        for i in range(0, len(chunks), actual_workers):
            batch = chunks[i : i + actual_workers]
            batch_processes = []

            for chunk_id, chunk_start, chunk_end in batch:
                process = multiprocessing.Process(
                    target=worker_process,
                    args=(
                        chunk_id,
                        chunk_start,
                        chunk_end,
                        info_only,
                        use_local,
                        reset,
                    ),
                )
                process.start()
                batch_processes.append(process)
                processes.append(process)

            if i + actual_workers >= len(chunks):
                monitor_process = multiprocessing.Process(
                    target=monitor_progress,
                    args=(len(chunks), start, end),
                )
                monitor_process.start()

                for process in batch_processes:
                    process.join()

                monitor_process.terminate()
                monitor_process.join()
                break
            else:
                for process in batch_processes:
                    process.join()

    except KeyboardInterrupt:
        click.echo("\nInterrupted by user. Terminating all processes...")
        for process in processes:
            if process.is_alive():
                process.terminate()
                process.join()

    click.echo("\nGenerating final summary...")

    total_processed = 0
    total_failed = 0
    all_failed_students = []

    for i in range(len(chunks)):
        progress = load_chunk_progress(i)
        chunk_start = progress.get("start_number", 0)
        chunk_end = progress.get("end_number", 0)

        if progress["completed"]:
            chunk_range = chunk_start - chunk_end + 1
            chunk_processed = chunk_range
        else:
            current_pos = progress.get("current_position", chunk_start)
            if chunk_start and chunk_end and current_pos:
                chunk_range = chunk_start - chunk_end + 1
                chunk_remaining = current_pos - chunk_end + 1
                chunk_processed = chunk_range - chunk_remaining
            else:
                chunk_processed = 0

        chunk_failed = progress.get("failed_pulls", [])
        total_processed += chunk_processed
        total_failed += len(chunk_failed)
        all_failed_students.extend(chunk_failed)

    click.echo("\n" + "=" * 60)
    click.echo("FINAL SUMMARY")
    click.echo("=" * 60)
    click.echo(f"Total students processed: {total_processed:,}")
    click.echo(f"Total failed: {total_failed:,}")

    if all_failed_students:
        click.secho(f"\nFirst 20 failed student numbers:", fg="red")
        for std_no in sorted(all_failed_students, reverse=True)[:20]:
            click.echo(f"  {std_no}")
        if len(all_failed_students) > 20:
            click.echo(f"  ... and {len(all_failed_students) - 20} more")


def cleanup_chunk_files() -> None:
    count = 0
    for filename in os.listdir("."):
        if filename.startswith("students_range_chunk_") and filename.endswith(
            "_progress.json"
        ):
            os.remove(filename)
            count += 1
    click.echo(f"Removed {count} chunk progress files")


def show_parallel_progress() -> None:
    chunk_files = [
        f
        for f in os.listdir(".")
        if f.startswith("students_range_chunk_") and f.endswith("_progress.json")
    ]

    if not chunk_files:
        click.secho("No parallel chunk progress files found.", fg="yellow")
        return

    total_processed = 0
    total_failed = 0
    completed_chunks = 0
    chunk_count = len(chunk_files)

    chunk_statuses = []

    for filename in sorted(chunk_files):
        chunk_id = int(filename.split("_")[3])
        progress = load_chunk_progress(chunk_id)

        if progress["completed"]:
            completed_chunks += 1
            chunk_start = progress.get("start_number", 0)
            chunk_end = progress.get("end_number", 0)
            chunk_range = chunk_start - chunk_end + 1
            chunk_processed = chunk_range
            chunk_remaining = 0
        else:
            chunk_start = progress.get("start_number", 0)
            chunk_end = progress.get("end_number", 0)
            current_pos = progress.get("current_position", chunk_start)

            if chunk_start and chunk_end and current_pos:
                chunk_range = chunk_start - chunk_end + 1
                chunk_remaining = current_pos - chunk_end + 1
                chunk_processed = chunk_range - chunk_remaining
            else:
                chunk_processed = 0
                chunk_remaining = 0

        chunk_failed = len(progress.get("failed_pulls", []))
        total_processed += chunk_processed
        total_failed += chunk_failed

        chunk_statuses.append(
            {
                "chunk_id": chunk_id,
                "start": progress.get("start_number", 0),
                "end": progress.get("end_number", 0),
                "processed": chunk_processed,
                "remaining": chunk_remaining,
                "failed": chunk_failed,
                "completed": progress["completed"],
            }
        )

    click.echo("=" * 80)
    click.echo("PARALLEL STUDENTS RANGE PULL - PROGRESS STATUS")
    click.echo("=" * 80)
    click.echo(f"Total chunks: {chunk_count}")
    click.echo(f"Completed chunks: {completed_chunks}")
    click.echo(f"Total processed: {total_processed:,}")
    click.echo(f"Total failed: {total_failed:,}")
    click.echo("-" * 80)

    for status in sorted(chunk_statuses, key=lambda x: x["chunk_id"]):
        chunk_total = status["processed"] + status["remaining"]
        chunk_percent = (
            (status["processed"] / chunk_total * 100) if chunk_total > 0 else 0
        )
        status_indicator = "✓" if status["completed"] else "⚠"

        click.echo(
            f"Chunk {status['chunk_id']:2d}: {status_indicator} "
            f"{status['start']:,} -> {status['end']:,} | "
            f"{status['processed']:,} processed, {status['remaining']:,} remaining, "
            f"{status['failed']:,} failed ({chunk_percent:.1f}%)"
        )
