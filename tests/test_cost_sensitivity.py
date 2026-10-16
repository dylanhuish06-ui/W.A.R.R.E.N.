"""Offline fee scenarios are not current IBKR quotes."""
import sys
import unittest
from decimal import Decimal
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from cost_sensitivity import SCENARIOS, trade, round_trip, build_report, D, HypotheticalFees

class CostSensitivityTests(unittest.TestCase):
    def test_transaction_costs_reduce_immediate_roundtrip(self):
        for f in SCENARIOS:
            result=round_trip(300,"20.00","20.04",f,stamp_duty_applies=True)
            self.assertLess(Decimal(result["instant_round_trip_pnl_gbp"]),0)
            self.assertEqual(result["orders_sent"],0)
            self.assertGreater(result["share_count"],0)
            self.assertLessEqual(-D(result["buy"]["signed_cash_gbp"]),D("300"))

    def test_duty_on_buy_only_and_applicability_explicit(self):
        fees=SCENARIOS[0]
        b=trade("BUY",5,20,20.05,fees,True)
        s=trade("SELL",5,20,20.05,fees,True)
        exempt=trade("BUY",5,20,20.05,fees,False)
        self.assertGreater(D(b["stamp_duty_gbp"]),0)
        self.assertEqual(D(s["stamp_duty_gbp"]),0)
        self.assertEqual(D(exempt["stamp_duty_gbp"]),0)
        with self.assertRaises(ValueError):
            trade("BUY",5,20,20.05,fees,None)

    def test_reject_unquoted_broker_fees_and_fractional_shares(self):
        with self.assertRaises(ValueError):
            trade("BUY",2.5,20,21,SCENARIOS[0],True)
        with self.assertRaises(ValueError):
            trade("SELL",1,21,20,SCENARIOS[0],True)
        with self.assertRaises(ValueError):
            trade("SELL",-1,20,21,SCENARIOS[0],True)
        with self.assertRaises(ValueError):
            HypotheticalFees("invalid", "-1",".1","0","5",".005").checked()

    def test_cost_report_remains_unverified(self):
        r=build_report()
        self.assertFalse(r["pricing_verified_against_ibkr_account"])
        self.assertFalse(r["tax_applicability_verified"])
        self.assertFalse(r["paper_execution_enabled"])
        self.assertEqual(len(r["trials"]),6)

if __name__=="__main__":
    unittest.main()
