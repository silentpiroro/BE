"""Customer playbook: one next-best action per buyer.

For each customer: segment (first match in priority order), measured 90-day reorder
baseline for that kind of customer (backtest), the product to offer (their size, the
complementary SKU family that real 2nd orders moved to, the color they don't own yet),
the incentive (bonus pairs before percent-off), channel and send date. A scheduler keeps
every segment at <=3 marketing emails in any rolling 30 days.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, timedelta

from . import config as C
from .magnet import _d, _gross, _pairs

BACKTEST_DAYS = 90


def _skus(r):
    return [s.strip() for s in (r.get("skus") or "").split(";") if s.strip()]


def _family(s):
    return s.split("-")[0] if re.match(r"^[A-Z0-9]+-\d", s) else None


def _size(s):
    if re.search(r"13-15|1315", s):
        return "13-15"
    if re.search(r"10-13|1013", s):
        return "10-13"
    if re.search(r"9-11|0911|-911", s):
        return "9-11"
    return None


def _color(s):
    s = s.lower()
    if "black" in s or "blk" in s:
        return "black"
    if "white" in s or "wht" in s:
        return "white"
    return None


def customers(rows: list[dict], as_of: date) -> list[dict]:
    by = defaultdict(list)
    for r in rows:
        by[(r.get("customer_email") or r.get("customer_id") or "").strip().lower()].append(r)
    out = []
    for cid, v in by.items():
        v.sort(key=_d)
        skus = [s for r in v for s in _skus(r)]
        sizes = Counter(z for s in skus if (z := _size(s)))
        fams = Counter(f for s in skus if (f := _family(s)))
        colors = {c for s in skus if (c := _color(s))}
        out.append({
            "id": cid,
            "email": (v[-1].get("customer_email") or "").strip().lower(),
            "first_name": v[-1].get("customer_first_name") or "",
            "lifetime_orders": int(float(v[-1].get("customer_lifetime_orders") or len(v))),
            "orders_in_window": len(v),
            "spend_usd": round(sum(_gross(r) for r in v), 2),
            "last_order": _d(v[-1]).isoformat(),
            "days_since": (as_of - _d(v[-1])).days,
            "last_pairs": round(_pairs(v[-1])),
            "size": sizes.most_common(1)[0][0] if sizes else None,
            "household": any(len({_size(s) for s in _skus(r)} - {None}) > 1 for r in v),
            "family": fams.most_common(1)[0][0] if fams else None,
            "families": set(fams),
            "colors": colors,
            "refunded": any(float(r.get("total_refunded") or 0) > 0 for r in v),
            "reordered_after_refund": any(float(r.get("total_refunded") or 0) > 0 for r in v[:-1]),
            "discount_buyer": any(float(r.get("total_discounts_original") or 0) > 0 for r in v),
            "wool": any("CF22032" in s for s in skus),
        })
    return out


def transitions(rows: list[dict]) -> dict[str, list[tuple[str, int]]]:
    """Family -> families bought in the customer's next order, by count (real 2nd orders)."""
    by = defaultdict(list)
    for r in rows:
        by[(r.get("customer_email") or r.get("customer_id") or "").strip().lower()].append(r)
    tr = defaultdict(Counter)
    for v in by.values():
        v.sort(key=_d)
        for a, b in zip(v, v[1:]):
            for x in {_family(s) for s in _skus(a)} - {None}:
                for y in {_family(s) for s in _skus(b)} - {None}:
                    if x != y:
                        tr[x][y] += 1
    return {k: c.most_common(3) for k, c in tr.items()}


# ----------------------------------------------------------------------------- segments
# (key, label, test, channel, timing rule, incentive, why)
def _segments(as_of):
    return [
        ("recent", "Just ordered (0–6 days)", lambda c: c["days_since"] < 7,
         "Transactional only", "Shipping + day 3 fit/care email", "None", "Let the order land."),
        ("service", "Refund, never came back", lambda c: c["refunded"] and not c["reordered_after_refund"] and c["lifetime_orders"] <= 2,
         "Gmail 1:1 from brand@ (CS)", "This week", "Free replacement pair in the right size, shipped with their next order",
         "Refunds are usually fit or feel. A personal fix turns a lost customer into a story."),
        ("vip_lapsed", "VIP gone quiet (3+ orders, 60+ days)", lambda c: c["lifetime_orders"] >= 3 and c["days_since"] >= 60,
         "Gmail 1:1 personal note (SUB only), then BFCM", "Nov 3–6, before the BFCM blasts",
         "+4 bonus pairs on any 12+ pack (cost ≈ $3.40), no % off",
         "Highest measured comeback rate of any lapsed group. They already trust the product; they need a nudge, not a discount."),
        ("vip_active", "VIP active (3+ orders, <60 days)", lambda c: c["lifetime_orders"] >= 3,
         "Omnisend", "At day 60 of their last order; gift email Dec 10",
         "Fresh Club invite: 90-day auto-ship, +2 pairs per shipment. No % off",
         "Lock in the profit engine. Discounts here only give margin away."),
        ("second_order", "Second-order window (1 order, day 7–27)", lambda c: c["lifetime_orders"] == 1 and c["days_since"] <= 27,
         "Omnisend flow (Wave A0)", "Day 10 after their order (rolling)",
         "+2 bonus pairs when they add a 6+ pack of the complementary style/color",
         "Half of all 2nd orders happen by day 16. This is the cheapest LTV you'll ever buy."),
        ("wave_a", "Wave A (1 order, day 28–45)", lambda c: c["lifetime_orders"] == 1 and c["days_since"] <= 45,
         "Omnisend (held draft)", "After Sy OK, week of Nov 3",
         "Club Starter ankle 6@$49 alone. No COMEBACK15, no bonus stack (locked)",
         "Locked working default."),
        ("household", "Household buyers (2+ sizes in one order)", lambda c: c["household"],
         "Omnisend", "Dec 10 gift send (ships by Dec 15)",
         "Family bundle: 18/24-pair pack split across two sizes, +2 bonus pairs",
         "They buy for more than one person, so the family pack is a real need, not an upsell."),
        ("bundle_clock", "Bundle buyers on the sock clock (13+ pairs, 60+ days)", lambda c: c["last_pairs"] >= 13 and c["days_since"] >= 60,
         "Omnisend", "Day 75–90 after the bundle; BFCM if inside that window",
         "Same pack, same size in one click, +4 bonus pairs or 90-day auto-ship",
         "13+ pair buyers come back later (median 34 days to 2nd vs 16). Time it to when the socks wear."),
        ("large_feet", "Large-feet customers (sock size 13–15), one order, 46–119 days", lambda c: c["size"] == "13-15" and c["lifetime_orders"] == 1 and c["days_since"] < 120,
         "Omnisend", "Nov 14 (World Diabetes Day)",
         "'Made for big feet': the complementary style in sock size 13–15, +2 bonus pairs, no % off",
         "Large-feet customers (sock size 13–15) reorder about twice as often. Few brands fit them; lean on that, not price."),
        ("ladder", "One order, 46–119 days", lambda c: c["lifetime_orders"] == 1 and c["days_since"] < 120,
         "Omnisend (Waves B / C60)", "Nov 14, then BFCM",
         "Complementary style + the color they don't own, +2 bonus pairs",
         "Measured 90-day reorder is still alive here; it drops to zero after day 120."),
        ("repeat_lapsed", "2 orders, 60+ days", lambda c: c["lifetime_orders"] == 2 and c["days_since"] >= 60,
         "Omnisend", "BFCM Nov 27",
         "Upgrade: their usual pack → 18-pair bundle at a per-pair price they can see",
         "They've proven they like it; bigger basket, same shipping cost."),
        ("dormant", "One order, 120+ days (C90)", lambda c: c["lifetime_orders"] == 1,
         "Omnisend (C90)", "Nov 10, one send; then BFCM",
         "COMEBACK15 once (ends ~Nov 26), the only % off in the plan",
         "0% came back on their own in the backtest. Cheapest list to try once, lowest priority."),
        ("other", "Everyone else", lambda c: True, "Omnisend", "BFCM Nov 27", "BFCM bundle offer", ""),
    ]


# Global marketing touches everybody subscribed is eligible for (date, name, priority: lower wins).
GLOBAL_TOUCHES = [("2026-11-27", "BFCM (single send, 'ends Monday')", 1),
                  ("2026-12-10", "Holiday gift send (order by Dec 15)", 2),
                  ("2026-11-14", "World Diabetes Day: foot-care story, no discount", 3)]
SEGMENT_TOUCHES = {
    "vip_lapsed": [("2026-11-04", "Personal note from brand@ (Gmail 1:1)", 0)],
    "vip_active": [("2026-12-10", "Holiday gift send (order by Dec 15)", 2)],
    "wave_a": [("2026-11-05", "Wave A 6@$49 ankle alone", 0)],
    "dormant": [("2026-11-10", "C90 win-back COMEBACK15 once", 0)],
    "large_feet": [("2026-11-14", "Made for big feet, sock size 13–15 (diabetes day)", 0)],
    "ladder": [("2026-11-14", "Style ladder + bonus pairs (diabetes day)", 0)],
    "household": [("2026-12-10", "Family bundle gift send", 0)],
}
NO_MARKETING = {"recent", "service"}


def schedule(seg: str, cap: int = C.MAX_MARKETING_EMAILS_PER_30D) -> dict:
    """Pick touches by priority so no 30-day window holds more than `cap` marketing emails."""
    if seg in NO_MARKETING:
        return {"sends": [], "dropped": [n for _, n, _ in GLOBAL_TOUCHES]}
    cands = {}
    for dt, name, pri in SEGMENT_TOUCHES.get(seg, []) + GLOBAL_TOUCHES:
        if dt not in cands or pri < cands[dt][1]:
            cands[dt] = (name, pri)
    chosen, dropped = [], []
    for dt, (name, pri) in sorted(cands.items(), key=lambda kv: kv[1][1]):
        trial = sorted(chosen + [date.fromisoformat(dt)])
        ok = all(sum(1 for x in trial if d0 <= x < d0 + timedelta(days=30)) <= cap for d0 in trial)
        if ok:
            chosen.append(date.fromisoformat(dt))
        else:
            dropped.append(name)
    sends = [{"date": d.isoformat(), "name": cands[d.isoformat()][0]} for d in sorted(chosen)]
    return {"sends": sends, "dropped": dropped}


def backtest(rows: list[dict], as_of: date, days: int = BACKTEST_DAYS) -> dict:
    """Measured reorder rate in the next `days` for customers who looked like each segment `days` ago."""
    t0 = as_of - timedelta(days=days)
    before = [r for r in rows if _d(r) < t0]
    after_by = defaultdict(list)
    for r in rows:
        if _d(r) >= t0:
            after_by[(r.get("customer_email") or r.get("customer_id") or "").strip().lower()].append(r)
    custs = customers(before, t0)
    after_orders = Counter()
    for r in rows:
        if _d(r) >= t0:
            after_orders[(r.get("customer_email") or r.get("customer_id") or "").strip().lower()] += 1
    for c in custs:  # lifetime at t0 = lifetime now minus orders after t0
        c["lifetime_orders"] = max(c["lifetime_orders"] - after_orders[c["id"]], 1)
    stats = defaultdict(lambda: [0, 0, 0.0])
    for c in custs:
        seg = assign(c, t0)
        a = after_by.get(c["id"], [])
        stats[seg][0] += 1
        stats[seg][1] += bool(a)
        stats[seg][2] += sum(_gross(r) for r in a)
    return {k: {"n": n, "reorder_rate": round(b / n, 3), "rev_per_customer_usd": round(v / n, 2)}
            for k, (n, b, v) in stats.items()}


def assign(c: dict, as_of: date) -> str:
    for key, _l, test, *_ in _segments(as_of):
        if test(c):
            return key
    return "other"


def recommend(c: dict, trans: dict) -> str:
    size = c["size"] or "their size"
    nxt = next((f for f, _n in trans.get(c["family"], []) if f not in c["families"]), None)
    if not nxt:
        nxt = "CF17180" if c["family"] != "CF17180" else "CF1004S"
    color = ("white" if c["colors"] == {"black"} else "black" if c["colors"] == {"white"} else None)
    base = f"{nxt} in sock size {size}" if c["size"] else nxt
    return base + (f", {color}" if color else "")


def build(rows: list[dict], as_of: date, consent: dict | None = None) -> tuple[dict, list[dict]]:
    """Returns (page summary, per-customer action rows kept local)."""
    trans = transitions(rows)
    bt = backtest(rows, as_of)
    segs = _segments(as_of)
    meta = {k: {"label": l, "channel": ch, "when": w, "incentive": inc, "why": why}
            for k, l, _t, ch, w, inc, why in segs}
    actions, agg = [], defaultdict(lambda: {"customers": 0, "spend_usd": 0.0, "products": Counter(), "sizes": Counter()})
    for c in customers(rows, as_of):
        seg = assign(c, as_of)
        prod = recommend(c, trans)
        state = (consent or {}).get(c["email"])
        actions.append({"email": c["email"], "first_name": c["first_name"], "segment": seg,
                        "lifetime_orders": c["lifetime_orders"], "days_since": c["days_since"],
                        "last_order": c["last_order"],
                        "spend_usd": c["spend_usd"], "size": c["size"], "product": prod,
                        "incentive": meta[seg]["incentive"], "channel": meta[seg]["channel"],
                        "send": "; ".join(f"{s['date']} {s['name']}" for s in schedule(seg)["sends"]),
                        "email_marketing_state": state or "UNKNOWN (join CoS profiles)"})
        a = agg[seg]
        a["customers"] += 1
        a["spend_usd"] += c["spend_usd"]
        a["products"][prod.split(",")[0]] += 1
        if c["size"]:
            a["sizes"][c["size"]] += 1
    order = [k for k, *_ in segs]
    summary = []
    for k in order:
        if k not in agg:
            continue
        a, b = agg[k], bt.get(k, {"n": 0, "reorder_rate": None, "rev_per_customer_usd": None})
        b = {**b, "small_sample": (b.get("n") or 0) < 20}
        summary.append({"key": k, **meta[k], "customers": a["customers"], "spend_usd": round(a["spend_usd"], 2),
                        "top_products": a["products"].most_common(3), "sizes": a["sizes"].most_common(3),
                        "baseline_90d": b, "schedule": schedule(k)})
    econ = {"cogs_per_pair_usd": C.COGS_PER_PAIR_USD,
            "pct15_on_87_usd": round(0.15 * 87, 2),
            "bonus_pairs_cost": {n: round(n * C.COGS_PER_PAIR_USD, 2) for n in (2, 4, 6)},
            "shipping_per_order_usd": C.SHIPPING_PER_ORDER_USD}
    vips = sorted((x for x in actions if x["segment"] in ("vip_lapsed", "vip_active")),
                  key=lambda x: (-x["lifetime_orders"], -x["spend_usd"]))[:12]
    top_vips = [{"name": (x["first_name"] or "—").split(" ")[0], "lifetime_orders": x["lifetime_orders"],
                 "days_since": x["days_since"], "spend_usd": x["spend_usd"], "size": x["size"],
                 "product": x["product"], "segment": x["segment"]} for x in vips]
    return {"segments": summary, "top_vips": top_vips, "transitions": {k: v for k, v in trans.items() if v and v[0][1] >= 3},
            "economics": econ, "backtest_days": BACKTEST_DAYS}, actions
