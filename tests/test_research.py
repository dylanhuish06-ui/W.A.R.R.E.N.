import csv
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

from warren.backtest import run_backtest
from warren.config import ResearchConfig
from warren.data import load_close_panel
from warren.risk import validate_target
from warren.signals import momentum_target


def panel(days=45, names=25):
    return [(date(2025, 1, 1) + timedelta(days=i),
             {f"S{j:02}": 100 + 0.2 * i + j / 10 + j * i * 0.003 for j in range(names)})
            for i in range(days)]


class WarrenResearchTests(unittest.TestCase):
    def test_defaults_fail_closed(self):
        config = ResearchConfig()
        self.assertFalse(config.trading_armed)
        self.assertFalse(config.live_trading_allowed)
        with self.assertRaises(ValueError):
            ResearchConfig(trading_armed=True)
        with self.assertRaises(ValueError):
            ResearchConfig(live_trading_allowed=True)

    def test_risk_caps(self):
        c = ResearchConfig()
        validate_target({f"S{i}": .05 for i in range(20)}, c)
        for target in ({"S1": .051}, {"S1": -.01}, {f"S{i}": .05 for i in range(21)}):
            with self.assertRaises(ValueError):
                validate_target(target, c)

    def test_no_signal_from_current_execution_close(self):
        prices = panel()
        cfg = ResearchConfig()
        before = momentum_target(prices, 23, cfg)
        manipulated = [(d, dict(v)) for d, v in prices]
        manipulated[24][1]["S00"] = 999999
        self.assertEqual(before, momentum_target(manipulated, 23, cfg))

    def test_strategy_is_long_only_and_capped(self):
        weights = momentum_target(panel(), 25, ResearchConfig())
        validate_target(weights, ResearchConfig())
        self.assertLessEqual(len(weights), 20)
        self.assertTrue(weights)

    def test_backtest_outputs_benchmark_and_metrics(self):
        result = run_backtest(panel())
        self.assertEqual(result["observations"], 24)
        self.assertIn("benchmark_final_gbp", result)
        self.assertFalse(result["live_trading_enabled"])
        self.assertEqual(len(result["history"]), result["observations"])
        self.assertGreater(result["final_equity_gbp"], 0)

    def test_breach_of_initial_capital_halts_trading(self):
        prices = panel()
        for i in range(23, len(prices)):
            for s in prices[i][1]:
                prices[i][1][s] *= 0.5
        outcome = run_backtest(prices)
        self.assertTrue(outcome["stopped"])
        self.assertEqual(outcome["history"][-1]["positions"], 0)

    def test_reject_bad_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "prices.csv"
            with path.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["date", "symbol", "close"])
                w.writerows([["2025-01-01", "A", 10], ["2025-01-01", "B", 20],
                             ["2025-01-02", "A", 11]])
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                load_close_panel(path)

    def test_finite_config_only(self):
        with self.assertRaises(ValueError):
            ResearchConfig(transaction_cost_bps=float("nan"))
        with self.assertRaises(ValueError):
            ResearchConfig(max_position_weight=float("inf"))

    def test_reject_insufficient_data(self):
        with self.assertRaisesRegex(ValueError, "warm-up"):
            run_backtest(panel(days=22))


if __name__ == "__main__":
    unittest.main()
