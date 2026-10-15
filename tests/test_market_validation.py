"""Offline no-network unit checks for the market benchmark and data parser."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_validation import index_closes, tracker_proxy, quality_audit


class TestMarketValidation(unittest.TestCase):
    def test_index_csv_parser(self):
        raw = ('Date,Price,Open,High,Low,Vol.,Change %\n'
               '"03/31/2026","10,100.00","10,000","10,200","9,900","",""\n'
               '"01/02/2024","8,000.00","8,000","8,100","7,900","",""\n').encode()
        self.assertEqual(index_closes(raw)["2026-03-31"], 10100.)

    def test_tracker_proxy_charges_entry_cost(self):
        values = {"2024-01-02": 1000., "2024-12-31": 1100.}
        p = tracker_proxy(values, "2024-01-01", "2024-12-31")
        self.assertLess(p["return_pct"], 10.0)
        self.assertGreater(p["return_pct"], 9.0)

    def test_tracker_requires_dates(self):
        with self.assertRaises(ValueError):
            tracker_proxy({"2024-01-02":1000.}, "2024-01-01", "2024-12-31")


if __name__ == "__main__":
    unittest.main()
