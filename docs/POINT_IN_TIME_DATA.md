# Independently sourced FTSE market-data intake — blocker #1

\`scripts/pit_data_audit.py\` is a **structural verification pipeline** for
user-provided **licensed** historical data. It does not download FTSE or other
restricted datasets, claim external source licensing, or infer membership
from today's FTSE shares.

Inputs:

- \`--prices\` CSV with exact fields:
  \`date,symbol,isin,close,unit,currency,split_adjusted,dividend_adjusted,source_ref\`.
  Prices can be GBp or GBP but currency must be GBP; adjusted flags are the
  literal strings \`true\` or \`false\`. Source references are required.
- \`--membership\` CSV:
  \`symbol,isin,member_from,member_to,known_at,source_ref\`.
  Inclusive historical membership intervals. \`member_to\` blank means open.
  Announcement or evidence-known date must be no later than effective entry.
  Instrument identity uses **both symbol and ISIN** to avoid ticker reuse.
- \`--manifest\` JSON includes byte-exact
  \`price_sha256,membership_sha256,provider,licence_reference,price_source_reference,
  membership_source_reference,corporate_actions_source_reference,collected_at_utc\`.
  The collected timestamp must be timezone-aware.

Usage:

    python scripts/pit_data_audit.py \
      --prices /private/licensed_daily.csv \
      --membership /private/historical_members.csv \
      --manifest /private/vendor_evidence.json \
      --output outputs/pit_source_audit.json

The audit rejects duplicate quotes, overlapping membership events, future
membership announcements, broken hashes, malformed evidence and disallowed
currency/units. It reports missing prices for members who were active on
each supplied trading date, unknown-membership rows and adjustment flags.

**Critical limitation:** Even \`structural_validation_passed=true\` cannot
confirm licensed-data provenance, correct delisting payouts, actual
adjustment factors or independent contemporaneous membership evidence.
Thus \`candidate_data_fit_for_backtest=false\` and
\`independent_source_evidence_verified=false\` ALWAYS, pending external
provider evidence and a separate independent audit. The code MUST NOT flip
a readiness gate automatically based on provider-supplied strings.

Do not commit raw licensed market data, account information or secrets.
The complete point-in-time historical constituents and corporate-actions
require licensed data and independent provider documentation, still pending.
