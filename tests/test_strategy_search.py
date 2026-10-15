import unittest
from pathlib import Path
import sys
from datetime import date, timedelta
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from strategy_search import Strategy, candidates, make_simulator


class StrategySearchTests(unittest.TestCase):
    def setUp(self):
        self.days = [(date(2023, 1, 1)+timedelta(days=i)).isoformat() for i in range(170)]
        self.prices = [[100+j+i*(.05+.01*j) for j in range(25)] for i in range(170)]

    def test_distinct_families(self):
        options = candidates()
        self.assertGreater(len(options), 100)
        self.assertEqual(len(set(x.name for x in options)), len(options))
        self.assertGreaterEqual(len(set(x.family for x in options)), 5)

    def test_costs_and_cash_only(self):
        sim = make_simulator(self.days, self.prices)
        c = Strategy("momentum", 20, 5, 21, .94)
        gross, net = sim(130, 169, c, False), sim(130, 169, c, True)
        self.assertGreater(net["costs_gbp"], 0)
        self.assertGreaterEqual(gross["end_gbp"], net["end_gbp"])

    def test_future_price_not_used(self):
        c = Strategy("momentum", 60, 3, 5, .65)
        expected = make_simulator(self.days, self.prices)(130, 150, c)
        future = [list(x) for x in self.prices]
        future[150][0] *= 12
        self.assertEqual(expected, make_simulator(self.days, future)(130, 150, c))

    def test_defensive_cash(self):
        falling = [[200-i*.3-j*.01 for j in range(25)] for i in range(170)]
        c = Strategy("dual_trend", 60, 3, 5, .94, True)
        r = make_simulator(self.days, falling)(130, 170, c)
        self.assertEqual(r["orders"], 0)
        self.assertEqual(r["end_gbp"], 1000.0)

    def test_rejects_invalid_input(self):
        wrong = [list(x) for x in self.prices]
        wrong[8][3] = float("nan")
        with self.assertRaises(ValueError):
            make_simulator(self.days, wrong)


if __name__ == "__main__":
    unittest.main()
