"""
Sends the admin a "the bot couldn't answer this — please update the docs"
email. Uses plain smtplib (works with Gmail app passwords, SendGrid SMTP,
Mailgun SMTP, etc.) so there's no extra SDK/dependency to add.

If SMTP isn't configured (smtp_host/admin_notify_email left blank, which is
the default), this quietly logs to the console instead of raising — so the
app still works out of the box before anyone's set up email, and a flaky
mail provider can never take down the chat endpoint.
"""
import logging
import smtplib
from email.message import EmailMessage

from app.config import settings

logger = logging.getLogger("notifications")


def notify_unanswered_question(question: str, standalone_question: str, top_score: float | None):
    subject = f"[{settings.institution_name}] Bot couldn't answer a question"
    score_line = f"{top_score:.2f}" if top_score is not None else "no relevant match found"
    body = (
        f"A user asked a question the knowledge base couldn't confidently answer.\n\n"
        f"Question: {question}\n"
        f"Interpreted as: {standalone_question}\n"
        f"Best retrieval match score: {score_line}\n\n"
        f"If this is something students should be able to ask, consider uploading or "
        f"updating a document that covers it — the bot will be able to answer it "
        f"immediately after the next upload, no other changes needed.\n\n"
        f"View all flagged questions in the admin dashboard under 'Unanswered questions'."
    )
    _send(subject, body)


def _send(subject: str, body: str):
    if not settings.smtp_host or not settings.admin_notify_email:
        logger.info("Email notification skipped (SMTP not configured): %s", subject)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from_email or settings.smtp_user
    msg["To"] = settings.admin_notify_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception:
        # Never let a broken mail server take down a chat request — this
        # runs from a FastAPI background task, well after the response was
        # already sent to the user.
        logger.exception("Failed to send admin notification email")
