# Gates 1, 2 and 3 — evidence acceptance report

**Status as of 16 October 2026: implementation advanced; empirical
acceptance gates 1, 2 and 3 remain BLOCKED.** No merge or broker integration.

## Gate 1 — independent point-in-time FTSE historical data

Implemented: historical constituent interval validator joined by ticker
AND ISIN; known-at/effective-date chronology; complete-membership prices,
adjusted-data flags, GBP/GBp price unit checks, source-hash verification and
optional licensed stock-market exchange-calendar completeness checking.

Acceptance still needs:
1. Confirmed legal access/licence for daily historical FTSE 100 members,
   including historical deletions/delisted issues, split/dividend factors,
   end-of-life receipts, data correction versions and separately preserved
   unadjusted execution prices.
2. Independent reconciliation against official FTSE Russell constituent
   additions/deletions and corporate-action events. Confirmation cannot
   rely solely on a vendor's self-declared manifest.
3. Private ingested source snapshots with audit and timestamp evidence.
   Do not upload raw licensed data to this public repository.

Independent provider access/approval is **not established**.

## Gate 2 — prospective timestamped prediction and mature outcomes

Implemented: frozen-model (research commit \`266a0b16...\`) GBM and OU
21-session predictions, immutable record hashes, source snapshot manifests,
record-time causal baseline probabilities, strict maturation and final
matched-event outputs. Simulated tests exercise rejection of hindsight,
missing baselines, duplicate entries and date/time errors.

Acceptance still needs: externally trusted predictions recorded with
a known verified as-of membership/price feed after 15 October 2026,
**before** their returns are observed, then independently verified
maturity. A 21-session horizon cannot be fully observed within one day
of the research cutoff. No independent evidence was supplied; **blocked**.

## Gate 3 — real directional skill and economic advantage

Implemented: prespecified diagnostic screen on a frozen H21 model;
>=12 nonoverlapping fully matured trading-origin cohorts spanning >=300
calendar days, >=25 securities, identical GBM/OU matched events,
positive 5th-percentile origin-bootstrap delta Brier, improvement in both
Brier and log loss against a baseline fixed at forecast time, 10-bin ECE
<=0.05 and 80%-interval coverage in [0.72, 0.88]. Runs only on
matured prospective files and reports statistical screen separately
from readiness authorization.

Acceptance still needs a large enough independent cohort with reliable
data, correction for selection/dependence, confirmation that forecasts
beat a simple time-causal rule, and *actual* risk/cost-adjusted portfolio
returns against a realistically investable FTSE total-return benchmark.
SDE models were only marginally better than a constant 50% probability
on previously viewed 2025 data. This proves no deployable alpha; **blocked**.

## Commands when appropriately sourced inputs become available

    python scripts/pit_data_audit.py --prices PRIVATE/adjusted.csv \
      --membership PRIVATE/members.csv --calendar PRIVATE/calendar.csv \
      --manifest PRIVATE/evidence.json --output outputs/data_audit.json

    python scripts/forward_gate.py record \
      --prices PRIVATE/verified_forward.csv \
      --manifest PRIVATE/forecast_manifest.json \
      --output PRIVATE/immutable_origin.json

    # After at least 21 *subsequent trading sessions*:
    python scripts/forward_gate.py score \
      --prices PRIVATE/verified_updated.csv \
      --manifest PRIVATE/updated_manifest.json \
      --ledger PRIVATE/immutable_origin.json \
      --output PRIVATE/matured_origin.json

    # Once multiple previously-recorded origins have matured:
    python scripts/prospective_evaluation.py \
      --matured PRIVATE/matured_*.json \
      --output outputs/prospective_evaluation.json

The forward-gate reader currently requires a rectangular daily price
panel, so actual FTSE entry/exit, share suspensions and delistings will
need explicit availability-aware schema reconciliation before reliable
live data ingestion. Provenance, external timestamps and independent
auditing are **human/provider tasks**, not a green-CI task.

**No IBKR order submission, no merging into main, no automatic gate
promotion, no real/paper broker connectivity.**
