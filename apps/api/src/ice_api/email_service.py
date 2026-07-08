from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from ice_shared import settings

log = logging.getLogger(__name__)


async def send_verification_email(email: str, code: str, name: str) -> bool:
    """
    Send a 6-digit verification code to the user's email.
    Falls back to console logging when SMTP credentials are not configured.
    """
    if not settings.smtp_user or not settings.smtp_password:
        log.warning(
            "SMTP not configured — verification code for %s: %s", email, code
        )
        print(f"\n{'=' * 50}\n  VERIFICATION CODE for {email}: {code}\n{'=' * 50}\n")
        return True

    try:
        subject = "Verify Your Email – Interactive Curriculum Engine"
        html_body = f"""
        <html>
        <body style="font-family: 'Inter', sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="text-align: center; padding: 40px 0;">
                <h1 style="color: #4F46E5;">Interactive Curriculum Engine</h1>
                <p style="font-size: 18px; color: #1A1A2E;">Hi {name},</p>
                <p style="color: #555;">Thank you for signing up! Please use the code below to verify your email address.</p>
                <div style="background: #F0F4FF; padding: 20px; border-radius: 12px; margin: 20px 0; text-align: center;">
                    <span style="font-size: 36px; font-weight: 700; letter-spacing: 8px; color: #4F46E5;">
                        {code}
                    </span>
                </div>
                <p style="color: #888; font-size: 14px;">This code will expire in 10 minutes.</p>
                <p style="color: #888; font-size: 14px; margin-top: 20px;">If you didn't request this, please ignore this email.</p>
            </div>
        </body>
        </html>
        """

        from_addr = settings.from_email or settings.smtp_user
        msg = MIMEMultipart()
        msg["From"] = from_addr
        msg["To"] = email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
        return True
    except Exception as e:
        log.error("Email sending failed for %s: %s", email, e)
        print(f"\n{'=' * 50}\n  VERIFICATION CODE for {email}: {code}\n{'=' * 50}\n")
        return False
