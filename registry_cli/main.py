import uuid

import click
from sqlalchemy.orm import Session, sessionmaker

from registry_cli.browser import BASE_URL
from registry_cli.db.config import engine
from registry_cli.models.course import Course
from registry_cli.models.student import Base, Student
from registry_cli.scrapers.course import CourseScraper

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
    """CLI tool for managing student records"""
    pass


@cli.group()
def pull() -> None:
    """Pull records from various sources"""
    pass


@pull.command()
def courses() -> None:
    """Pull course records from the website"""
    url = f"{BASE_URL}/f_programlist.php?showmaster=1&SchoolID=3"
    scraper = CourseScraper(url)

    try:
        courses_data = scraper.scrape()
        if not courses_data:
            click.echo("No courses found.")
            return

        db = get_db()
        for course_data in courses_data:
            course = Course(
                id=str(uuid.uuid4()),
                code=course_data["code"],
                name=course_data["name"],
                program_id=course_data["program_id"],
            )
            db.add(course)

        db.commit()
        click.echo(f"Successfully added {len(courses_data)} courses to the database.")

    except Exception as e:
        click.echo(f"Error pulling courses: {str(e)}")


@cli.command()
@click.argument("name", type=str)
def student(name: str) -> None:
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
