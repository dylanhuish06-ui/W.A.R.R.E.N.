"""Fail-closed, OFFLINE forecast ledger for future UK equity predictions.

Record predictions *before* future outcomes are available. Score only a
matured ledger. A SHA or self-declared manifest is not independent data audit
or tamper-proof timestamp evidence. No orders or broker access.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from datetime import date, datetime, timezone
from pathlib import Path

from sde_forecast import predict
from forecast_calibration import Observation, summarize

FROZEN_RESEARCH_COMMIT = "266a0b16e6ce6d2047f7a379823bfb84a9f5b584"
RESEARCH_CUTOFF = date(2026, 10, 15)
FROZEN_CONFIGS = (("gbm", 120, 21, .35), ("ou", 120, 21, .35))
REQUIRED_COLUMNS = ("date", "symbol", "adjusted_close_gbp")


def digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def canonical_json(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def parse_quotes(raw: bytes):
    try:
        lines = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if tuple(lines.fieldnames or ()) != REQUIRED_COLUMNS:
            raise ValueError("Expected CSV header: " + ",".join(REQUIRED_COLUMNS))
        observations = {}
        for row in lines:
            if set(row) != set(REQUIRED_COLUMNS):
                raise ValueError("Malformed or extra quote column")
            dt = date.fromisoformat(row["date"])
            symbol = row["symbol"]
            if not symbol or symbol != symbol.strip() or not symbol.isascii():
                raise ValueError("Invalid symbol")
            p = float(row["adjusted_close_gbp"])
            if not (math.isfinite(p) and p > 0):
                raise ValueError("Invalid adjusted GBP close")
            key = (dt.isoformat(), symbol)
            if key in observations:
                raise ValueError("Duplicate quote")
            observations[key] = p
    except (KeyError, TypeError, UnicodeDecodeError, OverflowError) as exc:
        raise ValueError("Malformed quote file") from exc
    if not observations:
        raise ValueError("No quotes")
    dates = sorted({k[0] for k in observations})
    symbols = sorted({k[1] for k in observations})
    if len(dates) < 122 or len(symbols) < 1 or len(dates) * len(symbols) != len(observations):
        raise ValueError("Incomplete uniform price panel / insufficient training history")
    prices = {s: [observations[(d, s)] for d in dates] for s in symbols}
    return dates, symbols, prices


def check_manifest(manifest: dict, quotes_sha: str, latest: str) -> None:
    # These attestations are user/provider supplied, NOT independently audited.
    required = ("provider", "source_reference", "price_sha256", "currency",
                "split_adjusted", "dividend_adjusted", "corporate_actions_verified",
                "historical_membership_verified", "membership_source_reference",
                "membership_asof", "collected_at_utc")
    if any(x not in manifest for x in required):
        raise ValueError("Missing manifest evidence/attestation fields")
    if (manifest["price_sha256"] != quotes_sha
            or manifest["currency"] != "GBP"
            or manifest["membership_asof"] != latest
            or any(manifest[k] is not True for k in
                   ("split_adjusted", "dividend_adjusted",
                    "corporate_actions_verified", "historical_membership_verified"))
            or any(not isinstance(manifest[k], str) or not manifest[k].strip()
                   for k in ("provider", "source_reference", "membership_source_reference"))):
        raise ValueError("Manifest attestation mismatch: fail closed")
    acquired = datetime.fromisoformat(manifest["collected_at_utc"].replace("Z", "+00:00"))
    if acquired.tzinfo is None:
        raise ValueError("Collection timestamp must include UTC zone")


def record(raw: bytes, manifest: dict, now: datetime) -> dict:
    if now.tzinfo is None:
        raise ValueError("Clock must be timezone-aware")
    now = now.astimezone(timezone.utc)
    dates, symbols, prices = parse_quotes(raw)
    origin = dates[-1]
    if date.fromisoformat(origin) <= RESEARCH_CUTOFF or origin >= now.date().isoformat():
        raise ValueError("Only fully completed post-freeze market sessions may be forecast")
    check_manifest(manifest, digest(raw), origin)
    acquired = datetime.fromisoformat(manifest["collected_at_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
    if acquired > now or acquired.date().isoformat() < origin:
        raise ValueError("Quote snapshot must have been acquired before forecast recording")
    records = []
    for symbol in symbols:
        series = prices[symbol]
        for model, lookback, horizon, shrink in FROZEN_CONFIGS:
            f = predict(series[-(lookback+1):], horizon, model, shrink)
            records.append({
                "symbol": symbol, "model": model, "lookback": lookback,
                "horizon": horizon, "shrinkage": shrink,
                "origin_date": origin, "origin_adjusted_close_gbp": series[-1],
                "probability_positive": f.probability_positive,
                "expected_return": f.expected_simple_return,
                "lower_decile": f.lower_decile_return,
                "upper_decile": f.upper_decile_return,
            })
    ledger = {
        "status": "PROSPECTIVE RECORD; NOT YET MATURE / NO CLAIM OF INDEPENDENT AUDIT",
        "model_commit": FROZEN_RESEARCH_COMMIT,
        "research_cutoff": RESEARCH_CUTOFF.isoformat(),
        "recorded_at_utc": now.isoformat(),
        "quotes_sha256": digest(raw),
        "manifest_sha256": digest(canonical_json(manifest)),
        "origin": origin, "forecast_count": len(records), "forecasts": records,
        "paper_orders_enabled": False, "live_orders_enabled": False,
    }
    ledger["content_sha256"] = digest(canonical_json(ledger))
    return ledger


def score(raw: bytes, manifest: dict, ledger: dict, now: datetime) -> dict:
    if now.tzinfo is None:
        raise ValueError("Clock must be timezone-aware")
    now = now.astimezone(timezone.utc)
    clone = dict(ledger)
    hash_value = clone.pop("content_sha256", None)
    if hash_value != digest(canonical_json(clone)):
        raise ValueError("Ledger integrity hash mismatch")
    if ledger.get("model_commit") != FROZEN_RESEARCH_COMMIT:
        raise ValueError("Wrong model freeze")
    recorded = datetime.fromisoformat(ledger["recorded_at_utc"])
    if recorded.tzinfo is None or recorded >= now:
        raise ValueError("Invalid ledger recording timestamp")
    origin = ledger["origin"]
    if date.fromisoformat(origin) <= RESEARCH_CUTOFF or not date.fromisoformat(origin) < recorded.date():
        raise ValueError("Ledger is not post-freeze prospective")
    dates, symbols, prices = parse_quotes(raw)
    check_manifest(manifest, digest(raw), dates[-1])
    acquired = datetime.fromisoformat(manifest["collected_at_utc"].replace("Z", "+00:00")).astimezone(timezone.utc)
    if acquired > now or acquired.date().isoformat() < dates[-1]:
        raise ValueError("Outcome quote snapshot collection timestamp invalid")
    if origin not in dates:
        raise ValueError("Original signal date absent from matured source")
    i = dates.index(origin)
    if i + 21 >= len(dates):
        raise ValueError("21-session forecast has not matured yet")
    if dates[i + 21] <= recorded.date().isoformat():
        raise ValueError("Predictions were recorded after outcomes became available")
    by_model: dict[str, list[Observation]] = {x[0]: [] for x in FROZEN_CONFIGS}
    expected = {(s, cfg[0]) for s in symbols for cfg in FROZEN_CONFIGS}
    actual = {(x["symbol"], x["model"]) for x in ledger["forecasts"]}
    if expected != actual or len(ledger["forecasts"]) != len(expected):
        raise ValueError("Ledger and present-day universe disagree")
    for item in ledger["forecasts"]:
        symbol, model = item["symbol"], item["model"]
        if model not in by_model or item["horizon"] != 21 or item["lookback"] != 120 or item["shrinkage"] != .35:
            raise ValueError("Forecast config not frozen")
        original = prices[symbol][i]
        if abs(original - item["origin_adjusted_close_gbp"]) > 1e-8:
            raise ValueError("Revised as-of price; independently reconcile corporate actions first")
        realized = prices[symbol][i + 21] / original - 1
        by_model[model].append(Observation(
            symbol, origin, dates[i + 21], item["probability_positive"],
            int(realized > 0), realized, item["expected_return"],
            item["lower_decile"], item["upper_decile"]))
    return {
        "title": "Post-freeze, previously recorded SDE prediction outcomes",
        "source_ledger_sha256": ledger["content_sha256"],
        "outcome_quotes_sha256": digest(raw),
        "origin": origin, "maturity": dates[i + 21],
        "model_metrics": {k: summarize(v) for k, v in by_model.items()},
        "independent_evidence_required": "Provider attestations and timestamps are not independently verified or tamper-proof",
        "audit_approved": False,
        "paper_orders_enabled": False, "live_orders_enabled": False,
    }


def main():
    cli = argparse.ArgumentParser(description="Offline future-signal ledger and matured scoring")
    cli.add_argument("mode", choices=["record", "score"])
    cli.add_argument("--prices", type=Path, required=True)
    cli.add_argument("--manifest", type=Path, required=True)
    cli.add_argument("--ledger", type=Path, help="Required for score")
    cli.add_argument("--output", type=Path, required=True)
    args = cli.parse_args()
    if args.output.exists():
        raise ValueError("Immutable output exists; refusing to overwrite")
    raw = args.prices.read_bytes()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    if args.mode == "record":
        result = record(raw, manifest, now)
    else:
        if args.ledger is None:
            raise ValueError("Score mode needs a pre-existing timestamped --ledger")
        result = score(raw, manifest, json.loads(args.ledger.read_text(encoding="utf-8")), now)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"mode": args.mode, "status": "offline; no broker",
                      "output": str(args.output), "audit_approved": False}))


if __name__ == "__main__":
    main()
