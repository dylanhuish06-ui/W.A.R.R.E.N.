# W.A.R.R.E.N. — Trading AI

W.A.R.R.E.N. is a research-first trading system being developed for FTSE 100 equities and an Interactive Brokers (IBKR) account.

> **PHASE 0 — OFFLINE RESEARCH ONLY. No broker connection, no order placement, and no live trading.** The initial strategy is a transparent momentum baseline, **not** yet a trained AI model.

## Implemented

- Strict daily-close CSV input with explicit validation. Expected columns: date,symbol,close.
- Causal 20-session momentum: day t-1 data determines a simulated day t closing trade.
- Long-only allocation, 20 symbols maximum and maximum 5% per holding.
- £1,000 initial capital with the previously selected halt if equity falls below initial capital.
- Transaction-cost accounting, turnover, drawdown and same-universe equal-weight passive comparison.
- Nine local unit tests and automated GitHub Actions checks.
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
