# October 2026 SDE forecast calibration: measured results

GitHub Actions run (pinned third-party historical equity data, no broker):
https://github.com/dylanhuish06-ui/W.A.R.R.E.N./actions/runs/38818045181

Download the `historical-forecast-calibration` workflow artifact for all
lookback/horizon combinations, annual metrics, five-bin reliability
tables, counts, data hashes and exclusions.

## Previously inspected 2025 period — not blind / not independently verified

Brier score evaluates predicted probability of a **positive** return.
Lower is better; a constant 0.5 forecast scores 0.25. The stated skill is
`1 - Brier/0.25`; near-zero values imply little or no advantage over this
uninformed reference. All forecasts are scored after completing their
maturity, and origin/maturity intervals are non-overlapping for each
horizon and issuer.

| Analytic model | Sessions estimated | Sessions ahead | Events | Brier | Skill vs 0.5 | 80% interval coverage |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GBM | 60 | 5 | 4,400 | 0.251498 | -0.5994% | 80.59% |
| GBM | 120 | 5 | 4,400 | 0.250112 | -0.0448% | 81.86% |
| OU | 60 | 5 | 4,400 | 0.251500 | -0.6001% | 81.66% |
| OU | 120 | 5 | 4,400 | 0.250038 | -0.0151% | 82.80% |
| GBM | 60 | 21 | 1,056 | 0.251103 | -0.4412% | 81.82% |
| GBM | 120 | 21 | 1,056 | 0.248646 | +0.5417% | 83.81% |
| OU | 60 | 21 | 1,056 | 0.250546 | -0.2184% | 83.05% |
| OU | 120 | 21 | 1,056 | 0.248497 | +0.6012% | 84.66% |

These are *observations* from the historical audit, not evidence of a
profitable predictive model. The apparent best 21-day scores barely
outperform an always-50%-positive forecast. The positive/negative event
frequencies are not necessarily 50%, so a fairer **historically available**
time-varying base-rate comparator should be added before any scientific
claims. Issuers share common market risk; 1,056 observations are not
1,056 independent events.

Central prediction interval coverage near 80% is a diagnostic, not
evidence of reliable tails, especially with estimated volatilities and
possible uncorrected split/dividend effects. The audit excludes
greater-than-75% daily log-return paths *after seeing outcomes*, records
exclusion counts, and thus cannot be treated as an investable forecast or
completely unselected performance estimate.

## Gate status

- Historical date window ends 2025-12-31.
- The SDE models were evaluated during development on this date range.
- Data universe has forward-survivor selection; corporate actions and
  point-in-time FTSE membership have not been independently confirmed.
- 2026 index-only data is **not** a security-level strategy holdout.
- Prospective recording and scored-maturity checking is available via
  [the forward ledger](FORWARD_GATE.md), but **no real prospective
  security-level dataset, future prediction ledger or independent audit
  has been provided yet**.
- W.A.R.R.E.N. remains **research-only**, with broker and order placement
  entirely disconnected.

## Next pass criteria

1. Independently verified split/dividend-adjusted prices, point-in-time
   security coverage and bid/ask/broker fee assumptions.
2. Predictions recorded and externally timestamped *before* outcomes.
3. All 5/21-session outcomes matured; score on matched issuer/date events
   against 0.5, time-causal prevalence and simple momentum baselines.
4. Report clustering-aware uncertainty, proper scoring rules, severe
   tail coverage and actual after-cost whole-share portfolio comparisons.
5. Independent review and explicit user approval before paper or live
   order-execution design.
