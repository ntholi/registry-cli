import logging
import time
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from registry_cli.models import RegistrationRequest, Student
from registry_cli.utils.email_sender import EmailSender
from registry_cli.utils.pdf_generator import RegistrationPDFGenerator

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def send_registration_confirmation(
    db: Session,
    request: RegistrationRequest,
    student: Student,
    registered_modules: List[str],
    term: str,
) -> Tuple[bool, Optional[str]]:
    """
    Generate a registration PDF and send an email confirmation to the student.

    Args:
        db: Database session
        request: Registration request
        student: Student information
        registered_modules: List of registered module codes

    Returns:
        tuple: (success, pdf_path) - A tuple containing success status and path to generated PDF
    """
    # Generate the PDF
    pdf_path = RegistrationPDFGenerator.generate_registration_pdf(
        db, request, student, registered_modules
    )

    if not pdf_path:
        logger.error(
            f"Failed to generate registration PDF for student {student.std_no}"
        )
        return False, None

    # Get student email - fallback to user email if student doesn't have one directly
    email = None
    if student.user_id and hasattr(student, "user") and student.user:
        email = student.user.email

    if not email:
        logger.warning(
            f"No email found for student {student.std_no}, cannot send notification"
        )
        return False, pdf_path

    # Prepare email content
    subject = f"Registration Confirmation - Semester {request.semester_number}"

    # Plain text email body
    body = f"""
Dear {student.name},

Your registration for Semester {request.semester_number} has been successfully completed.

Registration details:
- Student Number: {student.std_no}
- Term: {term}
- Sponsor: {request.sponsor.name if hasattr(request, 'sponsor') and request.sponsor else 'N/A'}
- Status: {request.status.upper()}
- Number of Modules: {len(registered_modules)}

Please find attached your official proof of registration. This document serves as confirmation 
of your enrollment in the courses listed therein.

If you have any questions or concerns regarding your registration, please contact the Registry office.

Thank you.

Regards,
Registry Department
Limkokwing University of Creative Technology
"""

    # HTML version of the email for better formatting
    html_content = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 0; background-color: #f4f4f4; }}
            .email-container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 4px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.08); }}
            .header {{ background-color: #222222; color: white; padding: 25px 20px; text-align: center; }}
            .header h2 {{ margin: 0; font-size: 22px; letter-spacing: 0.5px; }}
            .content {{ padding: 25px 20px; }}
            .student-name {{ font-weight: 600; color: #222; }}
            .message-box {{ background-color: #f9f9f9; border-left: 3px solid #444; padding: 12px; margin: 15px 0; }}
            .details {{ margin: 20px 0; padding: 15px; background-color: #f7f7f7; border: 1px solid #eaeaea; }}
            .details-title {{ font-weight: bold; margin-bottom: 10px; color: #222; }}
            .details div {{ margin: 6px 0; }}
            .details strong {{ color: #444; }}
            .note {{ font-style: italic; color: #555; margin: 15px 0; }}
            .footer {{ font-size: 12px; color: #777; padding: 15px; border-top: 1px solid #eaeaea; background-color: #f9f9f9; text-align: center; }}
            .signature {{ margin-top: 15px; }}
            .highlight {{ color: #222; font-weight: bold; }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h2>Registration Confirmation</h2>
            </div>
            <div class="content">
                <p>Dear <span class="student-name">{student.name}</span>,</p>
                
                <div class="message-box">
                    Your registration for <strong>Semester {request.semester_number}</strong> has been successfully completed.
                </div>
                
                <div class="details">
                    <div class="details-title">Registration Details:</div>
                    <div>Student Number: <strong>{student.std_no}</strong></div>
                    <div>Term: <strong>{term}</strong></div>
                    <div>Sponsor: <strong>{request.sponsor.name if hasattr(request, 'sponsor') and request.sponsor else 'N/A'}</strong></div>
                    <div>Status: <span class="highlight">{request.status.upper()}</span></div>
                    <div>Number of Modules: <strong>{len(registered_modules)}</strong></div>
                </div>
                
                <p>Please find attached your official <strong>Proof of Registration</strong>. This document serves as confirmation 
                of your enrollment in the courses listed therein.</p>
                
                <p class="note">If you have any questions or concerns regarding your registration, please contact the Registry office.</p>
                
                <p>Thank you.</p>
                
                <div class="signature">
                    Regards,<br>
                    <strong>Registry Department</strong><br>
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
    success = EmailSender.send_email(
        recipient_email=email,
        subject=subject,
        body=body,
        html_content=html_content,
        attachments=[pdf_path],
    )

    if success:
        logger.info(f"Registration confirmation email sent successfully to {email}")
        # Mark the email as sent in the database
        request.mail_sent = True
        request.updated_at = int(time.time())
        db.commit()
        return True, pdf_path
    else:
        logger.error(f"Failed to send registration confirmation email to {email}")
        return False, pdf_path
