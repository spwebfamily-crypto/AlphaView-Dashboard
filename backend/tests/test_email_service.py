from __future__ import annotations

import logging

import httpx
import pytest

from app.core.config import EmailDeliveryMode, Settings
from app.services.email_service import SmtpEmailService


def test_email_message_includes_html_and_inline_logo() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        email_smtp_host="smtp.gmail.com",
        email_smtp_port=465,
        email_smtp_use_ssl=True,
        email_smtp_username="mailer@example.com",
        email_smtp_password="app-password",
        email_from_email="mailer@example.com",
        email_from_name="AlphaView SMTP System",
    )
    service = SmtpEmailService(settings)
    text_body = "AlphaView status update"
    html_body = "<html><body><img src=\"cid:{{LOGO_CID}}\" alt=\"Logo\" /><p>Status update</p></body></html>"

    message = service._build_email_message(
        recipient_email="user@example.com",
        subject="AlphaView update",
        text_body=text_body,
        html_body=html_body,
    )

    plain_part = message.get_body(preferencelist=("plain",))
    html_part = message.get_body(preferencelist=("html",))

    assert plain_part is not None
    assert html_part is not None
    assert "AlphaView status update" in plain_part.get_content()
    html_content = html_part.get_content()
    assert "Status update" in html_content
    assert "cid:" in html_content
    assert "{{LOGO_CID}}" not in html_content

    related_parts = [part for part in message.walk() if part.get_content_maintype() == "image"]
    assert related_parts
    assert related_parts[0].get_content_type() == "image/svg+xml"


def test_email_can_be_logged_instead_of_sent(caplog: pytest.LogCaptureFixture) -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        email_delivery_mode=EmailDeliveryMode.LOG,
        email_from_email="mailer@example.com",
    )
    service = SmtpEmailService(settings)

    with caplog.at_level(logging.INFO):
        service.send_email(
            recipient_email="user@example.com",
            subject="AlphaView update",
            text_body="Status update 135790",
        )

    assert "email_delivery_logged" in caplog.text
    assert any(getattr(record, "text_body", "").find("135790") >= 0 for record in caplog.records)


def test_email_can_be_sent_via_resend(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_post(url: str, *, headers: dict[str, str], json: dict[str, object], timeout: int) -> httpx.Response:
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return httpx.Response(200, json={"id": "email_test_123"})

    monkeypatch.setattr(httpx, "post", fake_post)

    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        email_delivery_mode=EmailDeliveryMode.RESEND,
        resend_api_key="re_test_key",
        email_from_email="no-reply@example.com",
        email_from_name="AlphaView Dashboard",
    )
    service = SmtpEmailService(settings)
    service.send_email(
        recipient_email="user@example.com",
        subject="AlphaView update",
        text_body="Status update 246810",
        html_body="<html><body><p>Status update 246810</p></body></html>",
    )

    assert captured["url"] == "https://api.resend.com/emails"
    assert captured["timeout"] == settings.request_timeout_seconds
    headers = captured["headers"]
    assert isinstance(headers, dict)
    assert headers["Authorization"] == "Bearer re_test_key"
    payload = captured["json"]
    assert isinstance(payload, dict)
    assert payload["from"] == "AlphaView Dashboard <no-reply@example.com>"
    assert payload["to"] == ["user@example.com"]
    assert payload["subject"] == "AlphaView update"
    assert "246810" in str(payload["text"])
    assert "246810" in str(payload["html"])


def test_resend_requires_api_key_and_from_email() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+pysqlite:///:memory:",
        email_delivery_mode=EmailDeliveryMode.RESEND,
        frontend_base_url="https://alphaview.example.com",
    )
    service = SmtpEmailService(settings)

    with pytest.raises(Exception) as exc_info:
        service.send_email(
            recipient_email="user@example.com",
            subject="AlphaView update",
            text_body="Status update",
        )

    assert "RESEND_API_KEY and EMAIL_FROM_EMAIL" in str(exc_info.value)
