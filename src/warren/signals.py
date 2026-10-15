"""Deterministic momentum baseline; future ML must beat this out-of-sample."""
from math import isfinite
from .config import ResearchConfig


def momentum_target(
    history: list[tuple[object, dict[str, float]]],
    as_of_idx: int,
    config: ResearchConfig,
) -> dict[str, float]:
    """Use data up to and including as_of_idx only. Select positive 20-day momentum."""
    old_idx = as_of_idx - config.momentum_lookback
    if old_idx < 0:
        raise ValueError("Insufficient warm-up data")
    current = history[as_of_idx][1]
    older = history[old_idx][1]
    returns = [(current[symbol] / older[symbol] - 1.0, symbol) for symbol in current]
    for change, _ in returns:
        if not isfinite(change):
            raise ValueError("Invalid signal return")
    ranked = sorted((pair for pair in returns if pair[0] > 0), key=lambda x: (-x[0], x[1]))
    return {symbol: config.max_position_weight for _, symbol in ranked[: config.max_positions]}
