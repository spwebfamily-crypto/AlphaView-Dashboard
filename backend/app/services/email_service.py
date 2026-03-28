from __future__ import annotations

import logging
from pathlib import Path

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
        # Email delivery is disabled - always return False
        return False

    def send_email(
        self,
        *,
        recipient_email: str,
        subject: str,
        text_body: str,
        html_body: str | None = None,
    ) -> None:
        # Email delivery disabled - only logging
        logger.info(
            "email_delivery_logged",
            extra={
                "recipient_email": recipient_email,
                "subject": subject,
                "text_body": text_body,
            },
        )
        return

