# Prospective prediction ledger: how to record and score new data

This gate is **implemented, but no real new equity feed or timestamped ledger
has been submitted**. It cannot establish predictive skill from the existing
2020–2025 source; 2025 has already been inspected and cannot be relabelled
as prospective.

Frozen configurations: GBM and OU analytical 120-session estimation,
21-session horizon, drift-shrinkage 0.35, based on model commit
\`266a0b16e6ce6d2047f7a379823bfb84a9f5b584\`, October 15, 2026.
The first valid forecast origin is strictly **after 2026-10-15**.

## Input requirements

- UTF-8, rectangular *point-in-time constituent* quote CSV with exactly
  \`date,symbol,adjusted_close_gbp\`; one adjusted GBP close per stock/date,
  sorted as ISO dates. At least 122 complete market dates. No interpolation.
- Manifest JSON with provider, source_reference, the exact SHA-256 of the
  bytes of the CSV in \`price_sha256\`, currency="GBP",
  split_adjusted=true, dividend_adjusted=true,
  corporate_actions_verified=true, historical_membership_verified=true,
  membership_source_reference, membership_asof equal to the most recent quote
  date, and collected_at_utc with timezone. **Metadata is attestation, not
  external independent verification.** A single historical snapshot of
  constituents is not a guarantee of point-in-time correctness.
- Do not claim the system supports true total-return-adjusted UK equity
  execution without a third-party audit of correct dividend adjustments.
- Do not overwrite the ledger. Ideally store each prediction record using
  protected git commits or an independently timestamped append-only source,
  because hashes by themselves cannot prove a record predates outcomes.

## Generate predictions before outcomes are observable

    python scripts/forward_gate.py record \
      --prices path/to/verified_equities.csv \
      --manifest path/to/verified_manifest.json \
      --output outputs/frozen_2026_forecasts.json

The newest quote date must be after research cutoff and *before* the current
UTC calendar date. Source and time evidence must be preserved.

## Score only after 21 additional trading sessions

    python scripts/forward_gate.py score \
      --prices path/to/updated_verified_equities.csv \
      --manifest path/to/updated_manifest.json \
      --ledger outputs/frozen_2026_forecasts.json \
      --output outputs/matured_2026_calibration.json

Fails closed on missing manifest fields, mismatched hashes, unrealised
21-session outcomes, changed signal origin prices, duplicate/missing quotes,
tampered ledger contents and pre-cutoff predictions. The scored report compares
frozen GBM and OU on matched assets/outcomes.

**Important:** this is an offline research assistant, not a trusted timestamp
authority. Data attestation and ledger integrity checks do **not** prove
independent data quality or guarantee no lookahead. \`audit_approved=false\`
is permanent until independent review outside this program.

## Evaluation extension required

Record multiple future origin dates, then aggregate pre-specified matured
predictions and report Brier skill, log loss, reliability, interval coverage,
uncertainty intervals clustered by trading date and issuer, and separate
after-cost whole-share strategy returns vs an actual investable total-return
FTSE tracker. No IBKR orders are triggered by these scripts.
