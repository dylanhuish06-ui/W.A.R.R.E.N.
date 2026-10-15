"""Synthetic, clock-controlled forward-gate tests; not market evidence."""
import csv
import hashlib
import io
import json
import math
import sys
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from forward_gate import record, score, parse_quotes


def fixture(n=170, start_date=date(2026, 6, 1)):
    start = start_date
    days = []
    cur = start
    while len(days) < n:
        if cur.weekday() < 5:
            days.append(cur.isoformat())
        cur += timedelta(days=1)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["date", "symbol", "adjusted_close_gbp"])
    for i, d in enumerate(days):
        for symbol, j in (("AAA", 0), ("BBB", 1)):
            writer.writerow([d, symbol, f"{100*math.exp(i*.0004+j*.01 + .005*math.sin(i/7+j)):.8f}"])
    raw = buf.getvalue().encode()
    manifest = dict(provider="test provider", source_reference="tests-only",
                    price_sha256=hashlib.sha256(raw).hexdigest(), currency="GBP",
                    split_adjusted=True, dividend_adjusted=True, corporate_actions_verified=True,
                    historical_membership_verified=True, membership_source_reference="tests-only",
                    membership_asof=days[-1], collected_at_utc=days[-1]+"T18:00:00+00:00")
    return raw, manifest, days


class ForwardGateTests(unittest.TestCase):
    def test_no_pre_freeze_record(self):
        raw, manifest, dates = fixture(130, date(2026, 1, 1))
        with self.assertRaisesRegex(ValueError, "post-freeze"):
            record(raw, manifest, datetime(2027, 3, 11, tzinfo=timezone.utc))

    def test_manifest_fail_closed(self):
        raw, manifest, dates = fixture()
        manifest["historical_membership_verified"] = False
        with self.assertRaises(ValueError):
            record(raw, manifest, datetime(2027, 3, 11, tzinfo=timezone.utc))

    def test_record_and_matured_score(self):
        raw, manifest, dates = fixture()
        # Record earlier snapshot, not after outcome available.
        rows = raw.decode().strip().splitlines()
        cut = 135 * 2 + 1
        early = ("\n".join(rows[:cut]) + "\n").encode()
        early_m = dict(manifest, price_sha256=hashlib.sha256(early).hexdigest(),
                       membership_asof=dates[134], collected_at_utc=dates[134]+"T18:00:00+00:00")
        timestamp = datetime.fromisoformat(dates[135] + "T12:00:00+00:00")
        ledger = record(early, early_m, timestamp)
        result = score(raw, manifest, ledger, datetime(2027, 3, 11, tzinfo=timezone.utc))
        self.assertFalse(result["audit_approved"])
        self.assertEqual(result["model_metrics"]["gbm"]["n"], 2)
        self.assertEqual(result["model_metrics"]["ou"]["n"], 2)

    def test_unmatured_rejected(self):
        raw, manifest, dates = fixture(160)
        lines = raw.decode().strip().splitlines()
        early = ("\n".join(lines[:281]) + "\n").encode()
        early_m = dict(manifest, price_sha256=hashlib.sha256(early).hexdigest(),
                       membership_asof=dates[139], collected_at_utc=dates[139]+"T18:00:00+00:00")
        ledger = record(early, early_m, datetime.fromisoformat(dates[140]+"T12:00:00+00:00"))
        with self.assertRaises(ValueError):
            score(early, early_m, ledger, datetime(2027, 3, 11, tzinfo=timezone.utc))

    def test_modified_ledger_rejected(self):
        raw, manifest, dates = fixture()
        lines = raw.decode().strip().splitlines()
        early = ("\n".join(lines[:271]) + "\n").encode()
        early_m = dict(manifest, price_sha256=hashlib.sha256(early).hexdigest(),
                       membership_asof=dates[134])
        ledger = record(early, early_m, datetime.fromisoformat(dates[135]+"T12:00:00+00:00"))
        ledger["forecasts"][0]["probability_positive"] = .99
        with self.assertRaises(ValueError):
            score(raw, manifest, ledger, datetime(2027, 3, 11, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
