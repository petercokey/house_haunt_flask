from flask_mail import Message
from flask import current_app
from app import mail

def send_email(subject, recipients, body, html=None):
    """
    Send an email using Flask-Mail.

    Args:
        subject (str): Email subject
        recipients (list[str]): List of recipient emails
        body (str): Plain text content
        html (str, optional): HTML content for rich emails
    """
    if not recipients:
        current_app.logger.warning("No recipients provided for email: %s", subject)
        return False

    msg = Message(
        subject=subject,
        recipients=recipients,
        body=body,
        html=html
    )

    try:
        mail.send(msg)
        current_app.logger.info("Email sent to: %s", recipients)
        return True
    except Exception as e:
        current_app.logger.error("Failed to send email: %s", e)
        return False
