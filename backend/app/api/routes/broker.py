from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_db_session
from app.models.order import Order
from app.models.symbol import Symbol
from app.schemas.broker import (
    BrokerStatusResponse,
    ExecutionResponse,
    OrderCreateRequest,
    OrderResponse,
    PositionResponse,
)
from app.utils.serializers import to_float

router = APIRouter(prefix="/broker")


class _BrokerServiceProxy:
    def __getattr__(self, name: str):
        from app.services import broker_service as service

        return getattr(service, name)


broker_service = _BrokerServiceProxy()


@router.get("/status", response_model=BrokerStatusResponse)
def status(request: Request) -> BrokerStatusResponse:
    connected, details = broker_service.broker_status(request.app.state.settings)
    return BrokerStatusResponse(
        adapter=request.app.state.settings.broker_adapter,
        mode=request.app.state.settings.execution_mode.value,
        connected=connected,
        details=details,
    )


@router.post("/orders", response_model=OrderResponse)
def place_order(
    payload: OrderCreateRequest,
    request: Request,
    session: Session = Depends(get_db_session),
) -> OrderResponse:
    row = broker_service.place_simulated_order(
        session,
        request.app.state.settings,
        symbol=payload.symbol,
        side=payload.side,
        quantity=payload.quantity,
        order_type=payload.order_type,
        limit_price=payload.limit_price,
    )
    return _serialize_order(session, row)


@router.post("/orders/{order_id}/cancel", response_model=OrderResponse)
def cancel_order(order_id: int, session: Session = Depends(get_db_session)) -> OrderResponse:
    return _serialize_order(session, broker_service.cancel_order(session, order_id))


@router.get("/orders", response_model=list[OrderResponse])
def list_orders(session: Session = Depends(get_db_session)) -> list[OrderResponse]:
    return [_serialize_order(session, row) for row, _ in broker_service.list_orders(session)]


@router.get("/positions", response_model=list[PositionResponse])
def positions(session: Session = Depends(get_db_session)) -> list[PositionResponse]:
    symbols = {row.id: row.ticker for row in session.scalars(select(Symbol))}
    return [
        PositionResponse(
            id=row.id,
            symbol=symbols.get(row.symbol_id, "UNKNOWN"),
            status=row.status,
            quantity=to_float(row.quantity) or 0.0,
            average_price=to_float(row.average_price),
            market_value=to_float(row.market_value),
            unrealized_pnl=to_float(row.unrealized_pnl),
            realized_pnl=to_float(row.realized_pnl),
            opened_at=row.opened_at,
        )
        for row in broker_service.list_positions(session)
    ]


@router.get("/executions", response_model=list[ExecutionResponse])
def executions(session: Session = Depends(get_db_session)) -> list[ExecutionResponse]:
    return [
        ExecutionResponse(
            id=row.id,
            order_id=row.order_id,
            executed_at=row.executed_at,
            price=to_float(row.price) or 0.0,
            quantity=to_float(row.quantity) or 0.0,
            fees=to_float(row.fees),
        )
        for row in broker_service.list_executions(session)
    ]


def _serialize_order(session: Session, row: Order) -> OrderResponse:
    symbol = session.scalar(select(Symbol).where(Symbol.id == row.symbol_id))
    return OrderResponse(
        id=row.id,
        symbol=(symbol.ticker if symbol else "UNKNOWN"),
        side=row.side,
        order_type=row.order_type,
        quantity=to_float(row.quantity) or 0.0,
        limit_price=to_float(row.limit_price),
        status=row.status,
        mode=row.mode,
        submitted_at=row.submitted_at,
    )
