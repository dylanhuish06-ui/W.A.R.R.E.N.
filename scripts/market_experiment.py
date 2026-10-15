"""W.A.R.R.E.N. OFFLINE market study: never connects to a broker or orders.

2024 is the validation period; 2025 was inspected in October 2026 and
must not be used again as a fresh blind holdout after changing strategies.
"""
import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path

SOURCE_SHA = "06850a4578dde1f07134fd4923fae7db3c0c6117"
SOURCE_URL = ("https://raw.githubusercontent.com/arjundangwaluk/Ftse100database/"
              + SOURCE_SHA + "/ftse100_database.csv")


@dataclass(frozen=True)
class Strategy:
    name: str
    lookback: int
    positions: int
    rebalance_sessions: int


CANDIDATES = (
    Strategy("baseline_20d_20_daily", 20, 20, 1),
    Strategy("baseline_60d_20_weekly", 60, 20, 5),
    Strategy("aggr_20d_5_weekly", 20, 5, 5),
    Strategy("aggr_60d_5_weekly", 60, 5, 5),
    Strategy("aggr_120d_5_weekly", 120, 5, 5),
    Strategy("aggr_20d_3_weekly", 20, 3, 5),
    Strategy("aggr_60d_3_weekly", 60, 3, 5),
    Strategy("aggr_60d_3_monthly", 60, 3, 21),
    Strategy("aggr_120d_3_monthly", 120, 3, 21),
    Strategy("aggr_120d_5_monthly", 120, 5, 21),
    Strategy("aggr_60d_5_monthly", 60, 5, 21),
)


def load_market_csv(raw: bytes):
    reader = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    columns, fields, dates_header = next(reader), next(reader), next(reader)
    if columns[0] != "Ticker" or fields[0] != "Price" or dates_header[0] != "Date":
        raise ValueError("Unexpected CSV header")
    if (len(columns) - 1) % 5 or len(columns) != len(fields):
        raise ValueError("Unexpected field count")
    names = [columns[i] for i in range(1, len(columns), 5)]
    if len(set(names)) != len(names):
        raise ValueError("Duplicate tickers")
    for i in range(1, len(columns), 5):
        if fields[i:i+5] != ["Open", "High", "Low", "Close", "Volume"]:
            raise ValueError("Unexpected quote field order")
    dates, prices = [], []
    for row in reader:
        if not row:
            continue
        if len(row) != len(columns):
            raise ValueError("Malformed row")
        date = row[0]
        if dates and date <= dates[-1]:
            raise ValueError("Dates out of order")
        dates.append(date)
        closes = []
        for i in range(4, len(columns), 5):
            try:
                value = float(row[i])
            except ValueError:
                value = float("nan")
            closes.append(value if math.isfinite(value) and value > 0 else None)
        prices.append(closes)
    if not dates or dates[0] > "2023-01-01" or dates[-1] < "2025-12-31":
        raise ValueError("Dataset does not span 2023–2025")
    start = next(i for i, d in enumerate(dates) if d >= "2023-01-01")
    selected = [j for j in range(len(names)) if all(row[j] is not None for row in prices[start:])]
    if len(selected) < 20:
        raise ValueError("Not enough complete histories")
    excluded = [names[j] for j in range(len(names)) if j not in selected]
    return dates, [names[j] for j in selected], [[row[j] for j in selected] for row in prices], excluded


def fee(notional: float, buying: bool) -> float:
    """£1 min commission, 5bps slippage, blanket 50bps buy-side SDRT assumption."""
    return max(1.0, notional * .0005) + notional * .0005 + (notional * .005 if buying else 0.0)


def simulate(dates, prices, start: int, end: int, spec: Strategy, floor: float = 850.0):
    """Today-close assumed fill of yesterday's signal; cash-only, fractional notionals."""
    if start < 121 or start >= end or end > len(dates):
        raise ValueError("Bad date interval")
    cash, holdings, stop = 1000.0, [0.0] * len(prices[0]), None
    costs, orders, peak, max_dd = 0.0, 0, 1000.0, 0.0

    def trade(j, requested):
        nonlocal cash, costs, orders
        delta = requested
        amount = abs(delta)
        if amount < 1:
            return
        cost = fee(amount, delta > 0)
        if delta > 0 and cash < amount + cost + .01:
            delta = min(delta, max(0.0, (cash - 1.01) / 1.006))
            amount = abs(delta)
            if amount < 1:
                return
            cost = fee(amount, True)
        if delta > 0 and cash < delta + cost - 1e-8:
            raise AssertionError("No leverage allowed")
        cash -= delta + cost
        holdings[j] += delta
        costs += cost
        orders += 1

    for i in range(start, end):
        for j, notional in enumerate(holdings):
            if notional:
                holdings[j] *= prices[i][j] / prices[i - 1][j]
        equity = cash + sum(holdings)
        if stop is None and equity < floor:
            stop = dates[i]
        if (i - start) % spec.rebalance_sessions == 0 or (stop and any(holdings)):
            target = [0.0] * len(holdings)
            if stop is None:
                yesterday, earlier = prices[i - 1], prices[i - 1 - spec.lookback]
                ranking = sorted(
                    ((yesterday[j] / earlier[j] - 1.0, j) for j in range(len(holdings))
                     if yesterday[j] > earlier[j]),
                    key=lambda x: (-x[0], x[1]),
                )
                for _, j in ranking[:spec.positions]:
                    target[j] = equity * .94 / spec.positions
            for j in range(len(holdings)):
                change = target[j] - holdings[j]
                if change < 0 and (target[j] == 0 or abs(change) >= 30):
                    trade(j, change)
            for j in range(len(holdings)):
                change = target[j] - holdings[j]
                if change >= 30 or (holdings[j] == 0 and change >= 1):
                    trade(j, change)
        equity = cash + sum(holdings)
        if cash < -1e-7 or any(v < -1e-7 for v in holdings):
            raise AssertionError("Cash-only/long-only invariant violated")
        peak = max(peak, equity)
        max_dd = max(max_dd, 1.0 - equity / peak)
    return {
        "final_equity_gbp": round(equity, 2),
        "return_pct": round((equity / 1000 - 1) * 100, 2),
        "max_drawdown_pct": round(max_dd * 100, 2),
        "total_costs_gbp": round(costs, 2),
        "orders": orders, "stop_date": stop,
    }


def passive(prices, start, end):
    n = len(prices[0])
    wealth = 1000.0 * sum(prices[end - 1][j] / prices[start][j] for j in range(n)) / n
    return {"final_equity_gbp": round(wealth, 2),
            "return_pct": round(100 * (wealth / 1000 - 1), 2)}


def experiment(raw: bytes):
    dates, symbols, prices, excluded = load_market_csv(raw)
    validation = next(i for i, d in enumerate(dates) if d >= "2024-01-01")
    holdout = next(i for i, d in enumerate(dates) if d >= "2025-01-01")
    candidates = [
        {"strategy": asdict(spec),
         "validation": simulate(dates, prices, validation, holdout, spec),
         "test_2025": simulate(dates, prices, holdout, len(dates), spec)}
        for spec in CANDIDATES
    ]
    selected = max(candidates, key=lambda v: v["validation"]["return_pct"])
    return {
        "study": "EXPLORATORY; no brokerage access; 2025 ALREADY EXAMINED",
        "source": SOURCE_URL, "source_sha256": hashlib.sha256(raw).hexdigest(),
        "dataset_start": dates[0], "dataset_end": dates[-1],
        "universe_count": len(symbols), "excluded_missing_tickers": excluded,
        "universe_bias": "later FTSE members; hindsight completeness; excludes delisted shares",
        "validation": [dates[validation], dates[holdout - 1]],
        "test": [dates[holdout], dates[-1]],
        "cost_model": "£1 min tiered fee, 5bp slippage, 50bp SDRT all buys; excludes venue fees",
        "portfolio": "£1000, 94% invested, long-only, no leverage, fractional approximation, £850 floor",
        "benchmark_validation": passive(prices, validation, holdout),
        "benchmark_test_2025": passive(prices, holdout, len(dates)),
        "selected_from_validation": selected["strategy"]["name"],
        "selected_test_2025": selected["test_2025"],
        "candidates": candidates, "live_trading_enabled": False,
    }


def main():
    parser = argparse.ArgumentParser(description="Offline UK stock momentum study; NO ORDERS")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--input", type=Path)
    group.add_argument("--download", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("outputs/market_research.json"))
    args = parser.parse_args()
    if args.download:
        req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "WARREN-research/0.1"})
        with urllib.request.urlopen(req, timeout=90) as response:
            raw = response.read()
    else:
        raw = args.input.read_bytes()
    report = experiment(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "candidates"}, indent=2))
    for row in report["candidates"]:
        print(row["strategy"]["name"], row["validation"]["return_pct"], row["test_2025"]["return_pct"])


if __name__ == "__main__":
    main()
