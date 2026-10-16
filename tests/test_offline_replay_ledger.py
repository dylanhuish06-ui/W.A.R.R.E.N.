"""Offline SQLite safety/recovery checks; no broker orders."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from paper_sandbox import SafetyBlock, plan_rebalance
from offline_replay_ledger import OfflineReplayLedger, ACKNOWLEDGEMENT


class OfflineReplayTests(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.TemporaryDirectory()
        self.db = Path(self.root.name) / "local_only.db"
        self.now = datetime(2026, 10, 16, 10, 30, tzinfo=timezone.utc)
        t = (self.now - timedelta(seconds=15)).isoformat()
        self.snapshot = dict(
            environment="SIMULATION_ONLY", broker_connected=False,
            asof_utc=t, cash_currency="GBP", cash_gbp="950",
            open_orders=[], positions={},
            quotes={
                "AAA": dict(currency="GBP", exchange="LSE", security_type="STK",
                            quote_unit="GBP", conid=11, bid="19.99", ask="20.01", asof_utc=t),
                "BBB": dict(currency="GBP", exchange="LSE", security_type="STK",
                            quote_unit="GBp", conid=22, bid="989", ask="991", asof_utc=t),
            })
        self.plan = plan_rebalance(
            self.snapshot, {"AAA": ".20", "BBB": ".15"}, now=self.now,
            kill_switch=False, allow_simulation=True,
        )

    def tearDown(self):
        self.root.cleanup()

    def test_halt_on_new_database_and_requires_explicit_ack(self):
        with OfflineReplayLedger(self.db) as ledger:
            self.assertTrue(ledger.halted)
            with self.assertRaisesRegex(SafetyBlock, "kill switch"):
                ledger.replay_once(self.snapshot, self.plan, now=self.now)
            with self.assertRaisesRegex(SafetyBlock, "acknowledgement"):
                ledger.enable_offline_only(acknowledgement="yes", operator_confirmed=True)
            with self.assertRaisesRegex(SafetyBlock, "acknowledgement"):
                ledger.enable_offline_only(acknowledgement=ACKNOWLEDGEMENT, operator_confirmed=False)
            self.assertTrue(ledger.halted)

    def test_atomic_simulation_duplicate_block_and_restart(self):
        with OfflineReplayLedger(self.db) as ledger:
            ledger.enable_offline_only(
                acknowledgement=ACKNOWLEDGEMENT, operator_confirmed=True)
            result = ledger.replay_once(self.snapshot, self.plan, now=self.now)
            self.assertEqual(result["orders_submitted"], 0)
            self.assertEqual(result["status"], "OFFLINE_SIMULATION_RECORDED")
            with self.assertRaisesRegex(SafetyBlock, "Duplicate"):
                ledger.replay_once(self.snapshot, self.plan, now=self.now)
            chain = ledger.verify_chain()
        with OfflineReplayLedger(self.db) as ledger:
            self.assertFalse(ledger.halted)
            self.assertEqual(ledger.verify_chain(), chain)
            with self.assertRaisesRegex(SafetyBlock, "Duplicate"):
                ledger.replay_once(self.snapshot, self.plan, now=self.now)
            ledger.halt()
        with OfflineReplayLedger(self.db) as ledger:
            self.assertTrue(ledger.halted)
            with self.assertRaisesRegex(SafetyBlock, "kill switch"):
                ledger.replay_once(self.snapshot, self.plan, now=self.now)

    def test_direct_database_edit_detected(self):
        with OfflineReplayLedger(self.db) as ledger:
            ledger.enable_offline_only(
                acknowledgement=ACKNOWLEDGEMENT, operator_confirmed=True)
            ledger.replay_once(self.snapshot, self.plan, now=self.now)
            ledger.connection.execute(
                "UPDATE events SET payload=? WHERE kind='SIMULATION'",
                ('{"forged":true}',))
            with self.assertRaises(SafetyBlock):
                ledger.verify_chain()
            with self.assertRaises(SafetyBlock):
                ledger.halt()

    def test_tampered_kill_switch_metadata_rejected(self):
        with OfflineReplayLedger(self.db) as ledger:
            ledger.connection.execute(
                "UPDATE simulation_control SET halted=0 WHERE singleton=1")
            with self.assertRaisesRegex(SafetyBlock, "Kill-switch"):
                ledger.verify_chain()
            with self.assertRaises(SafetyBlock):
                ledger.replay_once(self.snapshot, self.plan, now=self.now)

    def test_failed_replay_does_not_consume_plan(self):
        with OfflineReplayLedger(self.db) as ledger:
            ledger.enable_offline_only(
                acknowledgement=ACKNOWLEDGEMENT, operator_confirmed=True)
            changed = dict(self.snapshot, cash_gbp="951")
            with self.assertRaisesRegex(SafetyBlock, "mismatched plan"):
                ledger.replay_once(changed, self.plan, now=self.now)
            successful = ledger.replay_once(self.snapshot, self.plan, now=self.now)
            self.assertEqual(successful["orders_submitted"], 0)
            self.assertEqual(len(ledger.connection.execute(
                "SELECT * FROM events WHERE kind='SIMULATION'").fetchall()), 1)


if __name__ == "__main__":
    unittest.main()
