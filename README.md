# W.A.R.R.E.N. — Trading AI

W.A.R.R.E.N. is a research-first trading system being developed for FTSE 100 equities and an Interactive Brokers (IBKR) account.

> **PHASE 0 — OFFLINE RESEARCH ONLY. No broker connection, no order placement, and no live trading.** The initial strategy is a transparent momentum baseline, **not** yet a trained AI model.

## Implemented

- Strict daily-close CSV input with explicit validation. Expected columns: date,symbol,close.
- Causal 20-session momentum: day t-1 data determines a simulated day t closing trade.
- Long-only allocation, 20 symbols maximum and maximum 5% per holding.
- £1,000 initial capital with the previously selected halt if equity falls below initial capital.
- Transaction-cost accounting, turnover, drawdown and same-universe equal-weight passive comparison.
- Automated GitHub Actions checks (23 unit tests at the predictive revision).
- Deliberately no IBKR account access or live-trading code.

## Quick start (Python 3.11+)

    python -m venv .venv
    source .venv/bin/activate
    python -m pip install -e .
    python -m unittest discover -s tests -v
    python scripts/generate_demo_data.py --output data/demo_prices.csv
    warren backtest --prices data/demo_prices.csv --output outputs/demo_report.json

On Windows PowerShell, activate the virtual environment using .venv\Scripts\Activate.ps1.

The demo symbols and prices are synthetic, **not market performance**. Use a daily close CSV for offline research; data ingestion will be added in a separate phase. Price files must have complete daily coverage for the same symbols. The eventual universe must reflect historical index membership to avoid survivorship bias.


## Broad market strategy study (October 2026)

The [strategy search](scripts/strategy_search.py) initially evaluated **188** rule-based combinations
across five strategy families; the predictive extension expands this to **252**
configurations across seven families using pinned public market data, with an automated
GitHub Actions job and machine-readable artifact. Strategies are scored on
**2023-07-04 to 2023-12-29** (development) plus **2024** (validation). The
2025 interval has already been viewed in earlier work and is **not blind**.

The selected 120-session / 3-name / ~monthly / 94%-invested momentum baseline
produced +11.156% (2023 H2), +8.017% (2024) and -19.098% (2025 retrospective).
The illustrative cost-adjusted FTSE 100 price-index tracker proxy returned
+2.69%, +5.69%, and +20.05% respectively. This does **not** show reliable
outperformance. The 2025 strategy drawdown reached 27.749% despite the
nominal £850 stop; losses can exceed the stop threshold before liquidation.

The fixed share universe was selected with future knowledge and lacks
historical constituent membership and corporate-action verification. The
source audit found 2,067 invalid/missing share closes and 420 inconsistent
OHLC readings in the underlying full source. **These returns are research
simulations, not investment advice or executable trading results.**
For exact methodology and limits, see
[the study](docs/STRATEGY_SEARCH.md) and
[the predictive comparison](docs/PREDICTIVE_RESULTS.md).

Run locally:

    python scripts/strategy_search.py --output outputs/strategy_optimization.json

This requires permitted outbound access to the pinned public data. It does
not connect to IBKR. Output files remain untracked.

## Predictive stochastic models (experimental)

The [SDE predictive research layer](docs/PREDICTIVE_SDE.md) adds analytical
*distributional forecasts (not empirically calibrated probabilities)* from geometric Brownian motion (GBM) and mean-reverting
Ornstein–Uhlenbeck (OU) daily log-return dynamics. These are analytical
baseline models, **not trained CNNs or transformers**. Probability thresholds,
forecast windows, portfolio concentration and exposure are configurable.
The expanded strategy search has **252 candidate configurations** (188 prior
rules + 64 SDE variants). All evaluations remain offline and exploratory.
No new independent 2026 stock holdout or reliable forecast accuracy is verified;
2025 was already examined and is **not blind out-of-sample**.


## Probability calibration and forward gate

The [retrospective 2025 forecast audit](docs/FORECAST_CALIBRATION_RESULTS.md)
shows only marginal 21-session Brier improvement over a constant 50% forecast;
shorter-horizon results generally show no skill. This is not proof of alpha.
The [forward test ledger](docs/FORWARD_GATE.md) requires future post-freeze
prediction records and separately matured observations; it has not yet
received any independently verified live-market input. Broker actions remain
disabled.

## Architecture

| Component | Location | Permission |
| --- | --- | --- |
| Code and unit tests | GitHub | Research CI only |
| Historical data, models and generated reports | Local computer/server | Local only |
| IBKR TWS / IB Gateway | Future local integration | Paper, read-only first |
| Live execution | Not implemented | DISABLED |

For IBKR, the documented usual local paper ports are 7497 (TWS) and 4002 (Gateway), but these can be changed in the TWS application. No broker connectivity code is present.

## Important limitations

The cost model is simplified; it does not represent order-book spreads, partial fills, impact, taxes, realistic slippage, dividends or corporate actions. The benchmark is an equal-weight buy-and-hold portfolio of the dataset's symbols, not the FTSE 100 index. Performance does not demonstrate future profitability.

An initial-capital floor of exactly £1,000 may halt trading almost immediately after paying entry fees. This deliberately preserves the earlier strict stop instruction; evaluate it before any paper/live execution.

This repository is currently public. **Never commit account credentials, IBKR IDs, API secrets, portfolio statements, proprietary strategy inputs or actual brokerage data.** Consider switching to private repository visibility for later phases.

See docs/ROADMAP.md for the next research, ML, paper-trading and live-readiness milestones.
