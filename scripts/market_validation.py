"""Auditable, reproducible study on pinned public market datasets.

This is exploratory research. 2025 was viewed during development and cannot
be called a blind holdout. 2026 individual-share data is unavailable from the
pinned source; only a separate 2026 FTSE index sanity check is possible.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import urllib.request
from datetime import datetime
from pathlib import Path

from market_experiment import CANDIDATES, SOURCE_URL, Strategy, experiment, fee, simulate

INDEX_COMMIT = "aa60b746f089c3f54df6760bf021708c2d3ce1e8"
INDEX_URL = ("https://raw.githubusercontent.com/Hareeshkesavan/Stock-Market-Dataset/"
             + INDEX_COMMIT + "/FTSE%20100%20Historical%20Data.csv")
START_YEAR = "2020"


def download_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "WARREN-offline-research/0.2"})
    with urllib.request.urlopen(request, timeout=120) as resp:
        raw = resp.read()
    if len(raw) < 1000:
        raise ValueError("Source unexpectedly short")
    return raw


def index_closes(raw: bytes) -> dict[str, float]:
    data = {}
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))):
        day = datetime.strptime(row["Date"], "%m/%d/%Y").date().isoformat()
        close = float(row["Price"].replace(",", ""))
        if not (math.isfinite(close) and close > 0) or day in data:
            raise ValueError(f"Corrupt index close on {day}")
        data[day] = close
    if not data or max(data) < "2026-03-31":
        raise ValueError("Index series does not reach March 2026")
    return data


def tracker_proxy(closes: dict[str, float], start: str, end: str) -> dict:
    """Illustrative *single-ticket* index-tracker proxy, not an actual ETF quote.

    One £1 buy commission + 5bps initial slippage, held through end; no
    dividends, TER, tracking error, FX, exit fee, or SDRT on qualifying ETFs.
    """
    eligible = sorted(d for d in closes if start <= d <= end)
    if len(eligible) < 2:
        raise ValueError("Insufficient index dates")
    begin, finish = eligible[0], eligible[-1]
    invested = (1000.0 - 1.0) / 1.0005
    final_value = invested * closes[finish] / closes[begin]
    return {
        "period": [begin, finish],
        "end_value_gbp": round(final_value, 2),
        "return_pct": round((final_value / 1000 - 1) * 100, 2),
        "raw_index_return_pct": round((closes[finish] / closes[begin] - 1) * 100, 2),
        "model": "FTSE100 price-only index, 1 hypothetical ETF purchase, £1 commission, 5bps entry slippage; excludes fund charges and dividends",
    }


def quality_audit(raw: bytes) -> dict:
    records = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    tickers = next(records)
    next(records)
    next(records)
    n = (len(tickers) - 1) // 5
    if n != 100:
        raise ValueError(f"Expected 100 tickers, got {n}")
    rows = 0
    missing_closes = 0
    invalid_ohlc_rows = 0
    first_day = last_day = None
    for values in records:
        if not values:
            continue
        if len(values) != len(tickers):
            raise ValueError("Malformed OHLC row")
        day = values[0]
        if last_day is not None and day <= last_day:
            raise ValueError("Unsorted or duplicate date")
        first_day = first_day or day
        last_day = day
        rows += 1
        for k in range(n):
            offset = 1 + k * 5
            raw_ohlc = values[offset:offset+4]
            try:
                o, h, l, c = [float(x) for x in raw_ohlc]
            except ValueError:
                missing_closes += 1
                continue
            if not (math.isfinite(c) and c > 0):
                missing_closes += 1
            if (all(math.isfinite(x) and x > 0 for x in (o, h, l, c))
                and (h < max(o, c, l) - 1e-5 or l > min(o, c, h) + 1e-5)):
                invalid_ohlc_rows += 1
    if rows < 1000 or last_day != "2025-12-31":
        raise ValueError("Unexpected market dataset coverage")
    return {
        "rows": rows,
        "raw_tickers": n,
        "first_day": first_day,
        "last_day": last_day,
        "invalid_or_missing_closes": missing_closes,
        "ohlc_inconsistencies": invalid_ohlc_rows,
        "data_warning": "Raw provider has missing quotes and OHLC inconsistencies. Do not treat as clean, tradable, or corporate-action-corrected.",
    }


def early_regime_sensitivity(raw: bytes, selected: Strategy) -> dict:
    """Out-of-window earlier years: NOT chronological out-of-sample."""
    records = csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    columns = next(records)
    next(records)
    next(records)
    names = [columns[i] for i in range(1, len(columns), 5)]
    dates, values = [], []
    for row in records:
        if row:
            dates.append(row[0])
            tmp = []
            for k in range(len(names)):
                try:
                    close = float(row[4 + 5*k])
                    tmp.append(close if math.isfinite(close) and close > 0 else None)
                except ValueError:
                    tmp.append(None)
            values.append(tmp)
    # Survivorship-biased complete 2020–2025 historical sample, labelled as such.
    eligible = [k for k in range(len(names)) if all(row[k] is not None for row in values)]
    filtered = [[row[k] for k in eligible] for row in values]
    idx2021 = next(i for i, d in enumerate(dates) if d >= "2021-01-01")
    idx2022 = next(i for i, d in enumerate(dates) if d >= "2022-01-01")
    idx2023 = next(i for i, d in enumerate(dates) if d >= "2023-01-01")
    return {
        "eligible_2020_to_2025": len(eligible),
        "2021": simulate(dates, filtered, idx2021, idx2022, selected),
        "2022": simulate(dates, filtered, idx2022, idx2023, selected),
        "qualification": "Historical-regime sensitivity only; earlier than parameter selection, not a forward blind test; 2025-survivor selection remains.",
    }


def build_report(raw_market: bytes, raw_index: bytes) -> dict:
    core = experiment(raw_market)
    idx = index_closes(raw_index)
    audit = quality_audit(raw_market)
    selected = next(c for c in CANDIDATES if c.name == core["selected_from_validation"])
    proxy2024 = tracker_proxy(idx, "2024-01-01", "2024-12-31")
    proxy2025 = tracker_proxy(idx, "2025-01-01", "2025-12-31")
    proxy2026 = tracker_proxy(idx, "2026-01-01", "2026-03-31")

    rows = []
    for x in core["candidates"]:
        rows.append({
            "name": x["strategy"]["name"],
            "validation_2024": x["validation"],
            "observed_2025_not_blind": x["test_2025"],
            "2024_excess_vs_tracker_proxy_pp": round(x["validation"]["return_pct"] - proxy2024["return_pct"], 2),
            "2025_excess_vs_tracker_proxy_pp": round(x["test_2025"]["return_pct"] - proxy2025["return_pct"], 2),
        })
    top = next(row for row in rows if row["name"] == selected.name)
    return {
        "title": "W.A.R.R.E.N. pinned FTSE equity exploratory audit",
        "study_type": "EXPLORATORY NOT OOS-CONFIRMED; NO BROKER ACCESS",
        "selection": "max 2024 net total return across 11 frozen candidates; 2025 already seen (NOT BLIND)",
        "source_equities": SOURCE_URL,
        "equity_file_sha256": hashlib.sha256(raw_market).hexdigest(),
        "source_index": INDEX_URL,
        "index_file_sha256": hashlib.sha256(raw_index).hexdigest(),
        "dataset_audit": audit,
        "universe_2023_25_valid_tickers": core["universe_count"],
        "excluded_data_gap_symbols": core["excluded_missing_tickers"],
        "equity_historical_membership_available": False,
        "corporate_actions_verified": False,
        "funded_portfolio": "£1,000 initial; long-only; 94% target; max £150 per name for 3 positions; £850 floor; fractional notionals approximation; costs include £1 min per trade, 5bp slippage, 50bp buy-side SDRT assumption",
        "benchmark": "FTSE 100 price-only tracker proxy (single simulated purchase); not ETF observed total return",
        "benchmark_2024": proxy2024,
        "benchmark_2025": proxy2025,
        "new_2026_index_only": proxy2026,
        "2026_equity_holdout_status": "NOT EXECUTED: no compatible verified 2026 constituent prices; index-only check is NOT a test of equity algorithm",
        "selected_2024": top,
        "all_11_candidates": rows,
        "regime_2021_2022_selected_strategy": early_regime_sensitivity(raw_market, selected),
        "risk_assessment": "FAIL: selection does not generalise into already-inspected 2025; unknown survivorship bias, unverified corporate actions and low-capital high transaction fees",
        "deployment_gate": "BLOCKED: no IBKR connection; no live execution",
        "limitations": [
            "The 2023–2025 88-share universe is chosen with hindsight; missing 12 of 100 and excludes important firms.",
            "Raw provider OHLC fields are sometimes internally inconsistent; possible adjustment discrepancies.",
            "2025 candidate inspection and strategy selection make 2025 unusable as a new blind holdout.",
            "A genuinely later and verified 2026 equity market feed plus point-in-time membership is required.",
            "The price-only FTSE 100 proxy excludes dividends, tracking fees and real ETF execution.",
            "Fractional UK equity trading is approximated; actual broker execution may not permit it.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--equities", type=Path, help="Optional downloaded pinned equities CSV")
    parser.add_argument("--index", type=Path, help="Optional downloaded pinned index CSV")
    parser.add_argument("--output", type=Path, default=Path("outputs/market_validation.json"))
    args = parser.parse_args()
    equities = args.equities.read_bytes() if args.equities else download_bytes(SOURCE_URL)
    index = args.index.read_bytes() if args.index else download_bytes(INDEX_URL)
    report = build_report(equities, index)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "selected_strategy": report["selected_2024"]["name"],
        "validation_2024": report["selected_2024"]["validation_2024"],
        "observed_2025": report["selected_2024"]["observed_2025_not_blind"],
        "tracker_2024": report["benchmark_2024"],
        "tracker_2025": report["benchmark_2025"],
        "2026_index_only": report["new_2026_index_only"],
        "audit": report["dataset_audit"],
        "eligibility": report["risk_assessment"],
    }, indent=2))


if __name__ == "__main__":
    main()
