from typing import List, Set, Tuple

import click
from sqlalchemy import and_
from sqlalchemy.orm import Session

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
            RegistrationRequest.status == "pending",
        )
        .all()
    )

    if not requests:
        click.secho("No pending registration requests found", fg="yellow")
        return

    issues_found = False
    for request in requests:
        failed_prereqs = get_failed_prerequisites(db, request)
        if failed_prereqs:
            issues_found = True
            student = db.query(Student).filter(Student.std_no == request.std_no).first()
            if student:
                click.echo(f"\nStudent: {student.name} ({student.std_no})")
                click.echo(f"Registration Request ID: {request.id}")
                click.echo("Failed Prerequisites:")
                for module, prereqs in failed_prereqs:
                    click.echo(f"  Module: {module.code} - {module.name}")
                    for prereq in prereqs:
                        click.echo(f"    ↳ {prereq.code} - {prereq.name}")

    if not issues_found:
        click.secho("No prerequisite issues found in pending requests", fg="green")


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
        past_modules = (
            db.query(StudentModule)
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
            for past_module in past_modules:
                failing_grades = ["F", "X", "FX", "DNC", "DNA", "DNS", "PX"]
                if (
                    past_module.module_id == prereq_module.id
                    and past_module.grade not in failing_grades
                ):
                    passed = True
                    break

            if not passed:
                failed_prereqs.add(prereq_module)

        if failed_prereqs:
            module = db.query(Module).filter(Module.id == req_module.module_id).first()
            if module:
                failed_prerequisites.append((module, failed_prereqs))

    return failed_prerequisites
