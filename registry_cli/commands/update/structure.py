import click
from sqlalchemy.orm import Session

from registry_cli.models import Student


def update_structure_id(db: Session, std_nos: list[int], structure_id: int) -> None:
    """
    Update structure_id for a list of students.

    Args:
        db: Database session
        std_nos: List of student numbers to update
        structure_id: Structure ID to apply to all students
    """
    try:
        # Find all students with the provided student numbers
        students = db.query(Student).filter(Student.std_no.in_(std_nos)).all()

        if not students:
            click.secho(f"No students found with the provided numbers.", fg="yellow")
            return

        # Update each student's structure_id
        for student in students:
            old_structure_id = student.structure_id
            student.structure_id = structure_id
            click.echo(
                f"Updated student {student.std_no} ({student.name}): structure_id {old_structure_id} -> {structure_id}"
            )

        # Commit the changes
        db.commit()

        # Display summary
        click.secho(
            f"Successfully updated structure_id to {structure_id} for {len(students)} out of {len(std_nos)} students",
            fg="green",
        )

        # Show which students were not found if any
        not_found = set(std_nos) - {student.std_no for student in students}
        if not_found:
            click.secho(
                f"The following student numbers were not found: {', '.join(map(str, not_found))}",
                fg="yellow",
            )

    except Exception as e:
        db.rollback()
        click.secho(f"Error updating structure IDs: {str(e)}", fg="red")
