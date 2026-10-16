"""Append-only *in-memory* hash-chain audit for offline order-intent events.

Hashes detect accidental modification when the initial trusted digest is
retained; they are NOT an external timestamp/notarization system.
"""
from __future__ import annotations
import hashlib
import json
from dataclasses import dataclass

def _canonical(event):
    return json.dumps(event, sort_keys=True, separators=(",", ":"), allow_nan=False)

def _sha(obj):
    return hashlib.sha256(_canonical(obj).encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class AuditEvent:
    index: int
    previous_digest: str
    category: str
    payload_digest: str
    digest: str

def add_event(events, category, payload):
    if category not in ("PLAN", "SIMULATED_RECONCILIATION", "HALT"):
        raise ValueError("Unknown offline audit event")
    if not isinstance(payload, dict) or payload.get("orders_submitted") != 0:
        raise ValueError("Only offline events with zero submitted orders accepted")
    verify_events(events)
    ix = len(events)
    prev = events[-1].digest if ix else "GENESIS"
    body = dict(index=ix, previous_digest=prev, category=category,
                payload_digest=_sha(payload))
    return events + [AuditEvent(**body, digest=_sha(body))]

def verify_events(events):
    last = "GENESIS"
    for i, event in enumerate(events):
        body = dict(index=event.index, previous_digest=event.previous_digest,
                    category=event.category, payload_digest=event.payload_digest)
        if event.index != i or event.previous_digest != last or _sha(body) != event.digest:
            raise ValueError("Audit chain integrity failed")
        last = event.digest
    return last
