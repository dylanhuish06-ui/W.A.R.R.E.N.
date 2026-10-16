"""W.A.R.R.E.N. offline prequential calibration audit for analytic GBM/OU forecasts.

Score matured forecasts only; NEVER claim the already-viewed 2025 interval is
a newly blind holdout. No broker connection or order placement.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from market_experiment import SOURCE_URL, load_market_csv
from market_validation import download_bytes, quality_audit
from sde_forecast import predict

EPS = 1e-7
HORIZONS = (5, 21)
LOOKBACKS = (60, 120)
MODELS = ("gbm", "ou")
YEAR_PERIODS = (2023, 2024, 2025)


@dataclass(frozen=True)
class Observation:
    symbol: str
    origin: str
    maturity: str
    probability: float
    positive: int
    realized_return: float
    expected_return: float
    lower_decile: float
    upper_decile: float
    baseline_probability: float = 0.5


def schedule(dates: list[str], start: int, end: int, horizon: int, lookback: int) -> list[int]:
    """One prediction per H non-overlapping sessions, with maturity inside period."""
    if not (1 <= horizon <= 63 and lookback >= 20 and 0 <= start <= end <= len(dates)):
        raise ValueError("Invalid forecast horizon, lookback or period")
    begin = max(start, lookback)
    return [i for i in range(begin, end - horizon, horizon)]


def _daily_moves_valid(prices: list[list[float]], j: int, start: int, end: int) -> bool:
    """Flag suspected corporate actions / unadjusted quote jumps, never impute."""
    for t in range(start + 1, end + 1):
        a, b = prices[t - 1][j], prices[t][j]
        if not (math.isfinite(a) and math.isfinite(b) and a > 0 and b > 0):
            return False
        if abs(math.log(b / a)) > 0.75:
            return False
    return True


def matured_hit_rate(prices: list[list[float]], symbol_col: int,
                     origin: int, lookback: int, horizon: int,
                     prior_strength: float = 6.0) -> float:
    """Smoothed hit-rate estimated using only PREVIOUSLY MATURED labels.

    Prior origin+k horizon must not exceed prediction origin. Nonoverlapping
    historical event windows (stride=horizon) mitigate duplicated labels.
    This is a causal comparator, not a claimed calibrated forecast.
    """
    if not (1 <= horizon <= lookback and origin >= lookback):
        raise ValueError("Invalid baseline window")
    if prior_strength <= 0 or not math.isfinite(prior_strength):
        raise ValueError("Invalid baseline prior")
    positive = 0
    events = 0
    # Each historical label matures at or before the current origin.
    for start in range(origin - horizon, origin - lookback - 1, -horizon):
        a, z = prices[start][symbol_col], prices[start + horizon][symbol_col]
        if not (math.isfinite(a) and math.isfinite(z) and a > 0 and z > 0):
            raise ValueError("Corrupt historical data")
        if abs(math.log(z / a)) > .75:
            continue
        positive += z > a
        events += 1
    return (positive + prior_strength * .5) / (events + prior_strength)


def _paired_brier(items: list[Observation], probability_attribute: str) -> float:
    return sum((getattr(x, probability_attribute) - x.positive) ** 2
               for x in items) / len(items)


def _paired_logloss(items: list[Observation], probability_attribute: str) -> float:
    total = 0.0
    for row in items:
        p = max(EPS, min(1 - EPS, getattr(row, probability_attribute)))
        total += -row.positive * math.log(p) - (1 - row.positive) * math.log1p(-p)
    return total / len(items)


def origin_cluster_differences(items: list[Observation]) -> dict:
    """Distribution of per-origin mean Brier improvement vs causal baseline.

    Descriptive only: not a t-test and not independent, as assets share market
    risk and origins share underlying return regimes.
    """
    groups = defaultdict(list)
    for x in items:
        groups[x.origin].append((x.baseline_probability - x.positive) ** 2
                                - (x.probability - x.positive) ** 2)
    values = [sum(g) / len(g) for _, g in sorted(groups.items())]
    n = len(values)
    mean = sum(values) / n
    spread = (sum((x - mean)**2 for x in values)/(n - 1))**.5 if n > 1 else None
    return {
        "origin_clusters": n,
        "mean_brier_improvement_per_origin": round(mean, 8),
        "stddev_origin_mean_difference": round(spread, 8) if spread is not None else None,
        "note": "Descriptive between-date variability only; correlated windows and common factors remain",
    }


def observations(
    dates: list[str], symbols: list[str], prices: list[list[float]],
    start: int, end: int, model: str, lookback: int, horizon: int,
    drift_shrinkage: float = .35,
) -> tuple[list[Observation], dict]:
    if not prices or not symbols or any(len(row) != len(symbols) for row in prices):
        raise ValueError("Prices/symbols mismatch")
    origins = schedule(dates, start, end, horizon, lookback)
    results: list[Observation] = []
    anomalies = 0
    model_abstentions = 0
    for origin in origins:
        for j, symbol in enumerate(symbols):
            # Only the close at origin is exposed to the predictor. The
            # future path is read solely for scoring a matured outcome.
            look = [prices[t][j] for t in range(origin - lookback, origin + 1)]
            if not _daily_moves_valid(prices, j, origin, origin + horizon):
                anomalies += 1
                continue
            try:
                forecast = predict(look, horizon, model, drift_shrinkage)
            except ValueError:
                model_abstentions += 1
                continue
            outcome = prices[origin + horizon][j] / prices[origin][j] - 1
            results.append(Observation(
                symbol, dates[origin], dates[origin + horizon],
                forecast.probability_positive, int(outcome > 0), outcome,
                forecast.expected_simple_return, forecast.lower_decile_return,
                forecast.upper_decile_return,
                matured_hit_rate(prices, j, origin, lookback, horizon),
            ))
    return results, {
        "origins": len(origins), "potential_asset_forecasts": len(origins) * len(symbols),
        "excluded_future_path_anomalies": anomalies,
        "abstentions_due_to_model_or_training_data": model_abstentions,
        "event_count": len(results),
    }


def summarize(items: list[Observation]) -> dict:
    if not items:
        raise ValueError("No mature usable probabilistic observations")
    n = len(items)
    bs = 0.0
    log_loss = 0.0
    mae = 0.0
    interval_hits = 0
    low_breaches = 0
    high_breaches = 0
    bins = [dict(count=0, sum_probability=0.0, positives=0) for _ in range(5)]
    confident = [x for x in items if x.probability >= .60]
    for o in items:
        p = o.probability
        if not math.isfinite(p) or not 0 <= p <= 1:
            raise ValueError("Invalid forecast probability")
        bs += (p - o.positive) ** 2
        pc = max(EPS, min(1 - EPS, p))
        log_loss += -o.positive * math.log(pc) - (1 - o.positive) * math.log(1 - pc)
        mae += abs(o.expected_return - o.realized_return)
        interval_hits += o.lower_decile <= o.realized_return <= o.upper_decile
        low_breaches += o.realized_return < o.lower_decile
        high_breaches += o.realized_return > o.upper_decile
        bucket = min(4, int(p * 5))
        bins[bucket]["count"] += 1
        bins[bucket]["sum_probability"] += p
        bins[bucket]["positives"] += o.positive
    table = []
    ece = 0.0
    for i, b in enumerate(bins):
        count = b["count"]
        pred = b["sum_probability"] / count if count else None
        frequency = b["positives"] / count if count else None
        if count:
            ece += (count / n) * abs(pred - frequency)
        table.append({
            "bin": f"{i*20}-{(i+1)*20}%", "n": count,
            "mean_probability": round(pred, 5) if count else None,
            "observed_positive_fraction": round(frequency, 5) if count else None,
        })
    model_brier = bs / n
    causal_brier = _paired_brier(items, "baseline_probability")
    causal_logloss = _paired_logloss(items, "baseline_probability")
    return {
        "n": n,
        "observed_positive_fraction": round(sum(o.positive for o in items) / n, 6),
        "mean_forecast_probability": round(sum(o.probability for o in items) / n, 6),
        "brier": round(model_brier, 6),
        "brier_constant_0_5": 0.25,
        "brier_causal_hit_rate": round(causal_brier, 6),
        "brier_skill_vs_causal_hit_rate": round(1 - model_brier / causal_brier, 6)
            if causal_brier > 0 else None,
        "log_loss_causal_hit_rate": round(causal_logloss, 6),
        "origin_cluster_differences": origin_cluster_differences(items),
        "brier_skill_vs_0_5": round(1 - model_brier / 0.25, 6),
        "log_loss": round(log_loss / n, 6),
        "log_loss_constant_0_5": round(math.log(2), 6),
        "mae_simple_return": round(mae / n, 6),
        "central_80pct_interval_coverage": round(interval_hits / n, 6),
        "lower_decile_breach_fraction": round(low_breaches / n, 6),
        "upper_decile_breach_fraction": round(high_breaches / n, 6),
        "expected_calibration_error_5_bins": round(ece, 6),
        "reliability": table,
        "p_ge_0_60": {
            "n": len(confident),
            "actual_positive_fraction": (round(sum(x.positive for x in confident) / len(confident), 6)
                                         if confident else None),
            "mean_predicted_probability": (round(sum(x.probability for x in confident) / len(confident), 6)
                                           if confident else None),
        },
    }


def build_report(raw: bytes) -> dict:
    dates, symbols, prices, excluded = load_market_csv(raw)
    cut = next(i for i, d in enumerate(dates) if d >= "2023-01-01")
    dates, prices = dates[cut:], prices[cut:]
    periods = {}
    for year in YEAR_PERIODS:
        start = next(i for i, d in enumerate(dates) if d >= f"{year}-01-01")
        end = next((i for i, d in enumerate(dates) if d >= f"{year+1}-01-01"), len(dates))
        if year == 2023:
            start = max(start, 125)
        periods[str(year)] = (start, end)
    report = {
        "title": "Prequential, non-overlapping SDE probability calibration audit",
        "data_source": SOURCE_URL,
        "data_sha256": hashlib.sha256(raw).hexdigest(),
        "universe": {
            "symbols": len(symbols), "excluded_symbols": excluded,
            "selection": "Future-complete 2023–2025 survivor stocks; biased",
        },
        "source_quality": quality_audit(raw),
        "methods": {
            "models": ["gbm", "ou"],
            "drift_shrinkage_fixed": .35,
            "lookbacks": list(LOOKBACKS), "horizons": list(HORIZONS),
            "origin_schedule": "One forecast per non-overlapping H sessions per year and symbol",
            "maturity_rule": "Only outcomes wholly inside the assessment period are scored",
            "forecast_information": "Prices through and including origin close only; no outcome leakage",
            "reliability_bins": "Fixed 0.0-0.2-0.4-0.6-0.8-1.0",
            "score_rule": "Proper Brier/log loss; constant 0.5 and non-overlapping matured historical hit-rate with 0.5 Beta-style smoothing prior, both matched events",
            "interval": "Gaussian log-return predictive central 80% (10th–90th quantiles)",
            "anomaly_policy": "Exclude >75% absolute daily log-return on future evaluation path; record counts and acknowledge post-outcome filtering",
            "no_training_on_assessment_year": "Parameters are fixed from prior study; no supervised calibration fitted",
            "sampling_caveat": "Cross-sectional stocks are dependent and repeated annual origin intervals are not fully independent",
        },
        "period_status": {
            "2023": "2023 H2 development; in-sample research",
            "2024": "2024 previously used for model/strategy selection; validation contaminated",
            "2025": "2025 already inspected; NOT BLIND prospective OOS",
            "2026": "NOT EVALUATED: no verified complete independent equity data",
        },
        "period_dates": {k: [dates[v[0]], dates[v[1]-1]] for k, v in periods.items()},
        "results": {},
        "deployment_gate_passed": False,
        "paper_orders_enabled": False,
        "live_orders_enabled": False,
    }
    for year, (start, end) in periods.items():
        year_out = {}
        for model in MODELS:
            for lb in LOOKBACKS:
                for horizon in HORIZONS:
                    tag = f"{model}_L{lb}_H{horizon}"
                    rows, exclusions = observations(dates, symbols, prices, start, end, model, lb, horizon)
                    year_out[tag] = {
                        "model": model, "lookback": lb, "horizon": horizon,
                        "selection": "fixed before this audit; descriptive only",
                        "counts": exclusions,
                        "scores": summarize(rows) if rows else None,
                    }
        report["results"][year] = year_out
    return report


def main() -> None:
    cli = argparse.ArgumentParser(description="Offline probability calibration; NEVER places orders")
    cli.add_argument("--equities", type=Path, help="Pinned existing source data CSV; offline option")
    cli.add_argument("--output", type=Path, default=Path("outputs/forecast_calibration.json"))
    args = cli.parse_args()
    raw = args.equities.read_bytes() if args.equities else download_bytes(SOURCE_URL)
    report = build_report(raw)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = {
        "data_sha256": report["data_sha256"], "universe_n": report["universe"]["symbols"],
        "retrospective_2025_NOT_BLIND": {
            tag: {"brier": r["scores"]["brier"],
                  "skill_vs_0_5": r["scores"]["brier_skill_vs_0_5"],
                  "central_80_coverage": r["scores"]["central_80pct_interval_coverage"],
                  "n": r["scores"]["n"]}
            for tag, r in report["results"]["2025"].items() if r["scores"]
        },
        "status": "RETROSPECTIVE QUALITY AUDIT ONLY; 2026 FORWARD GATE BLOCKED",
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
