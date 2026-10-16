"""Independent evidence/point-in-time data gate for FTSE research.

This inspects user-supplied LICENSED historical data and membership archives.
It neither scrapes restricted feeds nor treats a self-declared manifest as
independent verification. NO orders or broker API. Fails closed for promotion.
"""
from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import io
import json
from pathlib import Path
from collections import defaultdict

PRICE_FIELDS = ("date","symbol","isin","close","unit","currency",
                "split_adjusted","dividend_adjusted","source_ref")
MEMBER_FIELDS = ("symbol","isin","member_from","member_to","known_at","source_ref")


def _hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _rows(raw: bytes, expected: tuple[str,...]) -> list[dict]:
    try:
        data = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
        if tuple(data.fieldnames or ()) != expected:
            raise ValueError("Unexpected CSV fields; expected "+",".join(expected))
        rows = list(data)
        if not rows or any(set(row) != set(expected) or None in row for row in rows):
            raise ValueError("Missing or malformed CSV records")
        return rows
    except UnicodeDecodeError as exc:
        raise ValueError("CSV must be UTF-8") from exc


def _isin(value: str) -> bool:
    return len(value)==12 and value.isascii() and value.isupper() and value.isalnum()


def _date(value: str) -> date:
    return date.fromisoformat(value)


def _positive_decimal(value: str) -> Decimal:
    try:
        val=Decimal(str(value))
    except (InvalidOperation,ValueError) as exc:
        raise ValueError("Invalid price") from exc
    if not val.is_finite() or val <= 0:
        raise ValueError("Nonpositive/nonfinite close")
    return val


def _manifest(raw_prices: bytes, raw_members: bytes, manifest: dict) -> None:
    for field in ("price_sha256","membership_sha256","provider","licence_reference",
                  "price_source_reference","membership_source_reference",
                  "corporate_actions_source_reference","collected_at_utc"):
        if not isinstance(manifest.get(field),str) or not manifest[field].strip():
            raise ValueError("Missing manifest evidence field: "+field)
    if (manifest["price_sha256"] != _hash(raw_prices)
        or manifest["membership_sha256"] != _hash(raw_members)):
        raise ValueError("Input hashes do not match manifest")
    dt=datetime.fromisoformat(manifest["collected_at_utc"].replace("Z","+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Manifest date must be timezone-aware")


def audit(raw_prices: bytes, raw_members: bytes, manifest: dict) -> dict:
    """Validate structure, historical effective dates and currency normalization.

    Audit remains EXTERNALLY UNVERIFIED even when internal checks succeed.
    Structural completeness is necessary but not proof of legitimate point-
    in-time membership (archives may have been revised retrospectively).
    """
    _manifest(raw_prices,raw_members,manifest)
    members=defaultdict(list)
    seen=set()
    for row in _rows(raw_members, MEMBER_FIELDS):
        sym, security=row["symbol"],row["isin"]
        if not sym or not sym.isascii() or not _isin(security) or not row["source_ref"]:
            raise ValueError("Invalid security/member evidence")
        lo=_date(row["member_from"])
        hi=_date(row["member_to"]) if row["member_to"] else None
        known=_date(row["known_at"])
        if (hi is not None and hi < lo) or known > lo:
            raise ValueError("Membership interval or announcement uses future information")
        key=(sym,security,lo,hi)
        if key in seen:
            raise ValueError("Repeated membership interval")
        seen.add(key)
        members[(sym,security)].append((lo,hi,known))
    # Membership sets are keyed by ISIN and ticker to avoid mistakenly
    # joining unrelated instruments that reused a ticker.
    for intervals in members.values():
        ordered=sorted(intervals,key=lambda x:x[0])
        for x,y in zip(ordered,ordered[1:]):
            if x[1] is None or x[1]>=y[0]:
                raise ValueError("Conflicting overlapping membership history")

    quoted={}
    issues=defaultdict(int)
    dates=set()
    for row in _rows(raw_prices, PRICE_FIELDS):
        dt=_date(row["date"]);sym=row["symbol"];isin=row["isin"]
        if not sym or not sym.isascii() or not _isin(isin) or not row["source_ref"]:
            raise ValueError("Missing security identifier or pricing source")
        if row["currency"]!="GBP" or row["unit"] not in ("GBp","GBP"):
            raise ValueError("Unqualified quote currency or unit")
        val=_positive_decimal(row["close"])
        amount=val / 100 if row["unit"]=="GBp" else val
        if row["split_adjusted"]!="true" or row["dividend_adjusted"]!="true":
            issues["unverified_adjustment_flags"] += 1
        key=(dt,sym,isin)
        if key in quoted:
            raise ValueError("Duplicate daily security quote")
        quoted[key]=amount;dates.add(dt)
        if not any(lo<=dt and (hi is None or dt<=hi) and known<=dt
                   for lo,hi,known in members.get((sym,isin), [])):
            issues["price_without_known_membership"] += 1

    missing=0
    for dt in dates:
        active={(sym,isin) for (sym,isin), intervals in members.items()
                if any(lo<=dt and (hi is None or dt<=hi) and known<=dt
                       for lo,hi,known in intervals)}
        known={(sym,isin) for d,sym,isin in quoted if d==dt}
        missing+=len(active-known)
    issues["missing_active_constituent_closes"] = missing
    structurally_acceptable=all(n==0 for n in issues.values())
    return {
        "title":"Point-in-time FTSE data intake structural audit",
        "structural_validation_passed":structurally_acceptable,
        "status":"BLOCKED_EXTERNAL_VERIFICATION" if structurally_acceptable
                 else "BLOCKED_DATA_INTEGRITY",
        "independent_source_evidence_verified":False,
        "candidate_data_fit_for_backtest":False,
        "source_provider_claim":manifest["provider"],
        "source_evidence_references":[manifest["price_source_reference"],
                                    manifest["membership_source_reference"],
                                    manifest["corporate_actions_source_reference"]],
        "prices_sha256":_hash(raw_prices),
        "membership_sha256":_hash(raw_members),
        "trading_dates":len(dates),
        "date_min":min(dates).isoformat(),"date_max":max(dates).isoformat(),
        "security_issuers":len({isin for _,_,isin in quoted}),
        "rows":len(quoted),
        "membership_intervals":sum(len(x) for x in members.values()),
        "issues":dict(issues),
        "warnings":[
            "Manifest/licence/source strings are attestations, NOT independently verified provenance",
            "Survivorship cannot be assessed without independently confirmed historical FTSE reviews",
            "Split/dividend adjustment flags are not an audit of actual corporate-action factors",
            "Historical membership is inclusive by date; trade eligibility also depends on exchange/security state",
            "This code cannot supply licensed FTSE data or prove commercial reproduction rights",
        ],
        "approval_to_merge":False,"paper_orders_enabled":False,
    }


def main():
    ap=argparse.ArgumentParser(description="Offline licensed FTSE data evidence audit; never broker")
    ap.add_argument("--prices",type=Path,required=True)
    ap.add_argument("--membership",type=Path,required=True)
    ap.add_argument("--manifest",type=Path,required=True)
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    r=audit(args.prices.read_bytes(),args.membership.read_bytes(),
            json.loads(args.manifest.read_text(encoding="utf-8")))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(r,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({"status":r["status"],"issues":r["issues"],
                      "independent_source_evidence_verified":False},indent=2))


if __name__=="__main__":
    main()
