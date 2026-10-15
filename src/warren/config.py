"""Immutable, fail-closed portfolio and execution settings."""
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class ResearchConfig:
    initial_cash_gbp: float = 1000.0
    capital_floor_gbp: float = 1000.0
    momentum_lookback: int = 20
    max_positions: int = 20
    max_position_weight: float = 0.05
    transaction_cost_bps: float = 10.0
    trading_armed: bool = False
    live_trading_allowed: bool = False

    def __post_init__(self) -> None:
        if not (isfinite(self.initial_cash_gbp) and self.initial_cash_gbp > 0):
            raise ValueError("initial_cash_gbp must be positive and finite")
        if not (isfinite(self.capital_floor_gbp) and 0 <= self.capital_floor_gbp <= self.initial_cash_gbp):
            raise ValueError("capital_floor_gbp must be within [0, initial_cash_gbp]")
        if self.momentum_lookback < 2 or self.max_positions < 1:
            raise ValueError("lookback must be >=2 and max_positions >=1")
        if not (isfinite(self.max_position_weight) and 0 < self.max_position_weight <= 1):
            raise ValueError("max_position_weight must be in (0,1]")
        if not (isfinite(self.transaction_cost_bps) and 0 <= self.transaction_cost_bps <= 10000):
            raise ValueError("transaction_cost_bps must be within [0,10000]")
        if self.trading_armed or self.live_trading_allowed:
            raise ValueError("Research mode cannot arm trading or enable live brokerage execution")
