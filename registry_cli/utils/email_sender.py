import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Optional

from dotenv import load_dotenv

from registry_cli.utils.logging_config import get_logger

logger = get_logger(__name__)

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "mail.portal.co.ls")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "no-reply@portal.co.ls")


class EmailSender:
    """Class for sending emails with attachments"""

    @staticmethod
    def send_email(
        recipient_email: str,
        subject: str,
        body: str,
        attachments: Optional[List[str]] = None,
        html_content: Optional[str] = None,
    ) -> bool:
        """Send an email with optional attachments.

        Args:
            recipient_email: Email address of the recipient
            subject: Email subject
            body: Email body text
            attachments: List of file paths to attach
            html_content: HTML version of the email body

        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        if not all(
            [SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, SENDER_EMAIL]
        ):
            logger.error(
                "Email configuration is incomplete. Check environment variables."
            )
            return False

        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = SENDER_EMAIL
            msg["To"] = recipient_email
            msg["Subject"] = subject

            msg.attach(MIMEText(body, "plain"))

            if html_content:
                msg.attach(MIMEText(html_content, "html"))

            if attachments:
                for file_path in attachments:
                    if os.path.exists(file_path):
                        with open(file_path, "rb") as attachment:
                            part = MIMEApplication(attachment.read())
                            part.add_header(
                                "Content-Disposition",
                                f"attachment; filename={os.path.basename(file_path)}",
                            )
                            msg.attach(part)
                    else:
                        logger.warning(f"Attachment not found: {file_path}")

            with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USERNAME, SMTP_PASSWORD)
                server.send_message(msg)

            logger.info(f"Email sent successfully to {recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
            return False
