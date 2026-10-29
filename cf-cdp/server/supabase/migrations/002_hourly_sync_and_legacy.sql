-- Hourly sync job (pg_cron → cdp-sync edge function). The secret is read from settings at run time.
create extension if not exists pg_net with schema extensions;
create extension if not exists pg_cron;
select cron.schedule('cdp-hourly-sync', '7 * * * *', $$
  select net.http_post(
    url := 'https://urgdkrwoxndfdxnllbvx.supabase.co/functions/v1/cdp-sync',
    headers := jsonb_build_object('Content-Type','application/json','x-cron-secret',(select v->>'secret' from public.settings where k='cron_secret')),
    body := '{}'::jsonb, timeout_milliseconds := 120000);
$$);
-- Old, empty prototype tables were publicly readable/writable. Parked (not deleted) in the private legacy schema.
alter table if exists public.products set schema legacy;
alter table if exists public.order_line_items set schema legacy;
alter table if exists public.customer_journey set schema legacy;
alter table if exists public.ai_recommendations set schema legacy;
alter table if exists public.ad_metrics set schema legacy;
alter table if exists public.outreach_log set schema legacy;
alter table if exists public.action_queue set schema legacy;
alter table if exists public.outreach_drafts set schema legacy;
revoke all on all tables in schema legacy from anon, authenticated;
