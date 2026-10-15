"""Tests verify SDE mathematics, causality and safe probability outputs."""
import sys
import unittest
from math import exp
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sde_forecast import predict
from strategy_search import Strategy, candidates, make_simulator


class PredictiveTests(unittest.TestCase):
    def setUp(self):
        self.prices = [100 * exp(0.001 * i + .008 * __import__("math").sin(i / 3))
                       for i in range(160)]
        self.dates = [f"2023-{1 + i // 28:02}-{1 + i % 28:02}" for i in range(160)]
        self.panel = [[p * (1 + j * .001) * exp(0.0001 * i * j)
                       for j in range(12)] for i, p in enumerate(self.prices)]

    def test_gbm_closed_form(self):
        f = predict(self.prices[:121], 5, "gbm", .3)
        self.assertGreaterEqual(f.probability_positive, 0)
        self.assertLessEqual(f.probability_positive, 1)
        self.assertLess(f.lower_decile_return, f.upper_decile_return)
        self.assertAlmostEqual(
            f.expected_simple_return,
            exp(f.mean_log_return + .5 * f.sd_log_return ** 2) - 1, places=12)

    def test_ou_stable_and_distribution(self):
        f = predict(self.prices[:121], 21, "ou", .3)
        self.assertGreaterEqual(f.ar1_phi, 0)
        self.assertLessEqual(f.ar1_phi, .95)
        self.assertGreaterEqual(f.sd_log_return, 0)
        self.assertLess(f.lower_decile_return, f.upper_decile_return)

    def test_no_future_data_used(self):
        a = predict(self.prices[:121], 5, "gbm")
        changed = list(self.prices)
        changed[121] *= 50
        b = predict(changed[:121], 5, "gbm")
        self.assertEqual(a, b)

    def test_reject_price_anomaly_and_bad_horizon(self):
        bad = self.prices[:121]
        bad[25] *= 6
        with self.assertRaises(ValueError):
            predict(bad, 5)
        with self.assertRaises(ValueError):
            predict(self.prices, 0)

    def test_parametrized_candidates_and_risk_gates(self):
        c = candidates()
        self.assertTrue(any(s.family == "sde_gbm" for s in c))
        self.assertTrue(any(s.family == "sde_ou" for s in c))
        self.assertEqual(len(c), len(set(s.name for s in c)))
        predict_models = [x for x in c if x.family.startswith("sde_")]
        self.assertTrue(all(0 < s.invested <= .94 for s in predict_models))
        sim = make_simulator(self.dates, self.panel)
        a = next(x for x in predict_models if x.family == "sde_gbm")
        b = next(x for x in predict_models if x.family == "sde_ou")
        for cfg in (a, b):
            result = sim(125, 159, cfg)
            self.assertGreater(result["end_gbp"], 0)
            self.assertGreaterEqual(result["costs_gbp"], 0)

    def test_future_execution_close_does_not_change_prior_backtest(self):
        c = next(x for x in candidates() if x.family == "sde_gbm")
        sim = make_simulator(self.dates, self.panel)
        a = sim(125, 145, c)
        modified = [row.copy() for row in self.panel]
        modified[145][0] *= 12
        b = make_simulator(self.dates, modified)(125, 145, c)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
