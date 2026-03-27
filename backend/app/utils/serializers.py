from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    return float(value)


def isoformat(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()
