from typing import List, Set, Tuple

import click
from sqlalchemy.orm import Session

from registry_cli.models import Module, RegistrationRequest, RequestedModule, Student
from registry_cli.utils.email_sender import EmailSender


def send_prerequisite_notification(
    db: Session,
    student: Student,
    request: RegistrationRequest,
    failed_prereqs: List[Tuple[Module, Set[Module]]],
) -> bool:
    """
    Send email notification to student about failed prerequisites.

    Args:
        db: Database session
        student: Student object
        request: Registration request
        failed_prereqs: List of tuples (module, set of failed prerequisites)

    Returns:
        bool: True if email was sent successfully, False otherwise
    """

    email = None
    if student.user_id and hasattr(student, "user") and student.user:
        email = student.user.email

    if not email:
        click.secho(
            f"No email found for student {student.std_no}, cannot send notification",
            fg="red",
        )
        return False

    subject = "Important: Registration Module Prerequisites Not Met"

    body = f"""
Dear {student.name},

Our records indicate that you attempted to register for modules that require prerequisites which you have not yet passed.

The following modules have prerequisite requirements that must be met:

"""

    for module, prereqs in failed_prereqs:
        body += f"MODULE: {module.code} - {module.name}\n"
        body += "MISSING PREREQUISITES:\n"
        for prereq in prereqs:
            body += f"- {prereq.code} - {prereq.name}\n"
        body += "\n"

    body += """
These modules will be REMOVED from your registration request since the prerequisites have not been met.

Please consult with your faculty year leader for guidance on course selection and to ensure proper academic progression.

Thank you.

Regards,
Registry Department
Limkokwing University of Creative Technology
"""

    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; }}
            .header {{ background-color: #222; color: white; padding: 15px; }}
            .content {{ padding: 20px; }}
            .module {{ margin-bottom: 20px; border-left: 4px solid #222; padding-left: 15px; }}
            .module-title {{ font-weight: bold; }}
            .prereq {{ margin-left: 20px; }}
            .warning {{ color: #c00; font-weight: bold; }}
            .footer {{ margin-top: 30px; border-top: 1px solid #eee; padding-top: 15px; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>Registration Prerequisite Alert</h2>
            </div>
            <div class="content">
                <p>Dear {student.name},</p>
                
                <p>Our records indicate that you attempted to register for modules that require prerequisites which you have not yet passed.</p>
                
                <p><strong>The following modules have prerequisite requirements that must be met:</strong></p>
    """

    for module, prereqs in failed_prereqs:
        html_content += f"""
                <div class="module">
                    <div class="module-title">{module.code} - {module.name}</div>
                    <div><strong>Missing Prerequisites:</strong></div>
        """
        for prereq in prereqs:
            html_content += f"""
                    <div class="prereq">• {prereq.code} - {prereq.name}</div>
            """
        html_content += """
                </div>
        """

    html_content += """
                <p class="warning">These modules will be REMOVED from your registration request since the prerequisites have not been met.</p>
                
                <p>Please consult with your academic advisor for guidance on course selection and to ensure proper academic progression.</p>
                
                <p>Thank you.</p>
                
                <div class="footer">
                    Regards,<br>
                    <strong>Registry Department</strong><br>
                    Limkokwing University of Creative Technology
                </div>
            </div>
        </div>
    </body>
    </html>
    """

    success = EmailSender.send_email(
        recipient_email=email,
        subject=subject,
        body=body,
        html_content=html_content,
    )

    if success:
        for module, _ in failed_prereqs:
            requested_module = (
                db.query(RequestedModule)
                .filter(
                    RequestedModule.registration_request_id == request.id,
                    RequestedModule.module_id == module.id,
                )
                .first()
            )
            if requested_module:
                requested_module.status = "rejected"

        db.commit()
        return True

    return False
