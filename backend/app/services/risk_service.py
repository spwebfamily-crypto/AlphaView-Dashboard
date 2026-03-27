from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class RiskDecision:
    allowed: bool
    reason: str


def evaluate_trade_risk(
    *,
    action: str,
    trade_size: float,
    max_position_size: float,
    max_exposure_per_symbol: float,
    max_daily_loss: float,
    daily_pnl: float,
    last_trade_at: datetime | None,
    current_timestamp: datetime,
    cooldown_minutes: int,
) -> RiskDecision:
    if action == "HOLD":
        return RiskDecision(False, "hold_signal")
    if trade_size > max_position_size:
        return RiskDecision(False, "max_position_size_exceeded")
    if trade_size > max_exposure_per_symbol:
        return RiskDecision(False, "max_exposure_per_symbol_exceeded")
    if daily_pnl <= -abs(max_daily_loss):
        return RiskDecision(False, "max_daily_loss_reached")
    if last_trade_at is not None:
        elapsed_minutes = (current_timestamp - last_trade_at).total_seconds() / 60
        if elapsed_minutes < cooldown_minutes:
            return RiskDecision(False, "cooldown_active")
    return RiskDecision(True, "allowed")

