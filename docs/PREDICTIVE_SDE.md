# Predictive layer: GBM and OU stochastic models (research only)

## Architecture

The existing W.A.R.R.E.N. optimiser searches momentum, relative-risk
momentum, trend filters, short-horizon mean reversion and equal-weight controls.
This addition introduces **two parameterised predictive families**, not a
profit-guaranteeing "AI":

1. **SDE-GBM**: estimate the mean and variance of daily log returns over the
   previous 60 or 120 sessions. Shrink estimated drift toward zero to avoid
   unrealistically confident trend extrapolation. Solve geometric Brownian
   motion analytically: cumulative log return over H sessions is Gaussian
   with mean H * drift and variance H * sigma².
2. **SDE-OU**: model *daily log returns* as a stationary Ornstein–Uhlenbeck
   process, implemented using its AR(1) exact sample-time analogue.
   Estimate positive mean-reversion coefficient from historical lagged returns;
   derive conditional H-step integrated Gaussian mean and variance analytically.

The output is a predictive **distribution** for the next 5 or 21 sessions:
expected simple return, probability of a positive return, and 10th/90th
percentile return. Predictions are made using **at most yesterday's close**
when placing a hypothetical trade at today's close. There is no ML
training process or future data in signal construction.

## Trading rule

Choose highest predictive risk-adjusted expected returns if BOTH:

- Predicted probability of positive holding-period return exceeds the chosen
  threshold (52% or 60%).
- Predicted expected return exceeds estimated two-sided dealing friction:
  £1 minimum per buy and sale, slippage and UK stamp duty approximation,
  using expected target notional.
- Filter out implausible raw-price jumps, reject missing data and require
  the model 10th-percentile holding-period loss better than -20%.

Strategy sweep:
- Distribution models: GBM, OU.
- Lookbacks 60/120, 3/5 portfolio names, rebalance 5/21 sessions,
  exposure 65%/94%, probability gate 52%/60%.
- Conventional strategies remain explicit controls.
- No short positions, leverage or broker connection.

## Validation and interpretation

Optimisation uses shortened 2023H2 development followed by 2024 validation.
2025 had already been viewed in earlier W.A.R.R.E.N. work and is only a
**contaminated retrospective diagnostic**, NOT out-of-sample proof.
Public share data ends in 2025 and contains material errors; no accurate
fresh 2026 equity test is available in this research workflow.

The 2023–25 fixed symbol list is hindsight-selected, and corporate actions,
historical index membership, broker tradability and currency conventions are
not verified. The FTSE 100 price-only tracker proxy excludes dividends.
Forecast probability accuracy must be evaluated using time-ordered Brier
scores and reliability plots on **new data** before any paper trading.

## Why not CNNs/Transformers yet?

Training deep neural architectures on ~88 historically selected shares and
a few years of daily bars would introduce serious overfitting risk.
SDE models provide cheap, interpretable, reproducible probabilistic baselines;
future CNN / transformer candidates can be added behind the same Forecast
interface and compared with walk-forward retraining, proper calibration and
a freshly acquired untouched forward holdout.

## Run

    python -m unittest discover -s tests -v
    python scripts/strategy_search.py --output outputs/strategy_optimization.json

CI uploads the optimiser's output as an artifact. These outputs are NOT live
trading signals. Investment outcomes are uncertain and stochastic forecasts
do not guarantee correct direction.
