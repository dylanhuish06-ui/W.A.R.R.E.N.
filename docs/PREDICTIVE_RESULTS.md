# Observed results: probabilistic SDE strategies (15 October 2026)

**Status: exploratory, not deployment-quality; no paper or live broker orders.**

Reproducible GitHub Actions run:
https://github.com/dylanhuish06-ui/W.A.R.R.E.N./actions/runs/38816364233

The run successfully executed **23 tests**, the market-source quality audit,
and the expanded optimiser on **252 combinations across 7 families**. Its
machine-readable full output is an attached `exploratory-strategy-search`
artifact. Historical data is from pinned public third-party sources, with
unverified point-in-time membership, splits, dividends and other adjustments.

## 2023 development / 2024 validation / already-seen 2025 diagnostic

Percent return of a fresh hypothetical £1,000 investment for each **separate**
calendar window (the 2023 window runs July 4–December 29). Portfolio variants
have approximate dealing costs; index proxy assumes one buy and is price-only.
There is no compounding across columns.

| Variant | 2023 H2 | 2024 | 2025 (NOT blind) |
| --- | ---: | ---: | ---: |
| Selected 120-day GBM; 3 names; 21-session rebalance; 94% target invested | +11.928% | +12.842% | -16.662% |
| Previous 120-day momentum; 3 names; monthly; 94% target | +11.156% | +8.017% | -19.098% |
| Illustrative FTSE 100 price-index tracker proxy | +2.69% | +5.69% | +20.05% |

The GBM candidate was **selected from the 2023/2024 scoring function**,
not the 2025 outcome. It gained 4.825 percentage points relative to
the previous 2024 momentum strategy, but **2025 remains a major failure**:
GBP 833.38 ending equity on GBP 1,000, 25.573% maximum peak-to-trough
drawdown and first capital-floor breach on 4 April 2025, compared with
+20.05% for the passive FTSE 100 price-index proxy. A threshold is a
trigger, **not a guarantee of a maximum loss**.

Other candidate diagnostics generated unusually high returns (for example
the OU 120-day / 3-share / monthly / 94%-invested variant recorded
+86.002% in the previously-viewed 2025 period). **Do not treat these as
confirmed performance**: incomplete corporate-action corrections,
survivorship bias, concentrated exposure and idealised order simulation
can cause dramatic distortions. 2025 has been used during research and
cannot be repurposed as an untouched out-of-sample test.

The probabilistic forecast distribution has **not been validated for
calibration**, Brier score, log loss, or risk-conditional coverage on a
fresh sample. An SDE forecast is not proof of genuine predictive power.

## Research gate: blocked

The underlying equities dataset has 2,067 missing/invalid closes and 420
OHLC inconsistencies in the source; 88 of the nominal 100 symbols were
selected for complete 2023–2025 histories. The 2026 input presently
contains a price-index series but no adequately validated, comparable
individual-share prices. No real 2026 share-strategy holdout was executed.
The fixed candidate universe has future-membership knowledge. Transaction
fees, fractional-share accounting, price-only tracker assumptions,
corporate actions, execution timing and dividends require independent audit.

**Next scientific test:** freeze model parameters; acquire externally
verified point-in-time FTSE membership and corporate-action-adjusted
2026 equity data; perform calibration and walk-forward forecasts, plus
realistic whole-share execution against an investable total-return
benchmark. Do not promote the SDE signals to IBKR order execution yet.
