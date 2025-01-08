import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.db.config import engine
from registry_cli.models.student import Base, Student

Base.metadata.create_all(bind=engine)


def get_db():
    db = Session(engine)
    try:
        return db
    finally:
        db.close()


@click.group()
def cli() -> None:
    """CLI tool for managing student records"""
    pass


@cli.command()
@click.argument("name", type=str)
def pull(name: str) -> None:
    """Pull a student record from the database by name"""
    db = get_db()
    student = db.query(Student).filter(Student.name == name).first()
    if student:
        click.echo(f"Found student: {student}")
    else:
        click.echo(f"No student found with name: {name}")


@cli.command()
@click.argument("name", type=str)
def push(name: str) -> None:
    """Push a new student record to the database"""
    db = get_db()

    student = Student(id=str(uuid.uuid4()), name=name)
    db.add(student)
    try:
        db.commit()
        click.echo(f"Successfully added student: {student}")
    except Exception as e:
        db.rollback()
        click.echo(f"Error adding student: {str(e)}")


if __name__ == "__main__":
    cli()
