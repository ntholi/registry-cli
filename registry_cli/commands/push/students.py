import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.models.student import Student


def student_push(db: Session, name: str) -> None:
    """Push a new student record to the database"""
    student = Student(id=str(uuid.uuid4()), name=name)
    db.add(student)
    try:
        db.commit()
        click.echo(f"Successfully added student: {student}")
    except Exception as e:
        db.rollback()
        click.echo(f"Error adding student: {str(e)}")
