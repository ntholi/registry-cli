from typing import List, Set, Tuple

import click
from sqlalchemy import and_
from sqlalchemy.engine import Row
from sqlalchemy.orm import Session

from registry_cli.commands.check.email_notifications import (
    send_prerequisite_notification,
)
from registry_cli.models import (
    Module,
    ModulePrerequisite,
    RegistrationRequest,
    RequestedModule,
    Student,
    StudentModule,
    StudentProgram,
    StudentSemester,
    Term,
)


def check_prerequisites(db: Session) -> None:
    """
    List students who have registered for modules but failed their prerequisites.
    Options to send email notifications to students about the failed prerequisites.
    """
    # Get active term
    active_term = db.query(Term).filter(Term.is_active == True).first()
    if not active_term:
        click.secho("No active term found", fg="red")
        return

    # Get pending registration requests for current term
    requests = (
        db.query(RegistrationRequest)
        .filter(
            RegistrationRequest.term_id == active_term.id,
        )
        .all()
    )

    if not requests:
        click.secho("No pending registration requests found", fg="yellow")
        return

    issues_found = False
    students_with_prereq_issues = []

    # First, collect all students with failed prerequisites
    for request in requests:
        failed_prereqs = get_failed_prerequisites(db, request)
        if failed_prereqs:
            issues_found = True
            student = db.query(Student).filter(Student.std_no == request.std_no).first()
            if student:
                students_with_prereq_issues.append((student, request, failed_prereqs))

    if not issues_found:
        click.secho("No prerequisite issues found in pending requests", fg="green")
        return

    total_students = len(students_with_prereq_issues)
    click.secho(
        f"\nFound {total_students} students with prerequisite issues", fg="yellow"
    )

    # Now process each student one by one with confirmation prompt
    for idx, (student, request, failed_prereqs) in enumerate(
        students_with_prereq_issues, 1
    ):
        click.echo(
            f"\n{idx}/{total_students}) Student: {student.name} ({student.std_no})"
        )
        click.echo(f"Registration Request ID: {request.id}")
        click.echo("Failed Prerequisites:")

        # Display the failed prerequisites for this student
        for module, prereqs in failed_prereqs:
            click.echo(f"  Module: {module.code} - {module.name}")
            for prereq in prereqs:
                click.echo(f"    ↳ {prereq.code} - {prereq.name}")

        # Prompt for confirmation to send email
        if click.confirm(f"\nSend email notification to this student?", default=False):
            send_prerequisite_notification(db, student, request, failed_prereqs)
            click.secho("Email sent.", fg="green")
        else:
            click.secho("Email not sent.", fg="yellow")


def get_failed_prerequisites(
    db: Session, request: RegistrationRequest
) -> List[Tuple[Module, Set[Module]]]:
    """
    Get list of modules with their failed prerequisites for a registration request.
    """
    failed_prerequisites = []

    # Get all requested modules
    requested_modules = (
        db.query(RequestedModule)
        .filter(RequestedModule.registration_request_id == request.id)
        .all()
    )

    for req_module in requested_modules:
        # Get prerequisites for this module
        prerequisites = (
            db.query(ModulePrerequisite)
            .filter(ModulePrerequisite.module_id == req_module.module_id)
            .all()
        )

        if not prerequisites:
            continue

        # Get all the student's past modules with their grades
        past_modules: List[Row[Tuple[StudentModule, Module]]] = (
            db.query(StudentModule, Module)
            .join(Module, StudentModule.module_id == Module.id)
            .join(StudentSemester)
            .join(
                StudentProgram, StudentSemester.student_program_id == StudentProgram.id
            )
            .filter(StudentProgram.std_no == request.std_no)
            .all()
        )

        # Track failed prerequisites
        failed_prereqs = set()

        for pre in prerequisites:
            prereq_module = (
                db.query(Module).filter(Module.id == pre.prerequisite_id).first()
            )
            if not prereq_module:
                continue

            # Check if student passed this prerequisite
            passed = False
            failing_grades = ["F", "X", "FX", "DNC", "DNA", "DNS", "PP"]
            for row in past_modules:
                student_module: StudentModule
                module: Module
                student_module, module = row._mapping.values()
                module_code = fix_module_code(module.code)
                if (
                    module_code == prereq_module.code
                ) and student_module.grade not in failing_grades:
                    passed = True
                    break

            if not passed:
                failed_prereqs.add(prereq_module)

        if failed_prereqs:
            maybe_module = (
                db.query(Module).filter(Module.id == req_module.module_id).first()
            )
            if maybe_module:
                failed_prerequisites.append((maybe_module, failed_prereqs))

    return failed_prerequisites


def fix_module_code(module_code: str) -> str:
    if module_code == "DDDR110":
        return "DDDR1110"
    return module_code
