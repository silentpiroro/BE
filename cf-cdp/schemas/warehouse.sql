-- Comfort Fresh CDP warehouse schema.
-- Storage today: files under cf-cdp/warehouse/ (CSV / JSON / JSONL), queryable with DuckDB
--   e.g.  SELECT * FROM read_csv_auto('warehouse/profiles/profiles_2026-10-28.csv');
-- Same DDL runs on Postgres (Supabase) if/when we move to a live database.
-- Identity key everywhere: lower(email). Secondary: shopify_customer_id. Comfort Fresh store only.

-- 1. PROFILES  (one row per person; rebuilt daily by build_profiles.py; file: profiles/profiles_<as_of>.csv)
CREATE TABLE profiles (
  email                  TEXT PRIMARY KEY,           -- lowercase
  shopify_customer_id    TEXT,
  first_name             TEXT,
  last_name              TEXT,
  email_marketing_state  TEXT NOT NULL,              -- SUBSCRIBED | NOT_SUBSCRIBED | UNSUBSCRIBED (Shopify consent)
  order_count_paid       INTEGER NOT NULL DEFAULT 0,
  lifetime_revenue_usd   NUMERIC(12,2) NOT NULL DEFAULT 0,
  first_order_at         DATE,
  last_order_at          DATE,
  days_since_last        INTEGER,                    -- as_of - last_order_at
  primary_style          TEXT,                       -- ankle | crew | wool | other | mixed
  styles_bought          TEXT,                       -- pipe-separated in CSV, e.g. "ankle|crew"
  missing_next_style     TEXT,                       -- next rung on ankle -> crew -> wool
  day_n_band             TEXT,                       -- d0-27 | d28-45 | d46-59 | d60-89 | d90+ | none
  wave                   TEXT,                       -- A | B | C60 | C90 | none
  wave_sub_eligible      BOOLEAN NOT NULL,           -- email_marketing_state = SUBSCRIBED
  has_active_subscription BOOLEAN NOT NULL DEFAULT FALSE,
  ankle_pref             BOOLEAN,
  tags                   TEXT,                       -- pipe-separated Shopify tags
  as_of                  DATE NOT NULL,
  source                 TEXT NOT NULL               -- e.g. shopify_admin_mcp
);

-- 2. EVENTS  (append-only; never update or delete; file: events/events_<YYYY-MM>.jsonl, one JSON object per line)
CREATE TABLE events (
  event_id     TEXT PRIMARY KEY,   -- deterministic, for idempotent re-runs: "<event_type>:<source_id>", e.g. "order_paid:gid://shopify/Order/123"
  event_type   TEXT NOT NULL,      -- order_paid | refund | consent_change | email_sent | email_click | wave_enrolled
  occurred_at  TIMESTAMP NOT NULL, -- UTC
  email        TEXT NOT NULL,      -- lowercase identity key
  shopify_customer_id TEXT,
  channel      TEXT,               -- shopify | omnisend | gmail | meta
  kind         TEXT,               -- marketing | transactional | cs   (email events; caps count kind=marketing)
  amount_usd   NUMERIC(12,2),      -- order_paid / refund
  properties   JSON,               -- order_id, skus, pairs, campaign_id, consent from/to, wave, ...
  ingested_at  TIMESTAMP NOT NULL,
  source       TEXT NOT NULL
);

-- 3. AUDIENCES
-- 3a. wave_membership  (shared Wave keys; file: audiences/wave_membership_<as_of>.csv)
CREATE TABLE wave_membership (
  email                 TEXT NOT NULL,
  wave                  TEXT NOT NULL,     -- A | B | C60 | C90 (precedence A > B > C60 > C90, one wave per person)
  day_n_band            TEXT NOT NULL,
  email_marketing_state TEXT NOT NULL,
  ankle_pref            BOOLEAN,
  wave_sub_eligible     BOOLEAN NOT NULL,  -- filter TRUE before any Omnisend step
  as_of                 DATE NOT NULL,
  PRIMARY KEY (email, as_of)
);

-- 3b. audience_runs  (one row per build or push attempt; file: audiences/audience_runs.jsonl)
CREATE TABLE audience_runs (
  run_id        TEXT PRIMARY KEY,
  audience      TEXT NOT NULL,     -- wave_A | wave_B | wave_C60 | wave_C90 | wool_C
  as_of         DATE NOT NULL,
  members_all   INTEGER NOT NULL,
  members_sub_eligible INTEGER NOT NULL,
  status        TEXT NOT NULL,     -- BUILT | DRY_RUN | DRAFT_HELD_FOR_SY | APPROVED | PUSHED | HOLD
  approved_by   TEXT,              -- must be 'Sy' for APPROVED / PUSHED
  approval_ref  TEXT,              -- link or message id of Sy's OK
  plan_path     TEXT,              -- omnisend_plan_<wave>_<as_of>.json
  created_at    TIMESTAMP NOT NULL
);

-- 4. META_DAILY  (file: meta/daily/meta_daily_<date>.json; only real rows, never estimates)
CREATE TABLE meta_daily (
  date               DATE NOT NULL,
  campaign_id        TEXT,
  campaign_name      TEXT NOT NULL,
  adset_id           TEXT,
  adset_name         TEXT,
  spend_usd          NUMERIC(12,2) NOT NULL,
  impressions        INTEGER,
  clicks             INTEGER,
  purchases          INTEGER,
  purchase_value_usd NUMERIC(12,2),
  cpr_usd            NUMERIC(12,2),    -- spend / purchases (floor: <= $25-35)
  purchase_roas      NUMERIC(8,2),     -- value / spend     (floor: >= 3.5-4.0x)
  source             TEXT NOT NULL,    -- adspirer_meta | ads_manager_dump
  as_of              DATE NOT NULL,
  PRIMARY KEY (date, campaign_name, adset_name)
);

-- 5. REVENUE_DAILY  (Shopify actuals by paid date; file: revenue/revenue_daily.json; feeds Revenue & Profit)
CREATE TABLE revenue_daily (
  date                   DATE PRIMARY KEY,
  orders_paid            INTEGER NOT NULL,
  gross_sales_usd        NUMERIC(12,2) NOT NULL,  -- before discounts
  discounts_usd          NUMERIC(12,2) NOT NULL,
  refunds_usd            NUMERIC(12,2) NOT NULL,
  net_sales_usd          NUMERIC(12,2) NOT NULL,  -- gross - discounts - refunds
  pairs_sold             INTEGER NOT NULL,        -- from SKU -> pairs map (Store SKUs != warehouse 1:1)
  new_customer_orders    INTEGER NOT NULL,
  repeat_customer_orders INTEGER NOT NULL,        -- second+ orders = profit engine
  source                 TEXT NOT NULL,           -- shopify_admin_mcp | shopify_orders_csv | PLACEHOLDER
  as_of                  DATE NOT NULL
);

-- 6. PIPELINE_RUNS  (routine health for the CoS ops page; file: pipelines/runs.jsonl)
CREATE TABLE pipeline_runs (
  run_id      TEXT PRIMARY KEY,
  pipeline    TEXT NOT NULL,     -- cdp_inventory_0800 | day_n_0830 | omnisend_delta_mon | meta_pull
  started_at  TIMESTAMP NOT NULL,
  finished_at TIMESTAMP,
  status      TEXT NOT NULL,     -- OK | FAILED | SKIPPED
  rows_in     INTEGER,
  rows_out    INTEGER,
  message     TEXT
);
