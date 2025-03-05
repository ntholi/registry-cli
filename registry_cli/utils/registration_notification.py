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
- Term: {request.sponsor.name if hasattr(request, 'sponsor') and request.sponsor else 'N/A'}
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
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .header {{ background-color: #003366; color: white; padding: 20px; text-align: center; }}
            .content {{ padding: 20px; }}
            .footer {{ font-size: 12px; color: #666; padding: 20px; border-top: 1px solid #eee; }}
            .details {{ margin: 15px 0; }}
            .details div {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="header">
            <h2>Registration Confirmation</h2>
        </div>
        <div class="content">
            <p>Dear {student.name},</p>
            
            <p>Your registration for <strong>Semester {request.semester_number}</strong> has been successfully completed.</p>
            
            <div class="details">
                <strong>Registration Details:</strong>
                <div>Student Number: {student.std_no}</div>
                <div>Term: {request.sponsor.name if hasattr(request, 'sponsor') and request.sponsor else 'N/A'}</div>
                <div>Status: <strong>{request.status.upper()}</strong></div>
                <div>Number of Modules: {len(registered_modules)}</div>
            </div>
            
            <p>Please find attached your official <strong>Proof of Registration</strong>. This document serves as confirmation 
            of your enrollment in the courses listed therein.</p>
            
            <p>If you have any questions or concerns regarding your registration, please contact the Registry office.</p>
            
            <p>Thank you.</p>
        </div>
        <div class="footer">
            <p>
                Regards,<br>
                Registry Department<br>
                Limkokwing University of Creative Technology
            </p>
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
