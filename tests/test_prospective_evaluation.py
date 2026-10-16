"""Synthetic maturity-evidence contract and conservative benchmark tests."""
import copy
from datetime import date, timedelta
import hashlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from prospective_evaluation import assess, bootstrap_origin_cluster_lower


def report(i, count=30):
    origin = date(2027,1,4) + timedelta(days=i*35)
    maturity = origin + timedelta(days=30)
    origin_str = origin.isoformat()
    maturity_str = maturity.isoformat()
    sha=hashlib.sha256(origin_str.encode()).hexdigest()
    rows=[]
    for model in ("gbm","ou"):
        for j in range(count):
            positive = j % 2
            rows.append({
                "model":model, "issuer":f"S{j:03}",
                "origin":origin_str, "maturity":maturity_str,
                "positive":positive,
                "model_probability": .96 if positive else .04,
                "causal_baseline_probability":.5,
                "realized_return":(.15 if positive else -.15) if j % 5 == 0 else (.05 if positive else -.05),
                "lower_decile":-.10, "upper_decile":.10,
                "origin_ledger_sha256":sha,
            })
    return {"audit_approved":False,"paper_orders_enabled":False,
            "horizon_sessions":21, "origin":origin_str,"maturity":maturity_str,
            "prediction_recorded_at_utc":(origin+timedelta(days=1)).isoformat()+"T09:00:00+00:00",
            "source_ledger_sha256":sha,"prospective_observations":rows}


class ProspectiveEvidenceTests(unittest.TestCase):
    def test_no_data_rejected(self):
        with self.assertRaises(ValueError):
            assess([])

    def test_one_origin_is_never_sufficient(self):
        r=assess([report(0)])
        self.assertFalse(r["sample_thresholds_passed"])
        self.assertFalse(r["evaluations"]["gbm"]["statistical_screen_passed"])
        self.assertFalse(r["paper_order_execution_approved"])

    def test_synthetic_favorable_scores_still_require_external_audit(self):
        r=assess([report(i) for i in range(12)])
        self.assertTrue(r["sample_thresholds_passed"])
        self.assertTrue(r["evaluations"]["ou"]["statistical_screen_passed"])
        self.assertFalse(r["independent_data_provenance_approved"])
        self.assertFalse(r["after_cost_portfolio_alpha_demonstrated"])
        self.assertFalse(r["merge_approved"])

    def test_overlap_and_reused_ledger_fail_closed(self):
        rows=[report(i) for i in range(12)]
        rows[1]["origin"]=rows[0]["origin"]
        with self.assertRaisesRegex(ValueError,"Duplicate origin"):
            assess(rows)
        rows=[report(i) for i in range(12)]
        rows[1]["source_ledger_sha256"]=rows[0]["source_ledger_sha256"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            assess(rows)

    def test_inconsistent_model_label_rejected(self):
        example=report(0)
        example["prospective_observations"][30]["positive"]=1
        with self.assertRaises(ValueError):
            assess([example])

    def test_ledger_hash_mismatch_rejected(self):
        example=report(0)
        example["prospective_observations"][0]["origin_ledger_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"Mismatched"):
            assess([example])

    def test_negative_skill_cannot_pass(self):
        events=[report(i) for i in range(12)]
        for e in events:
            for row in e["prospective_observations"]:
                row["model_probability"]=.25 if row["positive"] else .75
        r=assess(events)
        self.assertFalse(r["evaluations"]["gbm"]["statistical_screen_passed"])

    def test_cluster_bootstrap_deterministic(self):
        a=bootstrap_origin_cluster_lower([.1, .2, .25, -.05])
        b=bootstrap_origin_cluster_lower([.1, .2, .25, -.05])
        self.assertEqual(a,b)


if __name__=="__main__":
    unittest.main()
