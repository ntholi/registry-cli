import click
from sqlalchemy.orm import Session

from registry_cli.models.student import Student, StudentProgram, ProgramStatus
from registry_cli.scrapers.student import StudentScraper, StudentProgramScraper


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

        # Pull student programs
        program_scraper = StudentProgramScraper(student_id)
        try:
            program_data = program_scraper.scrape()

            # Get existing programs for this student
            existing_programs = (
                db.query(StudentProgram)
                .filter(StudentProgram.student_id == student.id)
                .all()
            )

            # Create a map of existing programs by name for quick lookup
            existing_program_map = {prog.name: prog for prog in existing_programs}

            # Update or create programs
            for prog in program_data:
                if prog["name"] in existing_program_map:
                    # Update existing program
                    existing_prog = existing_program_map[prog["name"]]
                    existing_prog.status = ProgramStatus(prog["status"])
                else:
                    # Create new program
                    new_program = StudentProgram(
                        code=prog["code"],
                        name=prog["name"],
                        status=ProgramStatus(prog["status"]),
                        student_id=student.id,
                    )
                    db.add(new_program)

            db.commit()
            click.echo(
                f"Successfully pulled {len(program_data)} programs for student: {student}"
            )

        except Exception as e:
            db.rollback()
            click.echo(f"Error pulling student program data: {str(e)}")

    except Exception as e:
        db.rollback()
        click.echo(f"Error pulling student data: {str(e)}")
