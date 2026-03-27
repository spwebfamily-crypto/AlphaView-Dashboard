from __future__ import annotations


def clip_probability(value: float, floor: float = 0.01, ceiling: float = 0.99) -> float:
    return max(floor, min(ceiling, value))

