# Gates 1–3 — completed software, observed statistical diagnostics

**Date:** 2026-10-16.
**Software revision:** \`23e47490aec5b6e17ea3a49440e956f7f9670325\`.
**CI evidence:** [research run 38908930927](https://github.com/dylanhuish06-ui/W.A.R.R.E.N./actions/runs/38908930927)
and [readiness run 38908930896](https://github.com/dylanhuish06-ui/W.A.R.R.E.N./actions/runs/38908930896).

Both jobs completed successfully; **81 offline unit tests** passed.
These are software tests, not approvals of independent market data or IBKR.

## Historical 2025 retrospective diagnostic (already inspected; NOT blind)

Each model forecasts whether an equity's H-session simple return is
positive. Brier score is lower-is-better. \`causal_brier\` is the score of
an illustrative issuer-specific *past-matured* hit-rate baseline with a
smoothing prior; unlike a post-hoc base-rate, it contains no future
outcomes at the evaluated forecast origin.

| Model | Historical lookback | Horizon | Brier | Causal baseline Brier | Relative skill | Fixed-50% Brier |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| GBM | 120 | 21 | 0.248646 | 0.256371 | +3.0132% | 0.250000 |
| OU | 120 | 21 | 0.248497 | 0.256371 | +3.0712% | 0.250000 |
| GBM | 120 | 5 | 0.250112 | 0.255020 | +1.9245% | 0.250000 |
| OU | 120 | 5 | 0.250038 | 0.255020 | +1.9536% | 0.250000 |

**Interpretation:** The proposed causal hit-rate comparator is relatively
weak on these historical events (Brier >0.25), so the percentage skill vs
that comparator **overstates apparent value** compared with a fixed 50%
probability forecast. The best 21-session SDEs improved only **0.54% and
0.60% relative to fixed-50% Brier** in the previously inspected 2025
period. None is a genuine independent alpha validation. No pre-specified
cluster bootstrap inference was claimed for these contaminated events.

All source equity histories are hindsight-survivor-selected. The vendor
raw data include thousands of bad/missing closes, unverified historical
constituent membership and unverified corporate actions. The existence
of output metrics does not mean these estimates are investable.

## Gate-by-gate acceptance

- **Gate 1: BLOCKED** pending privately sourced, independently validated
  licensed FTSE 100 constituent/ISIN/corporate-action/price and calendar
  evidence. Code can audit the schema but has no certified source.
- **Gate 2: BLOCKED** pending genuinely forecast-before-outcome records
  with independent timestamps and actual market prices **after**
  the October 15 model freeze, followed by 21 completed trading sessions
  per prediction. The current date is October 16; none of these new
  predictions can have matured.
- **Gate 3: BLOCKED** pending a sufficiently broad prospective dataset,
  frozen proper-score improvement with dependence-aware uncertainty, plus
  independently audited risk-adjusted **after-cost** equity returns vs
  an investable total-return FTSE benchmark. Stronger synthetic tests
  cannot deliver this evidence.

The isolated branch **does not** merge into main, submit paper/live
orders, or use IBKR trading credentials. The user will separately
prepare IBKR's local API; broker-specific step 7 is deferred.

To reproduce the audit: \`python scripts/forecast_calibration.py
--output outputs/forecast_calibration.json\` and download the same
GitHub Actions artifact from the linked run.
