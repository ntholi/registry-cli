import time

import click
from sqlalchemy.orm import sessionmaker

from registry_cli.commands.approve.signups import approve_signups
from registry_cli.commands.check.prerequisites import check_prerequisites
from registry_cli.commands.enroll.approved import enroll_approved
from registry_cli.commands.enroll.student import enroll_by_student_number
from registry_cli.commands.pull.modules import modules_pull
from registry_cli.commands.pull.programs import program_pull
from registry_cli.commands.pull.schools import school_pull
from registry_cli.commands.pull.structures import single_structure_pull, structure_pull
from registry_cli.commands.pull.student import student_pull
from registry_cli.commands.pull.student.semesters import semesters_pull
from registry_cli.commands.pull.student.student_modules import student_modules_pull
from registry_cli.commands.pull.students_range import (
    retry_failed,
    show_progress,
    students_range_pull,
)
from registry_cli.commands.pull.students_range_parallel import (
    cleanup_chunk_files,
    show_parallel_progress,
    students_range_parallel_pull,
)
from registry_cli.commands.push.students import student_push
from registry_cli.commands.send.notifications import send_notifications
from registry_cli.commands.send.proof import send_proof_registration
from registry_cli.commands.update.marks import update_marks_from_excel
from registry_cli.commands.update.module_refs import update_semester_module_refs
from registry_cli.db.config import get_engine


def get_db():
    use_local = input("Choose environment (local/prod)? ").lower().strip() != "prod"
    engine = get_engine(use_local)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@click.group()
def cli() -> None:
    pass


@cli.group()
def pull() -> None:
    pass


@pull.command()
def schools() -> None:
    db = get_db()
    school_pull(db)


@pull.command()
@click.argument("program_id", type=int)
def structures(program_id: int) -> None:
    db = get_db()
    structure_pull(db, program_id)


@pull.command()
@click.argument("structure_id", type=int)
def structure(structure_id: int) -> None:
    db = get_db()
    single_structure_pull(db, structure_id)


@pull.command()
@click.argument("school_id", type=int)
def programs(school_id: int) -> None:
    db = get_db()
    program_pull(db, school_id)


@pull.command()
@click.argument("std_no", type=int)
@click.option(
    "--info",
    is_flag=True,
    help="Only update student information without programs and modules",
)
def student(std_no: int, info: bool) -> None:
    db = get_db()
    student_pull(db, std_no, info)


@pull.command(name="student-semester")
@click.argument("std_nos", type=int, nargs=-1)
@click.option("--term", required=True, help="Academic term (e.g. 2024-07)")
def student_semester(std_nos: tuple[int, ...], term: str) -> None:
    """Pull student semester and modules for a specific term and update in database."""
    db = get_db()
    for i, std_no in enumerate(std_nos):
        print(f"{i+1}/{len(std_nos)}) {std_no}...")
        student_modules_pull(db, std_no, term)


@pull.command()
@click.argument("std_no", type=int)
@click.option("--program", help="Program name filter")
def semesters(std_no: int, program: str) -> None:
    db = get_db()
    semesters_pull(db, std_no, program)


@pull.command()
@click.argument("std_nos", type=int, nargs=-1)
@click.option(
    "--info",
    is_flag=True,
    help="Only update student information without programs and modules",
)
def students(std_nos: tuple[int, ...], info: bool) -> None:
    """Pull multiple student records from the registry system."""
    db = get_db()
    for i, std_no in enumerate(std_nos):
        print(f"{i+1}/{len(std_nos)}) {std_no}...")
        student_pull(db, std_no, info)


@pull.command(name="students-range")
@click.option(
    "--start",
    type=int,
    default=901019990,
    help="Starting student number (default: 901019990)",
)
@click.option(
    "--end",
    type=int,
    default=901000001,
    help="Ending student number (default: 901000001)",
)
@click.option(
    "--info",
    is_flag=True,
    help="Only update student information without programs and modules",
)
@click.option(
    "--reset",
    is_flag=True,
    help="Reset progress and start from beginning",
)
def students_range(start: int, end: int, info: bool, reset: bool) -> None:
    """Pull student records from start number down to end number with progress persistence."""
    db = get_db()
    students_range_pull(db, start, end, info, reset)


@pull.command(name="students-progress")
def students_progress() -> None:
    """Show progress of the students-range command."""
    show_progress()


@pull.command(name="students-retry")
@click.option(
    "--info",
    is_flag=True,
    help="Only update student information without programs and modules",
)
def students_retry(info: bool) -> None:
    """Retry pulling students that previously failed."""
    db = get_db()
    retry_failed(db, info)


@pull.command(name="students-range-parallel")
@click.option(
    "--start",
    type=int,
    default=901019990,
    help="Starting student number (default: 901019990)",
)
@click.option(
    "--end",
    type=int,
    default=901000001,
    help="Ending student number (default: 901000001)",
)
@click.option(
    "--chunk-size",
    type=int,
    default=500,
    help="Number of students per chunk (default: 500)",
)
@click.option(
    "--max-workers",
    type=int,
    default=10,
    help="Maximum number of parallel workers (default: 10)",
)
@click.option(
    "--info",
    is_flag=True,
    help="Only update student information without programs and modules",
)
@click.option(
    "--reset",
    is_flag=True,
    help="Reset progress and start from beginning",
)
def students_range_parallel(
    start: int, end: int, chunk_size: int, max_workers: int, info: bool, reset: bool
) -> None:
    """Pull student records using multiple parallel processes for faster processing."""
    use_local = input("Choose environment (local/prod)? ").lower().strip() != "prod"
    students_range_parallel_pull(
        start, end, chunk_size, max_workers, info, use_local, reset
    )


@pull.command(name="students-parallel-progress")
def students_parallel_progress() -> None:
    """Show progress of the parallel students-range command."""
    show_parallel_progress()


@pull.command(name="students-parallel-cleanup")
def students_parallel_cleanup() -> None:
    """Clean up chunk progress files from parallel students-range command."""
    if click.confirm(
        "This will delete all chunk progress files. Are you sure?", default=False
    ):
        cleanup_chunk_files()


@pull.command()
def modules() -> None:
    """Pull all modules from the registry system."""
    db = get_db()
    modules_pull(db)


@cli.group()
def approve() -> None:
    pass


@approve.command()
def signups() -> None:
    db = get_db()
    try:
        while True:
            print("Running signup approvals...")
            approve_signups(db)
            print("Waiting 5 minutes before next check...")
            time.sleep(5 * 60)
    except KeyboardInterrupt:
        print("\nStopping signup approval loop...")
        db.close()


@cli.command()
@click.argument("name", type=str)
def push(name: str) -> None:
    db = get_db()
    student_push(db, name)


@cli.group()
def enroll() -> None:
    pass


@enroll.command()
def approved() -> None:
    db = get_db()
    try:
        while True:
            print("Running enrollment for approved students...")
            enroll_approved(db)
            print("Waiting 5 minutes before next check...")
            time.sleep(5 * 60)
    except KeyboardInterrupt:
        print("\nStopping enrollment loop...")
        db.close()


@enroll.command(name="student")
@click.argument("std_no", type=int)
def enroll_student(std_no: int) -> None:
    db = get_db()
    enroll_by_student_number(db, std_no)


@cli.group()
def send() -> None:
    """Commands to send documents and notifications."""
    pass


@send.command()
@click.argument("std_no", type=int)
def proof(std_no: int) -> None:
    """Send proof of registration to the specified student."""
    db = get_db()
    send_proof_registration(db, std_no)


@send.command()
def notifications() -> None:
    """Send notifications to students with rejected registration clearances."""
    db = get_db()
    try:
        while True:
            print("Checking for pending notifications...")
            send_notifications(db)
            print("Waiting 15 minutes before next check...")
            time.sleep(15 * 60)
    except KeyboardInterrupt:
        print("\nStopping notifications loop...")
        db.close()


@cli.group()
def update() -> None:
    """Commands for updating existing records."""
    pass


@update.command()
@click.argument("file_path", type=click.Path(exists=True))
def marks(file_path: str) -> None:
    """
    Update student module marks from an Excel file.

    FILE_PATH should be the path to an Excel file with columns:
    ModuleID, Final Mark, and Grade
    """
    db = get_db()
    update_marks_from_excel(db, file_path)


@update.command(name="module-refs")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Only show what would be updated without making actual changes",
)
def update_module_references(dry_run: bool) -> None:
    """
    Update semester_module module_id references by matching codes.

    This command goes through all semester_modules and finds the corresponding
    module by using the code, then assigns the semester_module's module_id
    to the found module's id.
    """
    db = get_db()
    update_semester_module_refs(db, dry_run)


@cli.group()
def check() -> None:
    """Commands for checking and validating data."""
    pass


@check.command()
def prerequisites() -> None:
    db = get_db()
    check_prerequisites(db)


if __name__ == "__main__":
    cli()
