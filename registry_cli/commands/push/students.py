import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.models.student import Student


def student_push(db: Session, name: str) -> None:
    """Push a new student record to the database"""
    student = Student(std_no=1234, name=name)  # You'll need to implement proper std_no generation
    db.add(student)
    try:
        db.commit()
        click.echo(f"Successfully added student: {student}")
    except Exception as e:
        db.rollback()
        click.echo(f"Error adding student: {str(e)}")
