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
from registry_cli.commands.pull.semesters import semesters_pull
from registry_cli.commands.pull.structures import single_structure_pull, structure_pull
from registry_cli.commands.pull.student import student_pull
from registry_cli.commands.pull.student_modules import student_modules_pull
from registry_cli.commands.push.students import student_push
from registry_cli.commands.send.notifications import send_notifications
from registry_cli.commands.send.proof import send_proof_registration
from registry_cli.commands.update.marks import update_marks_from_excel
from registry_cli.commands.update.module_refs import update_semester_module_refs
from registry_cli.commands.update.structure import update_structure_id
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


@update.command(name="student-structure")
@click.argument("std_nos", type=int, nargs=-1)
@click.option(
    "--id",
    required=True,
    type=int,
    help="Structure ID to apply to all students",
)
def update_student_structure(std_nos: tuple[int, ...], id: int) -> None:
    """
    Update structure_id for a list of students.

    std_nos: One or more student numbers to update
    """
    db = get_db()
    update_structure_id(db, list(std_nos), id)


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
