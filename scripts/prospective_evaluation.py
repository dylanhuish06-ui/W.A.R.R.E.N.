"""Independent forward-evidence diagnostic for frozen GBM/OU predictions.

Inputs are matured outcomes of *previously recorded* offline ledgers.
This can test forecasts statistically, but cannot certify provenance,
source independence or profitability and never promotes an IBKR gate.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import random

MODELS = ("gbm", "ou")
MIN_ORIGINS = 12
MIN_ISSUERS = 25
MIN_SPAN_CALENDAR_DAYS = 300
BOOTSTRAP_REPLICATIONS = 2000
BOOTSTRAP_SEED = 20261016


def _binary(value):
    if type(value) is not int or value not in (0, 1):
        raise ValueError("Outcome label must be exactly zero or one")
    return value


def _prob(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Nonfinite or invalid probability")
    if not 0 <= value <= 1:
        raise ValueError("Probability outside [0,1]")
    return value


def _finite(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("Invalid numeric outcome")
    return value


def _brier(p, y):
    return (p - y) ** 2


def _logloss(p, y):
    p = min(1 - 1e-7, max(1e-7, p))
    return -y * math.log(p) - (1 - y) * math.log1p(-p)


def _date(s):
    return date.fromisoformat(s)


def _ece(records):
    bins = [[0, 0., 0.] for _ in range(10)]
    for r in records:
        k = min(9, int(r["model_probability"] * 10))
        bins[k][0] += 1
        bins[k][1] += r["model_probability"]
        bins[k][2] += r["positive"]
    n = len(records)
    return sum(abs(total_p - total_y) for c, total_p, total_y in bins if c) / n


def bootstrap_origin_cluster_lower(differences, *, draws=BOOTSTRAP_REPLICATIONS):
    """One-sided 5th percentile over equally weighted independent origin clusters.

    The estimate assumes temporal origin clusters are exchangeable and remains
    a rough diagnostic, not a multiple-testing adjusted inference guarantee.
    """
    rng = random.Random(BOOTSTRAP_SEED)
    data = list(differences)
    if len(data) < 2:
        return None
    means = []
    n = len(data)
    for _ in range(draws):
        means.append(sum(data[rng.randrange(n)] for _ in range(n)) / n)
    means.sort()
    return means[max(0, int(.05 * draws) - 1)]


def assess(reports: list[dict]) -> dict:
    """Fail-closed assessment of matched, matured, non-overlapping labels."""
    if not reports:
        raise ValueError("No matured prospective score reports supplied")
    assembled = {model: [] for model in MODELS}
    seen_sha, periods, seen_keys = set(), {}, set()
    for report in reports:
        if report.get("audit_approved") is not False or report.get("paper_orders_enabled") is not False:
            raise ValueError("Unexpected broker/promotion flags")
        if report.get("horizon_sessions") != 21:
            raise ValueError("This acceptance gate is frozen at H=21")
        origin, maturity = _date(report["origin"]), _date(report["maturity"])
        recorded = datetime.fromisoformat(report["prediction_recorded_at_utc"])
        if recorded.tzinfo is None or not origin < recorded.date() < maturity:
            raise ValueError("Forecast must have been recorded between origin and maturity")
        ledger = report["source_ledger_sha256"]
        if not isinstance(ledger, str) or len(ledger) != 64 or ledger in seen_sha:
            raise ValueError("Duplicate/malformed previously recorded origin ledger")
        seen_sha.add(ledger)
        if origin in periods:
            raise ValueError("Duplicate origin date")
        periods[origin] = maturity
        for item in report["prospective_observations"]:
            model = item["model"]
            if model not in MODELS or (item["origin"], item["maturity"]) != (
                    report["origin"], report["maturity"]):
                raise ValueError("Model/date outside original recorded horizon")
            if item.get("origin_ledger_sha256") != ledger:
                raise ValueError("Mismatched immutable prediction origin")
            issuer = item["issuer"]
            if not isinstance(issuer, str) or not issuer or len(issuer) > 64:
                raise ValueError("Invalid issuer")
            key = (model, origin, issuer)
            if key in seen_keys:
                raise ValueError("Duplicate model/issuer/origin event")
            seen_keys.add(key)
            y = _binary(item["positive"])
            p = _prob(item["model_probability"])
            b = _prob(item["causal_baseline_probability"])
            r = _finite(item["realized_return"])
            lo = _finite(item["lower_decile"])
            hi = _finite(item["upper_decile"])
            if lo > hi or (r > 0) != (y == 1):
                raise ValueError("Invalid future-return label or confidence interval")
            assembled[model].append({
                "origin": origin, "maturity": maturity, "issuer": issuer,
                "model_probability": p, "baseline_probability": b,
                "positive": y, "lower_decile": lo,
                "upper_decile": hi, "realized_return": r,
            })
    sorted_periods = sorted(periods.items())
    overlapping = any(next_origin <= maturity
                      for (_, maturity), (next_origin, _) in zip(sorted_periods, sorted_periods[1:]))
    # Identical assets/outcomes required to compare model families fairly.
    identity = {}
    for model, rows in assembled.items():
        for r in rows:
            key = (r["origin"], r["issuer"])
            if model == MODELS[0]:
                identity[key] = (r["maturity"], r["positive"], r["realized_return"], r["baseline_probability"])
            elif key not in identity or identity[key] != (
                    r["maturity"], r["positive"], r["realized_return"], r["baseline_probability"]):
                raise ValueError("Model forecasts not evaluated on identical outcomes")
    if set((r["origin"], r["issuer"]) for r in assembled["ou"]) != set(identity):
        raise ValueError("Unmatched GBM/OU issuer/date panel")
    origins = len(periods)
    days = (sorted_periods[-1][0] - sorted_periods[0][0]).days
    issuers = len({r["issuer"] for r in assembled["gbm"]})
    sufficient = (origins >= MIN_ORIGINS and issuers >= MIN_ISSUERS
                  and days >= MIN_SPAN_CALENDAR_DAYS and not overlapping)

    diagnostics = {}
    for model, rows in assembled.items():
        if not rows:
            raise ValueError("No evaluable observations for model: "+model)
        n = len(rows)
        brier = sum(_brier(r["model_probability"],r["positive"]) for r in rows)/n
        base = sum(_brier(r["baseline_probability"],r["positive"]) for r in rows)/n
        logloss = sum(_logloss(r["model_probability"],r["positive"]) for r in rows)/n
        base_logloss = sum(_logloss(r["baseline_probability"],r["positive"]) for r in rows)/n
        clusters = defaultdict(list)
        for row in rows:
            clusters[row["origin"]].append(
                _brier(row["baseline_probability"], row["positive"])
                - _brier(row["model_probability"], row["positive"]))
        per_origin = [sum(vals)/len(vals) for _,vals in sorted(clusters.items())]
        low = bootstrap_origin_cluster_lower(per_origin) if sufficient else None
        coverage = sum(r["lower_decile"] <= r["realized_return"] <= r["upper_decile"] for r in rows)/n
        ece = _ece(rows)
        # Gate 3 requires prespecified OOS success on proper scores and
        # calibrated probability ranges. This is NOT a trading-alpha test.
        statistical_screen = (sufficient and low is not None and low > 0
                              and brier < base and logloss < base_logloss
                              and ece <= .05 and .72 <= coverage <= .88)
        diagnostics[model] = {
            "n": n, "origin_clusters": len(clusters),
            "brier": round(brier, 7), "causal_baseline_brier": round(base, 7),
            "logloss": round(logloss, 7), "causal_baseline_logloss": round(base_logloss, 7),
            "brier_skill_vs_causal_baseline": round(1-brier/base, 6) if base>0 else None,
            "lower_5pct_origin_cluster_bootstrap_delta_brier":
                round(low, 7) if low is not None else None,
            "ece_10_bins": round(ece, 6),
            "central_80pct_interval_coverage": round(coverage, 6),
            "statistical_screen_passed": statistical_screen,
        }
    return {
        "title": "Frozen H21 GBM/OU prospective probabilistic evaluation",
        "status": "BLOCKED_INDEPENDENT_SOURCE_AND_FINANCIAL_VALIDATION",
        "matured_origin_clusters": origins,
        "issuer_count": issuers,
        "calendar_span_days": days,
        "overlapping_outcomes": overlapping,
        "minimum_nonoverlapping_origins": MIN_ORIGINS,
        "minimum_issuers": MIN_ISSUERS,
        "minimum_span_days": MIN_SPAN_CALENDAR_DAYS,
        "sample_thresholds_passed": sufficient,
        "evaluations": diagnostics,
        "independent_data_provenance_approved": False,
        "externally_trusted_timestamp_evidence_approved": False,
        "after_cost_portfolio_alpha_demonstrated": False,
        "paper_order_execution_approved": False,
        "merge_approved": False,
        "caveat": "Favorable statistics do not verify source/time evidence or investable alpha.",
    }


def main():
    cli=argparse.ArgumentParser(description="Offline prospective forecasts; no broker")
    cli.add_argument("--matured", type=Path, nargs="+", required=True)
    cli.add_argument("--output", type=Path, required=True)
    args=cli.parse_args()
    report=assess([json.loads(path.read_text(encoding="utf-8")) for path in args.matured])
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"sample_thresholds_passed":report["sample_thresholds_passed"],
                      "paper_order_execution_approved":False}))


if __name__=="__main__":
    main()
