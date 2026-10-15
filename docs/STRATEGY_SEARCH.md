# Broad strategy optimisation: research, not deployment

Run: `python scripts/strategy_search.py --output outputs/strategy_optimization.json`

The GitHub Actions **optimisation** job downloads pinned public FTSE datasets,
runs seven strategy families (188 rule-based configurations plus 64 SDE forecasts) and uploads all ranked trials with the dataset hash.

Rule-based strategies: 20/60/120-session momentum, volatility-adjusted momentum,
3/5-session mean reversion after a positive 120-session trend, dual-trend
momentum, and an equal-weight subset control. They vary 3/5/10/20 names,
weekly/monthly/quarterly rebalancing, 65% or 94% invested and an optional
breadth-based cash filter (at least 50% of assets above their price 120 days ago).

**Date discipline:** 2023 development, 2024 validation and 2025 post-selection
diagnostic. The project previously examined 2025, so 2025 is NOT fresh blind
out-of-sample evidence. 2026 cannot be used for equities without obtaining a
suitable independently audited 2026 per-share feed and historical membership.
The score uses 2023/2024 excess returns vs a cost-adjusted price-only FTSE
index tracker proxy, drawdown, excess-return instability, and stop penalties.
The same £1,000 initial capital, £850 stop and approximate £1 minimum fee,
5bp slippage and blanket 50bp buy-side SDRT model apply.

Known blocking limitations: source share universe survives through 2025,
not historical point-in-time constituents; 2067 invalid or missing closes and
420 inconsistent OHLC records in original data; no verified corporate actions,
dividends, broker fills, or whole-share execution; material multiple-testing
risk. Future research must obtain independently corrected source prices,
point-in-time constituents, a truly new post-selection holdout and paper
trading validation before order placement. This branch is **offline only**.

GBM and OU SDE forecasts add 64 variants for 252 total; see [forecast
methodology](PREDICTIVE_SDE.md) and [observed comparisons](PREDICTIVE_RESULTS.md).
