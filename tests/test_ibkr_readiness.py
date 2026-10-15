"""Offline IBKR readiness/preview tests: no IBKR socket or orders."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from ibkr_readiness import report
from paper_preview import propose_buys
from ibkr_readonly_probe import validate_connection

class ReadinessTests(unittest.TestCase):
    def test_never_promote_ci_to_paper_approval(self):
        x=report()
        self.assertEqual(x["status"], "BLOCKED_PENDING_INDEPENDENT_EVIDENCE")
        self.assertFalse(x["approval_to_merge"])
        self.assertFalse(x["paper_execution_armed"])
        self.assertFalse(x["live_execution_allowed"])
        self.assertIn("broker_probe", x["blockers"])
        self.assertIn("fresh_forward", x["blockers"])

    def test_never_allow_live_port_or_remote_host(self):
        for host,port,account in (("0.0.0.0",7497,"DU1234"),("127.0.0.1",7496,"DU1234"),
                                  ("localhost",4001,"DU1234"),("localhost",7497,"U1234")):
            with self.subTest(host=host,port=port,account=account):
                with self.assertRaises(ValueError):
                    validate_connection(host,port,account)
        validate_connection("127.0.0.1",7497,"DU1234")

    def test_integer_buy_proposals_never_submit(self):
        x=propose_buys(1000,{"A":12.50,"B":21.10,"C":250},{"A":.30,"B":.30,"C":.34},1000)
        self.assertEqual(x["orders_submitted"],0)
        self.assertFalse(x["execution_armed"])
        self.assertGreaterEqual(x["estimated_cash_remaining_gbp"],0)
        self.assertTrue(all(isinstance(a["quantity_whole_shares"],int) and
                            a["quantity_whole_shares"]>0 for a in x["intents"]))

    def test_reject_overweight_or_margin(self):
        with self.assertRaises(ValueError):
            propose_buys(1000,{"A":12},{"A":.5},1000)
        with self.assertRaises(ValueError):
            propose_buys(1000,{"A":12,"B":13,"C":14},
                         {"A":.35,"B":.35,"C":.35},1000)
        with self.assertRaises(ValueError):
            propose_buys(-100,{"A":12},{"A":.3},1000)

    def test_avoid_fractional_shares_and_cash_overdraft(self):
        x=propose_buys(75,{"X":300},{"X":.35},1000)
        self.assertEqual(x["intents"],[])
        x=propose_buys(10,{"X":1},{"X":.30},1000)
        self.assertLessEqual(x["estimated_spend_gbp"],10)

if __name__=="__main__":
    unittest.main()
