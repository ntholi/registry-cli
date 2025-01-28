import click
from sqlalchemy.orm import Session

from registry_cli.models.student import (
    ProgramStatus,
    SemesterStatus,
    Student,
    StudentProgram,
    StudentSemester,
)
from registry_cli.scrapers.student import (
    StudentProgramScraper,
    StudentScraper,
    StudentSemesterScraper,
)


def student_pull(db: Session, student_id: int) -> None:
    """Pull a student record from the registry system."""
    scraper = StudentScraper(student_id)

    try:
        student_data = scraper.scrape()
        student = (
            db.query(Student).filter(Student.std_no == student_data["std_no"]).first()
        )
        if student:
            for key, value in student_data.items():
                setattr(student, key, value)
        else:
            student = Student(**student_data)
            db.add(student)

        db.commit()
        click.echo(
            f"Successfully {'updated' if student else 'added'} student: {student}"
        )

        program_scraper = StudentProgramScraper(student_id)
        try:
            program_data = program_scraper.scrape()
            existing_programs = (
                db.query(StudentProgram)
                .filter(StudentProgram.student_id == student.id)
                .all()
            )
            existing_program_map = {prog.name: prog for prog in existing_programs}

            for prog in program_data:
                program = existing_program_map.get(prog["name"])
                if program:
                    program.status = ProgramStatus(prog["status"])
                else:
                    program = StudentProgram(
                        code=prog["code"],
                        name=prog["name"],
                        status=ProgramStatus(prog["status"]),
                        student_id=student.id,
                    )
                    db.add(program)
                db.commit()

                # Pull semesters for this program
                try:
                    semester_scraper = StudentSemesterScraper(prog["id"])
                    semester_data = semester_scraper.scrape()

                    existing_semesters = (
                        db.query(StudentSemester)
                        .filter(StudentSemester.student_program_id == program.id)
                        .all()
                    )

                    existing_semester_map = {
                        sem.term: sem for sem in existing_semesters
                    }

                    for sem in semester_data:
                        if sem["term"] in existing_semester_map:
                            existing_sem = existing_semester_map[sem["term"]]
                            existing_sem.status = sem["status"]
                        else:
                            new_semester = StudentSemester(
                                term=sem["term"],
                                status=sem["status"],
                                student_program_id=program.id,
                            )
                            db.add(new_semester)

                    db.commit()
                    click.echo(
                        f"Successfully pulled {len(semester_data)} semesters for program: {program.name}"
                    )

                except Exception as e:
                    db.rollback()
                    click.echo(
                        f"Error pulling semester data for program {program.name}: {str(e)}"
                    )

            click.echo(
                f"Successfully pulled {len(program_data)} programs for student: {student}"
            )

        except Exception as e:
            db.rollback()
            click.echo(f"Error pulling student program data: {str(e)}")

    except Exception as e:
        db.rollback()
        click.echo(f"Error pulling student data: {str(e)}")
