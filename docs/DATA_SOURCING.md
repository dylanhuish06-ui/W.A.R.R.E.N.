# FTSE 100 historical data sourcing — evidence plan

Status **BLOCKED_DATA_PROVENANCE**. This document identifies authoritative
reference material and a data-procurement schema; it does NOT claim any
paid or independently audited dataset has been obtained. As of 2026-10-16.

## Public official reference sources

1. [LSEG FTSE 100 index resource page](https://www.lseg.com/en/ftse-russell/indices/ftse100)
   links to FTSE UK methodology, historical constituent changes, index
   factsheets and current constituents.
2. [FTSE 100 historic additions/deletions (LSEG PDF)](https://www.lseg.com/content/dam/ftse-russell/en_us/documents/policy-documents/ftse-100-constituent-history.pdf)
   lists historical effective addition/removal events, company names and
   special corporate-action annotations. It is a **useful independent
   cross-check**, but does not directly provide a complete security-level
   adjusted total-return price database or the issuer ISIN crosswalk. The
   latest listed historical event file can change; archive its retrieved
   version/date with a checksum if licence allows.
3. [LSEG developer article: Building historical index constituents](https://developers.lseg.com/en/article-catalog/article/building-historical-index-constituents)
   demonstrates constructing historical FTSE 100 constituents from an
   initial index snapshot plus subsequent changes, given appropriate
   LSEG data/licensed access. This is a methodology reference; don't
   mistake example API calls for an entitlement.
4. [LSEG index-data subscription guide](https://www.lseg.com/en/ftse-russell/index-resources/indices-subscribe-data)
   describes historical constituents/weights for selected index series,
   subject to availability and licensing. Verify that the **FTSE 100**,
   chosen dates, exact granularity, weights and adjustment methodology
   are covered before arranging access.

## Procurement questions for a Durham/academic licence or vendor

Ask the financial-data librarian / LSEG representative to verify:

- Is **historical, point-in-time FTSE 100 membership** available for every
  trading day during at least Jan 2020–Oct 2026, with announced/effective
  dates and delisted securities retained? Is redistribution into a public
  GitHub repository **forbidden**? Assume it is unless explicitly licensed.
- Can membership and company rebrand/merger events be reconciled with
  immutable **ISIN**, historical exchange RIC and corporate-action IDs?
- Is the security-level daily series priced in GBp or GBP per instrument,
  with bid/ask, volume, official close, trading status, splits, cash/special
  dividends, spin-offs, delisting settlements and share-class changes?
- Are unadjusted execution prices and split/dividend-adjusted research
  series **distinct**, with transparent factor definitions and revisions?
  A dividend-adjusted research return series should not be passed into a
  whole-share trading simulator as a real executable quote.
- Does licensing permit academic research locally, derived statistics in
  public GitHub Actions, and internal daily incremental use without
  uploading the raw feed or API tokens to a public runner?
- Are data timestamp, calendar/time zone, update frequency and history of
  corrections supplied? Is the 2026 after-freeze period obtainable as
  subsequent daily snapshots with trusted collection timestamps?

The prospective benchmark must be an investable FTSE 100 **total-return**
ETF series with dividends, fund charges, spreads and trading costs handled
consistently; a price-index level alone isn't sufficient.

## Intake and cross-check design

1. Save original licensed input **privately** with a cryptographic SHA-256,
   collection time, provider name and licence proof; do not upload full
   prices or issuer data to public workflows.
2. Translate the source using an explicitly audited crosswalk to the
   \`prices\`, \`membership\` and manifest schema in
   [POINT_IN_TIME_DATA.md](POINT_IN_TIME_DATA.md).
3. Run \`scripts/pit_data_audit.py\`, examine missing members, overlap,
   announcement-timing, unverified adjustment flags and GBP/GBp conversions.
4. Independently sample membership changes against LSEG's history
   announcement file and a second timestamped source. Resolve different
   share classes and mergers by ISIN, **not names/tickers alone**.
5. Run adjusted-price split/dividend accounting and delisting reconstruction,
   plus exchange-calendar, stale-quote and extreme-jump checks.
6. Obtain independent approval of data lineage before changing gate 1;
   a structurally green report alone never authorizes promotion.

## IBKR cost references (not user-account pricing)

The [published IBKR UK stocks schedule](https://www.interactivebrokers.com/en/pricing/commissions-stocks.php)
describes tiered/fixed approaches with an illustrative **£1 tiered**
minimum and **£3 fixed SmartRouting** minimum for UK share orders.
These numbers vary by product, routing and applicable fees; verify
the user's actual fee plan and tax applicability locally before treating
costs as validated. The isolated [COST_SENSITIVITY.md](COST_SENSITIVITY.md)
runs illustrative £1/£3 cases and stress tests, not real order previews.

## Current status

No vendor login, access rights, paid order, confidential source file,
IBKR account credentials or direct broker connection has been obtained or
used as part of this work. Gate 1 and gate 4 remain **blocked** pending
independent evidence.
