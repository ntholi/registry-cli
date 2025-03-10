import click
from sqlalchemy.orm import sessionmaker

from registry_cli.commands.approve.signups import approve_signups
from registry_cli.commands.enroll.approved import enroll_approved
from registry_cli.commands.enroll.student import enroll_by_student_number
from registry_cli.commands.pull.modules import modules_pull
from registry_cli.commands.pull.programs import program_pull
from registry_cli.commands.pull.schools import school_pull
from registry_cli.commands.pull.semesters import semesters_pull
from registry_cli.commands.pull.structures import single_structure_pull, structure_pull
from registry_cli.commands.pull.student import student_pull
from registry_cli.commands.push.students import student_push
from registry_cli.commands.send.proof import send_proof_registration
from registry_cli.commands.update.marks import update_marks_from_excel
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


@pull.command()
@click.argument("std_no", type=int)
@click.option("--term", required=True, help="Academic term (e.g. 2024-07)")
def modules(std_no: int, term: str) -> None:
    db = get_db()
    modules_pull(db, std_no, term)


@pull.command()
@click.argument("std_no", type=int)
@click.option("--program", help="Program name filter")
def semesters(std_no: int, program: str) -> None:
    db = get_db()
    semesters_pull(db, std_no, program)


@cli.group()
def approve() -> None:
    pass


@approve.command()
def signups() -> None:
    db = get_db()
    approve_signups(db)


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
    enroll_approved(db)


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


if __name__ == "__main__":
    cli()
