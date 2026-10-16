# UK equities cost sensitivity — gate 4 research

\`scripts/cost_sensitivity.py\` simulates illustrative whole-share *immediate*
buy and sell at **bid/ask**, with additional adverse price slippage, a minimum
commission, percentage commission, venue fee, and a separately toggled
buy-side duty. The scenario estimates both **money** and **percentage of
allocated capital** lost to instantaneous trading friction.

Command:

    python scripts/cost_sensitivity.py --output outputs/cost_sensitivity.json

This is a deliberately synthetic experiment using a **£300** order budget
in a hypothetical £1,000 account and a £20.00 bid / £20.04 ask.
It evaluates three *illustrative unverified* cost parameterisations,
each with both duty-applicable and exempt cases. No actual market quotes,
broker API or account-specific pricing is accessed. The default £1 and
illustrative £3 commissions are **assumptions**, not a representation of
a binding IBKR rate.

For an independently verified cost model, obtain the IBKR paper account's
available pricing plan and order previews/statements locally, along with
the instrument-specific UK stamp duty, PTM levy, venue, exchange and FX
terms applicable at execution date. A source comparison should record
screenshots/redacted schedule references, effective date, quote currency,
venue/currency metadata and actual instrument qualification; prices
denominated in GBp must be converted to GBP.

Required promotion test: each hypothetical fee line reproduces one
**externally verified** commission/tax calculation, including the
stamp-exempt path. Verify bid/ask timestamps, partial fills, changing
spreads and integer quantity constraints. The script intentionally
reports \`pricing_verified_against_ibkr_account=false\`.

Do not change research readiness flags from green CI alone.
