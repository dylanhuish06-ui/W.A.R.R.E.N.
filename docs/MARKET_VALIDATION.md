# Phase 2: market study, benchmark comparison and validation audit

The executable entry point is:

    python scripts/market_validation.py --output outputs/market_validation.json

It downloads two **pinned GitHub datasets**, records SHA-256s, runs 11
historical 2024/2025 strategy simulations and generates a full JSON report.

- Equity data: [arjundangwaluk/Ftse100database](https://github.com/arjundangwaluk/Ftse100database)
  at commit 06850a4578dde1f07134fd4923fae7db3c0c6117 (100 nominal symbols,
  daily 2020-01-02 to 2025-12-31, downloaded from Yahoo Finance by dataset author).
- Index price data: [Hareeshkesavan/Stock-Market-Dataset](https://github.com/Hareeshkesavan/Stock-Market-Dataset)
  at commit aa60b746f089c3f54df6760bf021708c2d3ce1e8
  (FTSE 100 **price** index 2015-01-02 to 2026-03-31).

## How to interpret the report

- **Model-selection validation:** calendar 2024; 11 candidate strategies ranked by 2024
  realised return (net of stated simulated trading costs).
- **Already-viewed secondary assessment:** calendar 2025. Because the 2025
  data was viewed during development, this is NOT fresh blind holdout.
- **Older-regime stress:** 2021 and 2022 using full-history survivor set.
  They predate 2024 model selection and are NOT chronological forward tests.
- **2026:** price-index benchmark only, January–March. This is NOT an
  equity-algorithm holdout. Do not compare a 2026 index return with a 2025
  stock strategy return or present it as evidence of strategy efficacy.
- **Passive comparison:** model a £1,000 single-ticket passive tracker
  indexed to FTSE 100 price-only close. £1 buy commission and 5bps entry
  slippage, no dividends, ongoing charges, exit fee or tracking differences.
  It is an illustrative proxy, not a directly observed ETF return.
- 2024/2025 strategy portfolio: £1,000, 94% invested, £850 stop, no leverage,
  fractional amounts, minimum £1 commission/order, 5bps slippage and a
  blanket 50bps buy-side stamp-duty assumption.
- Only 88 of 100 symbols have all daily closes over 2023–2025;
  survivorship and historical index membership are **not** solved.
- The dataset has internally inconsistent OHLC readings and unverified
  corporate actions. The reported returns are exploratory, not deployable.

**No claims of real-world outperformance or proven generalisation.**

## Step 3 gate (not passed)

To run a credible *new* forward equity holdout, freeze strategy and universe
from 2024/2025, obtain 2026 individually adjusted UK equity data and 2026
historical FTSE membership, reconcile splits/dividends/suspensions and broker
access, and re-run costs with whole shares. **No live trading permitted.**
