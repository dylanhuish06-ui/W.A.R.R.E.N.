"""Reproducible multi-family FTSE strategy search. RESEARCH ONLY: NO BROKER."""
from __future__ import annotations
import argparse
import hashlib
import itertools
import json
import math
from dataclasses import dataclass, asdict
from functools import lru_cache
from pathlib import Path
from market_experiment import SOURCE_URL, load_market_csv
from market_validation import INDEX_URL, download_bytes, index_closes, tracker_proxy, quality_audit

INITIAL = 1000.0
FLOOR = 850.0


@dataclass(frozen=True)
class Strategy:
    family: str
    lookback: int
    n: int
    period: int
    invested: float
    defensive: bool = False

    @property
    def name(self):
        return f"{self.family}-{self.lookback}-{self.n}-{self.period}-{self.invested:.2f}-{int(self.defensive)}"


def candidates():
    items = []
    for family, looks, nums, periods, defensives in [
        ("momentum", (20, 60, 120), (3, 5, 10), (5, 21), (False, True)),
        ("risk_momentum", (60, 120), (3, 5, 10), (5, 21), (False, True)),
        ("mean_reversion", (3, 5), (3, 5), (5, 21), (False, True)),
        ("dual_trend", (60, 120), (3, 5, 10), (5, 21), (True,)),
        ("equal_weight", (120,), (5, 10, 20), (21, 63), (False,)),
    ]:
        for look, n, period, exp, defensive in itertools.product(
            looks, nums, periods, (.65, .94), defensives
        ):
            items.append(Strategy(family, look, n, period, exp, defensive))
    assert len(items) == len(set(s.name for s in items))
    return items


def make_simulator(dates, prices):
    if len(dates) != len(prices) or not dates or dates != sorted(set(dates)):
        raise ValueError("Price dates invalid")
    m = len(prices[0])
    if m < 2 or any(len(row) != m or any(v is None or not math.isfinite(v) or v <= 0 for v in row) for row in prices):
        raise ValueError("Price panel incomplete or invalid")

    @lru_cache(maxsize=3000)
    def breadth(t):
        return sum(prices[t][j] > prices[t-120][j] for j in range(m)) / m

    @lru_cache(maxsize=60000)
    def rank(family, look, t):
        prices_t = prices[t]
        past = prices[t-look]
        ret = [prices_t[j]/past[j]-1 for j in range(m)]
        if family == "equal_weight":
            return tuple(range(m))
        if family == "mean_reversion":
            scored = [(-ret[j], j) for j in range(m)
                      if ret[j] < 0 and prices_t[j] > prices[t-120][j]]
        elif family == "risk_momentum":
            scored = []
            for j in range(m):
                if ret[j] <= 0:
                    continue
                r = [prices[k][j]/prices[k-1][j]-1 for k in range(t-19, t+1)]
                mean = sum(r)/len(r)
                sd = math.sqrt(sum((v-mean)**2 for v in r)/len(r))
                scored.append((ret[j]/max(sd, .001), j))
        elif family in ("momentum", "dual_trend"):
            scored = [(ret[j], j) for j in range(m) if ret[j] > 0
                      and (family == "momentum" or prices_t[j] > prices[t-120][j])]
        else:
            raise ValueError("Unknown strategy family")
        return tuple(j for _, j in sorted(scored, key=lambda z: (-z[0], z[1])))

    def simulate(start, end, spec, charge_costs=True):
        if start < max(122, spec.lookback+2) or end <= start or end > len(dates):
            raise ValueError("Insufficient data")
        positions = [0.0]*m
        cash, cost_sum, orders, turnover = INITIAL, 0.0, 0, 0.0
        stop_date = None
        peak, dd = INITIAL, 0.0
        for t in range(start, end):
            positions = [x * prices[t][j]/prices[t-1][j] for j, x in enumerate(positions)]
            equity = cash + sum(positions)
            if stop_date is None and equity < FLOOR:
                stop_date = dates[t]
            if (t-start) % spec.period == 0 or (stop_date is not None and any(positions)):
                target = [0.0] * m
                if stop_date is None and (not spec.defensive or breadth(t-1) >= .50):
                    picks = rank(spec.family, spec.lookback, t-1)[:spec.n]
                    for j in picks:
                        target[j] = equity * spec.invested / len(picks)
                # Liquidate first; avoid pointless micro-trades and preserve cash-only.
                sells, buys = [], []
                for j in range(m):
                    delta = target[j] - positions[j]
                    if delta < -5 or (target[j] == 0 and positions[j] > 0):
                        sells.append((j, min(-delta, positions[j])))
                    if delta > 5:
                        buys.append((j, delta))
                for j, amount in sells:
                    fee = (max(1., amount*.0005) + amount*.0005) if charge_costs else 0.
                    positions[j] -= amount
                    cash += amount-fee
                    cost_sum += fee
                    turnover += amount
                    orders += 1
                for j, amount in buys:
                    amount = min(amount, max(0., (cash-(1.01 if charge_costs else 0.)) /
                                           (1.006 if charge_costs else 1.)))
                    if amount < 5:
                        continue
                    fee = (max(1., amount*.0005) + amount*.0005 + amount*.005) if charge_costs else 0.
                    if cash+1e-7 < amount+fee:
                        raise AssertionError("Margin trade attempted")
                    positions[j] += amount
                    cash -= amount+fee
                    cost_sum += fee
                    turnover += amount
                    orders += 1
            equity = cash + sum(positions)
            if cash < -1e-7 or min(positions) < -1e-7 or not math.isfinite(equity) or equity <= 0:
                raise AssertionError("Portfolio invariants failed")
            peak = max(peak, equity)
            dd = max(dd, 1-equity/peak)
        return dict(end_gbp=round(equity, 2), return_pct=round(100*(equity/INITIAL-1), 3),
                    max_drawdown_pct=round(100*dd, 3), costs_gbp=round(cost_sum, 2),
                    orders=orders, turnover_gbp=round(turnover, 2), stop_date=stop_date)
    return simulate


def build_report(raw_shares, raw_index):
    dates, symbols, prices, excluded = load_market_csv(raw_shares)
    idx = index_closes(raw_index)
    audit = quality_audit(raw_shares)
    year_starts = {y: next(i for i, d in enumerate(dates) if d >= f"{y}-01-01")
                   for y in (2023, 2024, 2025)}
    periods = {2023: (year_starts[2023], year_starts[2024]),
               2024: (year_starts[2024], year_starts[2025]),
               2025: (year_starts[2025], len(dates))}
    benchmark = {str(y): tracker_proxy(idx, f"{y}-01-01", f"{y}-12-31") for y in periods}
    simulate = make_simulator(dates, prices)
    tested = []
    grid = candidates()
    for config in grid:
        dev = simulate(*periods[2023], config)
        valid = simulate(*periods[2024], config)
        a = dev["return_pct"] - benchmark["2023"]["return_pct"]
        b = valid["return_pct"] - benchmark["2024"]["return_pct"]
        score = (.55*min(a, b) + .45*(a+b)/2 - .35*max(dev["max_drawdown_pct"],
                 valid["max_drawdown_pct"]) - .15*abs(a-b)
                 - 12*int(dev["stop_date"] is not None) - 12*int(valid["stop_date"] is not None))
        tested.append(dict(config=asdict(config) | {"name": config.name},
                           development_2023=dev, validation_2024=valid,
                           excess_2023_pp=round(a, 3), excess_2024_pp=round(b, 3),
                           score=round(score, 4)))
    ranked = sorted(tested, key=lambda row: (-row["score"], row["config"]["name"]))
    for row in ranked[:10]:
        configuration = row["config"].copy()
        configuration.pop("name")
        candidate = Strategy(**configuration)
        result = simulate(*periods[2025], candidate)
        row["observed_2025_not_blind"] = result
        row["excess_2025_pp_not_blind"] = round(
            result["return_pct"]-benchmark["2025"]["return_pct"], 3)
    return {
        "title": "W.A.R.R.E.N. broad exploratory strategy research",
        "market_data_source": SOURCE_URL,
        "market_data_sha256": hashlib.sha256(raw_shares).hexdigest(),
        "index_data_source": INDEX_URL,
        "index_data_sha256": hashlib.sha256(raw_index).hexdigest(),
        "market_data_audit": audit,
        "symbols_with_complete_2023_2025_history": len(symbols),
        "excluded_for_missing_share_prices": excluded,
        "candidates_count": len(grid),
        "families": sorted(set(c.family for c in grid)),
        "periods": {str(y): [dates[a], dates[b-1]] for y, (a, b) in periods.items()},
        "passive_cost_adjusted_price_index_proxy": benchmark,
        "optimization": "2023 development and 2024 validation only; score = 55% worst-year excess + 45% average excess - 35% worst-year drawdown - 15% excess instability - 12 per stop",
        "winner": ranked[0],
        "top_10": ranked[:10],
        "all_optimization_candidates": ranked,
        "diagnostic_2025_status": "ALREADY-VIEWED, NOT FRESH BLIND HOLDOUT",
        "holdout_2026_status": "NOT RUN; no matching 2026 individual-stock dataset",
        "warnings": [
            "Survivorship-biased fixed share universe, no point-in-time FTSE membership",
            "Raw OHLC inconsistencies and share corporate actions unverified",
            "Fractional-share assumption and next-close idealised execution",
            "188+ alternative searches induce multiple-testing/overfitting risk",
            "Tracker proxy is FTSE price-only, excludes dividend reinvestment and ETF fees",
            "Broker fees approximate: £1 min commission plus 5bp slippage and 50bp SDRT on buys",
        ],
        "broker_or_live_execution": False, "deployment_approved": False,
    }


def main():
    p = argparse.ArgumentParser(description="W.A.R.R.E.N. offline strategy optimisation")
    p.add_argument("--equities", type=Path)
    p.add_argument("--index", type=Path)
    p.add_argument("--output", type=Path, default=Path("outputs/strategy_optimization.json"))
    a = p.parse_args()
    equities = a.equities.read_bytes() if a.equities else download_bytes(SOURCE_URL)
    index = a.index.read_bytes() if a.index else download_bytes(INDEX_URL)
    result = build_report(equities, index)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({
        "candidates": result["candidates_count"], "families": result["families"],
        "winner": result["winner"],
        "benchmark_2023": result["passive_cost_adjusted_price_index_proxy"]["2023"],
        "benchmark_2024": result["passive_cost_adjusted_price_index_proxy"]["2024"],
        "benchmark_2025": result["passive_cost_adjusted_price_index_proxy"]["2025"],
        "top_5": [{"name": r["config"]["name"], "score": r["score"],
                    "2023": r["development_2023"]["return_pct"],
                    "2024": r["validation_2024"]["return_pct"],
                    "2025_not_blind": r.get("observed_2025_not_blind", {}).get("return_pct")}
                   for r in result["top_10"][:5]],
        "status": "NO FRESH 2026 HOLDOUT; BROKER/LIVE EXECUTION DISABLED"
    }, indent=2))


if __name__ == "__main__":
    main()
