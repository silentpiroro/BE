// Comfort Fresh CDP engine: the same rules as the CDP app (ui/templates/cdp_app.html), so the app,
// Claude and Grok bots all see the same audiences, values and next moves.
export const COGS = 0.85, SHIP = 7.5, CAC = 70, CAC_CUT = 85, NS = 100000;

export type Order = { id: string; email: string; name: string | null; day: string; gross: number; discount: number; refund: number; pairs: number; skus: string[]; seq: number };
export type Customer = { email: string; first_name: string | null; last_name: string | null; lifetime_orders: number; consent: string | null };

export const SEG_ORDER = ["recent", "service", "vip_lapsed", "vip_active", "second_order", "wave_a", "household", "bundle_clock", "large_feet", "ladder", "repeat_lapsed", "dormant", "other"];
export const SEG_LABEL: Record<string, string> = {
  recent: "Just ordered (0–6 days)", service: "Refund, never came back", vip_lapsed: "VIP gone quiet (3+ orders, 60+ days)",
  vip_active: "VIP active (3+ orders, <60 days)", second_order: "Second-order window (1 order, day 7–27)", wave_a: "Wave A (1 order, day 28–45)",
  household: "Household buyers (2+ sizes in one order)", bundle_clock: "Bundle buyers on the sock clock (13+ pairs, 60+ days)",
  large_feet: "Large-feet customers (sock size 13–15), 1 order, 46–119 days", ladder: "One order, 46–119 days", repeat_lapsed: "2 orders, 60+ days",
  dormant: "One order, 120+ days (C90)", other: "Everyone else",
};
export const SEG_RULE: Record<string, string[]> = {
  recent: ["last order 0–6 days ago"], service: ["has a refunded order", "no order after the refund", "2 lifetime orders or fewer"],
  vip_lapsed: ["3+ lifetime orders", "last order 60+ days ago"], vip_active: ["3+ lifetime orders", "last order under 60 days ago"],
  second_order: ["1 lifetime order", "last order 7–27 days ago"], wave_a: ["1 lifetime order", "last order 28–45 days ago"],
  household: ["bought 2+ sock sizes in one order"], bundle_clock: ["last order had 13+ pairs", "last order 60+ days ago"],
  large_feet: ["mostly buys sock size 13–15", "1 lifetime order", "last order 46–119 days ago"], ladder: ["1 lifetime order", "last order 46–119 days ago"],
  repeat_lapsed: ["2 lifetime orders", "last order 60+ days ago"], dormant: ["1 lifetime order", "last order 120+ days ago"], other: ["matches none of the rules above"],
};
// Offers checked against Shopify on 2026-10-28. Bonus-pair offers have no Shopify discount yet.
export const OFFER: Record<string, string> = {
  wave_a: "Club Starter: 6 pairs for $49 (email and downsell only). No code stacked.", dormant: "COMEBACK15: 15% off, once per customer, expires Nov 26.",
  second_order: "Crew + ankle cross-sell. Free insoles with 18/24-pair packs, free shipping over $50.", vip_active: "Thank-you + 18-pair pack with free insoles. No % off.",
  household: "One order for the whole family, every size. Free insoles with 18/24 packs, free shipping over $50.", bundle_clock: "Same style and size restock. Free insoles with 18/24 packs.",
  large_feet: "World Diabetes Day foot-care story for sock size 13–15. No discount.", ladder: "The other height (crew/ankle) or Multi-Color. Free insoles with 18/24 packs.",
  repeat_lapsed: "Per-pair math: 18 pairs = $6.06/pair vs $6.58 on 12. Free insoles included.", vip_lapsed: "Personal Gmail note. Bonus pairs need a Shopify discount first (Sy OK).",
  service: "Personal Gmail note: free replacement pair in the right size (handled manually by CS).",
};
// One Omnisend template per audience (name rule "CF · <code> · v1").
export const TEMPLATE: Record<string, [string, string]> = {
  wave_a: ["6ae044a48c5e23687ae5b7aa", "Wave A · Day-30 replenish 6@$49 · ankle Club Starter"], dormant: ["6ae023d149fd8e9926e27c65", "COMEBACK15 Winback Ankle CF17180 v2"],
  second_order: ["6ae25484888da9da17b64e5c", "CF · Second order · v1"], vip_active: ["6ae25497888da9da17b64e84", "CF · VIP active · v1"], household: ["6ae254a585e6f965c359f1c5", "CF · Household · v1"],
  bundle_clock: ["6ae254b9888da9da17b64ed7", "CF · Bundle restock · v1"], large_feet: ["6ae254c72b29279290c62805", "CF · Large feet 13-15 · v1"], ladder: ["6ae254dc85e6f965c359f1f8", "CF · Cross-sell · v1"],
  repeat_lapsed: ["6ae254e9888da9da17b64f2a", "CF · Bundle upgrade · v1"],
};
export const SUBJECT: Record<string, string> = {
  vip_active: "A thank-you for our regulars", second_order: "Your second pair of colors is waiting", wave_a: "Your Club Starter: 6 pairs for $49", household: "Socks for everyone at home",
  bundle_clock: "Time for fresh socks?", large_feet: "Made for big feet: sock size 13–15", ladder: "Try the other half of the drawer", repeat_lapsed: "Upgrade to the 18-pair bundle", dormant: "We saved you 15%: COMEBACK15",
};
export const GMAIL_ONLY = ["vip_lapsed", "service"];
// Planned send dates from the Money Magnet plan (2026 Q4).
export const SCHEDULE: Record<string, string[]> = {
  vip_lapsed: ["2026-11-04", "2026-11-14", "2026-11-27", "2026-12-10"], vip_active: ["2026-11-14", "2026-11-27", "2026-12-10"], second_order: ["2026-11-14", "2026-11-27", "2026-12-10"],
  wave_a: ["2026-11-05", "2026-11-14", "2026-11-27", "2026-12-10"], household: ["2026-11-14", "2026-11-27", "2026-12-10"], bundle_clock: ["2026-11-14", "2026-11-27", "2026-12-10"],
  large_feet: ["2026-11-14", "2026-11-27", "2026-12-10"], ladder: ["2026-11-14", "2026-11-27", "2026-12-10"], repeat_lapsed: ["2026-11-14", "2026-11-27", "2026-12-10"],
  dormant: ["2026-11-10", "2026-11-14", "2026-11-27", "2026-12-10"], other: ["2026-11-14", "2026-11-27", "2026-12-10"],
};

export const today = () => new Intl.DateTimeFormat("en-CA", { timeZone: "America/Chicago" }).format(new Date());
export const addDays = (iso: string, n: number) => { const d = new Date(iso + "T12:00:00Z"); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); };
export const daysBetween = (a: string, b: string) => Math.round((Date.parse(b + "T12:00:00Z") - Date.parse(a + "T12:00:00Z")) / 86400000);
const sizeOf = (s: string) => /13-15|1315/.test(s) ? "13-15" : /10-13|1013/.test(s) ? "10-13" : /9-11|0911|-911/.test(s) ? "9-11" : null;
const familyOf = (s: string) => (/^[A-Z0-9]+-\d/.test(s) ? s.split("-")[0] : null);

export type Profile = ReturnType<typeof derive>;
export function derive(c: Customer, all: Order[], asOf: string) {
  const o = all.slice().sort((a, b) => a.day.localeCompare(b.day));
  const net = (x: Order) => (+x.gross || 0) - (+x.discount || 0) - (+x.refund || 0);
  const cost = (x: Order) => (x.pairs || 0) * COGS + SHIP;
  const acquiredHere = o.length > 0 && (o[0].seq || 1) === 1;
  const skus = o.flatMap((x) => x.skus || []);
  const sizes: Record<string, number> = {}; skus.forEach((s) => { const z = sizeOf(s); if (z) sizes[z] = (sizes[z] || 0) + 1; });
  const fams: Record<string, number> = {}; skus.forEach((s) => { const f = familyOf(s); if (f) fams[f] = (fams[f] || 0) + 1; });
  const size = Object.entries(sizes).sort((a, b) => b[1] - a[1])[0]?.[0] || null;
  const last = o[o.length - 1], first = o[0], second = o[1];
  const lo = Math.max(c.lifetime_orders || 0, last ? last.seq || o.length : 0);
  const firstRef = o.findIndex((x) => (+x.refund || 0) > 0);
  const p = {
    email: c.email, name: [c.first_name, c.last_name].filter(Boolean).join(" ") || c.email, first_name: c.first_name, consent: c.consent || "unknown",
    orders: o.length, lifetime_orders: lo, ltv_net: +o.reduce((a, x) => a + net(x), 0).toFixed(2),
    ltv_profit: +(o.reduce((a, x) => a + net(x) - cost(x), 0) - (acquiredHere ? CAC : 0)).toFixed(2),
    first_order: first ? { day: first.day, gross: +first.gross } : null, second_order: second ? { day: second.day, gross: +second.gross } : null,
    days_to_second: second ? daysBetween(first.day, second.day) : null, last_order: last ? last.day : null, days_since: last ? daysBetween(last.day, asOf) : null,
    size, last_pairs: last ? last.pairs || 0 : 0, family: Object.entries(fams).sort((a, b) => b[1] - a[1])[0]?.[0] || null,
    household: o.some((x) => new Set((x.skus || []).map(sizeOf).filter(Boolean)).size > 1),
    refunded: firstRef >= 0, reordered_after_refund: firstRef >= 0 && firstRef < o.length - 1, audience: "other",
  };
  p.audience = segmentOf(p);
  return p;
}
function segmentOf(c: { days_since: number | null; lifetime_orders: number; refunded: boolean; reordered_after_refund: boolean; household: boolean; last_pairs: number; size: string | null }) {
  const ds = c.days_since ?? 9999, lo = c.lifetime_orders;
  if (ds < 7) return "recent";
  if (c.refunded && !c.reordered_after_refund && lo <= 2) return "service";
  if (lo >= 3 && ds >= 60) return "vip_lapsed";
  if (lo >= 3) return "vip_active";
  if (lo === 1 && ds <= 27) return "second_order";
  if (lo === 1 && ds <= 45) return "wave_a";
  if (c.household) return "household";
  if (c.last_pairs >= 13 && ds >= 60) return "bundle_clock";
  if (c.size === "13-15" && lo === 1 && ds < 120) return "large_feet";
  if (lo === 1 && ds < 120) return "ladder";
  if (lo === 2 && ds >= 60) return "repeat_lapsed";
  if (lo === 1) return "dormant";
  return "other";
}

export function sumPeriod(orders: Order[], start: string, end: string) {
  const a = { orders: 0, gross: 0, discount: 0, refund: 0, pairs: 0, new_customers: 0, repeat_orders: 0, first_order_gross: 0 };
  for (const x of orders) if (x.day >= start && x.day <= end) {
    a.orders++; a.gross += +x.gross || 0; a.discount += +x.discount || 0; a.refund += +x.refund || 0; a.pairs += x.pairs || 0;
    if ((x.seq || 1) > 1) a.repeat_orders++; else { a.new_customers++; a.first_order_gross += +x.gross || 0; }
  }
  return { ...a, gross: +a.gross.toFixed(2), aov: a.orders ? +(a.gross / a.orders).toFixed(2) : 0, first_order_aov: a.new_customers ? +(a.first_order_gross / a.new_customers).toFixed(2) : 0 };
}

export function nextSend(aud: string, sentDates: string[]) {
  const t = today();
  if (aud === "second_order" || aud === "service") return { date: t, label: aud === "service" ? "this week" : "rolling: day 10 after each first order" };
  const last = sentDates.sort().at(-1);
  const d = (SCHEDULE[aud] || []).find((x) => x >= t && (!last || x > last));
  return d ? { date: d, label: "planned send" } : null;
}

// ≤3 marketing emails per 30 days per audience, and no Omnisend + Gmail marketing in the same week.
export function capCheck(aud: string, date: string, channel: string, sends: { audience: string; day: string; channel: string; name: string }[]) {
  const hits = sends.filter((s) => s.audience === aud || s.audience === "all" || aud === "all");
  let worst = 0;
  for (let k = 0; k < 30; k++) { const ws = addDays(date, -k), we = addDays(ws, 29); worst = Math.max(worst, hits.filter((s) => s.day >= ws && s.day <= we).length + 1); }
  const week = (d: string) => { const x = new Date(d + "T12:00:00Z"); return addDays(d, -((x.getUTCDay() + 6) % 7)); };
  const other = hits.find((s) => s.channel !== channel && week(s.day) === week(date));
  return { ok: worst <= 3 && !other, email_number_in_30_days: worst, conflict: other ? `${other.name} went by ${other.channel} the same week` : null };
}
