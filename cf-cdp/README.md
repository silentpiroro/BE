# Comfort Fresh CDP (CF-native)

The five Segment jobs (sources, identity, profiles, audiences, destinations) built in-house on the connectors we already have: Shopify, Omnisend, Meta (Adspirer or Ads Manager dumps). No Twilio Segment, no Klaviyo this quarter.

## Economics (set 2026-10-27)
- **CAC $70** per new customer (ad spend ÷ new customers in Shopify). At a ~$90 bundle-first order the first order nets ≈ $3 after product, shipping and CAC: it pays for itself, nothing more.
- **Profit comes from second and later orders** (~$53 each). 15% net at $100k/mo needs ~0.29 repeat orders per customer in year 1 (0.19 today) and ~266 repeat orders/month.
- Scale / hold / cut on 7-day CAC: ≤ $70 scale +30%/week, $70–85 hold, > $85 cut a step. Any step above the $5–8k/mo band still needs Sy's OK. This replaces the earlier 3.5× ROAS floor for planning.

## Architecture in 10 bullets
1. **Sources:** Shopify (orders, customers, consent, SKUs, inventory) via Admin MCP run by CoS only. Meta via Adspirer, or Ads Manager CSV dumps as fallback. Omnisend and Gmail only feed back `email_sent` / `email_click` events.
2. **Identity:** one person = `lower(email)`, secondary `shopify_customer_id`, Comfort Fresh store only. No cross-store or fuzzy merges.
3. **Warehouse = files, not a SaaS:** CSV / JSON / append-only JSONL under `warehouse/` (git-ignored, holds PII). The DDL in `schemas/warehouse.sql` reads these through DuckDB today and runs as-is on Postgres/Supabase later.
4. **Profiles:** the Phase 1 trait table (`build_profiles.py`, live 2026-10-28) is rebuilt daily from Shopify and is the single source for traits.
5. **Events:** append-only log (`order_paid`, `refund`, `consent_change`, `email_sent`, `email_click`, `wave_enrolled`) with deterministic `event_id`, so re-runs never double count. Frequency caps read from it.
6. **Audiences:** `build_day_n_audiences` assigns one wave per person (A > B > C60 > C90). Wool C is a separate list on HOLD until CF22032 > 0. Output is the shared `wave_membership` file that Retention binds to.
7. **Destinations:** Omnisend only through `push_omnisend_segment`. It defaults to a dry run, drops non-SUB contacts, enforces ≤3 marketing emails per 30 days and no Gmail marketing the same week, and needs Sy's approval. Campaigns stay drafts. Meta CAPI comes later.
8. **Money math lives in one place:** `cdp/pnl.py` (tested). Pages only render a precomputed feed, so the dashboard and the jobs can't disagree.
9. **Operator pages are static HTML artifacts** (CoS ops, Money Magnet, Revenue & Profit). A job rebuilds the feed, inlines it into the page and republishes. Every number carries an ACTUAL / MODELED / ESTIMATE label.
10. **Pipelines = scheduled Claude Code routines:** weekday 8:00 (profiles + revenue + Meta), 8:30 (day-N audiences + feeds), Monday (Omnisend contact delta, dry run). Each logs to `pipeline_runs` for the ops health panel.

## Stack choice (and assumptions)
- **Python 3.11+ standard library only** for jobs. Nothing to install, so it runs in any Claude Code session or cron.
- **Claude Code** runs the jobs and holds the MCP connectors (Shopify, Omnisend, Adspirer). The CLI never stores API keys.
- **Claude Artifacts** host the operator pages: one self-contained HTML file each, so phone viewing works.
- **Upgrade path:** move `warehouse/` into Supabase Postgres when we need multiple writers or live pages (Phase 4). The schema is already Postgres-compatible.
- Assumed: CoS keeps running `build_profiles.py` where it lives today. This repo consumes its CSV output and does not replace it.

## What's in this folder
| Path | What |
|---|---|
| `cdp/pnl.py` | Revenue & Profit model: periods, P&L lines, 15%-net breakeven, gap to $100k |
| `cdp/waves.py` | Day-N wave rules, wave_membership, Wool C HOLD |
| `cdp/sources.py` | Shopify orders CSV → `revenue_daily`; Ads Manager CSV → `meta_daily` |
| `cdp/omnisend_push.py` | Dry-run plan + guardrails; live push needs Sy |
| `cdp/config.py` | Locked unit economics and guardrail constants |
| `cdp_cli.py` | Job runner (see top of file) |
| `schemas/warehouse.sql` | profiles, events, wave_membership, audience_runs, meta_daily, revenue_daily, pipeline_runs |
| `docs/JOBS.md` | Job specs: sync_shopify_profiles, build_day_n_audiences, pull_meta, push_omnisend_segment |
| `docs/WIREFRAMES.md` | CoS ops, Money Magnet, Revenue & Profit |
| `ui/revenue_profit.html` | Built dashboard (feed inlined). Template in `ui/templates/` |
| `data/sample/` | PLACEHOLDER revenue, empty `meta_daily`, 2026-10-28 wave counts, synthetic profiles |
| `tests/test_cdp.py` | P&L, wave rules, Omnisend guardrails, CSV adapters |

## Run it
```bash
cd cf-cdp
python3 -m unittest discover -s tests          # 11 tests
python3 cdp_cli.py sample-data                 # regenerate placeholder inputs
python3 cdp_cli.py feed && python3 cdp_cli.py render
open ui/revenue_profit.html
```
Swap in actuals with no credentials needed: export orders from Shopify Admin, then
`python3 cdp_cli.py build-revenue --shopify-csv orders_export.csv` and
`python3 cdp_cli.py feed --revenue warehouse/revenue/revenue_daily.json`.

## Operator pages (Claude artifacts)
| Page | What it's for | Data |
|---|---|---|
| North Star War Room | Daily command page: alerts, month pacing, the 3 gates, action board with Sy approvals, Meta daily log, email-cap checker | Artifact db (`board/scoreboard` written by Claude via `cdp_cli.py warroom-seed`; `actions`, `meta_daily`, `sends` written by the team) + live Shopify MTD through the viewer's Shopify connector, accepted only for `md-diab.myshopify.com` |
| Money Magnet | Ranked moves, win-back playbook, path to $100k | `cdp_cli.py magnet` feed |
| Revenue & Profit | Actuals + modeled P&L | `cdp_cli.py feed` |

Refresh after a new Shopify export: `build-revenue` → `feed`/`render`, `magnet` → render, `warroom-seed` → write `board/scoreboard` into the War Room db.

## Build phases
| Phase | Status | Next step |
|---|---|---|
| 1 Profiles + wave_membership + build_profiles.py | Done | — |
| 1b Glue: day-N CSVs land → build_profiles → build-audiences → feed → render → STATUS | Spec'd | Schedule the 8:30 routine to chain these |
| 2 Append-only event log | Schema done | CoS writes `order_paid` / `refund` / `consent_change` in sync; Omnisend writes `email_sent` after sends |
| 2b Stable audience path for Money Magnet | Spec'd | Write `wave_membership_latest.csv` on each build |
| 3 Live Meta via Adspirer → meta_daily | Adapter for dumps done | Finish Adspirer OAuth; then the "Live" media toggle turns on by itself |
| 3b Omnisend upsert from audiences | Dry-run done | Live upsert via Omnisend MCP after Sy OK per send |
| 4 Live UI refresh | Static + rebuild done | Routine republishes the artifacts; later Supabase-backed pages |
| — Revenue & Profit dashboard | **Built (placeholder data)** | Feed it a Shopify export |

## Needs live credentials vs runs offline
| Piece | Offline now | Needs |
|---|---|---|
| P&L model, dashboard render, wave rules, Omnisend dry-run plan, tests | Yes | — |
| Revenue actuals | Yes, from a Shopify orders CSV export | Live daily sync: Shopify Admin MCP (CoS) |
| Profiles refresh | Yes, from CoS's `profiles_<as_of>.csv` | Shopify Admin MCP (CoS) |
| Wool C HOLD check | Manual number via `--wool-available` | Shopify inventory read (CoS) |
| Meta spend / CPR / ROAS | Yes, from an Ads Manager CSV dump | Adspirer Meta OAuth for daily pulls |
| Omnisend contact upsert / campaign draft | Dry-run plan only | Omnisend MCP **and** Sy's explicit OK per send |
| Gmail same-week check | Uses `events` if logged | Gmail connector to log 1:1 marketing touches |
| Meta CAPI / offline events | No | Meta access + pixel/dataset ID (future) |

## Guardrails built into code
- `push-omnisend` never sends. Live mode needs `--approved-by Sy --approval-ref`, and campaigns stay drafts.
- Non-SUB contacts, the 30-day cap of 3, and same-week Gmail contacts are dropped before any plan.
- Wool C refuses while CF22032 ≤ 0.
- `meta_daily` only accepts real rows. Media in the P&L is labeled ESTIMATE until live rows exist.
- Nothing in this repo mutates Shopify.
