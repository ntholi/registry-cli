from tabnanny import check

import click
from sqlalchemy import func
from sqlalchemy.orm import Session

from registry_cli.commands.enroll.enrollment import enroll_student
from registry_cli.models import RegistrationClearance, RegistrationRequest


def enroll_approved(db: Session) -> None:
    approved_requests = (
        db.query(RegistrationRequest)
        .filter(RegistrationRequest.status == "pending")
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
            if len(request.requested_modules) < 1:
                click.secho(
                    f"Skipping request for {request.std_no}, requested for zero modules",
                    fg="yellow",
                )
                continue
            enroll_student(db, request)
            print(f"Successfully enrolled student {request.std_no}")
        except Exception as e:
            click.secho(
                f"Failed to enroll student {request.std_no}: {str(e)}", fg="red"
            )
    click.secho("Done!", fg="green")
