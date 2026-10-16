# IBKR paper-trading readiness — approval summary (2026-10-15)

**Scope:** isolated pre-merge readiness branch
\`feature/ibkr-paper-readiness-autovalidation\` based on the approved-by-tests
research/calibration branch. **No merge to main, orders or broker logins.**

## Already implemented

- FTSE research core, 252 historical strategy parameterizations across 7
  families, cost-adjusted FTSE 100 *price-only* tracker proxy.
- Probabilistic analytic GBM/OU SDE strategies; calendar 2023H2 development,
  2024 optimisation, previously viewed 2025 diagnostic.
- Forecast-scoring audit (Brier, log loss, coverage, bin reliability),
  fail-closed future signal ledger requiring completed post-freeze sessions.
- Isolated deterministic GBP *whole-share order-intent preview only* with
  cash/position caps and no broker order APIs.
- Optional local **read-only** TWS/IB Gateway handshake that only allows
  localhost paper ports 7497/4002, checks for expected paper account
  without printing IDs, never transmits an order.
- GitHub CI and recurring default-branch dispatcher executing *research-only*
  validations; automated JSON reports and summaries. Cloud CI is not the
  same as actual TWS connectivity.

## Key numerical findings (not validated investable returns)

Best-selected GBM L120/N3/21-session rebalance/94% exposure:
2023H2 +11.928%, 2024 +12.842%, **2025 -16.662%** (already inspected;
NOT blind). Illustrative FTSE price-only tracker proxy: 2.69%, 5.69%,
20.05%. In 2025 GBM L120/H21 Brier 0.248646 (+0.54% vs fixed p=0.5),
OU L120/H21 0.248497 (+0.60%). Differences are marginal and cannot
establish statistically significant predictive skill.

## Fail-closed blockers — not IBKR paper ready

1. Source data has 2,067 missing/invalid historical closes and 420
   inconsistent OHLC records; 88/100 complete survivor stocks.
2. Need licensed, independently adjusted historic/prospective
   security prices (GBP/GBp handled), point-in-time FTSE constituents
   and independently verified corporate actions/dividends.
3. Need genuinely prospective, externally timestamped forecast records
   and **matured** post-freeze labels and after-cost whole-share outcomes;
   verify calibrated skill and drawdown vs investable total-return comparator.
4. Need local user-side TWS/Gateway *PAPER* login/API read-only handshake,
   account/currency/market subscriptions, contract resolution and fee checks.
5. Need more granular emergency cancellation, logging, reconciliation and
   paper-only canary tests before order enablement. These are NOT enabled.
6. An explicit **user approval** is required before merging the research
   branch into W.A.R.R.E.N. main; a separate subsequent approval is
   required to activate any paper-order submission. Live orders are forbidden.

## Operational limits

IBKR documents normal local TWS paper socket port **7497**, Gateway
paper port **4002**. These are defaults, **not a guarantee** of paper
account identity. Confirm the actual TWS paper-mode banner and read-only
API setting. GitHub cloud runners **cannot** access the Mac's localhost
TWS socket and should never receive API passwords or real account IDs.

The isolated GitHub workflow runs automatically on **pushes and pull requests**
and supports manual `workflow_dispatch`. GitHub-native `schedule` events
run only from the repository's default branch, so a recurring GitHub
dispatcher **has NOT been installed on main**: main remains untouched pending
approval. A separate ChatGPT readiness watch checks the branch, CI and
evidence every **four hours**, notifying on meaningful status changes;
it does not promise autonomous code changes or magically clear external gates.
New commits trigger another full GitHub offline check. These checks
CANNOT access the user's localhost IBKR socket or validate subscriptions.

## Decision requested

**Hold merge** until the independent evidence and local paper preparation
gates are met. The user will review the summary and authorize a merge
separately. No trading account or funds have been touched.

Further details: \`docs/FORECAST_VALIDATION.md\`,
\`docs/FORECAST_CALIBRATION_RESULTS.md\`,
\`docs/FORWARD_GATE.md\`, \`docs/PREDICTIVE_RESULTS.md\`.

IBKR official docs:
- https://www.interactivebrokers.com/campus/trading-lessons/installing-configuring-tws-for-the-api/
- https://www.interactivebrokers.com/docs/tws-api/doc/introduction
- https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows


## New October 16: operational safety simulation

- Deterministic **whole-share** synthetic rebalancing with stale quote
  checks, explicit GBp -> GBP conversion, specified LSE contract identity,
  conservative two-sided bid/ask and dealing-cost estimates, long-only
  cash constraints, gross/name concentration and turnover limits.
- Offline **simulation-only** position/cash reconciliation and plans signed
  with reproducible input SHA-256 hashes, plus hash-chained audit events.
- SQLite local replay registry with default persistent HALT, explicit
  simulation-only acknowledgement, duplicate-plan suppression after
  restart, transaction rollback on failure and audit continuity checks.
- Synthetic end-to-end rehearsal on every isolated readiness CI run;
  upload machine-readable \`outputs/offline_rehearsal.json\`, with
  zero broker connections and zero submitted orders.
- These are **simulation controls**, not actual IBKR paper-session
  validation; external data/forward skill/account/runbook gates stay
  blocked and merge approval is unchanged.

See \`docs/PAPER_SANDBOX.md\` and \`docs/OFFLINE_REPLAY_LEDGER.md\`.

## October 16 research/data and cost preparation (no IBKR required)

- Added `scripts/pit_data_audit.py` for licensed, user-supplied historical
  prices and point-in-time FTSE membership, joined on both ticker and ISIN.
  Reports source hashes, membership-known dates, missing member prices,
  adjustment flags and GBP/GBp conventions. **Cannot independently certify**
  source correctness or licensed use and does not clear the data gate.
- Added per-security causal historical-hit-rate comparator to the GBM/OU
  prequential validation, using *only matured past outcomes* at each origin.
  The original constant-50% benchmark is retained; the time-causal
  comparator is matched on the identical scored events. Results from
  2025 remain retrospective and NOT blind out-of-sample.
- Added `scripts/cost_sensitivity.py` with three illustrative cash-only
  whole-share fee scenarios including bid/ask, explicit duty applicability,
  minimum commission and slippage. Scenarios are unverified, not IBKR prices.
- CI runs reproducible offline fee scenarios. The licensed data intake audit
  is test-covered with synthetic fixtures; CI deliberately does not download
  or publish restricted provider material.

User is preparing local paper API separately. **IBKR broker-specific gate 7
remains deferred**, with no order-capable integration or paper/live trades.
Approval to merge remains ungranted.


## Gates 1–3 software acceptance hardening (October 16)

- Gate 1: enhanced point-in-time membership/ISIN/GBP-unit data intake now
  optionally checks against a separately sourced licensed trading calendar.
  **No point-in-time FTSE stock-level licensed data has been procured or
  externally certified. Gate 1 remains BLOCKED.**
- Gate 2: frozen forecasts include a *pre-recorded causal baseline*, evidence
  digest, observation output and strict 21-session maturity. New reporting
  rejects hindsight-reconstructed baselines and duplicate prediction
  dates. **No real post-freeze matured forecasts. Gate 2 remains BLOCKED.**
- Gate 3: matched GBM/OU forward evidence evaluator enforces at least
  12 non-overlapping origin groups spanning 300 calendar days, >=25
  issuers, positive origin-cluster-bootstrap improvement, better
  Brier/log loss than the pre-recorded causal baseline, ECE <=5% and
  central-80% interval coverage 72–88%. Even hypothetical statistical
  pass CANNOT override independent-data or after-cost proof. 2025 is
  retrospectively contaminated. **Gate 3 remains BLOCKED.**
- Scripts: \`scripts/pit_data_audit.py\`, \`scripts/forward_gate.py\`,
  \`scripts/prospective_evaluation.py\`; tests are synthetic only.
- No broker/API connection or paper/live orders; user independently
  preparing IBKR API. Main remains unmerged.

## 16 October — Gates 1–3 outcome report

Independent market-data and forecast-performance gates remain **blocked**.
The software adds calendar-backed point-in-time data intake, frozen
pre-recorded causal benchmark probabilities and prospective H21 multi-origin
acceptance tests. 81 unit tests and all offline CI jobs passed. See
`docs/GATES_1_2_3_RESULTS.md` for measured 2025 retrospective comparisons.
The 2025 GBM/OU models do not yet demonstrate independently verified alpha.
