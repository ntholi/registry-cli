import click
from sqlalchemy.orm import Session

from registry_cli.models.student import (
    ModuleStatus,
    ModuleType,
    ProgramStatus,
    SemesterStatus,
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
                        semester = existing_semester_map.get(sem["term"])
                        if semester:
                            semester.status = SemesterStatus(sem["status"])
                        else:
                            semester = StudentSemester(
                                term=sem["term"],
                                status=SemesterStatus(sem["status"]),
                                student_program=program,
                            )
                            db.add(semester)
                        db.commit()

                        # Scrape and save modules for this semester
                        module_scraper = StudentModuleScraper(semester.id)
                        try:
                            module_data = module_scraper.scrape()
                            existing_modules = (
                                db.query(StudentModule)
                                .filter(StudentModule.student_semester_id == semester.id)
                                .all()
                            )
                            existing_module_map = {mod.code: mod for mod in existing_modules}

                            for mod in module_data:
                                module = existing_module_map.get(mod["code"])
                                if module:
                                    module.name = mod["name"]
                                    module.type = ModuleType(mod["type"])
                                    module.status = ModuleStatus(mod["status"])
                                    module.credits = mod["credits"]
                                    module.marks = mod["marks"]
                                    module.grade = mod["grade"]
                                else:
                                    module = StudentModule(
                                        code=mod["code"],
                                        name=mod["name"],
                                        type=ModuleType(mod["type"]),
                                        status=ModuleStatus(mod["status"]),
                                        credits=mod["credits"],
                                        marks=mod["marks"],
                                        grade=mod["grade"],
                                        student_semester=semester,
                                    )
                                    db.add(module)
                            db.commit()
                            click.echo(
                                f"Successfully saved {len(module_data)} modules for semester {semester.term}"
                            )
                        except Exception as e:
                            click.echo(f"Error scraping modules: {str(e)}", err=True)

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
