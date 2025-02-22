from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from registry_cli.commands.enroll.enrollment import enroll_student
from registry_cli.models import RegistrationClearance, RegistrationRequest
import click


def enroll_by_student_number(db: Session, std_no: str) -> None:
    registration_request = (
        db.query(RegistrationRequest)
        .join(RegistrationClearance)
        .filter(
            and_(
                RegistrationRequest.std_no == std_no,
                RegistrationRequest.id == RegistrationClearance.registration_request_id,
                RegistrationClearance.status == "approved",
                RegistrationClearance.id.in_(
                    db.query(RegistrationClearance.registration_request_id)
                    .filter(
                        and_(
                            RegistrationClearance.department.in_(
                                ["finance", "library"]
                            ),
                            RegistrationClearance.status == "approved",
                        )
                    )
                    .group_by(RegistrationClearance.registration_request_id)
                    .having(func.count(RegistrationClearance.id) == 2)
                ),
            )
        )
        .first()
    )

    if not registration_request:
        print(f"No approved registration request found for student {std_no}")
        return

    print(f"Processing enrollment for student {std_no}")
    if enroll_student(db, registration_request):
        print(f"Successfully enrolled student {std_no}")
    else:
        click.secho(f"Failed to enroll student {std_no}", fg="red")
