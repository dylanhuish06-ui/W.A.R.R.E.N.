"""Fail-closed W.A.R.R.E.N. IBKR paper-readiness evidence report.

This tool NEVER connects to a broker or places an order. It distinguishes
passing research CI from external permissions, data validity and actual
paper-environment checks. Do not equate a green workflow to trading readiness.
"""
from __future__ import annotations
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

CHECKS = (
    ("unit_tests", "Offline unit and smoke tests", "repository", "verified"),
    ("calibration_audit", "Retrospective probability calibration recorded", "repository", "verified"),
    ("data_provenance", "Independently audited historical membership, adjusted prices and GBP units", "external", "blocked"),
    ("fresh_forward", "Post-freeze, externally time-stamped predictions and matured independent returns", "external", "blocked"),
    ("probability_skill", "Prespecified calibration and risk thresholds passed on untouched forward data", "external", "blocked"),
    ("costs", "Verified IBKR GBP/GBp commissions, stamp duty, exchange fees and whole-share execution", "external", "blocked"),
    ("broker_probe", "TWS/Gateway read-only verified locally in paper session against expected account", "local", "blocked"),
    ("paper_account", "Paper account base currency, permissions and data subscription confirmed", "local", "blocked"),
    ("runbook", "Kill switch, operational controls, logging and human review exercised", "external", "blocked"),
)

def report() -> dict:
    """Green research jobs do not establish an IBKR-safe operational connection.

    No secrets or account numbers are embedded, and no arbitrary JSON
    overrides may flip external approval gates.
    """
    checks = [
        {"id": key, "requirement": title, "provenance": scope,
         "state": default, "evidence": (
             "CI tests validate offline code only" if default == "verified"
             else "Required external/local evidence not yet independently established")}
        for key, title, scope, default in CHECKS
    ]
    blocked = [x["id"] for x in checks if x["state"] != "verified"]
    return {
        "project": "W.A.R.R.E.N.", "workflow": "IBKR PAPER readiness only",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED_PENDING_INDEPENDENT_EVIDENCE" if blocked else "READY_FOR_HUMAN_PAPER_REVIEW",
        "candidate_branch": "feature/ibkr-paper-readiness-autovalidation",
        "base_prs": [1, 2],
        "blockers": blocked, "checks": checks,
        "intended_broker": "IBKR Trader Workstation or IB Gateway; PAPER ONLY",
        "broker_connected": False, "orders_sent": 0,
        "paper_execution_armed": False, "live_execution_allowed": False,
        "approval_to_merge": False, "limitations": [
            "A green GitHub Actions workflow is NOT authorization or evidence that the broker is ready.",
            "GitHub cloud runners cannot access the user's local TWS/IB Gateway socket.",
            "Provider licence, market data corrections, account access and market permissions require independent verification.",
            "There is no current new blind, matured stock-level 2026 forward test.",
            "Approval to merge and begin paper-order trials must be separately obtained from the user.",
        ],
    }

def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=Path("outputs/ibkr_readiness.json"))
    args = p.parse_args()
    result = report()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": result["status"], "remaining": result["blockers"],
                      "broker_connected": False, "orders_sent": 0}, indent=2))

if __name__ == "__main__":
    main()
