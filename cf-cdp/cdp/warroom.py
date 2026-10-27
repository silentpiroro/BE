"""War room seed: the scoreboard document (aggregates only, no PII) and the
starter action list. Both are written into the War Room artifact's db by Claude
(ArtifactData batch); the page reads them live and the team edits actions there.
"""

from __future__ import annotations

from datetime import date

from . import config as C
from . import magnet, playbook, pnl, sources


def scoreboard(orders_csv: str, as_of: date) -> dict:
    rows = magnet.load(orders_csv)
    metrics, _aud = magnet.analyze(rows, as_of)
    sim = magnet.simulate(metrics)
    ss = magnet.steady_state(metrics)
    pb, _actions = playbook.build(rows, as_of)
    rev, _q = sources.revenue_daily_from_order_summary_csv(orders_csv, as_of.isoformat())
    trend = pnl.monthly_trend(rev, as_of, months=6)
    mtd = trend[-1]
    l30 = metrics["last30"]
    return {
        "as_of": as_of.isoformat(),
        "source": "Shopify order export",
        "north_star_usd": C.NORTH_STAR_MONTHLY_SALES_USD,
        "mtd": {"month": mtd["month"], "sales_usd": mtd["gross_sales_usd"], "orders": mtd["orders_paid"],
                "days": mtd["days"]},
        "last30": {k: l30[k] for k in ("revenue_usd", "orders", "new_customers", "new_first_aov_usd",
                                        "repeat_orders", "repeat_aov_usd")},
        "actual_months": [{"month": t["month"], "sales_usd": t["gross_sales_usd"], "partial": t["partial"]}
                          for t in trend],
        "plan_months": [{"month": m["month"], "revenue_usd": m["revenue_usd"], "new_customers": m["new_customers"],
                         "repeat_orders": m["repeat_orders"], "media_usd": m["media_usd"], "over_band": m["over_band"],
                         "pairs": m["pairs"], "repeat_orders_needed_15pct": m["repeat_orders_needed_15pct"],
                         "net_usd": m["modeled_net_usd"], "net_margin": m["modeled_net_margin"]} for m in sim["months"]],
        "economics": {"cac_usd": C.CAC_USD, "cac_cut_usd": C.CAC_CUT_USD,
                      "first_order_profit_usd": ss["first_order_profit_usd"],
                      "repeat_profit_per_order_usd": ss["repeat_profit_per_order_usd"],
                      "repeat_per_customer_yr1_now": ss["today"]["repeat_orders_per_customer_yr1"],
                      "repeat_per_customer_yr1_needed": ss["repeat_orders_per_customer_needed_15pct"]},
        "hits_target": sim["hits_target"],
        "gates": {"cac_usd": C.CAC_USD, "cac_cut_usd": C.CAC_CUT_USD,
                  "target_first_aov_usd": magnet.ASSUMPTIONS["first_aov_usd"],
                  "first_aov_now_usd": l30["new_first_aov_usd"],
                  "second_order_month1_now": metrics["repeat_hazard_by_month"][0], "second_order_month1_goal": 0.15,
                  "media_band_max_usd": magnet.ASSUMPTIONS["media_band_max_usd"]},
        "segments": [{"key": s["key"], "label": s["label"], "customers": s["customers"], "when": s["when"],
                      "offer": s["incentive"], "reorder_90d": s["baseline_90d"].get("reorder_rate")}
                     for s in pb["segments"] if s["key"] not in ("other", "recent")],
    }


def _a(i, title, owner, due, lane, needs_sy=False, impact=None, note=""):
    return {"id": f"a{i:02d}", "title": title, "owner": owner, "due": due, "lane": lane,
            "needs_sy": needs_sy, "impact_usd": impact, "note": note, "order": i,
            "status": "todo", "sy_ok": False}


def actions(sb: dict) -> list[dict]:
    feb_pairs = next((m["pairs"] for m in sb["plan_months"] if m["month"] == "2027-02"), None)
    seg = {s["key"]: s["customers"] for s in sb["segments"]}
    return [
        _a(1, "Refund recovery: 1:1 email from brand@, free pair in the right size", "CF CS", "2026-10-31", "retention",
           note=f"{seg.get('service', 0)} customers. Tab 'Refund recovery' in the email workbook."),
        _a(2, f"Stock check on hero SKUs + place the PO that lands in February (~{feb_pairs:,} pairs that month)", "CoS", "2026-11-01", "ops",
           note="8 weeks factory + ~1 month ship. CF17180 family ≈ 70% of revenue."),
        _a(3, "Point every Meta ad set at the 18/24-pair bundle page; set the scale rule", "CF Meta Ads", "2026-11-01", "meta",
           note="+30%/week only while 7-day CAC (spend ÷ new customers) ≤ $70; hold $70–85; cut a step above $85."),
        _a(4, "Build the day 3 / 10 / 21 post-purchase flow and the Wave A0 draft", "CF Retention", "2026-11-01", "retention",
           note=f"A0 = 1 order, day 7–27 ({seg.get('second_order', 0)} people now)."),
        _a(5, "Preview the held Wave A draft (26 SUB)", "Sy", "2026-11-01", "approval", needs_sy=True),
        _a(6, "Send Wave A (Club Starter ankle 6@$49 alone) + A0", "CF Retention", "2026-11-05", "retention", needs_sy=True,
           note="No COMEBACK15 on Wave A."),
        _a(7, "Connect Meta data (Supermetrics Facebook Ads or Adspirer)", "CF Meta Ads", "2026-11-06", "meta",
           note="Until then, log yesterday's Meta numbers in the Meta log every morning."),
        _a(8, "Personal notes to VIPs gone quiet (+4 bonus pairs on a 12+ pack)", "Sy", "2026-11-04", "retention", needs_sy=True,
           note=f"{seg.get('vip_lapsed', 0)} customers, SUB only. Not the same week as any Omnisend send to them."),
        _a(9, "Send C90 win-back (COMEBACK15 once)", "CF Retention", "2026-11-10", "retention", needs_sy=True, impact=1371),
        _a(10, "World Diabetes Day email: foot-care story, no discount", "CF Retention", "2026-11-14", "retention", needs_sy=True),
        _a(11, "BFCM Meta creative: large feet (sock size 13–15), non-binding, 18/24-pair value", "CF Meta Ads", "2026-11-15", "meta"),
        _a(12, "Confirm BFCM hero stock; suppress anyone who ordered in the last 14 days", "CoS", "2026-11-20", "ops"),
        _a(13, "BFCM email draft (bundle-first, single send 'ends Monday')", "CF Retention", "2026-11-20", "retention", needs_sy=True),
        _a(14, "BFCM send to the subscribed list", "CF Retention", "2026-11-27", "retention", needs_sy=True, impact=8802),
        _a(15, "Next Meta budget step only if 7-day CAC held ≤ $70", "CF Meta Ads", "2026-11-28", "meta", needs_sy=True),
        _a(16, "Post-purchase flow live", "CF Retention", "2026-12-01", "retention"),
        _a(17, "November review: BFCM result, CAC, 30-day 2nd-order rate", "Sy", "2026-12-01", "approval", needs_sy=True),
        _a(18, "Holiday gift + family bundle send (ships by Dec 15)", "CF Retention", "2026-12-10", "retention", needs_sy=True),
        _a(19, "Replenish club test: 90-day auto-ship on the 18-pair pack", "CF Retention", "2027-01-15", "retention"),
    ]
