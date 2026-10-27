# Operator UI wireframes

Shared on every screen:
- **Header:** page name · `North star $100k/mo` · `AS OF <date>` · `Shop lock: Comfort Fresh` · data-source chip (`PLACEHOLDER` in amber until Shopify actuals load).
- **Guardrail strip** (always visible, amber): No send / no Shopify change without Sy · Wool Wave C HOLD · Meta live or not connected (media = ESTIMATE).
- **Basis chips** on every number: `ACTUAL` (Shopify / meta_daily) · `MODELED` (unit economics) · `ESTIMATE` (media scenario).

## 1. CoS ops shell
```
┌ nav ───────────┬ header + guardrail strip ─────────────────────────────────┐
│ Overview       │ KPI row: MTD sales · 30d orders · AOV · repeat % · SUB     │
│ Profiles       │──────────────────────────────────────────────────────────│
│ Ripe today     │ Overview: day-N counts by wave │ Meta fuel (spend/CPR/ROAS)│
│ Meta fuel      │ Heroes + Wool HOLD card        │ Routine health (8:00/8:30/│
│ Inventory      │                                │ Mon delta: OK/FAILED/age) │
│ Pipelines      │                                                            │
└────────────────┴────────────────────────────────────────────────────────────┘
```
| Screen | Components | Binds to |
|---|---|---|
| Overview | KPI tiles, wave count bars, hero SKU cards, Wool HOLD card | revenue_daily, wave_membership summary, inventory |
| Profiles | search box (email), filters (state, wave, style, band), table, profile drawer (traits + event timeline) | profiles, events |
| Ripe today | wave tabs A/B/C60/C90, ripe-today count, CSV export for Retention | wave_membership |
| Meta fuel | spend/CPR/ROAS table per campaign, floor badges (CPR ≤$25–35, ROAS ≥3.5–4×), "scale / hold / cut" chip | meta_daily |
| Inventory | hero SKUs, available, weeks of cover, reorder date (8 wk factory + ~4 wk ship) | Shopify inventory (CoS) |
| Pipelines | last run, status, rows in/out, age alarm if > 26h | pipeline_runs |

## 2. Money Magnet (Retention)
Tabs, default = **Make money**.
| Tab | Components |
|---|---|
| Make money | Ranked next moves: card per move with audience size (SUB-eligible), offer, expected orders × AOV (MODELED), blocker, "Request Sy OK" state |
| North star | $100k gap meter, repeat-order share trend, "≥1 paid every quarter" rate (now ~0.3–0.5%/qtr) |
| Customers | style-ladder funnel ankle → crew → wool, LTV path (illustrative $109×3) |
| Ripe today | table from `wave_membership` (stable path: `warehouse/audiences/wave_membership_latest.csv`) |
| Waves | per wave: rule, members / SUB-eligible, offer, Omnisend draft status (`DRAFT_HELD_FOR_SY`) |
| Send path | step tracker: built → dry run → draft in Omnisend → Sy OK → sent; cap checks (≤3/30d, no Gmail same week) |
| Cash path Nov → Q4'27 | monthly modeled sales from repeat + Meta, vs $100k line, labeled MODELED |
| Blockers | Wool CF22032 = 0, Meta OAuth pending, Sy approvals waiting |

## 3. Revenue & Profit (built: `ui/revenue_profit.html`)
```
header chips ............................................. [PLACEHOLDER]
guardrail strip
[Period: MTD | 30d | 90d]   [Meta media: $5k | $6.5k | $8k | Live(disabled)]
┌ Sales ┬ Orders ┬ AOV ┬ Repeat % ┬ Pairs/order ┐   ← ACTUAL
┌ Modeled P&L ──────────────────┐ ┌ Gap to $100k/mo ─────────┐
│ Gross sales          ACTUAL   │ │ meter · run-rate · gap   │
│ − Discounts+refunds  ACTUAL   │ │ orders/day now · needed  │
│ = Net sales                   │ └──────────────────────────┘
│ − COGS pairs×$0.85   MODELED  │ ┌ Monthly sales (6 mo) ────┐
│ − Ship orders×$7.50  MODELED  │ │ bars, MTD bar lighter,   │
│ = Contribution                │ │ repeat % under each      │
│ − Meta media         ESTIMATE │ └──────────────────────────┘
│ − Salaries ~$1.7k/mo MODELED  │
│ = Modeled net, margin vs 15%  │
│ verdict + sales needed for 15%│
│ scenario comparison table     │
└───────────────────────────────┘
┌ Day-N waves: profile counts · wave table · Wool C HOLD ──────────────┐
```
