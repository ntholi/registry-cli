import click
from sqlalchemy.orm import Session

from registry_cli.models.student import Student


def student_pull(db: Session, name: str) -> None:
    """Pull a student record from the database by name"""
    student = db.query(Student).filter(Student.name == name).first()
    if student:
        click.echo(f"Found student: {student}")
    else:
        click.echo(f"No student found with name: {name}")
