# Persistent **offline** replay ledger

\`scripts/offline_replay_ledger.py\` uses standard-library SQLite to provide
transactionally consistent **simulation-only** intent history, not an order
management system. All work occurs locally. Do NOT place the SQLite file in
the repository or upload account snapshots, contract IDs or credentials.

- New database starts in **HALT**. A local simulator must explicitly
  acknowledge \`OFFLINE-REPLAY-NO-BROKER\` and confirm the operator deliberately
  wants to run a *simulation*. No real broker ports, order APIs or network.
- Already-recorded plan digests are rejected as duplicates, even after a
  process restart. A failed reconciliation rolls back and does not consume
  the digest.
- Every committed synthetic action has a chained SHA-256 digest, with
  continuity verified under SQLite's \`BEGIN IMMEDIATE\` transaction.
- The HALT/ENABLE switch survives process restarts and must match the
  simulated control history. **Every new process opening automatically
  re-enters HALT**, even if the previous process was unlocked; re-arming
  requires renewed explicit acknowledgement. It cannot be bypassed by merely
  choosing an execution parameter in the replay method.
- Synthetic instant-full-fill reconciliation checks positions, cash and the
  underlying original quote snapshot SHA before committing a simulation.

**Important limits:** This is not a tamper-proof ledger, trusted external
timestamp, production distributed idempotency store or IBKR order
reconciliation. Database administrators can rewrite the entire history and
its digests. No partial fills, broker errors or order acknowledgment are
modelled. All trades remain hypothetical and no account was accessed.

Run regression tests with
\`PYTHONPATH=src python -m unittest discover -s tests -v\`.

Further requirements for a future broker stage: independent persisted
operator authorization, local paper-account identity and API verification,
durable broker transaction identity, retry/failure semantics, open-order
snapshot reconciliation, realized commission reports and tested cancellation.
Nothing should be connected to a broker until explicit user review.
