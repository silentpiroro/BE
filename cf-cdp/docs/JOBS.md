# Jobs (pipelines)

All jobs are idempotent: re-running a day overwrites that day's files. Every job appends a row to `warehouse/pipelines/runs.jsonl`.
Anything that sends email or changes Shopify is out of scope for jobs. Those steps stop at a plan file for Sy.

| Job | When | Reads | Writes | Needs live creds? |
|---|---|---|---|---|
| `sync_shopify_profiles` | weekday ~8:00 | Shopify Admin (CoS) | `profiles/`, `revenue/revenue_daily.json`, `events/` (order_paid, refund, consent_change) | Yes: Shopify, CoS only |
| `build_day_n_audiences` | weekday ~8:30, right after profiles | `profiles/`, inventory for CF22032 | `audiences/wave_membership_<as_of>.csv`, summary JSON | No |
| `pull_meta` | weekday ~8:00 | Adspirer Meta, or Ads Manager CSV dump | `meta/daily/meta_daily_<date>.json` | Adspirer: yes. Dump: no |
| `push_omnisend_segment` | Monday delta, or on request | `wave_membership`, `events/` | `audiences/omnisend_plan_<wave>_<as_of>.json` | Dry run: no. Live: Omnisend + Sy OK |
| `feed` + `render` | after any of the above | revenue, meta, wave summary | `dashboard_feed.json`, `ui/revenue_profit.html` | No |

## sync_shopify_profiles
- **Run by:** CoS only (sole Shopify accessor). Read-only queries; no mutations.
- **Live path:** Shopify Admin GraphQL via MCP. `customers` (email, id, `emailMarketingConsent.marketingState`, `numberOfOrders`, `amountSpent`, tags), and `orders(query:"financial_status:paid OR financial_status:partially_refunded processed_at:>=<since>")` with line items (sku, title, quantity), `subtotalPriceSet`, `totalDiscountsSet`, `totalRefundedSet`, `processedAt`.
- **Offline path (works today):** Admin → Orders → Export CSV, then
  `python3 cdp_cli.py build-revenue --shopify-csv orders_export.csv --pairs-map pairs_by_sku.json`.
  Export at least 13 months so new-vs-repeat is right.
- **Rules:** identity = `lower(email)`; drop other stores; style from SKU map (`ankle|crew|wool|other`); `pairs_sold` from a maintained `pairs_by_sku.json`, falling back to "N pairs" / "N-pack" in the title.
- **Then:** existing `build_profiles.py` produces `profiles_<as_of>.csv` (Phase 1, live). Phase 1b glue: when the day-N CSVs land, run `build_profiles.py` → `build-audiences` → `feed` → `render`, then write STATUS.

## build_day_n_audiences
`python3 cdp_cli.py build-audiences --profiles warehouse/profiles/profiles_<as_of>.csv --as-of <as_of> --wool-available <CF22032 available>`
- A: exactly 1 paid order, SUBSCRIBED, d28–45, prefers ankle.
- B: ankle-only, d46–59. C60: ankle-only, d60–89. C90: ankle-only, d90+.
- One wave per person, precedence A > B > C60 > C90. `wave_sub_eligible = SUBSCRIBED`.
- Wool C: buyers without merino; status HOLD unless CF22032 available > 0. A negative Shopify "available" is treated as 0 (it is not always a real oversell).
- Code: `cdp/waves.py`. Tests: `tests/test_cdp.py`.

## pull_meta
- **Preferred:** Adspirer Meta connector (after OAuth). Pull yesterday + 7-day backfill at campaign/ad set level: spend, impressions, link clicks, purchases, purchase value. Write `meta_daily` rows with `source=adspirer_meta`.
- **Fallback (works today):** Ads Manager → Reports → breakdown by Day → export CSV, then
  `python3 cdp_cli.py pull-meta --dump ads_manager_daily.csv`.
- Derived: `cpr_usd = spend / purchases`, `purchase_roas = value / spend`. Flag winners against the floors (CPR ≤ $25–35, ROAS ≥ 3.5–4×).
- Never write estimates into `meta_daily`. Scenarios live only in the P&L model.

## push_omnisend_segment (dry run by default)
`python3 cdp_cli.py push-omnisend --wave A --as-of 2026-10-28`
1. Filters to the wave, then removes: not SUBSCRIBED; ≥3 marketing emails in 30 days; anyone who got Gmail marketing this week.
2. Writes the plan (`would_upsert`, skip counts, email list, offer notes). Wave A note: 6@$49 ankle alone, no COMEBACK15.
3. Wool C refuses while HOLD.
4. `--execute` needs `--approved-by Sy --approval-ref <link>`. Even then the CLI stops: the live upsert (contacts + tag `cf_wave_<x>`) runs through the Omnisend MCP from a Claude session using the plan file. Campaigns stay drafts until Sy publishes.
5. Log an `audience_runs` row and, once sent, `email_sent` events (channel=omnisend, kind=marketing) so caps keep working.

## feed + render
`python3 cdp_cli.py feed --revenue warehouse/revenue/revenue_daily.json --meta warehouse/meta/daily/<latest>.json --waves warehouse/audiences/wave_membership_summary_<as_of>.json --as-of <date>`
then `python3 cdp_cli.py render`. The page is one self-contained HTML file, ready to republish as an Artifact.
