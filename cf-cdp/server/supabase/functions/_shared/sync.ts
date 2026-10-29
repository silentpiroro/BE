// Background sync: new Shopify orders + Omnisend email consent → CDP tables.
import { db, omni, omniBrandCheck, shopify } from "./clients.ts";

const packOf = (sku: string): number | null => {
  sku = String(sku || "").trim(); let m: RegExpMatchArray | null;
  const cap = (n: number) => (n > 0 && n <= 48 ? n : null);
  if ((m = sku.match(/^[A-Za-z0-9]+-(?:0?911|1013|1315)-((?:[A-Z]\d+)+)P?\b/i))) return cap((m[1].match(/\d+/g) || []).reduce((a, x) => a + +x, 0));
  if ((m = sku.match(/^[A-Za-z0-9]+-((?:\d+[A-Za-z]+)+)/))) return cap((m[1].match(/(\d+)[A-Za-z]+/g) || []).reduce((a, x) => a + parseInt(x, 10), 0));
  for (const re of [/PK(\d+)/i, /(\d+)\s*PR\b/i, /^CF-B[A-Z]{2}-(\d+)-/i, /^[A-Za-z0-9]+-(\d+)-[A-Za-z]/i, /(\d+)\s*pairs?\b/i]) if ((m = sku.match(re))) return cap(+m[1]);
  return null;
};
const chicago = (ts: string) => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Chicago" }).format(new Date(ts));

export async function syncShopify(sinceOverride?: string) {
  const { data: st } = await db.from("settings").select("v").eq("k", "shopify_cursor").maybeSingle();
  const since = sinceOverride || st?.v?.since || "2025-12-01";
  const Q = `query($first:Int!,$after:String,$q:String){orders(first:$first,after:$after,query:$q,sortKey:PROCESSED_AT){pageInfo{hasNextPage endCursor}
    nodes{id name processedAt cancelledAt displayFinancialStatus email customer{id defaultEmailAddress{emailAddress} firstName lastName numberOfOrders}
    subtotalPriceSet{shopMoney{amount}} totalDiscountsSet{shopMoney{amount}} totalRefundedSet{shopMoney{amount}} lineItems(first:20){nodes{sku quantity title}}}}}`;
  let after: string | null = null, pages = 0, maxTs = since;
  const custs = new Map<string, any>(), rows: any[] = [];
  do {
    const d: any = await shopify(Q, { first: 100, after, q: `processed_at:>=${since}` });
    const o = d.orders; after = o.pageInfo.hasNextPage ? o.pageInfo.endCursor : null; pages++;
    for (const n of o.nodes) {
      if (n.processedAt > maxTs) maxTs = n.processedAt;
      if (n.cancelledAt || !/^(PAID|PARTIALLY_REFUNDED|REFUNDED)$/.test(n.displayFinancialStatus || "")) continue;
      const email = String(n.customer?.defaultEmailAddress?.emailAddress || n.email || "").trim().toLowerCase(); if (!email) continue;
      const amt = (x: any) => +(x?.shopMoney?.amount || 0);
      let pairs = 0, units = 0; const skus: string[] = [];
      for (const l of n.lineItems?.nodes || []) { units += l.quantity || 0; skus.push(l.sku || l.title); pairs += (l.quantity || 0) * (packOf(l.sku || "") || packOf(l.title || "") || 1); }
      const prev = custs.get(email), life = Math.max(+(n.customer?.numberOfOrders || 0), prev?.lifetime_orders || 0);
      custs.set(email, { email, first_name: n.customer?.firstName || prev?.first_name || null, last_name: n.customer?.lastName || prev?.last_name || null, shopify_id: n.customer?.id || null, lifetime_orders: life, updated_at: new Date().toISOString() });
      const sub = amt(n.subtotalPriceSet), disc = amt(n.totalDiscountsSet);
      rows.push({ id: String(n.id).split("/").pop(), email, name: n.name, processed_at: n.processedAt, day: chicago(n.processedAt),
        gross: +(sub + disc).toFixed(2), discount: disc, refund: Math.min(amt(n.totalRefundedSet), sub), pairs: Math.round(pairs), units, skus: skus.slice(0, 6), source: "shopify" });
    }
  } while (after && pages < 60);
  const cl = [...custs.values()];
  for (let i = 0; i < cl.length; i += 500) { const { error } = await db.from("customers").upsert(cl.slice(i, i + 500), { onConflict: "email" }); if (error) throw new Error("customers: " + error.message); }
  for (let i = 0; i < rows.length; i += 500) { const { error } = await db.from("orders").upsert(rows.slice(i, i + 500), { onConflict: "id" }); if (error) throw new Error("orders: " + error.message); }
  await db.rpc("recompute_seq");
  const added = rows.length;
  await db.from("settings").upsert({ k: "shopify_cursor", v: { since: maxTs.slice(0, 10), at: new Date().toISOString() }, updated_at: new Date().toISOString() });
  return { orders_upserted: added, since };
}

const CONSENT_SEGS: Record<string, string> = { subscribed: "CF CDP · Email subscribed (consent sync)", unsubscribed: "CF CDP · Email unsubscribed (consent sync)" };
async function consentSegment(status: string) {
  let after: string | null = null;
  for (let i = 0; i < 20; i++) {
    const b: any = await omni("GET", "/segments", undefined, { limit: 50, after: after || undefined });
    const hit = (b.segments || []).find((x: any) => x.name === CONSENT_SEGS[status] && !x.archivedAt);
    if (hit) return hit.segmentID;
    after = b.paging?.hasMore ? b.paging?.cursors?.after : null; if (!after) break;
  }
  const body: any = await omni("POST", "/segments", { name: CONSENT_SEGS[status], conditionGroups: [{ conditions: [{ entity: "contact", junction: "and", filters: [{ channels: ["email"], operator: "equals", property: "subscriptionStatus", value: status }] }] }] });
  return body.segmentID || body.id;
}
export async function syncConsent() {
  await omniBrandCheck();
  const { data: cs } = await db.from("customers").select("email");
  const mine = new Set((cs || []).map((c: any) => c.email));
  const out: Record<string, number> = {};
  for (const status of ["subscribed", "unsubscribed"]) {
    const seg = await consentSegment(status); const hits: string[] = []; let after: string | null = null, n = 0;
    do {
      const b: any = await omni("GET", "/contacts", undefined, { segmentID: seg, limit: 250, after: after || undefined });
      for (const c of b.contacts || []) { n++; const e = String(c.email || "").toLowerCase(); if (mine.has(e)) hits.push(e); }
      after = b.paging?.hasMore ? b.paging?.cursors?.after : null;
    } while (after && n < 50000);
    for (let i = 0; i < hits.length; i += 500) await db.from("customers").update({ consent: status, consent_at: new Date().toISOString() }).in("email", hits.slice(i, i + 500));
    out[status + "_customers"] = hits.length; out[status + "_in_omnisend"] = n;
  }
  await db.from("settings").upsert({ k: "consent_sync", v: { ...out, at: new Date().toISOString() } });
  return out;
}
