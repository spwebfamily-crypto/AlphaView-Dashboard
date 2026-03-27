from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.schemas.logs import SystemLogResponse
from app.services.system_log_service import list_logs

router = APIRouter(prefix="/logs")


@router.get("", response_model=list[SystemLogResponse])
def system_logs(
    limit: int = Query(default=100, le=1000),
    session: Session = Depends(get_db_session),
) -> list[SystemLogResponse]:
    return [
        SystemLogResponse(
            id=row.id,
            level=row.level,
            source=row.source,
            event_type=row.event_type,
            message=row.message,
            context=row.context,
            logged_at=row.logged_at,
        )
        for row in list_logs(session, limit=limit)
    ]

