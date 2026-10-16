# Forecast calibration and prospective validation gate

This offline study tests whether the analytical SDE forecasts generate *reliable
probabilities*, not just favourable historical equity curves.

Run locally:

    python -m unittest discover -s tests -v
    python scripts/forecast_calibration.py --output outputs/forecast_calibration.json

## Evaluation protocol

- GBM and OU, historical lookbacks 60/120 sessions, prediction horizons 5/21
  sessions, existing and **fixed** drift shrinkage 0.35.
- Non-overlapping origin-to-maturity windows for each asset and horizon
  separately, with strictly mature labels and no same-day fill leakage.
- 2023H2 is development, 2024 was previously used to select models, and
  **2025 was previously inspected**, making it retrospective and NOT a new
  blind holdout. Model parameters are **not retuned to calibration findings**.
- Output: Brier score and log loss of positive-return event, no-skill
  constant-0.5 Brier reference, five-bin reliability table, expected
  calibration error, central 80% prediction interval coverage,
  lower/upper decile breach fractions and confident-signal hit rates.
- Individual security predictions are correlated cross-sectionally; naive
  observation counts are **not independent effective sample sizes**.
- Path-level extreme-return anomalies are excluded **from diagnostics**
  (>75% daily log-return) and explicit counts are supplied, making the
  evaluation post-outcome filtered. It is **not** an investable trading rule
  or a fair performance comparator. Source data must be corrected.
- The full source universe is hindsight-selected: 88 of nominal 100
  stocks with complete 2023–2025 data. There is no historical FTSE
  membership or corporate-action verification. Historic sample coverage
  alone cannot establish predictive value.

## The fresh holdout gate

No result becomes a scientifically independent forward test merely because
its calendar year is 2026. Strategy research ran during 2026; earlier 2026
market prices could already have been available or seen and must be treated
as **retrospective** unless a verifiable prior freeze exists.

1. **Freeze** selected configurations, data processing, cost models and
   pre-specified primary evaluation metrics under a Git commit and permanent
   experiment ID. Record the cutoff timestamp and input data hashes.
2. Acquire independently verified security-level GBp/GBP-normalised
   split/dividend-adjusted prices, historical membership, delisting,
   suspensions and realistic corporate actions.
3. Collect **future** post-freeze sessions, recording the timestamp and
   immutable SHA of each input. Never change hyperparameters after seeing
   those prices and then call them untouched.
4. Score matured, time-ordered 5/21-session predictions for Brier, log loss,
   calibration, coverage, model-vs-baseline differentials and actual after-cost
   whole-share portfolio outcomes. Report confidence intervals that respect
   serial/cross-asset dependence.
5. Require independent audit of brokerage availability, benchmark total
   returns, commissions, price timestamps and market data licence.

Until those gates are met, **paper orders and live orders remain disabled**.
The code does not interact with IBKR or any broker.
