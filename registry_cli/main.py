import click
from sqlalchemy.orm import sessionmaker

from registry_cli.commands.approve.signups import approve_signups
from registry_cli.commands.pull.programs import program_pull
from registry_cli.commands.pull.structures import structure_pull
from registry_cli.commands.pull.student import student_pull
from registry_cli.commands.push.students import student_push
from registry_cli.db.config import engine
from registry_cli.models import Base

Base.metadata.create_all(bind=engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
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
@click.argument("program_id", type=int)
def structures(program_id: int) -> None:
    db = get_db()
    structure_pull(db, program_id)


@pull.command()
@click.argument("school_id", type=int)
def programs(school_id: int) -> None:
    db = get_db()
    program_pull(db, school_id)


@pull.command()
@click.argument("student_id", type=int)
def student(student_id: int) -> None:
    db = get_db()
    student_pull(db, student_id)


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


if __name__ == "__main__":
    cli()
