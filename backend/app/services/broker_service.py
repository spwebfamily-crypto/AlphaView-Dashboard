from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, desc, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.execution import Execution
from app.models.market_bar import MarketDataBar
from app.models.order import Order
from app.models.position import Position
from app.models.symbol import Symbol
from app.services.ibkr.client import IbkrStatusProbe
from app.services.market_data_service import ensure_symbol, latest_price
from app.services.system_log_service import log_event


@dataclass(slots=True)
class SimulationExecutionPlan:
    should_fill: bool
    fill_price: float | None
    fees: float
    executed_at: datetime | None
    liquidity: str
    note: str


def broker_status(settings: Settings) -> tuple[bool, str]:
    if settings.broker_adapter.lower() == "mock":
        return False, "Simulation engine active over real market data; no external broker routing."
    return IbkrStatusProbe(settings).check_connection()


def place_simulated_order(
    session: Session,
    settings: Settings,
    *,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str,
    limit_price: float | None,
) -> Order:
    if settings.execution_mode == settings.execution_mode.LIVE and not settings.enable_live_trading:
        raise RuntimeError("LIVE execution is disabled by default.")

    symbol_row = ensure_symbol(session, symbol)
    normalized_side = side.upper()
    normalized_order_type = order_type.lower()
    order = Order(
        symbol_id=symbol_row.id,
        side=normalized_side,
        order_type=normalized_order_type,
        quantity=Decimal(str(quantity)),
        limit_price=Decimal(str(limit_price)) if limit_price is not None else None,
        status="submitted",
        mode=settings.execution_mode.value,
        submitted_at=datetime.now(timezone.utc),
    )
    session.add(order)
    session.commit()
    session.refresh(order)

    execution_plan = _build_execution_plan(
        session,
        settings,
        symbol=symbol,
        side=normalized_side,
        quantity=quantity,
        order_type=normalized_order_type,
        limit_price=limit_price,
    )

    if execution_plan.should_fill and execution_plan.fill_price is not None and execution_plan.executed_at is not None:
        session.add(
            Execution(
                order_id=order.id,
                executed_at=execution_plan.executed_at,
                price=Decimal(str(execution_plan.fill_price)),
                quantity=Decimal(str(quantity)),
                fees=Decimal(str(execution_plan.fees)),
                liquidity=execution_plan.liquidity,
            )
        )
        order.status = "filled"
        _apply_fill_to_position(session, symbol_row.id, normalized_side, quantity, execution_plan.fill_price)
        session.commit()
        session.refresh(order)

    log_event(
        session,
        level="INFO",
        source="broker",
        event_type="order_placed",
        message=f"Simulated {normalized_side} {quantity} {symbol_row.ticker}",
        context={
            "order_id": order.id,
            "symbol": symbol_row.ticker,
            "side": normalized_side,
            "order_type": normalized_order_type,
            "filled": execution_plan.should_fill,
            "note": execution_plan.note,
        },
    )
    return order


def place_paper_order(
    session: Session,
    settings: Settings,
    *,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str,
    limit_price: float | None,
) -> Order:
    return place_simulated_order(
        session,
        settings,
        symbol=symbol,
        side=side,
        quantity=quantity,
        order_type=order_type,
        limit_price=limit_price,
    )


def cancel_order(session: Session, order_id: int) -> Order:
    order = session.scalar(select(Order).where(Order.id == order_id))
    if order is None:
        raise RuntimeError("Order not found.")
    if order.status == "filled":
        raise RuntimeError("Filled orders cannot be cancelled.")
    order.status = "cancelled"
    session.commit()
    session.refresh(order)
    log_event(
        session,
        level="INFO",
        source="broker",
        event_type="order_cancelled",
        message=f"Cancelled order {order.id}",
        context={"order_id": order.id},
    )
    return order


def list_orders(session: Session, limit: int = 100) -> list[tuple[Order, str]]:
    symbols = {row.id: row.ticker for row in session.scalars(select(Symbol))}
    rows = list(session.scalars(select(Order).order_by(desc(Order.created_at)).limit(limit)))
    return [(row, symbols.get(row.symbol_id, "UNKNOWN")) for row in rows]


def list_executions(session: Session, limit: int = 100) -> list[Execution]:
    return list(session.scalars(select(Execution).order_by(desc(Execution.executed_at)).limit(limit)))


def list_positions(session: Session, limit: int = 100) -> list[Position]:
    return list(session.scalars(select(Position).order_by(desc(Position.updated_at)).limit(limit)))


def _build_execution_plan(
    session: Session,
    settings: Settings,
    *,
    symbol: str,
    side: str,
    quantity: float,
    order_type: str,
    limit_price: float | None,
) -> SimulationExecutionPlan:
    reference_price = latest_price(session, settings, symbol)
    slippage_bps = _estimate_slippage_bps(session, symbol=symbol, quantity=quantity)
    simulated_fees = _estimate_fees(quantity)
    now = datetime.now(timezone.utc)
    side_sign = 1 if side == "BUY" else -1

    if order_type == "market":
        fill_price = round(reference_price * (1 + side_sign * slippage_bps / 10_000), 6)
        return SimulationExecutionPlan(
            should_fill=True,
            fill_price=fill_price,
            fees=simulated_fees,
            executed_at=now + timedelta(milliseconds=350),
            liquidity=f"simulated-market-{slippage_bps:.1f}bps",
            note="Filled immediately using the latest stored market price plus simulated slippage.",
        )

    if order_type == "limit" and limit_price is not None:
        is_marketable = (side == "BUY" and reference_price <= limit_price) or (
            side == "SELL" and reference_price >= limit_price
        )
        if not is_marketable:
            return SimulationExecutionPlan(
                should_fill=False,
                fill_price=None,
                fees=0.0,
                executed_at=None,
                liquidity="resting-simulated-limit",
                note="Limit order remains submitted because the latest stored market price has not crossed the limit.",
            )

        impacted_price = reference_price * (1 + side_sign * slippage_bps / 10_000)
        fill_price = min(limit_price, impacted_price) if side == "BUY" else max(limit_price, impacted_price)
        return SimulationExecutionPlan(
            should_fill=True,
            fill_price=round(fill_price, 6),
            fees=simulated_fees,
            executed_at=now + timedelta(milliseconds=650),
            liquidity=f"simulated-limit-{slippage_bps:.1f}bps",
            note="Marketable limit order filled within the limit using the latest stored market price and simulated slippage.",
        )

    return SimulationExecutionPlan(
        should_fill=False,
        fill_price=None,
        fees=0.0,
        executed_at=None,
        liquidity="unsupported-order-type",
        note="Only market and limit orders are simulated by the local execution engine.",
    )


def _estimate_slippage_bps(session: Session, *, symbol: str, quantity: float) -> float:
    symbol_row = ensure_symbol(session, symbol)
    recent_market_bars = list(
        session.scalars(
            select(MarketDataBar)
            .where(MarketDataBar.symbol_id == symbol_row.id)
            .order_by(MarketDataBar.timestamp.desc())
            .limit(20)
        )
    )
    if recent_market_bars:
        volatility_component = sum(
            float((bar.high - bar.low) / bar.close) if float(bar.close or 0) else 0.0 for bar in recent_market_bars
        ) / len(recent_market_bars)
    else:
        volatility_component = 0.0015

    size_component = min(12.0, math.log10(max(quantity, 1.0)) * 2.4)
    market_component = min(18.0, volatility_component * 10_000 * 0.18)
    return round(max(1.5, size_component + market_component), 2)


def _estimate_fees(quantity: float) -> float:
    return round(max(0.35, min(6.5, quantity * 0.0035)), 2)


def _apply_fill_to_position(session: Session, symbol_id: int, side: str, quantity: float, fill_price: float) -> None:
    position = session.scalar(
        select(Position)
        .where(and_(Position.symbol_id == symbol_id, Position.status.in_(["open", "flat"])))
        .order_by(Position.updated_at.desc())
        .limit(1)
    )
    signed_fill = quantity if side == "BUY" else -quantity
    if position is None:
        session.add(
            Position(
                symbol_id=symbol_id,
                status="open",
                quantity=Decimal(str(signed_fill)),
                average_price=Decimal(str(fill_price)),
                market_value=Decimal(str(signed_fill * fill_price)),
                unrealized_pnl=Decimal("0"),
                realized_pnl=Decimal("0"),
                opened_at=datetime.now(timezone.utc),
            )
        )
        return

    current_qty = float(position.quantity)
    average_price = float(position.average_price or 0)
    realized_pnl = float(position.realized_pnl or 0)
    new_qty = current_qty + signed_fill

    if current_qty == 0 or _sign(current_qty) == _sign(signed_fill):
        weighted_cost = (abs(current_qty) * average_price) + (abs(signed_fill) * fill_price)
        position.average_price = Decimal(str(weighted_cost / max(abs(new_qty), 1e-9)))
    else:
        closed_qty = min(abs(current_qty), abs(signed_fill))
        realized_pnl += (fill_price - average_price) * closed_qty * _sign(current_qty)
        position.realized_pnl = Decimal(str(realized_pnl))
        if new_qty == 0:
            position.average_price = Decimal("0")
        elif _sign(new_qty) != _sign(current_qty):
            position.average_price = Decimal(str(fill_price))

    position.quantity = Decimal(str(new_qty))
    position.status = "flat" if new_qty == 0 else "open"
    position.market_value = Decimal(str(new_qty * fill_price))
    position.unrealized_pnl = Decimal(str((fill_price - float(position.average_price or 0)) * new_qty))


def _sign(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0
