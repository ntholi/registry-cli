import time

import click
from sqlalchemy.orm import sessionmaker

from registry_cli.commands.approve.signups import approve_signups
from registry_cli.commands.check.prerequisites import check_prerequisites
from registry_cli.commands.enroll.approved import enroll_approved
from registry_cli.commands.enroll.student import enroll_by_student_number
from registry_cli.commands.export.registrations import export_program_registrations
from registry_cli.commands.export.students import export_students_by_school
from registry_cli.commands.pull.modules import modules_pull
from registry_cli.commands.pull.programs import program_pull
from registry_cli.commands.pull.schools import school_pull
from registry_cli.commands.pull.structures import single_structure_pull, structure_pull
from registry_cli.commands.pull.student import student_pull
from registry_cli.commands.pull.student.semesters import semesters_pull
from registry_cli.commands.pull.student.student_modules import student_modules_pull
from registry_cli.commands.pull.students_range import students_range_pull
from registry_cli.commands.pull.students_range_parallel import (
    students_range_parallel_pull,
)
from registry_cli.commands.push.students import student_push
from registry_cli.commands.send.notifications import send_notifications
from registry_cli.commands.send.proof import send_proof_registration
from registry_cli.commands.update.marks import update_marks_from_excel
from registry_cli.commands.update.module_grades import create_module_grades
from registry_cli.commands.update.module_refs import update_semester_module_refs
from registry_cli.commands.update.student_module_refs import update_student_module_refs
from registry_cli.commands.update.student_modules import update_student_modules
from registry_cli.commands.update.term_student_modules import (
    update_specific_students_modules,
    update_term_student_modules,
)
from registry_cli.db.config import get_engine
from registry_cli.utils.logging_config import configure_from_env


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
    configure_from_env()


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


@pull.command(name="students-range-parallel")
@click.option(
    "--start",
    type=int,
    default=901013069,
    help="Starting student number (default: 901013069)",
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
@click.option(
    "--max-workers",
    type=int,
    default=10,
    help="Maximum number of parallel workers (default: 10)",
)
def students_range_parallel(
    start: int, end: int, info: bool, reset: bool, max_workers: int
) -> None:
    """Pull student records in parallel from start number down to end number with progress persistence."""
    use_local = input("Choose environment (local/prod)? ").lower().strip() != "prod"
    students_range_parallel_pull(start, end, info, reset, max_workers, use_local)


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


@update.command(name="module-grades")
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed calculation information for each grade created",
)
def update_module_grades(verbose: bool) -> None:
    """
    Calculate and create module grades from assessment marks.

    This command reads all assessment marks and creates module grades by:
    1. Calculating weighted totals based on assessment marks, total marks, and weights
    2. Determining the appropriate grade based on the weighted total
    3. Creating module_grade entries only where they don't already exist

    The weighted total is calculated as the sum of:
    (student_marks / assessment_total_marks) * 100 * (assessment_weight / 100)
    for each assessment in the module.
    """
    db = get_db()
    create_module_grades(db, verbose)


@update.command(name="student-modules")
@click.argument("std_no", type=int)
@click.argument("term", type=str)
def update_student_modules_cmd(std_no: int, term: str) -> None:
    """
    Update a student's module marks and grades from module_grades data.

    This command updates all modules for a student in a specific term by:
    1. Finding the student's semester for the given term
    2. Getting all student modules for that semester
    3. Looking up the corresponding module grades from module_grades table
    4. Updating both the website and database with the new marks and grades

    STD_NO: Student number
    TERM: Academic term (e.g. 2025-02)
    """
    db = get_db()
    update_student_modules(db, std_no, term)


@update.command(name="term-student-modules")
@click.argument("term", type=str)
@click.option(
    "--reset",
    is_flag=True,
    help="Reset progress and start from beginning",
)
def update_term_student_modules_cmd(term: str, reset: bool) -> None:
    """
    Update module marks and grades for all students in a specific term.

    This command processes all students who have semesters in the specified term:
    1. Finds all student semesters for the given term
    2. For each student, updates all their modules using module_grades data
    3. Shows progress with estimated completion time
    4. Saves progress to allow resuming interrupted runs

    TERM: Academic term (e.g. 2025-02)
    """
    db = get_db()
    update_term_student_modules(db, term, reset)


@update.command(name="specific-students-modules")
@click.argument("std_nos", type=int, nargs=-1, required=True)
@click.argument("term", type=str)
@click.option(
    "--reset",
    is_flag=True,
    help="Reset progress and start from beginning",
)
def update_specific_students_modules_cmd(
    std_nos: tuple[int, ...], term: str, reset: bool
) -> None:
    """
    Update module marks and grades for specific students in a specific term.

    This command processes only the specified students who have semesters in the given term:
    1. Validates that the specified students have semesters in the given term
    2. For each student, updates all their modules using module_grades data
    3. Shows progress with estimated completion time
    4. Saves progress to allow resuming interrupted runs

    STD_NOS: List of student numbers (space-separated)
    TERM: Academic term (e.g. 2025-02)
    """
    db = get_db()
    update_specific_students_modules(db, list(std_nos), term, reset)


@update.command(name="student-module-refs")
@click.argument("std_nos", type=int, nargs=-1, required=True)
@click.argument("term", type=str)
@click.argument("module_name", type=str)
@click.argument("new_sem_module_id", type=int)
def update_student_module_refs_cmd(
    std_nos: tuple[int, ...], term: str, module_name: str, new_sem_module_id: int
) -> None:
    """
    Update x_SemModuleID for specific students' modules in a given semester.

    This command updates the semester module reference for all matching modules
    for the specified students in a given term by:
    1. Finding each student's semester for the given term
    2. Finding all modules matching the module name for that semester
    3. Updating the x_SemModuleID field on the website and in the database

    STD_NOS: List of student numbers (space-separated)
    TERM: Academic term (e.g. 2025-02)
    MODULE_NAME: Module name to search for (e.g. "Probability & Statistics")
    NEW_SEM_MODULE_ID: New semester module ID to assign
    """
    db = get_db()
    update_student_module_refs(db, list(std_nos), term, module_name, new_sem_module_id)


@cli.group()
def check() -> None:
    """Commands for checking and validating data."""
    pass


@check.command()
def prerequisites() -> None:
    db = get_db()
    check_prerequisites(db)


@cli.group()
def export() -> None:
    """Commands for exporting data to various formats."""
    pass


@export.command()
def registrations() -> None:
    """Export registration statistics by program and semester to CSV."""
    db = get_db()
    export_program_registrations(db)


@export.command(name="students-by-school")
def students_by_school() -> None:
    """Export registered students by school to Excel with separate sheets."""
    db = get_db()
    export_students_by_school(db)


if __name__ == "__main__":
    cli()
