import logging
import time

import click
from sqlalchemy import and_
from sqlalchemy.orm import Session

from registry_cli.models import RegistrationClearance, Student, User
from registry_cli.utils.email_sender import EmailSender

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def send_notifications(db: Session) -> None:
    """
    Send email notifications to students whose registration clearance has been rejected.

    This command finds all registration clearances with status 'rejected',
    a non-empty message, and email_sent=False, then sends notifications
    to those students.

    Args:
        db: Database session
    """
    try:
        # Query for rejected clearances that haven't been emailed yet
        pending_notifications = (
            db.query(RegistrationClearance)
            .filter(
                and_(
                    RegistrationClearance.status == "rejected",
                    RegistrationClearance.message.isnot(None),
                    RegistrationClearance.message != "",
                    RegistrationClearance.email_sent == False,
                )
            )
            .all()
        )

        if not pending_notifications:
            click.secho("No pending rejection notifications found.", fg="yellow")
            return

        click.secho(
            f"Found {len(pending_notifications)} pending notifications to send.",
            fg="blue",
        )

        # Process each notification
        success_count = 0
        for clearance in pending_notifications:
            # Get the associated registration request
            registration_request = clearance.registration_request
            if not registration_request:
                click.secho(
                    f"Error: Registration request not found for clearance ID {clearance.id}",
                    fg="red",
                )
                continue

            # Get student information
            student = (
                db.query(Student)
                .filter(Student.std_no == registration_request.std_no)
                .first()
            )
            if not student:
                click.secho(
                    f"Error: Student not found for std_no {registration_request.std_no}",
                    fg="red",
                )
                continue

            # Get student email - try to get from user if available
            email = None
            if student.user_id:
                user = db.query(User).filter(User.id == student.user_id).first()
                if user and user.email:
                    email = user.email

            if not email:
                click.secho(
                    f"Warning: No email found for student {student.std_no}, skipping notification",
                    fg="yellow",
                )
                continue

            # Get responder name if available
            responder_name = "Registry Department"
            if clearance.responded_by:
                responder = (
                    db.query(User).filter(User.id == clearance.responded_by).first()
                )
                if responder and responder.name:
                    responder_name = f"{responder.name} - {clearance.department.capitalize()} Department"

            # Prepare email content
            subject = f"Important: Registration Request Update - {clearance.department.capitalize()} Department"

            body = f"""
Dear {student.name},

This is to inform you that your registration request has been reviewed by the {clearance.department.capitalize()} Department.

Unfortunately, your request has been rejected for the following reason:
{clearance.message}

Please contact the {clearance.department.capitalize()} Department as soon as possible to resolve this issue.

Registration request details:
- Student Number: {student.std_no}
- Department: {clearance.department.capitalize()}
- Status: REJECTED

If you have any questions, please reach out to the appropriate department for assistance.

Thank you.

Regards,
{responder_name}
Limkokwing University of Creative Technology
"""

            # HTML version of the email for better formatting
            html_content = f"""
            <html>
            <head>
                <style>
                    body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
                    .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
                    .header {{ background-color: #8B0000; color: white; padding: 25px 20px; text-align: center; }}
                    .header h2 {{ margin: 0; font-size: 22px; letter-spacing: 0.5px; }}
                    .content {{ padding: 25px 20px; }}
                    .student-name {{ font-weight: 600; color: #222; }}
                    .message-box {{ background-color: #fff0f0; border-left: 3px solid #8B0000; padding: 12px; margin: 15px 0; }}
                    .details {{ margin: 20px 0; padding: 15px; background-color: #f7f7f7; border: 1px solid #eaeaea; }}
                    .details-title {{ font-weight: bold; margin-bottom: 10px; color: #222; }}
                    .details div {{ margin: 6px 0; }}
                    .details strong {{ color: #444; }}
                    .note {{ font-style: italic; color: #555; margin: 15px 0; }}
                    .footer {{ font-size: 12px; color: #777; padding: 15px; border-top: 1px solid #eaeaea; background-color: #f9f9f9; text-align: center; }}
                    .signature {{ margin-top: 15px; }}
                    .highlight {{ color: #8B0000; font-weight: bold; }}
                </style>
            </head>
            <body>
                <div class="email-container">
                    <div class="header">
                        <h2>Registration Request Update</h2>
                    </div>
                    <div class="content">
                        <p>Dear <span class="student-name">{student.name}</span>,</p>
                        
                        <p>This is to inform you that your registration request has been reviewed by the <strong>{clearance.department.capitalize()} Department</strong>.</p>
                        
                        <div class="message-box">
                            <p>Unfortunately, your request has been <span class="highlight">REJECTED</span> for the following reason:</p>
                            <p><em>{clearance.message}</em></p>
                            <p>Please contact the {clearance.department.capitalize()} Department as soon as possible to resolve this issue.</p>
                        </div>
                        
                        <div class="details">
                            <div class="details-title">Registration Request Details:</div>
                            <div>Student Number: <strong>{student.std_no}</strong></div>
                            <div>Department: <strong>{clearance.department.capitalize()}</strong></div>
                            <div>Status: <span class="highlight">REJECTED</span></div>
                        </div>
                        
                        <p class="note">If you have any questions, please reach out to the appropriate department for assistance.</p>
                        
                        <p>Thank you.</p>
                        
                        <div class="signature">
                            Regards,<br>
                            <strong>{responder_name}</strong><br>
                            Limkokwing University of Creative Technology
                        </div>
                    </div>
                    <div class="footer">
                        © Limkokwing University of Creative Technology | This is an automated message, please do not reply to this email.
                    </div>
                </div>
            </body>
            </html>
            """

            # Send the email
            click.echo(
                f"Sending notification to {student.name} ({student.std_no}) - {email}"
            )
            success = EmailSender.send_email(
                recipient_email=email,
                subject=subject,
                body=body,
                html_content=html_content,
            )

            if success:
                # Update the database to mark email as sent
                clearance.email_sent = True
                clearance.response_date = (
                    int(time.time())
                    if not clearance.response_date
                    else clearance.response_date
                )
                db.commit()
                success_count += 1
                click.secho(f"✓ Notification sent successfully to {email}", fg="green")
            else:
                click.secho(f"✗ Failed to send notification to {email}", fg="red")

        # Summary
        if success_count > 0:
            click.secho(
                f"\nSummary: {success_count}/{len(pending_notifications)} notifications sent successfully.",
                fg="green",
            )
        else:
            click.secho("\nNo notifications were sent successfully.", fg="red")

    except Exception as e:
        db.rollback()
        click.secho(f"Error: {str(e)}", fg="red")
        logger.error(f"Error sending notifications: {str(e)}")
