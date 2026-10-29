import { createClient } from "npm:@supabase/supabase-js@2.45.4";

export const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
export const OMNI_BRAND = "627b6da1bef8064c8d7a4cd4";
export const SHOP = "md-diab.myshopify.com";

// ---------- Omnisend (REST). Same operations the Omnisend MCP exposes.
const OMNI_BASE = Deno.env.get("OMNISEND_API_BASE") || "https://api.omnisend.com/api";
export async function omni(method: string, path: string, body?: unknown, query?: Record<string, string | number | undefined>) {
  const key = Deno.env.get("OMNISEND_API_KEY");
  if (!key) throw new Error("OMNISEND_API_KEY is not set on the CDP server yet.");
  const qs = query ? "?" + Object.entries(query).filter(([, v]) => v !== undefined && v !== "").map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join("&") : "";
  const r = await fetch(OMNI_BASE + path + qs, {
    method, body: body ? JSON.stringify(body) : undefined,
    headers: { "X-API-KEY": key, Authorization: `Omnisend-API-Key ${key}`, "Content-Type": "application/json", Accept: "application/json" },
  });
  const text = await r.text();
  let data: any = text; try { data = text ? JSON.parse(text) : {}; } catch (_) { /* keep text */ }
  if (!r.ok) throw new Error(`Omnisend ${method} ${path} → ${r.status}: ${typeof data === "string" ? data.slice(0, 300) : JSON.stringify(data).slice(0, 300)}`);
  return data;
}
export async function omniBrandCheck() {
  const b = await omni("GET", "/brands/current");
  if (!b || b.brandID !== OMNI_BRAND) throw new Error(`Omnisend key belongs to ${b?.name || "another brand"}, not Comfort-fresh.com. Nothing was changed.`);
  return b;
}

// ---------- Shopify Admin GraphQL (read-only scopes: read_orders, read_customers).
export async function shopify(query: string, variables: Record<string, unknown> = {}) {
  const token = Deno.env.get("SHOPIFY_ADMIN_TOKEN");
  if (!token) throw new Error("SHOPIFY_ADMIN_TOKEN is not set on the CDP server yet.");
  const r = await fetch(`https://${SHOP}/admin/api/2026-10/graphql.json`, {
    method: "POST", headers: { "X-Shopify-Access-Token": token, "Content-Type": "application/json" }, body: JSON.stringify({ query, variables }),
  });
  const j = await r.json();
  if (!r.ok || j.errors) throw new Error(`Shopify ${r.status}: ${JSON.stringify(j.errors || j).slice(0, 300)}`);
  return j.data;
}

export async function sha256(s: string) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(h)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
