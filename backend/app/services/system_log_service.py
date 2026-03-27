from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.system_log import SystemLog


def log_event(
    session: Session,
    *,
    level: str,
    source: str,
    event_type: str,
    message: str,
    context: dict[str, float | int | str | bool | None] | None = None,
) -> SystemLog:
    entry = SystemLog(
        level=level.upper(),
        source=source,
        event_type=event_type,
        message=message,
        context=context,
        logged_at=datetime.now(timezone.utc),
    )
    session.add(entry)
    session.commit()
    session.refresh(entry)
    return entry


def list_logs(session: Session, limit: int = 100) -> list[SystemLog]:
    return list(
        session.scalars(select(SystemLog).order_by(desc(SystemLog.logged_at)).limit(limit))
    )

