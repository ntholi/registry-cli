import click
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.models import (
    Module,
    RegistrationRequest,
    RequestedModule,
    SemesterModule,
    Student,
    Term,
)
from registry_cli.utils.registration_notification import send_registration_confirmation


def send_proof_registration(db: Session, std_no: int) -> None:
    try:
        student = db.query(Student).filter(Student.std_no == std_no).first()
        if not student:
            click.secho(f"Error: Student {std_no} not found", fg="red")
            return

        active_term = db.query(Term).filter(Term.is_active == True).first()
        if not active_term:
            click.secho("Error: No active term found in the database", fg="red")
            return

        request = (
            db.query(RegistrationRequest)
            .filter(
                and_(
                    RegistrationRequest.std_no == std_no,
                    RegistrationRequest.term_id == active_term.id,
                    RegistrationRequest.status.in_(["registered", "partial"]),
                )
            )
            .order_by(RegistrationRequest.created_at.desc())
            .first()
        )

        if not request:
            click.secho(
                f"Error: No completed registration found for student {std_no} in the active term {active_term.name}",
                fg="red",
            )
            return

        registered_modules = [
            module.code
            for module in db.query(Module.code)
            .join(SemesterModule, Module.id == SemesterModule.module_id)
            .join(
                RequestedModule, SemesterModule.id == RequestedModule.semester_module_id
            )
            .filter(
                and_(
                    RequestedModule.registration_request_id == request.id,
                    RequestedModule.status == "registered",
                )
            )
            .all()
        ]

        if not registered_modules:
            click.secho(
                f"Error: No registered modules found for request ID {request.id}",
                fg="red",
            )
            return

        click.echo(f"Sending registration proof to student {student.name} ({std_no})")
        click.echo(
            f"Term: {active_term.name}, Semester: {request.semester_number}, Modules: {len(registered_modules)}"
        )

        email_sent, pdf_path = send_registration_confirmation(
            db=db,
            request=request,
            student=student,
            registered_modules=registered_modules,
            term=active_term.name,
        )

        if email_sent:
            click.secho("Registration proof sent successfully!", fg="green")
        elif pdf_path:
            click.secho(
                f"Registration PDF generated but email could not be sent. PDF saved at: {pdf_path}",
                fg="yellow",
            )
        else:
            click.secho("Failed to generate registration proof", fg="red")

    except ValueError:
        click.secho(f"Error: Invalid student number format: {std_no}", fg="red")
    except Exception as e:
        click.secho(f"Error: {str(e)}", fg="red")
