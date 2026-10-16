"""End-to-end, self-contained, synthetic paper-sandbox rehearsal.

NEVER imports a broker client. Demonstrates a clean balance/position
reconciliation, persisted offline idempotency, and restart HALT behavior.
The fixture securities/contract IDs are fictional, NOT investment signals.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from paper_sandbox import SafetyBlock, plan_rebalance
from offline_replay_ledger import ACKNOWLEDGEMENT, OfflineReplayLedger


def run_rehearsal(*, now: datetime) -> dict:
    if now.tzinfo is None:
        raise ValueError("Run timestamp must be timezone-aware")
    now = now.astimezone(timezone.utc)
    quoted_at = (now - timedelta(seconds=30)).isoformat()
    snapshot = {
        "environment": "SIMULATION_ONLY", "broker_connected": False,
        "asof_utc": quoted_at, "cash_currency": "GBP", "cash_gbp": "950.00",
        "positions": {}, "open_orders": [],
        "quotes": {
            "EXAMPLEA": {
                "currency": "GBP", "quote_unit": "GBP", "exchange": "LSE",
                "security_type": "STK", "conid": 100000001,
                "bid": "19.99", "ask": "20.01", "asof_utc": quoted_at,
            },
            "EXAMPLEB": {
                "currency": "GBP", "quote_unit": "GBp", "exchange": "LSE",
                "security_type": "STK", "conid": 100000002,
                "bid": "989", "ask": "991", "asof_utc": quoted_at,
            },
        },
    }
    proposal = plan_rebalance(
        snapshot, {"EXAMPLEA": ".20", "EXAMPLEB": ".15"},
        now=now, kill_switch=False, allow_simulation=True,
    )
    with TemporaryDirectory(prefix="warren-offline-") as tmp:
        path = Path(tmp) / "replay.db"
        with OfflineReplayLedger(path) as history:
            initially_halted = history.halted
            history.enable_offline_only(
                acknowledgement=ACKNOWLEDGEMENT, operator_confirmed=True)
            first = history.replay_once(snapshot, proposal, now=now)
            duplicate_blocked = False
            try:
                history.replay_once(snapshot, proposal, now=now)
            except SafetyBlock as exc:
                duplicate_blocked = "Duplicate" in str(exc)
            if not duplicate_blocked:
                raise AssertionError("Idempotency policy failed")
            history.halt()
            digest = history.verify_chain()
        with OfflineReplayLedger(path) as reopened:
            halt_persisted = reopened.halted
            chain_persisted = reopened.verify_chain() == digest
    if not all([initially_halted, duplicate_blocked, halt_persisted, chain_persisted]):
        raise AssertionError("Fail-closed sandbox rehearsal did not pass")
    return {
        "title": "W.A.R.R.E.N. synthetic execution rehearsal",
        "synthetic_only": True,
        "recorded_at_utc": now.isoformat(),
        "account_connected": False, "paper_orders_sent": 0,
        "live_orders_sent": 0, "kill_switch_after_replay": "ON",
        "test_stock_count": 2,
        "simulated_intent_count": len(proposal["intents"]),
        "estimated_cost_and_units_verified": True,
        "reconciled_cash_gbp": first["reconciliation"]["cash_gbp"],
        "reconciled_positions": first["reconciliation"]["positions"],
        "checks": {
            "default_halt": initially_halted,
            "simulated_reconciliation": first["reconciliation"]["status"] == "SIMULATED_RECONCILED",
            "duplicate_replay_rejected": duplicate_blocked,
            "restart_preserves_halt": halt_persisted,
            "hash_chain_persists": chain_persisted,
        },
        "provenance": "Fictional synthetic prices and contracts; no live TWS test",
        "remaining_gate": "Real broker paper session, independent market data, and human approval",
    }


def main():
    parser = argparse.ArgumentParser(description="Synthetic, offline W.A.R.R.E.N. rehearsal")
    parser.add_argument("--output", type=Path, default=Path("outputs/offline_rehearsal.json"))
    args = parser.parse_args()
    result = run_rehearsal(now=datetime.now(timezone.utc))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "synthetic_only": result["synthetic_only"],
        "checks": result["checks"],
        "paper_orders_sent": result["paper_orders_sent"],
    }, indent=2))


if __name__ == "__main__":
    main()
