"""Celery task: dispatch a support/feedback ticket email to the support inbox.

Dispatched from the API via ``send_task`` (see ``ice_api/routers/support.py``)
so the SMTP round-trip never blocks the request thread.
"""
from __future__ import annotations

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

from ice_shared import settings

from ice_worker.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="ice_worker.tasks.support_email.send_support_email",
    bind=True,
    autoretry_for=(Exception,),
    max_retries=2,
    retry_backoff=60,
    retry_jitter=False,
)
def send_support_email(
    self: Any,
    submitter_email: str,
    submitter_user_id: int,
    category: str,
    subject: str,
    description: str,
) -> str:
    """Send a support/feedback email to ``settings.support_email``.

    Dev fallback: when SMTP creds or ``support_email`` are unset, log the
    payload to the console and return success (mirrors ``email_service.py``).
    """
    dest = settings.support_email
    if not dest or not settings.smtp_user:
        logger.info(
            "[support-email] (dev fallback — no SMTP/SUPPORT_EMAIL) "
            "from=%s user_id=%s category=%s subject=%s\n%s",
            submitter_email,
            submitter_user_id,
            category,
            subject,
            description,
        )
        return "logged"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[ICE Support][{category}] {subject}"
    msg["From"] = settings.from_email or settings.smtp_user
    msg["To"] = dest
    msg["Reply-To"] = submitter_email

    plain = (
        f"Category: {category}\n"
        f"From: {submitter_email} (user_id={submitter_user_id})\n"
        f"Subject: {subject}\n\n"
        f"{description}\n"
    )
    msg.attach(MIMEText(plain, "plain"))

    html = (
        f"<h3>Support Ticket — {category}</h3>"
        f"<p><b>From:</b> {submitter_email} (user_id={submitter_user_id})</p>"
        f"<p><b>Subject:</b> {subject}</p>"
        f"<hr><pre>{description}</pre>"
    )
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)

    logger.info("support email sent to %s from %s", dest, submitter_email)
    return "sent"
