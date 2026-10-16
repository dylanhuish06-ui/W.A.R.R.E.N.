"""End-to-end synthetic rehearsal smoke test."""
from datetime import datetime, timezone
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from paper_rehearsal import run_rehearsal

class PaperRehearsalTests(unittest.TestCase):
    def test_rehearsal_can_complete_without_broker(self):
        report = run_rehearsal(now=datetime(2026, 10, 16, 12, tzinfo=timezone.utc))
        self.assertTrue(report["synthetic_only"])
        self.assertFalse(report["account_connected"])
        self.assertEqual(report["paper_orders_sent"], 0)
        self.assertEqual(report["live_orders_sent"], 0)
        self.assertGreater(report["simulated_intent_count"], 0)
        self.assertTrue(all(report["checks"].values()))
        self.assertEqual(report["kill_switch_after_replay"], "ON")

if __name__ == "__main__":
    unittest.main()
