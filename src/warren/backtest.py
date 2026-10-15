"""Close-to-close research simulation with lagged signals and trading frictions.

The signal at close of t-1 executes at close of t, avoiding same-close lookahead.
This is NOT a fill simulator and must not be treated as indicative of live fills.
"""
from dataclasses import asdict, dataclass
from datetime import date
from math import isfinite
from .config import ResearchConfig
from .risk import capital_floor_breached, validate_target
from .signals import momentum_target


@dataclass(frozen=True)
class EquityPoint:
    date: str
    equity_gbp: float
    benchmark_gbp: float
    turnover: float
    cost_gbp: float
    positions: int


def _max_drawdown(equities: list[float]) -> float:
    peak = equities[0]
    largest = 0.0
    for value in equities:
        peak = max(peak, value)
        largest = max(largest, 1.0 - value / peak)
    return largest


def run_backtest(
    prices: list[tuple[date, dict[str, float]]], config: ResearchConfig | None = None
) -> dict:
    config = config or ResearchConfig()
    first = config.momentum_lookback + 1
    if len(prices) <= first + 1:
        raise ValueError("Need enough dates for warm-up and evaluation")
    symbols = sorted(prices[0][1])
    if any(set(closes) != set(symbols) or any(not isfinite(v) or v <= 0 for v in closes.values())
           for _, closes in prices):
        raise ValueError("Invalid or incomplete panel")
    equity = config.initial_cash_gbp
    weights: dict[str, float] = {}
    benchmark_base = prices[first][1]
    benchmark_symbols = len(symbols)
    points: list[EquityPoint] = []
    stopped = False
    stop_reason: str | None = None
    total_cost_gbp = 0.0
    total_turnover = 0.0
    rebalance_count = 0

    for idx in range(first, len(prices)):
        day, today = prices[idx]
        yesterday = prices[idx - 1][1]
        cash_weight = max(0.0, 1.0 - sum(weights.values()))
        portfolio_growth = cash_weight + sum(weights[s] * today[s] / yesterday[s] for s in weights)
        equity *= portfolio_growth
        if not (isfinite(equity) and equity > 0):
            raise ValueError("Invalid simulated equity")
        drifted = {s: w * today[s] / yesterday[s] / portfolio_growth for s, w in weights.items()}

        if not stopped and capital_floor_breached(equity, config):
            stopped = True
            stop_reason = f"Equity below £{config.capital_floor_gbp:,.2f} on {day}"
        target = {} if stopped else momentum_target(prices, idx - 1, config)
        validate_target(target, config)
        turnover = sum(abs(target.get(s, 0.0) - drifted.get(s, 0.0)) for s in set(target) | set(drifted))
        cost = equity * turnover * config.transaction_cost_bps / 10_000
        equity -= cost
        if equity <= 0:
            raise ValueError("Trading costs exhausted capital")
        weights = target
        if turnover > 1e-12:
            rebalance_count += 1
        total_turnover += turnover
        total_cost_gbp += cost

        benchmark = config.initial_cash_gbp * sum(today[s] / benchmark_base[s] for s in symbols) / benchmark_symbols
        points.append(EquityPoint(
            date=day.isoformat(), equity_gbp=round(equity, 4), benchmark_gbp=round(benchmark, 4),
            turnover=round(turnover, 8), cost_gbp=round(cost, 4), positions=len(weights)
        ))

    end_equity = points[-1].equity_gbp
    end_benchmark = points[-1].benchmark_gbp
    result = {
        "model": "top_20_positive_momentum_v0",
        "execution_assumption": "previous-close signal, next-close simulated execution",
        "initial_cash_gbp": config.initial_cash_gbp,
        "final_equity_gbp": end_equity,
        "benchmark_name": "same-universe equal-weight buy-and-hold (no costs)",
        "benchmark_final_gbp": end_benchmark,
        "total_return_pct": round(100 * (end_equity / config.initial_cash_gbp - 1), 4),
        "benchmark_return_pct": round(100 * (end_benchmark / config.initial_cash_gbp - 1), 4),
        "excess_return_percentage_points": round(100 * (end_equity - end_benchmark) / config.initial_cash_gbp, 4),
        "max_drawdown_pct": round(100 * _max_drawdown([config.initial_cash_gbp] + [p.equity_gbp for p in points]), 4),
        "total_cost_gbp": round(total_cost_gbp, 4),
        "total_turnover": round(total_turnover, 5),
        "rebalances": rebalance_count,
        "stopped": stopped,
        "stop_reason": stop_reason,
        "live_trading_enabled": False,
        "observations": len(points),
        "history": [asdict(p) for p in points],
    }
    return result
