# W.A.R.R.E.N. roadmap

## P0. Offline research (current implementation)
- Price validation, no silent gap filling, synthetic reproducible demo.
- Causal momentum baseline, long-only caps, friction assumptions and capital floor.
- Unit tests and GitHub CI. No brokerage capability, live trading or implied profitability.

## P1. Point-in-time market data
- Appropriately licensed UK/IBKR market data with stable dataset and timestamp hashes.
- Historical FTSE 100 membership by date; splits, dividends, delistings and corporate actions.
- Exchange calendars, currencies, missing series, stale prices and trading halts.
- Historical raw/adjusted prices handled separately; private local data storage.

## P2. Advanced research and ML
- Walk-forward chronological train/validation/test with no future leakage.
- Reproducible feature pipelines, tuning hygiene, model versioning and ablation studies.
- Compare momentum, cash and buy-and-hold benchmarks to statistical/ML approaches.
- Slippage, spreads, transaction costs, stress scenarios, turnover, stability.
- Annual / monthly / weekly returns and growth of £1,000 relative to passive.

## P3. IBKR PAPER only
- Local TWS or IB Gateway, paper session and account whitelist, start read-only.
- Contract qualification, trade previews, risk constraints, double-check execution mode.
- Manual arming, finite order caps, reconciliation, audit logs and idempotency.
- Kill switch to block new orders; separately authorised emergency liquidation with confirmation.
- Network loss, stale quotes, partial fills, disconnected order management tests.

## P4. Dashboard and operations
- Equity, positions, orders, broker reconciliation, exception queue, alerts and reports.
- Email notifications without embedding credentials in code or CI.
- Recovery drills, day changes, duplicate execution prevention, trading-calendar tests.

## P5. Live readiness (separate explicit authorisation)
- Independent paper performance and safety acceptance tests.
- Human approval for first live activation, no automation to bypass gates.
- Remain unarmed by default after each restart.
- Financial, execution, compliance and data-permissions review.

## Non-negotiables
- Research and CI must NEVER send orders.
- TRADING_ARMED=false. LIVE_TRADING_ALLOWED=false.
- Preserve confidentiality of brokerage accounts and datasets.
- The research baseline is not claimed to be an AI or profit-making system.
