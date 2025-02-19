from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from registry_cli.commands.enroll.enrollment import enroll_student
from registry_cli.models import RegistrationClearance, RegistrationRequest


def enroll_approved(db: Session) -> None:
    approved_requests = (
        db.query(RegistrationRequest)
        .join(RegistrationClearance)
        .filter(
            and_(
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
        .all()
    )

    if len(approved_requests) == 0:
        print("No approved requests found.")
        return

    for i, request in enumerate(approved_requests):
        print()
        print("-" * 30)
        print(f"{i}/{len(approved_requests)}] {request.std_no}")
        if enroll_student(db, request):
            print(f"Successfully enrolled student {request.std_no}")
        else:
            print(f"Failed to enroll student {request.std_no}")
