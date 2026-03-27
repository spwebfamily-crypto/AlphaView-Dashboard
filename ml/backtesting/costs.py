from __future__ import annotations


def apply_bps_costs(raw_return: float, transaction_cost_bps: float, round_trips: int = 1) -> float:
    return raw_return - ((transaction_cost_bps * 2 * round_trips) / 10_000)

