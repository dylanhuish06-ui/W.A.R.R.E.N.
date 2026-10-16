"""Synthetic examples only; do not claim licensed FTSE source certification."""
import hashlib
import io
import csv
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from pit_data_audit import audit


def csvb(header, records):
    stream=io.StringIO();w=csv.writer(stream);w.writerow(header);w.writerows(records)
    return stream.getvalue().encode()

class PointInTimeDataTests(unittest.TestCase):
    def setUp(self):
        self.members=csvb(
            ["symbol","isin","member_from","member_to","known_at","source_ref"],
            [["AAA","GB0000000001","2026-09-01","","2026-08-29","vendor/archive"],
             ["BBB","GB0000000002","2026-09-01","2026-09-02","2026-08-29","vendor/archive"]])
        self.records=[
            ["2026-09-01","AAA","GB0000000001","1234","GBp","GBP","true","true","vendor/adjusted"],
            ["2026-09-01","BBB","GB0000000002","10.1","GBP","GBP","true","true","vendor/adjusted"],
            ["2026-09-02","AAA","GB0000000001","1250","GBp","GBP","true","true","vendor/adjusted"],
            ["2026-09-02","BBB","GB0000000002","11","GBP","GBP","true","true","vendor/adjusted"],
            ["2026-09-03","AAA","GB0000000001","12.6","GBP","GBP","true","true","vendor/adjusted"],
        ]
        self.header=["date","symbol","isin","close","unit","currency","split_adjusted",
                     "dividend_adjusted","source_ref"]

    def bundle(self, prices=None,members=None):
        raw=csvb(self.header, self.records if prices is None else prices)
        mem=self.members if members is None else members
        metadata=dict(price_sha256=hashlib.sha256(raw).hexdigest(),
                      membership_sha256=hashlib.sha256(mem).hexdigest(),
                      provider="example-not-real",licence_reference="synthetic fixture",
                      price_source_reference="example-source",membership_source_reference="example-archive",
                      corporate_actions_source_reference="example-corporate-actions",
                      collected_at_utc="2026-10-16T09:00:00+00:00")
        return raw,mem,metadata

    def test_complete_history_is_not_external_approval(self):
        raw,m,meta=self.bundle()
        result=audit(raw,m,meta)
        self.assertTrue(result["structural_validation_passed"])
        self.assertFalse(result["candidate_data_fit_for_backtest"])
        self.assertEqual(result["status"],"BLOCKED_EXTERNAL_VERIFICATION")
        self.assertEqual(result["issues"]["missing_active_constituent_closes"],0)

    def test_missing_current_constituent_is_flagged(self):
        raw,m,meta=self.bundle(prices=self.records[0:3]+self.records[4:])
        result=audit(raw,m,meta)
        self.assertGreater(result["issues"]["missing_active_constituent_closes"],0)
        self.assertEqual(result["status"],"BLOCKED_DATA_INTEGRITY")

    def test_future_known_membership_rejected(self):
        mem=csvb(["symbol","isin","member_from","member_to","known_at","source_ref"],
            [["AAA","GB0000000001","2026-09-01","","2026-09-03","archive"]])
        raw,m,meta=self.bundle(members=mem)
        with self.assertRaisesRegex(ValueError,"future information"):
            audit(raw,m,meta)

    def test_corrupted_hash_rejected(self):
        raw,m,meta=self.bundle()
        meta["price_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"hashes"):
            audit(raw,m,meta)

    def test_unverified_dividends_flags_cannot_pass(self):
        prices=[row.copy() for row in self.records]
        prices[0][7]="false"
        raw,m,meta=self.bundle(prices=prices)
        result=audit(raw,m,meta)
        self.assertEqual(result["issues"]["unverified_adjustment_flags"],1)
        self.assertFalse(result["structural_validation_passed"])

    def test_duplicate_stock_price_rejected(self):
        raw,m,meta=self.bundle(prices=self.records+[self.records[0]])
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            audit(raw,m,meta)

if __name__=="__main__":
    unittest.main()
