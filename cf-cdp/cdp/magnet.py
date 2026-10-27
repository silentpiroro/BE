"""Money Magnet: findings, ripe audiences, ranked opportunities and a month-by-month
path to the $100k/mo north star, computed from the one-row-per-order Shopify export.

Everything forward-looking is MODELED from the assumptions in ASSUMPTIONS. Meta CPR is
a gate we must hit, not a measured number, until live Meta data is connected.
"""

from __future__ import annotations

import csv
import statistics as st
from collections import Counter, defaultdict
from datetime import date, datetime

from . import config as C
from .sources import pairs_per_unit_from_sku

ASSUMPTIONS = {
    "target_cpr_usd": 25.0,          # gate: $90 AOV / $25 CPR = 3.6x first-order ROAS (floor 3.5x)
    "cpr_sensitivity_usd": [25.0, 30.0, 35.0],
    "first_aov_usd": 90.0,           # bundle-first hold (new customers last 30d: ~$88)
    "repeat_aov_usd": 70.0,          # between 10-mo average and last-30d repeat AOV
    "new_growth_per_month": 0.35,    # max month-on-month growth in new customers (Meta learning + stock)
    "organic_share_of_new": 0.35,    # new customers not from Meta (from order tags, last 30d)
    "retention_uplift": 1.5,         # day 7-30 second-order flow + replenish clock, live from Dec
    "retention_uplift_from": "2026-12",
    "media_band_max_usd": 8000.0,    # staged band; above this needs Sy OK on proven gates
    "bfcm_sub_list": 3912, "bfcm_conv": 0.03, "bfcm_aov_usd": 75.0,
    "winback_sub_list": 997, "winback_conv": 0.025, "winback_aov_usd": 55.0,
    "lead_time_months": 3,           # ~8 weeks factory + ~1 month ship
    "plan_start": "2026-11", "plan_months": 14,
}


def _d(r):
    return datetime.fromisoformat(r["processed_at_utc"].replace("Z", "+00:00")).date()


def _gross(r):
    return float(r["subtotal_original"] or 0) + float(r["total_discounts_original"] or 0)


def _pairs(r):
    ps = [pairs_per_unit_from_sku(s) or 1 for s in (r.get("skus") or "").split(";") if s.strip()]
    return float(r.get("total_quantity") or 0) * (sum(ps) / len(ps) if ps else 1)


def _src(tags: str) -> str:
    t = (tags or "").lower()
    if "facebook" in t or "meta" in t:
        return "meta"
    if "google" in t or "adwords" in t:
        return "google"
    if "omnisend" in t or "shopify_email" in t:
        return "email"
    return "untagged"


def _band(days: int) -> str:
    return ("d0-6" if days < 7 else "d7-27" if days < 28 else "d28-45" if days <= 45 else
            "d46-59" if days <= 59 else "d60-89" if days <= 89 else "d90+")


def load(path):
    with open(path, newline="", encoding="utf-8-sig") as fh:
        return [r for r in csv.DictReader(fh) if not r.get("cancelled_at")]


def analyze(rows: list[dict], as_of: date) -> tuple[dict, dict]:
    """Returns (metrics for the page, audiences {segment: [emails]} kept local)."""
    by = defaultdict(list)
    for r in rows:
        by[(r.get("customer_email") or r.get("customer_id") or "").strip().lower()].append(r)
    for v in by.values():
        v.sort(key=_d)
    life = {c: int(float(v[-1].get("customer_lifetime_orders") or len(v))) for c, v in by.items()}
    new_ids = [c for c, v in by.items() if life[c] - len(v) <= 0]

    # Repeat hazard by month since first order (new-in-window customers only).
    exposed, events, gaps = Counter(), Counter(), []
    for c in new_ids:
        v = by[c]
        f = _d(v[0])
        for k in range((as_of - f).days // 30 + 1):
            exposed[k] += 1
        for r in v[1:]:
            events[(_d(r) - f).days // 30] += 1
        if len(v) > 1:
            gaps.append((_d(v[1]) - f).days)
    hazard = []
    for k in range(12):
        if exposed[k] >= 50:
            hazard.append(round(events[k] / exposed[k], 4))
        else:
            hazard.append(hazard[-1] if hazard else 0.0)
    q = st.quantiles(gaps, n=4) if len(gaps) >= 4 else [None, None, None]

    # Repeat by acquisition source and first-order size (cohorts at least 60 days old).
    cutoff = date.fromordinal(as_of.toordinal() - 60)
    src, size = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    for c in new_ids:
        v = by[c]
        if _d(v[0]) > cutoff:
            continue
        s = _src(v[0].get("tags"))
        src[s][0] += 1; src[s][1] += len(v) > 1
        p = _pairs(v[0])
        b = "1-3 pairs" if p <= 3 else "4-6 pairs" if p <= 6 else "7-12 pairs" if p <= 12 else "13+ pairs"
        size[b][0] += 1; size[b][1] += len(v) > 1

    last30 = [r for r in rows if (as_of - _d(r)).days < 30]
    rev30 = Counter()
    for r in last30:
        rev30[_src(r.get("tags"))] += _gross(r)
    new30 = [by[c][0] for c in new_ids if (as_of - _d(by[c][0])).days < 30]
    rep30 = [r for v in by.values() for r in v[1:] if (as_of - _d(r)).days < 30]

    month_mix = []
    for m in sorted({_d(r).strftime("%Y-%m") for r in rows})[-4:]:
        mm = [r for r in rows if _d(r).strftime("%Y-%m") == m]
        big = [r for r in mm if _pairs(r) > 12]
        tot = sum(_gross(r) for r in mm) or 1
        month_mix.append({"month": m, "orders": len(mm), "aov_usd": round(tot / len(mm), 2),
                          "pairs_per_order": round(sum(_pairs(r) for r in mm) / len(mm), 1),
                          "bundle13_rev_share": round(sum(_gross(r) for r in big) / tot, 3)})

    sizes = Counter()
    for r in rows:
        for s in (r.get("skus") or "").split(";"):
            s = s.strip()
            if "13-15" in s or "1315" in s:
                sizes["13-15"] += 1
            elif "10-13" in s or "1013" in s:
                sizes["10-13"] += 1
            elif "9-11" in s or "911" in s:
                sizes["9-11"] += 1

    # Ripe audiences (emails stay local; page gets counts and $).
    aud, ripe = defaultdict(list), defaultdict(lambda: {"customers": 0, "spent_usd": 0.0})
    for c, v in by.items():
        email = (v[-1].get("customer_email") or "").strip().lower()
        if not email:
            continue
        seg = ("1 order" if life[c] == 1 else "2+ orders") + " · " + _band((as_of - _d(v[-1])).days)
        aud[seg].append(email)
        ripe[seg]["customers"] += 1
        ripe[seg]["spent_usd"] += sum(_gross(r) for r in v)
    bundle_buyers = [(by[c][-1].get("customer_email") or "").lower() for c in by
                     if any(_pairs(r) > 12 for r in by[c])]
    aud["bundle buyers (13+ pairs ever)"] = [e for e in bundle_buyers if e]

    disc = [r for r in rows if float(r["total_discounts_original"] or 0) > 0]
    metrics = {
        "as_of": as_of.isoformat(),
        "customers": len(by), "orders": len(rows),
        "new_customers_in_window": len(new_ids),
        "lifetime_orders_dist": dict(sorted(Counter(min(n, 5) for n in life.values()).items())),
        "gap_to_2nd_days": {"n": len(gaps), "p25": q[0], "median": q[1], "p75": q[2],
                            "share_by_day30": round(sum(g <= 30 for g in gaps) / len(gaps), 3) if gaps else None},
        "repeat_hazard_by_month": hazard,
        "repeat_by_source": {k: {"n": a, "repeat_rate": round(b / a, 3)} for k, (a, b) in src.items() if a >= 8},
        "repeat_by_first_order_size": {k: {"n": a, "repeat_rate": round(b / a, 3)} for k, (a, b) in sorted(size.items())},
        "last30": {
            "orders": len(last30), "revenue_usd": round(sum(_gross(r) for r in last30), 2),
            "new_customers": len(new30), "new_first_aov_usd": round(st.mean(_gross(r) for r in new30), 2) if new30 else 0,
            "repeat_orders": len(rep30), "repeat_aov_usd": round(st.mean(_gross(r) for r in rep30), 2) if rep30 else 0,
            "revenue_by_source_usd": {k: round(v, 2) for k, v in rev30.most_common()},
        },
        "month_mix": month_mix,
        "size_line_share": {k: round(v / sum(sizes.values()), 3) for k, v in sizes.items()},
        "discounted_order_share": round(len(disc) / len(rows), 3),
        "avg_discount_pct": round(st.mean(float(r["total_discounts_original"]) / _gross(r) for r in disc), 3) if disc else 0,
        "subscription_orders": sum("subscription" in (r.get("source_name") or "") for r in rows),
        "ripe": {k: {"customers": v["customers"], "spent_usd": round(v["spent_usd"], 2)} for k, v in sorted(ripe.items())},
        "pairs_per_order_recent": month_mix[-1]["pairs_per_order"] if month_mix else 6,
        "existing_cohorts": Counter(((as_of - _d(by[c][0])).days // 30) for c in new_ids),
    }
    metrics["existing_cohorts"] = {str(k): v for k, v in sorted(metrics["existing_cohorts"].items())}
    return metrics, dict(aud)


def _months(start: str, n: int) -> list[str]:
    y, m = map(int, start.split("-"))
    out = []
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def simulate(metrics: dict, a: dict = ASSUMPTIONS) -> dict:
    """Month-by-month path. New customers grow at most new_growth_per_month until the
    revenue target is reached; repeat orders come from every cohort via the measured hazard."""
    hazard = metrics["repeat_hazard_by_month"]
    months = _months(a["plan_start"], a["plan_months"])
    cohorts = {-int(k) - 1: v for k, v in metrics["existing_cohorts"].items()}  # month index -> customers
    new_prev = metrics["last30"]["new_customers"]
    pairs_po = metrics["pairs_per_order_recent"]
    cost_per_order = pairs_po * C.COGS_PER_PAIR_USD + C.SHIPPING_PER_ORDER_USD
    # Buyers from before the export window also reorder; hold their observed rate flat.
    modeled_last30 = sum(n * hazard[min(-j - 1, len(hazard) - 1)] for j, n in cohorts.items())
    base_repeat = max(metrics["last30"]["repeat_orders"] - modeled_last30, 0)
    rows, hit = [], None
    for i, m in enumerate(months):
        uplift = a["retention_uplift"] if m >= a["retention_uplift_from"] else 1.0
        # A cohort acquired in month j reorders in month i at hazard[i - j]; month 0 = its own month.
        repeat = (sum(n * hazard[min(i - j, len(hazard) - 1)] for j, n in cohorts.items()) + base_repeat) * uplift
        repeat_rev = repeat * a["repeat_aov_usd"]
        events, ev_rev = [], 0.0
        if m == "2026-11":
            for name, lst, conv, aov in (("BFCM email to SUB list", a["bfcm_sub_list"], a["bfcm_conv"], a["bfcm_aov_usd"]),
                                         ("C90 win-back (COMEBACK15 once)", a["winback_sub_list"], a["winback_conv"], a["winback_aov_usd"])):
                o = lst * conv
                events.append({"name": name, "orders": round(o), "revenue_usd": round(o * aov)})
                ev_rev += o * aov
        # New customers needed to hit target this month, capped by growth rate.
        need_rev = max(C.NORTH_STAR_MONTHLY_SALES_USD - repeat_rev - ev_rev, 0)
        need_new = need_rev / (a["first_aov_usd"] + hazard[0] * uplift * a["repeat_aov_usd"])
        new = min(new_prev * (1 + a["new_growth_per_month"]), need_new) if hit is None else need_new
        new = max(new, new_prev if hit is None else 0)
        meta_new = new * (1 - a["organic_share_of_new"])
        media = {f"cpr_{int(c)}": round(meta_new * c) for c in a["cpr_sensitivity_usd"]}
        media_base = meta_new * a["target_cpr_usd"]
        revenue = new * a["first_aov_usd"] + repeat_rev + ev_rev
        orders = new + repeat + sum(e["orders"] for e in events)
        contribution = revenue - orders * cost_per_order
        net = contribution - media_base - C.FIXED_SALARIES_USD_MONTH
        rows.append({
            "month": m, "new_customers": round(new), "meta_new_customers": round(meta_new),
            "repeat_orders": round(repeat), "event_orders": sum(e["orders"] for e in events),
            "revenue_new_usd": round(new * a["first_aov_usd"]), "revenue_repeat_usd": round(repeat_rev),
            "revenue_events_usd": round(ev_rev), "revenue_usd": round(revenue), "orders": round(orders),
            "pairs": round(orders * pairs_po), "media_usd": round(media_base), "media_sensitivity_usd": media,
            "over_band": media_base > a["media_band_max_usd"], "modeled_net_usd": round(net),
            "modeled_net_margin": round(net / revenue, 3) if revenue else 0, "events": events,
        })
        repeat_own = new * hazard[0] * uplift   # same-month 2nd orders from this month's new customers
        rows[-1]["repeat_orders"] = round(repeat + repeat_own)
        rows[-1]["revenue_repeat_usd"] = round(repeat_rev + repeat_own * a["repeat_aov_usd"])
        rows[-1]["revenue_usd"] = round(revenue + repeat_own * a["repeat_aov_usd"])
        rows[-1]["orders"] = round(orders + repeat_own)
        rows[-1]["pairs"] = round((orders + repeat_own) * pairs_po)
        net = net + repeat_own * (a["repeat_aov_usd"] - cost_per_order)
        rows[-1]["modeled_net_usd"] = round(net)
        rows[-1]["modeled_net_margin"] = round(net / rows[-1]["revenue_usd"], 3)
        if hit is None and rows[-1]["revenue_usd"] >= C.NORTH_STAR_MONTHLY_SALES_USD * 0.995:
            hit = m
        cohorts[i] = new
        new_prev = new
    # Inventory: pairs must be ordered lead_time months before the month they sell.
    for i, r in enumerate(rows):
        r["po_month"] = months[i - a["lead_time_months"]] if i >= a["lead_time_months"] else "now (late)"
    return {"months": rows, "hits_target": hit, "assumptions": a, "base_repeat_orders": round(base_repeat, 1),
            "first_order_roas_at_target_cpr": round(a["first_aov_usd"] / a["target_cpr_usd"], 2),
            "cost_per_order_usd": round(cost_per_order, 2)}


def steady_state(metrics: dict, a: dict = ASSUMPTIONS) -> dict:
    """New customers / month needed for $100k, with and without the retention program."""
    h = metrics["repeat_hazard_by_month"]
    out = {}
    for label, up in (("today", 1.0), ("with_retention", a["retention_uplift"])):
        repeats_per_customer = sum(h[1:12]) * up + h[0] * up  # first-year repeat orders per new customer
        per_new = a["first_aov_usd"] + repeats_per_customer * a["repeat_aov_usd"]
        n = C.NORTH_STAR_MONTHLY_SALES_USD / per_new
        out[label] = {"repeat_orders_per_customer_yr1": round(repeats_per_customer, 3),
                      "revenue_per_new_customer_usd": round(per_new, 2),
                      "new_customers_per_month": round(n),
                      "media_at_target_cpr_usd": round(n * (1 - a["organic_share_of_new"]) * a["target_cpr_usd"])}
    return out


def opportunities(metrics: dict, sim: dict, ss: dict) -> list[dict]:
    m = metrics
    l30 = m["last30"]
    ripe = m["ripe"]
    g = m["gap_to_2nd_days"]
    early = ripe.get("1 order · d7-27", {}).get("customers", 0) + ripe.get("1 order · d0-6", {}).get("customers", 0)
    nov = sim["months"][0]
    bfcm = next((e for e in nov["events"] if e["name"].startswith("BFCM")), {"orders": 0, "revenue_usd": 0})
    wb = next((e for e in nov["events"] if "win-back" in e["name"]), {"orders": 0, "revenue_usd": 0})
    src = m["repeat_by_source"]
    meta_r = src.get("meta", {}).get("repeat_rate", 0)
    other_r = src.get("untagged", {}).get("repeat_rate", 0)
    mix = m["month_mix"][-1] if m["month_mix"] else {}
    retention_gain = ss["today"]["new_customers_per_month"] - ss["with_retention"]["new_customers_per_month"]
    return [
        {
            "rank": 1, "name": "BFCM to the subscribed list", "owner": "CF Retention → Sy OK",
            "impact": f"≈${bfcm['revenue_usd']:,} one-time (Nov 27–30)", "impact_usd": bfcm["revenue_usd"],
            "confidence": "Medium", "when": "Draft by Nov 13, Sy OK by Nov 20, send Nov 27",
            "why": (f"{ASSUMPTIONS['bfcm_sub_list']:,} subscribed profiles; the biggest cash event left in 2026. "
                    f"Modeled at {ASSUMPTIONS['bfcm_conv']:.0%} conversion × ${ASSUMPTIONS['bfcm_aov_usd']:.0f}."),
            "steps": [
                "Offer = bundle-first: 18-pair and 24-pair packs as the hero, 6@$49 as the entry. No stacking with COMEBACK15.",
                "One send on Nov 27 that says 'ends Monday' (no separate Cyber Monday email): with Nov 14 and Dec 10 that keeps everyone at 3 marketing emails / 30 days.",
                "Exclude anyone emailed from Gmail that week and anyone who ordered in the last 14 days.",
                "Omnisend draft → Sy preview/OK → schedule. CoS confirms stock on hero SKUs by Nov 20.",
            ],
        },
        {
            "rank": 2, "name": "Second-order window: day 7–30, not day 28–45", "owner": "CF Retention → Sy OK",
            "impact": f"Repeat orders ×{ASSUMPTIONS['retention_uplift']} → {retention_gain} fewer new customers needed per month at $100k",
            "impact_usd": None, "confidence": "High on timing, medium on lift",
            "when": "Flow live by Dec 1",
            "why": (f"Median time to a 2nd order is {g['median']:.0f} days and {g['share_by_day30']:.0%} happen by day 30 "
                    f"(n={g['n']}). Month 1 reorder rate is {m['repeat_hazard_by_month'][0]:.0%}, then ~2%/month. "
                    f"Wave A (day 28–45) starts after most 2nd orders have already happened."),
            "steps": [
                "Omnisend post-purchase flow: day 3 fit/size check, day 10 'add a second color or size' (6@$49), day 21 'your next week of socks' bundle upgrade.",
                f"Keep Wave A as is; add Wave A0 = 1 order, day 7–27. {early} customers sit there today.",
                "Counts against the 3 / 30-day cap; transactional emails do not.",
                "Measure: 30-day 2nd-order rate per weekly cohort on this page. Goal 10% → 15%.",
            ],
        },
        {
            "rank": 3, "name": "Bundle-first Meta offer (makes the ROAS floor reachable)", "owner": "CF Meta Ads",
            "impact": f"First-order AOV ${l30['new_first_aov_usd']:.0f} (was ~$36 median) → ROAS {sim['first_order_roas_at_target_cpr']}× at ${ASSUMPTIONS['target_cpr_usd']:.0f} CPR",
            "impact_usd": None, "confidence": "High (already in the data)", "when": "Now; keep through Q1",
            "why": (f"13+ pair orders went from 10% to {mix.get('bundle13_rev_share', 0):.0%} of revenue in {mix.get('month', '')}. "
                    f"At a $36 first order no CPR passes 3.5× ROAS; at $90 you need CPR ≤ ${90/3.5:.0f}."),
            "steps": [
                "Every Meta ad lands on the 18/24-pair bundle page with 6-pack as the downsell, not the reverse.",
                "Creative angle: large feet (sock size 13–15) and non-binding for diabetic / swollen feet (size 13–15 is ~1 in 3 SKU lines).",
                "Scale rule: +30% budget per week only while 7-day CPR ≤ $25 and purchase ROAS ≥ 3.5×; else hold.",
                "Connect Adspirer so this page reads real CPR instead of the target.",
            ],
        },
        {
            "rank": 4, "name": "Scale Meta past the $8k band on proven gates", "owner": "CF Meta Ads → Sy OK",
            "impact": f"$100k needs ~{ss['with_retention']['new_customers_per_month']} new customers/month vs {l30['new_customers']} now",
            "impact_usd": None, "confidence": "Depends on CPR holding at scale",
            "when": f"Decision point when the band is full (modeled {next((r['month'] for r in sim['months'] if r['over_band']), 'n/a')})",
            "why": (f"Retention alone can't reach $100k: a new customer is worth ~${ss['with_retention']['revenue_per_new_customer_usd']:.0f} "
                    f"in year 1. Meta-acquired customers reorder {meta_r:.0%} vs {other_r:.0%} for untagged, so Meta buyers are the better base."),
            "steps": [
                f"Media at $100k ≈ ${ss['with_retention']['media_at_target_cpr_usd']:,}/mo at $25 CPR. Each step above $8k/mo needs Sy's OK with the last 14 days of CPR/ROAS.",
                "First order must pay its own CAC: $90 AOV − ~$17 product+ship = $73 contribution > $25 CPR.",
                "Stop rule: two weeks above $35 CPR → drop back one budget step.",
            ],
        },
        {
            "rank": 5, "name": "Stock for the ramp (3-month lead time)", "owner": "CoS + Inventory",
            "impact": "Avoids stock-outs that would cap growth", "impact_usd": None, "confidence": "High",
            "when": "PO this week for February",
            "why": "Factory ~8 weeks + ~1 month shipping. What sells in February has to be ordered now.",
            "steps": [
                "Use the pairs-per-month row in the path table as the demand plan; hero SKUs first (CF17180 family ≈ 70% of 60-day revenue).",
                "Wool CF22032 stays on HOLD for Wave C until available > 0; reorder only if merino tests well.",
                "CoS checks Shopify available vs warehouse counts (store SKUs ≠ warehouse 1:1).",
            ],
        },
        {
            "rank": 6, "name": "C90 win-back with COMEBACK15", "owner": "CF Retention → Sy OK",
            "impact": f"≈${wb['revenue_usd']:,} one-time", "impact_usd": wb["revenue_usd"], "confidence": "Medium-low",
            "when": "One send on Nov 10 (code ends ~Nov 26); not to Wave A",
            "why": f"997 SUB-eligible C90 members; {ripe.get('1 order · d90+', {}).get('customers', 0)} one-order buyers in this export went quiet 90+ days ago.",
            "steps": ["Single send, 15% once, ends ~Nov 26.", "Nov 10 keeps it inside the 3-emails-per-30-days cap with Nov 14 and Nov 27."],
        },
        {
            "rank": 7, "name": "Replenish club for bundle buyers", "owner": "CF Retention + Product",
            "impact": "Turns 13+ pair buyers into predictable revenue", "impact_usd": None, "confidence": "Low (new)",
            "when": "Test in January",
            "why": (f"Only {m['subscription_orders']} subscription orders in 10 months. 13+ pair first orders reorder at "
                    f"{m['repeat_by_first_order_size'].get('13+ pairs', {}).get('repeat_rate', 0):.0%} so far (they're stocked up); they need a 90–120 day clock, not day 30."),
            "steps": ["Offer auto-ship every 90 days on the 18-pair pack at a small saving.",
                      "Email at day 75 to bundle buyers: 'your socks are ~3 months old'."],
        },
    ]


def build_feed(path: str, as_of: date) -> tuple[dict, dict]:
    rows = load(path)
    metrics, aud = analyze(rows, as_of)
    sim = simulate(metrics)
    ss = steady_state(metrics)
    from . import playbook
    pb, actions = playbook.build(rows, as_of)
    aud["_actions"] = actions
    feed = {"feed": "money_magnet", "playbook": pb, "as_of": as_of.isoformat(), "source": "shopify_order_export",
            "metrics": metrics, "path": sim, "steady_state": ss,
            "opportunities": opportunities(metrics, sim, ss)}
    return feed, aud
