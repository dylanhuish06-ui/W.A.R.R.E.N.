"""Optional LOCAL READ-ONLY diagnostic for IBKR paper TWS/Gateway.

No order-placement code. Not executed on GitHub runners. Run ONLY after
checking the TWS paper-mode banner and Read-Only API setting on your computer.
Never output account IDs or passwords.
"""
from __future__ import annotations
import argparse
import json
import os
import threading
from pathlib import Path

PAPER_PORTS = (7497, 4002)
def validate_connection(host: str, port: int, expected_account: str) -> None:
    if host not in ("127.0.0.1", "localhost", "::1") or port not in PAPER_PORTS:
        raise ValueError("Only localhost and default IBKR PAPER ports are permitted")
    if not expected_account.startswith("DU") or len(expected_account) < 4:
        raise ValueError("Expected masked paper account must begin with DU; verify it locally")

def probe(host: str, port: int, expected_account: str, timeout: float = 8.0) -> dict:
    validate_connection(host, port, expected_account)
    try:
        from ibapi.client import EClient
        from ibapi.wrapper import EWrapper
    except ImportError as exc:
        raise RuntimeError("Install IBKR's official TWS Python API locally; not supplied in this repository") from exc

    signal = threading.Event()
    finished = threading.Event()
    state = {"connected": False, "expected_account_present": False, "error": False}

    class Reader(EWrapper, EClient):
        def __init__(self):
            EClient.__init__(self, self)

        def nextValidId(self, orderId):
            self.reqManagedAccts()
            self.reqCurrentTime()

        def managedAccounts(self, accountsList):
            # No account number is printed, logged or returned.
            accounts = [x.strip() for x in accountsList.split(",") if x.strip()]
            state["expected_account_present"] = expected_account in accounts
            state["connected"] = True
            signal.set()

        def error(self, *args, **kwargs):
            # Suppress raw broker messages to avoid disclosing account info.
            state["error"] = True

    app = Reader()
    try:
        app.connect(host, port, 87)
        thread = threading.Thread(target=app.run, daemon=True)
        thread.start()
        signal.wait(timeout)
    finally:
        app.disconnect()
    ok = state["connected"] and state["expected_account_present"] and not state["error"]
    return {
        "paper_port_only": True,
        "expected_account_matched": state["expected_account_present"],
        "socket_handshake_seen": state["connected"],
        "status": "LOCAL_READONLY_DIAGNOSTIC" if ok else "BLOCKED",
        "verified_paper_mode_from_api": False,
        "orders_sent": 0,
        "warning": "Port/account prefix alone do not prove paper login. Confirm TWS visibly says PAPER and read-only is enabled.",
    }

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--host", default="127.0.0.1")
    a.add_argument("--port", type=int, default=7497)
    a.add_argument("--timeout", type=float, default=8.0)
    args=a.parse_args()
    account=os.getenv("WARREN_IBKR_PAPER_ACCOUNT", "")
    validate_connection(args.host, args.port, account)
    print(json.dumps(probe(args.host, args.port, account, args.timeout), indent=2))

if __name__ == "__main__":
    main()
