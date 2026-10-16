# W.A.R.R.E.N. simulated execution safety harness (offline)

**No live or paper order-placement capability exists in this module.**
Neither \`paper_sandbox.py\` nor \`sandbox_audit.py\` imports IBKR,
connects a socket, queries account balances, transmits orders, or schedules
broker actions. This only tests deterministic proposed cash/position effects.

## What is implemented

- Fail-closed default **kill switch ON**, requiring deliberate local opt-in
  for even a *simulation*.
- Explicit \`SIMULATION_ONLY\` synthetic snapshots, \`broker_connected=false\`
  and **zero outstanding orders**.
- GBP cash, verified-format stock contract identifier, exchange=LSE,
  currency=GBP and raw quote unit in either GBP or GBp; GBp divided by 100
  before position accounting.
- Snapshot age at most 15 minutes and quote age at most 5 minutes,
  validated with timezone-aware timestamps; no future timestamps.
- Reject bad/crossed spreads and spreads over 2%, unknown positions, short
  holdings, borrowed GBP or duplicate instrument identifiers.
- Conservative whole-share share quantities, **sales before purchases**,
  maximum 35% per name, maximum 94% gross exposure, configurable turnover
  cap (default 50%), and no negative post-fee cash.
- Simple cost model: minimum £1 commission, 5 basis-point slippage each
  side, flat 50 basis-point hypothetical UK purchase duty. This is
  NOT the precise IBKR fee, venue-tax, liquidity or market-spread model.
- Every safe simulation returns a canonical SHA-256 plan digest, no
  API-compatible order request. A later local instant-full-fill *simulator*
  checks exact remaining GBP cash and each whole-share quantity.
- In-memory audit events form a SHA-256 hash chain. Hashes detect accidental
  edits when their digests are secured separately; this is **not**
  tamper-proof persistence, cryptographic external notarization or a
  user-authenticated order approval.

## Run local tests

    PYTHONPATH=src python -m unittest discover -s tests -v

This suite is also included in normal CI and the isolated IBKR-readiness
workflow. It is a preflight architecture test, **not a certification** of
IBKR order execution.

## Next extensions (remain blocked without user's approval)

1. Independent quote/contract qualification from actual paper TWS,
   permitted subscriptions, historical index constituents and splits.
2. Persistent order-intent registry with crash-resilient idempotency,
   broker-order acknowledgements and partial-fill reconciliation.
3. PAPER account isolation, emergency cancellation and kill-switch
   verification against an approved TWS/Gateway paper session.
4. Explicit signed human approval for any true paper order. No live trading.

The sandbox does **not** provide partial fills or execution at the price
quoted by the exchange; its "reconciled" state means *internal synthetic
arithmetic only*. Use the existing local read-only broker diagnostic before
considering any separately approved broker integration. Never commit
credentials, account IDs or raw broker confirmations.
