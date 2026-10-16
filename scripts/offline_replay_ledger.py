"""Persistent, offline-only, idempotent simulation ledger.

Database stores NO account ID, broker token, order ID or executable order.
SQLite transactions make local simulation records atomic, but hashes here
are NOT external timestamp authority or tamper-proof against DB rewriting.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3

from paper_sandbox import SafetyBlock, simulate_and_reconcile

ACKNOWLEDGEMENT = "OFFLINE-REPLAY-NO-BROKER"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


class OfflineReplayLedger:
    """No broker interface; default-on HALT persisted across process restarts.

    Never call broker connectivity or place_order; these methods do not exist.
    A record committed by SQLite's synchronous transaction can be inspected,
    but it is NOT a source of external immutable audit evidence.
    """

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.path), timeout=5, isolation_level=None)
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS simulation_control (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                halted INTEGER NOT NULL CHECK(halted IN (0,1))
            )
        """)
        self.connection.execute(
            "INSERT OR IGNORE INTO simulation_control(singleton, halted) VALUES(1,1)")
        self.connection.execute("""
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                kind TEXT NOT NULL CHECK(kind IN ('ENABLE_SIMULATION','HALT','SIMULATION')),
                plan_sha TEXT UNIQUE,
                payload TEXT NOT NULL,
                prev_digest TEXT NOT NULL,
                digest TEXT NOT NULL
            )
        """)
        # Fail closed on EVERY process open: a prior simulator unlock cannot
        # authorize a subsequent process. Verify history before appending
        # the synthetic reboot HALT event.
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.verify_chain()
            if not self.halted:
                self.connection.execute(
                    "UPDATE simulation_control SET halted=1 WHERE singleton=1")
                self._append_locked(
                    "HALT", None,
                    {"mode": "SIMULATION_ONLY", "orders_submitted": 0,
                     "reason": "NEW_PROCESS_REQUIRES_EXPLICIT_REENABLE"})
            self.connection.execute("COMMIT")
        except Exception:
            self.connection.execute("ROLLBACK")
            self.connection.close()
            raise

    def close(self):
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    @property
    def halted(self):
        row = self.connection.execute(
            "SELECT halted FROM simulation_control WHERE singleton=1").fetchone()
        if row is None:
            raise SafetyBlock("Missing persistent kill-switch")
        return bool(row[0])

    def verify_chain(self):
        rows = self.connection.execute(
            "SELECT seq,kind,plan_sha,payload,prev_digest,digest "
            "FROM events ORDER BY seq"
        ).fetchall()
        previous = "GENESIS"
        seen_plans = set()
        for offset, (seq, kind, plan, raw, prev, recorded) in enumerate(rows):
            if seq != offset + 1 or prev != previous:
                raise SafetyBlock("Simulation history continuity failure")
            try:
                payload = json.loads(raw)
                if _canonical(payload) != raw:
                    raise SafetyBlock("Noncanonical simulation payload")
            except (TypeError, ValueError) as exc:
                raise SafetyBlock("Malformed simulation payload") from exc
            if kind == "SIMULATION":
                if not isinstance(plan, str) or plan in seen_plans or payload.get("plan_sha256") != plan:
                    raise SafetyBlock("Simulation record identity mismatch")
                seen_plans.add(plan)
            elif plan is not None or kind not in ("ENABLE_SIMULATION", "HALT"):
                raise SafetyBlock("Invalid control event")
            expected = _digest(dict(seq=seq, kind=kind, plan_sha=plan,
                                    payload=payload, prev_digest=prev))
            if recorded != expected:
                raise SafetyBlock("Simulation history hash mismatch")
            previous = recorded
        # External DB rewriting remains possible; fail closed if local state
        # contradicts the latest recorded control event.
        controls = [row[1] for row in rows if row[1] in ("ENABLE_SIMULATION", "HALT")]
        expected_halted = controls[-1] != "ENABLE_SIMULATION" if controls else True
        if self.halted != expected_halted:
            raise SafetyBlock("Kill-switch and audit sequence disagree")
        return previous

    def _append_locked(self, kind, plan, payload):
        prior = self.connection.execute(
            "SELECT seq,digest FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        seq, prev = (prior[0] + 1, prior[1]) if prior else (1, "GENESIS")
        digest = _digest(dict(seq=seq, kind=kind, plan_sha=plan,
                              payload=payload, prev_digest=prev))
        self.connection.execute(
            "INSERT INTO events(seq,kind,plan_sha,payload,prev_digest,digest) VALUES(?,?,?,?,?,?)",
            (seq, kind, plan, _canonical(payload), prev, digest),
        )
        return digest

    def enable_offline_only(self, *, acknowledgement, operator_confirmed=False):
        if acknowledgement != ACKNOWLEDGEMENT or operator_confirmed is not True:
            raise SafetyBlock("Explicit OFFLINE simulation-only acknowledgement required")
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.verify_chain()
            self.connection.execute(
                "UPDATE simulation_control SET halted=0 WHERE singleton=1")
            marker = self._append_locked(
                "ENABLE_SIMULATION", None, {"mode": "SIMULATION_ONLY", "orders_submitted": 0})
            self.connection.execute("COMMIT")
            return marker
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def halt(self):
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.verify_chain()
            self.connection.execute(
                "UPDATE simulation_control SET halted=1 WHERE singleton=1")
            marker = self._append_locked(
                "HALT", None, {"mode": "SIMULATION_ONLY", "orders_submitted": 0})
            self.connection.execute("COMMIT")
            return marker
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

    def replay_once(self, snapshot, plan, *, now):
        """Perform synthetic reconciliation once and log the resulting state.

        No broker interaction. Atomic duplicate check, simulation and record
        commit for local crash recovery. Operator HALT is never bypassed.
        """
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            self.verify_chain()
            if self.halted:
                raise SafetyBlock("Persistent kill switch is ON")
            digest = plan.get("plan_sha256")
            if not isinstance(digest, str) or len(digest) != 64:
                raise SafetyBlock("Missing plan digest")
            existing = self.connection.execute(
                "SELECT 1 FROM events WHERE plan_sha=?", (digest,)).fetchone()
            if existing:
                raise SafetyBlock("Duplicate simulated plan rejected")
            result = simulate_and_reconcile(snapshot, plan, now=now)
            body = {
                "mode": "SIMULATION_ONLY",
                "orders_submitted": 0,
                "plan_sha256": digest,
                "reconciled_cash_gbp": result["cash_gbp"],
                "reconciled_positions": result["positions"],
            }
            marker = self._append_locked("SIMULATION", digest, body)
            self.connection.execute("COMMIT")
            return {"status": "OFFLINE_SIMULATION_RECORDED",
                    "chain_sha256": marker, "orders_submitted": 0,
                    "reconciliation": result}
        except sqlite3.IntegrityError as exc:
            self.connection.execute("ROLLBACK")
            raise SafetyBlock("Duplicate or corrupt simulation event") from exc
        except Exception:
            self.connection.execute("ROLLBACK")
            raise

