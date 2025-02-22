import click
from sqlalchemy.orm import Session

from registry_cli.models import (
    Module,
    Student,
    StudentModule,
    StudentProgram,
    StudentSemester,
)
from registry_cli.scrapers.student import (
    StudentModuleScraper,
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

        program_scraper = StudentProgramScraper(db, student_id)
        try:
            program_data = program_scraper.scrape()
            for prog in program_data:
                program = (
                    db.query(StudentProgram)
                    .filter(StudentProgram.id == prog["id"])
                    .first()
                )
                if program:
                    program.status = prog["status"]
                    program.structure_id = prog["structure_id"]
                    program.start_term = prog["start_term"]
                    program.stream = prog["stream"]
                    program.assist_provider = prog["assist_provider"]
                    program.std_no = student.std_no
                else:
                    program = StudentProgram(
                        id=prog["id"],
                        start_term=prog["start_term"],
                        structure_id=prog["structure_id"],
                        stream=prog["stream"],
                        status=prog["status"],
                        assist_provider=prog["assist_provider"],
                        std_no=student.std_no,
                    )
                    db.add(program)
                db.commit()

                try:
                    semester_scraper = StudentSemesterScraper(program.id)
                    semester_data = semester_scraper.scrape()

                    db.query(StudentSemester).filter(
                        StudentSemester.student_program_id == program.id
                    ).delete()
                    db.commit()

                    for sem in semester_data:
                        semester = StudentSemester(
                            id=sem["id"],
                            term=sem["term"],
                            status=sem["status"],
                            semester_number=sem["semester_number"],
                            student_program_id=program.id,
                        )
                        db.add(semester)
                        db.commit()

                        module_scraper = StudentModuleScraper(semester.id)
                        try:
                            module_data = module_scraper.scrape()
                            db.query(StudentModule).filter(
                                StudentModule.student_semester_id == semester.id
                            ).delete()
                            db.commit()
                            for mod in module_data:
                                db_module = (
                                    db.query(Module)
                                    .filter(
                                        # I did this because if a module has been deleted in the program structure
                                        # that module will not show the code and name of that module when in the
                                        # student academic/semesters/modules view
                                        # Ideally this query should just be: filter(Module.code == mod["code"])
                                        Module.id == int(mod["code"])
                                        if mod["code"].isdigit()
                                        else Module.code == mod["code"]
                                    )
                                    .first()
                                )
                                if not db_module:
                                    raise ValueError(
                                        f"Module with code {mod['code']} not found"
                                    )
                                module = StudentModule(
                                    id=mod["id"],
                                    status=mod["status"],
                                    marks=mod["marks"],
                                    grade=mod["grade"],
                                    module_id=db_module.id,
                                    semester=semester,
                                )
                                db.add(module)
                            db.commit()
                            click.echo(
                                f"Successfully saved {len(module_data)} modules for semester {semester.term}"
                            )
                        except Exception as e:
                            click.echo(f"Error scraping modules: {str(e)}", err=True)

                    click.echo(
                        f"Successfully pulled {len(semester_data)} semesters for program: {program.id}"
                    )

                except Exception as e:
                    db.rollback()
                    click.echo(
                        f"Error pulling semester data for program {program.id}: {str(e)}"
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
