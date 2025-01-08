import click
from sqlalchemy.orm import sessionmaker

from registry_cli.commands.pull.courses import course_pull
from registry_cli.commands.pull.students import student_pull
from registry_cli.commands.push.students import student_push
from registry_cli.db.config import engine
from registry_cli.models.student import Base

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
def courses() -> None:
    db = get_db()
    course_pull(db)


@cli.command()
@click.argument("name", type=str)
def student(name: str) -> None:
    db = get_db()
    student_pull(db, name)


@cli.command()
@click.argument("name", type=str)
def push(name: str) -> None:
    db = get_db()
    student_push(db, name)


if __name__ == "__main__":
    cli()
