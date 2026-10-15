"""Portfolio constraints evaluated independently from signal generation."""
from math import isfinite
from .config import ResearchConfig


def validate_target(weights: dict[str, float], config: ResearchConfig) -> None:
    if len(weights) > config.max_positions:
        raise ValueError("Max portfolio positions exceeded")
    for symbol, weight in weights.items():
        if not symbol or not isfinite(weight) or weight < 0:
            raise ValueError("Long-only nonnegative finite weights required")
        if weight > config.max_position_weight + 1e-12:
            raise ValueError("Per-position weight limit exceeded")
    if sum(weights.values()) > 1 + 1e-12:
        raise ValueError("Gross exposure above 100%")


def capital_floor_breached(equity_gbp: float, config: ResearchConfig) -> bool:
    return not isfinite(equity_gbp) or equity_gbp < config.capital_floor_gbp
