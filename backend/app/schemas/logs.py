from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class SystemLogResponse(BaseModel):
    id: int
    level: str
    source: str
    event_type: str
    message: str
    context: dict[str, float | int | str | bool | None] | None = None
    logged_at: datetime
