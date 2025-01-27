import click
from sqlalchemy.orm import Session

from registry_cli.models.student import Student
from registry_cli.scrapers.student import StudentScraper


def student_pull(db: Session, student_id: int) -> None:
    """Pull a student record from the registry system."""
    scraper = StudentScraper(student_id)

    try:
        student_data = scraper.scrape()

        # Check if student already exists
        student = (
            db.query(Student).filter(Student.std_no == student_data["std_no"]).first()
        )
        if student:
            # Update existing student
            for key, value in student_data.items():
                setattr(student, key, value)
        else:
            # Create new student
            student = Student(**student_data)
            db.add(student)

        db.commit()
        click.echo(
            f"Successfully {'updated' if student else 'added'} student: {student}"
        )

    except Exception as e:
        db.rollback()
        click.echo(f"Error pulling student data: {str(e)}")
