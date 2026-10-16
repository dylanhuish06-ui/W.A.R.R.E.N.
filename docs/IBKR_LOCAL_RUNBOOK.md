# Local IBKR PAPER API preflight — NO order placement

This runbook is a future manual test. The cloud branch cannot reach
local TWS/Gateway. Do not put broker credentials or the full account ID
in GitHub, issue comments, summary spreadsheets or workflow logs.

1. Open Interactive Brokers **paper** Trader Workstation (TWS) locally
   on your computer; verify the account environment visibly says *Paper*.
2. TWS settings: Global Configuration -> API -> Settings, turn on
   socket API, **Read-Only API**, and restrict access to localhost.
   Confirm the configured socket port; expected defaults are
   **7497 (TWS paper)** or **4002 (IB Gateway paper)**. Other ports
   are rejected by the research-only probe.
3. Install the official IBKR TWS Python API **locally**, using
   Interactive Brokers' currently supported instructions. Do NOT install
   GitHub Actions broker secrets or expose a remote TWS API port.
4. In a local terminal (do not share the terminal transcript with the
   full account number):

       export WARREN_IBKR_PAPER_ACCOUNT='DU...your-paper-account...'
       python scripts/ibkr_readonly_probe.py --host 127.0.0.1 --port 7497

5. The diagnostic requests **managed account identifiers and current
   server time only**; it submits no orders and prints no account IDs.
   Seeing a socket handshake and DU-prefixed account matching is
   **not independently sufficient** to establish paper vs live mode.
   Confirm TWS paper banner and read-only permission manually.
6. Record only a yes/no attestation and signed/redacted evidence privately.
   No account IDs, passwords, tokens or investor sensitive information
   should be committed in the repository.

## Risk and tradeability controls before any paper-order design

- Validate qualified IBKR contracts and the exchange-specific quote
  currency. LSE prices often use **GBp** while portfolio equity is
  in **GBP**; do not trade until the conversion is verified.
- Verify realistic commissions, stamp duty applicability, spreads,
  minimum order sizes, open session hours and account margin restrictions.
- Build paper-only order submission as a separate reviewed branch with
  account ID allowlist, zero live permissions, independent order-level
  approval, duplicate-order idempotency, kill switch, reconciliation and
  audit logging; **none of these order APIs exist in this readiness
  branch**.
- The £850 study floor is NOT an approved account loss limit; a
  threshold does not guarantee maximum loss when prices gap.

IBKR official resources:
https://www.interactivebrokers.com/campus/trading-lessons/installing-configuring-tws-for-the-api/
https://www.interactivebrokers.com/docs/tws-api/doc/introduction
