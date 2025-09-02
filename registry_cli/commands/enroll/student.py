import click
from sqlalchemy import and_, func, not_, or_
from sqlalchemy.orm import Session

from registry_cli.commands.enroll.enrollment import enroll_student
from registry_cli.models import Clearance, RegistrationClearance, RegistrationRequest


def enroll_by_student_number(db: Session, std_no: int) -> None:
    registration_request = (
        db.query(RegistrationRequest)
        .filter(
            RegistrationRequest.std_no == std_no,
        )
        .filter(
            RegistrationRequest.id.in_(
                db.query(RegistrationClearance.registration_request_id)
                .join(Clearance, RegistrationClearance.clearance_id == Clearance.id)
                .filter(
                    Clearance.department.in_(["finance", "library"]),
                    Clearance.status == "approved",
                )
                .group_by(RegistrationClearance.registration_request_id)
                .having(func.count(RegistrationClearance.registration_request_id) == 2)
            )
        )
        .first()
    )

    if not registration_request:
        print(f"No approved registration request found for student {std_no}")
        return

    print(f"Processing enrollment for student {std_no}")
    try:
        enroll_student(db, registration_request)
        print(f"Successfully enrolled student {std_no}")
    except Exception as e:
        click.secho(f"Failed to enroll student {std_no}: {str(e)}", fg="red")
