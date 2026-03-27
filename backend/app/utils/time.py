from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

EASTERN_TZ = ZoneInfo("America/New_York")
UTC = timezone.utc


def ensure_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def parse_iso_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return ensure_utc(parsed)


def session_window_for_date(session_date: date) -> tuple[datetime, datetime]:
    session_open = datetime.combine(session_date, time(9, 30), tzinfo=EASTERN_TZ).astimezone(UTC)
    session_close = datetime.combine(session_date, time(16, 0), tzinfo=EASTERN_TZ).astimezone(UTC)
    return session_open, session_close


def infer_session_flags(timestamp: datetime) -> tuple[int, int, int]:
    localized = ensure_utc(timestamp).astimezone(EASTERN_TZ)
    clock = localized.time()
    if time(4, 0) <= clock < time(9, 30):
        return 1, 0, 0
    if time(9, 30) <= clock < time(16, 0):
        return 0, 1, 0
    if time(16, 0) <= clock <= time(20, 0):
        return 0, 0, 1
    return 0, 0, 0


def generate_intraday_timestamps(start: datetime, end: datetime, step_minutes: int) -> list[datetime]:
    current = ensure_utc(start)
    finish = ensure_utc(end)
    timestamps: list[datetime] = []
    while current.date() <= finish.date():
        if current.weekday() < 5:
            session_open, session_close = session_window_for_date(current.date())
            cursor = max(session_open, current)
            while cursor < session_close and cursor <= finish:
                timestamps.append(cursor)
                cursor += timedelta(minutes=step_minutes)
        current = datetime.combine(current.date() + timedelta(days=1), time(0, 0), tzinfo=UTC)
    return timestamps


def timeframe_to_minutes(timeframe: str) -> int:
    normalized = timeframe.lower().strip()
    if normalized.endswith("min"):
        return int(normalized.replace("min", ""))
    if normalized in {"1h", "60min"}:
        return 60
    if normalized == "1day":
        return 390
    raise ValueError(f"Unsupported timeframe: {timeframe}")

