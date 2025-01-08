import uuid

import click
from sqlalchemy.orm import Session

from registry_cli.browser import BASE_URL
from registry_cli.models.course import Course
from registry_cli.scrapers.course import CourseScraper


def course_pull(db: Session) -> None:
    """Pull course records from the website"""
    url = f"{BASE_URL}/f_programlist.php?showmaster=1&SchoolID=3"
    scraper = CourseScraper(url)

    try:
        courses_data = scraper.scrape()
        if not courses_data:
            click.echo("No courses found.")
            return

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
