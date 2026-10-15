"""Synthetic tests of forecast scoring, strict maturity and temporal isolation."""
import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from forecast_calibration import Observation, observations, schedule, summarize


class ForecastCalibrationTests(unittest.TestCase):
    def setUp(self):
        self.dates = [(date(2023, 1, 1) + timedelta(days=i)).isoformat() for i in range(260)]
        self.symbols = ["A", "B", "C"]
        self.prices = [[100 * math.exp(j*.003 + i * (.0002 + j * .0001)
                                     + .008 * math.sin(i / 4 + j))
                        for j in range(3)] for i in range(260)]

    def test_schedule_non_overlapping_and_inside_window(self):
        out = schedule(self.dates, 140, 210, 21, 120)
        self.assertEqual(out, [140, 161, 182])
        self.assertTrue(all(i + 21 < 210 for i in out))

    def test_brier_and_logloss_on_known_events(self):
        rows = [Observation("A", "a", "b", .7, 1, .03, .01, -.1, .1),
                Observation("B", "a", "b", .3, 0, -.03, -.01, -.1, .1)]
        scores = summarize(rows)
        self.assertAlmostEqual(scores["brier"], .09)
        self.assertAlmostEqual(scores["brier_skill_vs_0_5"], .64)
        self.assertEqual(scores["central_80pct_interval_coverage"], 1)
        self.assertGreater(scores["log_loss"], 0)
        self.assertEqual(sum(x["n"] for x in scores["reliability"]), 2)

    def test_known_past_forecasts_unchanged_when_future_changes(self):
        a, _ = observations(self.dates, self.symbols, self.prices, 140, 180, "gbm", 120, 5)
        changed = [row.copy() for row in self.prices]
        for k in range(180, 260):
            changed[k][0] *= 1.5
        b, _ = observations(self.dates, self.symbols, changed, 140, 180, "gbm", 120, 5)
        self.assertEqual(a, b)

    def test_model_comparison_same_origin_set(self):
        gbm, g_counts = observations(self.dates, self.symbols, self.prices, 140, 220, "gbm", 120, 5)
        ou, o_counts = observations(self.dates, self.symbols, self.prices, 140, 220, "ou", 120, 5)
        self.assertEqual({(x.symbol, x.origin, x.maturity) for x in gbm},
                         {(x.symbol, x.origin, x.maturity) for x in ou})
        self.assertEqual(g_counts["potential_asset_forecasts"], o_counts["potential_asset_forecasts"])
        self.assertEqual(g_counts["excluded_future_path_anomalies"], 0)

    def test_future_jump_audit_count(self):
        altered = [row.copy() for row in self.prices]
        altered[152][0] *= 9
        _, counts = observations(self.dates, self.symbols, altered, 140, 190, "gbm", 120, 5)
        self.assertGreater(counts["excluded_future_path_anomalies"], 0)

    def test_no_empty_summary(self):
        with self.assertRaises(ValueError):
            summarize([])


if __name__ == "__main__":
    unittest.main()
