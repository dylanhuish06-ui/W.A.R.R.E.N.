# Frozen model prospective-evidence acceptance — Gates 2 and 3

\`scripts/prospective_evaluation.py\` consumes **multiple** matured files from
\`scripts/forward_gate.py score\`. It never accesses a broker and does not
turn a model into a trading signal. It will reject an empty list, duplicate
origin ledgers, inconsistent model-vs-baseline comparison cohorts, reused
forecasts, missing prediction-era baseline or unverifiable event labels.

Use:

    python scripts/prospective_evaluation.py \
      --matured /private/evidence/matured_*.json \
      --output outputs/frozen_forward_evaluation.json

The forecast must have been *recorded* after its completed market-session
origin and before its outcome maturity. A self-reported timestamp and hash
cannot establish independent provenance: a trusted externally time-stamped
store with provider evidence is still mandatory. Recorded forecast files
should be immutable; **never** derive the historical base rate from the
subsequently-observed outcomes.

## Prespecified statistical screen for H=21 only

- At least **12 nonoverlapping mature origin cohorts**, spanning **300
  calendar days**, and at least **25 separate stock identifiers**.
- Compare on identical \`(origin, issuer, outcome)\` pairs for GBM/OU:
  **Brier score** and **log loss** must both outperform the causally
  estimated hit-rate comparator.
- The lower 5% percentile of a 2,000-replicate origin-cluster bootstrap
  distribution of **baseline Brier minus model Brier** must be positive.
- 10-bin ECE must be <=0.05; the nominal central 80% return prediction
  interval must cover 72–88% of realised future returns.
- Use fixed model parameters frozen at \`266a0b16...\`, not revised
  variants tuned on prior prospective scores.

This is a **research diagnostic**, not a verified p-value or a regulatory
investment suitability test. Cross-sectional shared factors and serial
regime dependence are difficult to remove. A single point estimate from
12 monthly origins is not strong evidence of tradeable alpha; replicated
macro regimes, market impact and consistent risk-adjusted profitability
are additional requirements.

\`sample_thresholds_passed\` and \`statistical_screen_passed\` are only
software-calculated outputs. Even a perfect synthetic data fixture reports:

- \`independent_data_provenance_approved=false\`
- \`externally_trusted_timestamp_evidence_approved=false\`
- \`after_cost_portfolio_alpha_demonstrated=false\`
- \`paper_order_execution_approved=false\`

No actual prospective market sample currently meets these gates, and
the original 2025 dataset was seen during strategy selection. Never
relabel it as forward validation. Every data refresh and re-parameterized
model requires a separately frozen experiment identifier.

**Important engineering limitation:** The present \`forward_gate.py\`
accepts a complete rectangular security price panel. This is intentionally
restrictive and not yet appropriate for a real 100-issuer FTSE universe with
IPOs, suspensions, constituent churn and delistings. Before deploying its
real-data use, add explicit as-of identity/eligibility per stock and
permit availability-aware panels. A future change to the data schema
must not silently change the frozen predictive configuration. This
requirement is tracked as part of Gate 1.
