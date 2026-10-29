-- Comfort Fresh CDP server: one source of truth for the app, Claude and Grok bots.
-- Only the edge functions (service role) touch these tables; RLS is on with no public policies.
-- An earlier, empty prototype schema used the names customers/orders. Park it (not deleted) in schema "legacy".
create schema if not exists legacy;
do $$ begin
  if exists (select 1 from information_schema.columns where table_schema='public' and table_name='orders' and column_name not in
    ('id','email','name','processed_at','day','gross','discount','refund','pairs','units','skus','seq','source')) then
    execute 'alter table public.orders set schema legacy';
  end if;
  if exists (select 1 from information_schema.columns where table_schema='public' and table_name='customers' and column_name not in
    ('email','first_name','last_name','shopify_id','lifetime_orders','consent','consent_at','updated_at')) then
    execute 'alter table public.customers set schema legacy';
  end if;
end $$;
revoke all on schema legacy from anon, authenticated;
create table if not exists customers (
  email text primary key, first_name text, last_name text, shopify_id text,
  lifetime_orders int default 0, consent text default 'unknown', consent_at timestamptz, updated_at timestamptz default now());
create table if not exists orders (
  id text primary key, email text references customers(email) on delete cascade, name text, processed_at timestamptz, day date,
  gross numeric default 0, discount numeric default 0, refund numeric default 0, pairs int default 0, units int default 0,
  skus text[] default '{}', seq int default 1, source text);
create index if not exists orders_email on orders(email);
create index if not exists orders_day on orders(day);
create table if not exists meta_daily (day date primary key, spend numeric, purchases int, value numeric, new_customers int, source text, updated_at timestamptz default now());
create table if not exists tasks (id uuid primary key default gen_random_uuid(), title text not null, owner text, due date, status text default 'todo',
  needs_sy boolean default false, sy_ok boolean default false, sy_ok_by text, note text, impact_usd numeric, created_by text, created_at timestamptz default now(), updated_at timestamptz default now());
create table if not exists comments (id uuid primary key default gen_random_uuid(), ref text not null, author text not null, body text not null, created_at timestamptz default now());
create index if not exists comments_ref on comments(ref);
create table if not exists campaigns (id uuid primary key default gen_random_uuid(), audience text not null, status text default 'new', tag text, segment_id text,
  omnisend_campaign_id text, template_id text, subject text, preheader text, sender_name text, send_date date, send_time text, listed int,
  sy_ok boolean default false, sy_ok_by text, sy_ok_at timestamptz, sent_at timestamptz, sent_by text, log text default '', created_by text,
  created_at timestamptz default now(), updated_at timestamptz default now());
create table if not exists email_drafts (id uuid primary key default gen_random_uuid(), audience text, subject text, preheader text, body_html text,
  author text, status text default 'draft', omnisend_template_id text, created_at timestamptz default now(), updated_at timestamptz default now());
create table if not exists sends (id uuid primary key default gen_random_uuid(), audience text, day date, channel text, name text, by text, campaign_id uuid, at timestamptz default now());
create table if not exists api_keys (key_hash text primary key, name text not null, role text not null check (role in ('viewer','member','sy')), active boolean default true, created_at timestamptz default now());
create table if not exists audit (id bigserial primary key, at timestamptz default now(), actor text, tool text, args jsonb, ok boolean, result text);
create table if not exists settings (k text primary key, v jsonb, updated_at timestamptz default now());
alter table customers enable row level security; alter table orders enable row level security; alter table meta_daily enable row level security;
alter table tasks enable row level security; alter table comments enable row level security; alter table campaigns enable row level security;
alter table email_drafts enable row level security; alter table sends enable row level security; alter table api_keys enable row level security;
alter table audit enable row level security; alter table settings enable row level security;
-- Order number per customer (1 = first order). Orders before the data window are counted via Shopify's lifetime order count.
create or replace function recompute_seq() returns void language sql security definer set search_path = public as $$
  update orders o set seq = s.rn + greatest(0, coalesce(c.lifetime_orders, 0) - s.cnt)
  from (select id, email, row_number() over (partition by email order by processed_at, id) rn, count(*) over (partition by email) cnt from orders) s
  join customers c on c.email = s.email where o.id = s.id and o.seq is distinct from s.rn + greatest(0, coalesce(c.lifetime_orders, 0) - s.cnt);
$$;
revoke all on function recompute_seq() from public, anon, authenticated;
grant execute on function recompute_seq() to service_role;
