import click
from sqlalchemy import and_, func, not_
from sqlalchemy.orm import Session

from registry_cli.commands.enroll.enrollment import enroll_student
from registry_cli.models import RegistrationClearance, RegistrationRequest


def enroll_approved(db: Session) -> None:
    approved_requests = (
        db.query(RegistrationRequest)
        .filter(not_(RegistrationRequest.status.in_(["registered", "rejected"])))
        .filter(
            RegistrationRequest.id.in_(
                db.query(RegistrationClearance.registration_request_id)
                .filter(
                    RegistrationClearance.department.in_(["finance", "library"]),
                    RegistrationClearance.status == "approved",
                )
                .group_by(RegistrationClearance.registration_request_id)
                .having(func.count(RegistrationClearance.registration_request_id) == 2)
            )
        )
        .all()
    )

    if len(approved_requests) == 0:
        click.secho("No approved requests found.", fg="red")
        return

    for i, request in enumerate(approved_requests):
        print()
        print("-" * 30)
        print(f"{i}/{len(approved_requests)}] {request.std_no}")
        try:
            enroll_student(db, request)
            print(f"Successfully enrolled student {request.std_no}")
        except Exception as e:
            click.secho(
                f"Failed to enroll student {request.std_no}: {str(e)}", fg="red"
            )
    click.secho("Done!", fg="green")
