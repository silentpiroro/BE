// Hourly background sync (pg_cron → here). Pulls new Shopify orders and Omnisend consent into the CDP tables.
// Auth: header x-cron-secret must match settings.cron_secret (set once when the server is installed).
import { db } from "../_shared/clients.ts";
import { syncConsent, syncShopify } from "../_shared/sync.ts";

Deno.serve(async (req) => {
  const { data } = await db.from("settings").select("v").eq("k", "cron_secret").maybeSingle();
  const secret = data?.v?.secret;
  if (!secret || req.headers.get("x-cron-secret") !== secret) return new Response("unauthorized", { status: 401 });
  const out: Record<string, unknown> = { at: new Date().toISOString() };
  try { out.shopify = await syncShopify(); } catch (e) { out.shopify_error = (e as Error).message; }
  // Consent is heavier (pages through Omnisend segments); every 6th hour is enough.
  if (new Date().getUTCHours() % 6 === 0 || new URL(req.url).searchParams.has("consent")) {
    try { out.consent = await syncConsent(); } catch (e) { out.consent_error = (e as Error).message; }
  }
  await db.from("settings").upsert({ k: "last_sync", v: out, updated_at: new Date().toISOString() });
  return new Response(JSON.stringify(out), { headers: { "Content-Type": "application/json" } });
});
