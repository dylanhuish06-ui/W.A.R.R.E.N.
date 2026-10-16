"""Safety properties for OFFLINE whole-share sandbox; never talks to IBKR."""
from __future__ import annotations
import copy
from datetime import datetime, timedelta, timezone
from dataclasses import replace
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from paper_sandbox import SafetyBlock, validate, plan_rebalance, simulate_and_reconcile
from sandbox_audit import add_event, verify_events


class PaperSandboxTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 16, 10, 30, tzinfo=timezone.utc)
        t = (self.now - timedelta(seconds=30)).isoformat()
        self.snapshot = {
            "environment": "SIMULATION_ONLY", "broker_connected": False,
            "asof_utc": t, "cash_currency": "GBP", "cash_gbp": "900.00",
            "open_orders": [], "positions": {"AAA": 2},
            "quotes": {
                "AAA": {"bid": "19.95", "ask": "20.05", "asof_utc": t,
                        "currency": "GBP", "quote_unit": "GBP",
                        "exchange": "LSE", "security_type": "STK", "conid": 101},
                "BBB": {"bid": "2590", "ask": "2610", "asof_utc": t,
                        "currency": "GBP", "quote_unit": "GBp",
                        "exchange": "LSE", "security_type": "STK", "conid": 202},
                "CCC": {"bid": "9.99", "ask": "10.01", "asof_utc": t,
                        "currency": "GBP", "quote_unit": "GBP",
                        "exchange": "LSE", "security_type": "STK", "conid": 303},
            },
        }
        self.weights = {"AAA": ".20", "BBB": ".15", "CCC": ".10"}

    def plan(self, **kw):
        return plan_rebalance(
            self.snapshot, self.weights, now=self.now,
            kill_switch=False, allow_simulation=True, **kw
        )

    def test_default_kill_switch_and_explicit_unlock(self):
        with self.assertRaisesRegex(SafetyBlock, "Kill switch"):
            plan_rebalance(self.snapshot, self.weights, now=self.now)
        with self.assertRaisesRegex(SafetyBlock, "Kill switch"):
            plan_rebalance(self.snapshot, self.weights, now=self.now,
                           kill_switch=False)

    def test_round_trip_whole_shares_and_reconciliation(self):
        p = self.plan()
        self.assertFalse(p["broker_connected"])
        self.assertFalse(p["execution_enabled"])
        self.assertEqual(p["orders_submitted"], 0)
        self.assertTrue(p["intents"])
        self.assertTrue(all(isinstance(i["quantity"], int) for i in p["intents"]))
        self.assertEqual(p["intents"][0]["intent_type"], "NON_TRANSMITTABLE_SIMULATION")
        out = simulate_and_reconcile(self.snapshot, p, now=self.now)
        self.assertEqual(out["status"], "SIMULATED_RECONCILED")
        self.assertEqual(out["orders_submitted"], 0)
        self.assertEqual(out["positions"], p["projected_positions"])

    def test_pence_quote_is_explicitly_converted(self):
        _, _, q = validate(self.snapshot, self.now)
        self.assertEqual(str(q["BBB"]["bid"]), "25.90")
        self.assertEqual(str(q["BBB"]["ask"]), "26.10")
        self.assertEqual(str(q["AAA"]["ask"]), "20.05")

    def test_sells_before_buys(self):
        self.snapshot["cash_gbp"] = "700"
        self.snapshot["positions"] = {"AAA": 10}
        self.weights = {"BBB": ".15"}
        p = self.plan()
        self.assertEqual(p["intents"][0]["side"], "SELL")
        self.assertEqual(p["intents"][-1]["side"], "BUY")
        out = simulate_and_reconcile(self.snapshot, p, now=self.now)
        self.assertEqual(out["positions"]["AAA"], 0)

    def test_reject_stale_or_future_quotes(self):
        bad = copy.deepcopy(self.snapshot)
        bad["quotes"]["AAA"]["asof_utc"] = (
            self.now - timedelta(minutes=6)).isoformat()
        with self.assertRaisesRegex(SafetyBlock, "Stale"):
            plan_rebalance(bad, self.weights, now=self.now,
                           kill_switch=False, allow_simulation=True)
        bad = copy.deepcopy(self.snapshot)
        bad["asof_utc"] = (self.now + timedelta(seconds=5)).isoformat()
        with self.assertRaisesRegex(SafetyBlock, "Stale"):
            plan_rebalance(bad, self.weights, now=self.now,
                           kill_switch=False, allow_simulation=True)

    def test_reject_unqualified_contract_or_unit(self):
        for attr, value in [
            ("exchange", "SMART"), ("quote_unit", "USD"),
            ("currency", "USD"), ("security_type", "FUT"),
            ("conid", -1)
        ]:
            with self.subTest(attr=attr):
                bad = copy.deepcopy(self.snapshot)
                bad["quotes"]["BBB"][attr] = value
                with self.assertRaises(SafetyBlock):
                    self._plan_on(bad)

    def _plan_on(self, snapshot):
        return plan_rebalance(snapshot, self.weights, now=self.now,
                              kill_switch=False, allow_simulation=True)

    def test_reject_spread_too_wide_and_crossed(self):
        for bid, ask in (("10", "20"), ("30", "20")):
            bad = copy.deepcopy(self.snapshot)
            bad["quotes"]["BBB"]["bid"] = bid
            bad["quotes"]["BBB"]["ask"] = ask
            with self.assertRaisesRegex(SafetyBlock, "spread"):
                self._plan_on(bad)

    def test_reject_pending_orders_or_existing_margin(self):
        bad = copy.deepcopy(self.snapshot)
        bad["open_orders"] = ["unknown"]
        with self.assertRaisesRegex(SafetyBlock, "pending"):
            self._plan_on(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["cash_gbp"] = "-1"
        with self.assertRaisesRegex(SafetyBlock, "borrowing"):
            self._plan_on(bad)

    def test_reject_turnover_or_single_name_cap(self):
        with self.assertRaisesRegex(SafetyBlock, "turnover"):
            self.plan(max_turnover_fraction=".05")
        bad = copy.deepcopy(self.weights)
        bad["AAA"] = ".36"
        with self.assertRaisesRegex(SafetyBlock, "allocation"):
            plan_rebalance(self.snapshot, bad, now=self.now,
                           kill_switch=False, allow_simulation=True)

    def test_tampered_or_other_snapshot_cannot_reconcile(self):
        p = self.plan()
        changed = copy.deepcopy(p)
        changed["intents"][0]["quantity"] += 1
        with self.assertRaisesRegex(SafetyBlock, "Tampered"):
            simulate_and_reconcile(self.snapshot, changed, now=self.now)
        original = copy.deepcopy(self.snapshot)
        original["cash_gbp"] = "899"
        with self.assertRaisesRegex(SafetyBlock, "mismatched"):
            simulate_and_reconcile(original, p, now=self.now)

    def test_hash_chain_detects_modification_and_reordering(self):
        p = self.plan()
        r = simulate_and_reconcile(self.snapshot, p, now=self.now)
        chain = add_event([], "PLAN", p)
        chain = add_event(chain, "SIMULATED_RECONCILIATION", r)
        self.assertEqual(verify_events(chain), chain[-1].digest)
        with self.assertRaises(ValueError):
            verify_events(list(reversed(chain)))
        with self.assertRaises(ValueError):
            verify_events([chain[0], replace(chain[1], payload_digest="invalid")])

    def test_audit_never_accepts_submitted_orders(self):
        with self.assertRaisesRegex(ValueError, "zero submitted"):
            add_event([], "PLAN", {"orders_submitted": 1})

    def test_nonfinite_values_or_nonsensical_stock_quantity(self):
        for cash in ("NaN", "Infinity"):
            bad = copy.deepcopy(self.snapshot)
            bad["cash_gbp"] = cash
            with self.assertRaises(SafetyBlock):
                self._plan_on(bad)
        bad = copy.deepcopy(self.snapshot)
        bad["positions"]["AAA"] = -1
        with self.assertRaises(SafetyBlock):
            self._plan_on(bad)
        bad["positions"]["AAA"] = 2.5
        with self.assertRaises(SafetyBlock):
            self._plan_on(bad)


if __name__ == "__main__":
    unittest.main()
