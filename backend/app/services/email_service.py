from __future__ import annotations

import logging
import smtplib
import time
from email.message import EmailMessage
from email.utils import formataddr

from app.core.config import Settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class SmtpEmailService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.email_smtp_host and self.settings.email_from_email)

    def send_email(self, *, recipient_email: str, subject: str, body: str) -> None:
        if not self.enabled:
            raise EmailDeliveryError(
                "Email delivery is not configured. Set Gmail-compatible SMTP credentials first.",
                status_code=503,
            )

        message = EmailMessage()
        message["To"] = recipient_email
        message["From"] = formataddr((self.settings.email_from_name, self.settings.email_from_email or ""))
        message["Subject"] = subject
        message.set_content(body)

        retries = 3
        for attempt in range(retries):
            try:
                if self.settings.email_smtp_use_ssl:
                    smtp_client = smtplib.SMTP_SSL(
                        self.settings.email_smtp_host,
                        self.settings.email_smtp_port,
                        timeout=self.settings.request_timeout_seconds,
                    )
                else:
                    smtp_client = smtplib.SMTP(
                        self.settings.email_smtp_host,
                        self.settings.email_smtp_port,
                        timeout=self.settings.request_timeout_seconds,
                    )

                with smtp_client as client:
                    client.ehlo()
                    if self.settings.email_smtp_use_starttls and not self.settings.email_smtp_use_ssl:
                        client.starttls()
                        client.ehlo()
                    if self.settings.email_smtp_username:
                        client.login(
                            self.settings.email_smtp_username,
                            self.settings.email_smtp_password or "",
                        )
                    client.send_message(message)
                    return
            except (OSError, smtplib.SMTPException) as exc:
                logger.warning("email_delivery_attempt_failed", extra={"attempt": attempt + 1, "error": str(exc)})
                if attempt < retries - 1:
                    time.sleep(0.35 * (attempt + 1))
                    continue
                raise EmailDeliveryError("Email delivery failed after retries.", status_code=502) from exc

    def send_verification_code(
        self,
        *,
        recipient_email: str,
        recipient_name: str | None,
        code: str,
        ttl_minutes: int,
    ) -> None:
        greeting_name = recipient_name or recipient_email
        body = (
            f"Hello {greeting_name},\n\n"
            "Your AlphaView confirmation code is:\n\n"
            f"{code}\n\n"
            f"This code expires in {ttl_minutes} minutes.\n\n"
            "If you did not create this account, you can ignore this email.\n"
        )
        self.send_email(
            recipient_email=recipient_email,
            subject="AlphaView confirmation code",
            body=body,
        )
