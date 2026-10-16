# Independent evidence intake — next milestone (16 October 2026)

**Status: BLOCKED; preparation only.** This checklist does not certify market data, timestamp a forecast, or approve trading.

## Data-provider handoff (Gate 1)

Obtain licensed historical and ongoing FTSE 100 security-level prices and *point-in-time* membership, including removed/delisted constituents. Require provider identifiers (ticker and ISIN), announcement and effective dates, corporate-action histories (splits, special/ordinary dividends, rights, mergers), original unadjusted exchange prices, total-return-adjusted research prices, GBP/GBp conventions, trading calendars, correction/version history, and legal permission for local processing. Keep licensed raw data and identifying account details out of the repository and Actions artifacts.

Preserve original vendor files unchanged in private storage with SHA-256 digests and acquisition timestamps. Reconcile membership events and corporate actions against a separately sourced FTSE Russell/exchange record. Document differences and remediation. The local `scripts/pit_data_audit.py` report is a *screen*, not independent certification. Do not mark Issue #4 Gate 1 complete until a human reviewer signs off on linked non-sensitive evidence.

## Prospective forecast registration (Gate 2)

Frozen model: `266a0b16e6ce6d2047f7a379823bfb84a9f5b584`; GBM/OU L120, H21, shrinkage 0.35. First eligible completed origin must be after 2026-10-15. Before outcomes are observed:

1. Validate the provider snapshot and market session, with independent membership/corporate-action reconciliation.
2. Record `scripts/forward_gate.py record` locally against private source files and manifest, with no interpolation or hindsight correction.
3. Preserve ledger, manifest digest, source digest, model commit and an externally verifiable **pre-outcome** timestamp (for example a trusted timestamp authority or independent immutable archival service). A local clock, Git commit or self-declared JSON timestamp alone is not sufficient independent proof.
4. Keep an append-only origin registry; never overwrite prior forecasts. Any corrected vendor data should be stored as a new version and reconciled, not silently substituted.
5. After **21 subsequent trading sessions**, score using independently verified updated quotes; archive maturity evidence and track missing/delisted issuers explicitly. Do not use a rectangular-survivor-only panel to claim true FTSE-wide outcomes.
6. Aggregate prespecified independent origins for Gate 3 only after maturity, using `scripts/prospective_evaluation.py`; evaluate costs and total-return comparator separately.

## Current engineering limitation

`scripts/forward_gate.py` requires a complete rectangular `date,symbol,adjusted_close_gbp` panel. This cannot faithfully represent index entries/exits, suspensions or delistings without a separate availability-aware reconciliation. **Do not register a production-quality FTSE-wide cohort using survivor-only data.** Any initial ledger is experimental until this limitation is resolved and independently audited.

## Human-supplied evidence needed

- Data vendor, licence and exact historical/current products.
- Independent FTSE membership/corporate-action cross-check source.
- Private immutable source snapshot hashes and trusted timestamp mechanism.
- Human-reviewed discrepancies and documented approvals.

## Release guardrail

Keep PR #3 draft, research branch isolated, and all external gates blocked. Do not merge, authenticate to a broker, or submit paper/live orders. Passing CI cannot clear these gates. Separate explicit approvals are required for merge and later paper-order activation.
