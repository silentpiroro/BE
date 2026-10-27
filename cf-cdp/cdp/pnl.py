"""Revenue & Profit model.

Actual inputs come from revenue_daily rows (Shopify). Everything after
contribution is MODELED: media is a scenario until meta_daily has live rows.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import config as C


def _d(s: str) -> date:
    return date.fromisoformat(s[:10])


def sum_period(rows: list[dict], start: date, end: date) -> dict:
    """Sum revenue_daily rows with start <= date <= end."""
    keys = [
        "orders_paid", "gross_sales_usd", "discounts_usd", "refunds_usd",
        "net_sales_usd", "pairs_sold", "new_customer_orders", "repeat_customer_orders",
    ]
    out = {k: 0.0 for k in keys}
    days_with_data = 0
    for r in rows:
        d = _d(r["date"])
        if start <= d <= end:
            days_with_data += 1
            for k in keys:
                out[k] += float(r.get(k) or 0)
    out["orders_paid"] = int(out["orders_paid"])
    out["pairs_sold"] = int(out["pairs_sold"])
    out["new_customer_orders"] = int(out["new_customer_orders"])
    out["repeat_customer_orders"] = int(out["repeat_customer_orders"])
    out["days"] = (end - start).days + 1
    out["days_with_data"] = days_with_data
    out["aov_usd"] = round(out["gross_sales_usd"] / out["orders_paid"], 2) if out["orders_paid"] else 0.0
    out["pairs_per_order"] = round(out["pairs_sold"] / out["orders_paid"], 2) if out["orders_paid"] else 0.0
    for k in ("gross_sales_usd", "discounts_usd", "refunds_usd", "net_sales_usd"):
        out[k] = round(out[k], 2)
    return out


def model_pnl(actual: dict, media_month_usd: float | None, media_label: str,
              live_media_usd: float | None = None) -> dict:
    """Modeled P&L for one period.

    live_media_usd: real Meta spend summed from meta_daily for the period.
    When given it replaces the scenario and the line is labeled ACTUAL.
    """
    month_frac = actual["days"] / C.DAYS_PER_MONTH
    gross = actual["gross_sales_usd"]
    disc_ref = actual["discounts_usd"] + actual["refunds_usd"]
    net_sales = gross - disc_ref
    cogs = actual["pairs_sold"] * C.COGS_PER_PAIR_USD
    ship = actual["orders_paid"] * C.SHIPPING_PER_ORDER_USD
    contribution = net_sales - cogs - ship
    if live_media_usd is not None:
        media, media_basis = live_media_usd, "ACTUAL (meta_daily)"
    else:
        media, media_basis = (media_month_usd or 0) * month_frac, f"ESTIMATE ({media_label})"
    salaries = C.FIXED_SALARIES_USD_MONTH * month_frac
    net = contribution - media - salaries
    margin = net / gross if gross else 0.0
    contribution_pct = contribution / gross if gross else 0.0
    # Monthly sales needed for 15% net at this contribution % and this fixed load.
    fixed_month = (media / month_frac if month_frac else 0) + C.FIXED_SALARIES_USD_MONTH
    headroom = contribution_pct - C.TARGET_NET_MARGIN
    breakeven_15 = round(fixed_month / headroom, 0) if headroom > 0 else None
    r = lambda x: round(x, 2)
    return {
        "lines": [
            {"key": "gross_sales", "label": "Gross sales", "usd": r(gross), "basis": "ACTUAL"},
            {"key": "discounts_refunds", "label": "Discounts + refunds", "usd": r(-disc_ref), "basis": "ACTUAL"},
            {"key": "net_sales", "label": "Net sales", "usd": r(net_sales), "basis": "ACTUAL", "subtotal": True},
            {"key": "cogs", "label": f"COGS ({actual['pairs_sold']:,} pairs × ${C.COGS_PER_PAIR_USD:.2f})", "usd": r(-cogs), "basis": "MODELED"},
            {"key": "shipping", "label": f"Shipping ({actual['orders_paid']:,} orders × ${C.SHIPPING_PER_ORDER_USD:.2f})", "usd": r(-ship), "basis": "MODELED"},
            {"key": "contribution", "label": "Contribution after product + ship", "usd": r(contribution), "basis": "MODELED", "subtotal": True},
            {"key": "media", "label": "Meta media", "usd": r(-media), "basis": media_basis},
            {"key": "salaries", "label": "Fixed salaries (2 staff)", "usd": r(-salaries), "basis": "MODELED"},
            {"key": "net", "label": "Modeled net", "usd": r(net), "basis": "MODELED", "subtotal": True, "total": True},
        ],
        "net_usd": r(net),
        "net_margin": round(margin, 4),
        "contribution_pct": round(contribution_pct, 4),
        "meets_target": margin >= C.TARGET_NET_MARGIN,
        "monthly_sales_for_15pct_net": breakeven_15,
    }


def build_periods(rows: list[dict], as_of: date) -> dict:
    mtd_start = as_of.replace(day=1)
    return {
        "mtd": (mtd_start, as_of, f"MTD ({mtd_start:%b} 1–{as_of.day})"),
        "30d": (as_of - timedelta(days=29), as_of, "Last 30 days"),
        "90d": (as_of - timedelta(days=89), as_of, "Last 90 days"),
    }


def monthly_trend(rows: list[dict], as_of: date, months: int = 6) -> list[dict]:
    out = []
    y, m = as_of.year, as_of.month
    keys = []
    for _ in range(months):
        keys.append((y, m))
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    for y, m in reversed(keys):
        start = date(y, m, 1)
        nxt = date(y + (m == 12), m % 12 + 1, 1)
        end = min(nxt - timedelta(days=1), as_of)
        s = sum_period(rows, start, end)
        out.append({
            "month": f"{y}-{m:02d}",
            "gross_sales_usd": s["gross_sales_usd"],
            "orders_paid": s["orders_paid"],
            "aov_usd": s["aov_usd"],
            "repeat_share": round(s["repeat_customer_orders"] / s["orders_paid"], 4) if s["orders_paid"] else 0,
            "partial": end < nxt - timedelta(days=1),
            "days": s["days"],
        })
    return out


def gap_to_north_star(actual_30d: dict) -> dict:
    run_rate = actual_30d["gross_sales_usd"] / actual_30d["days"] * C.DAYS_PER_MONTH
    gap = max(C.NORTH_STAR_MONTHLY_SALES_USD - run_rate, 0)
    aov = actual_30d["aov_usd"] or 1
    return {
        "run_rate_month_usd": round(run_rate, 2),
        "north_star_usd": C.NORTH_STAR_MONTHLY_SALES_USD,
        "gap_usd": round(gap, 2),
        "pct_of_north_star": round(run_rate / C.NORTH_STAR_MONTHLY_SALES_USD, 4),
        "orders_per_day_now": round(actual_30d["orders_paid"] / actual_30d["days"], 2),
        "orders_per_day_needed": round(C.NORTH_STAR_MONTHLY_SALES_USD / aov / C.DAYS_PER_MONTH, 1),
        "aov_usd": actual_30d["aov_usd"],
    }


def build_feed(revenue_daily: list[dict], meta_daily: list[dict], waves: dict,
               as_of: date, source: str) -> dict:
    """Assemble the dashboard feed (dashboard_feed.json)."""
    meta_live = len(meta_daily) > 0
    periods = {}
    for key, (start, end, label) in build_periods(revenue_daily, as_of).items():
        actual = sum_period(revenue_daily, start, end)
        live = None
        if meta_live:
            live = round(sum(float(m["spend_usd"]) for m in meta_daily
                             if start <= _d(m["date"]) <= end), 2)
        scenarios = {
            name: model_pnl(actual, usd, f"${usd/1000:g}k/mo scenario")
            for name, usd in C.MEDIA_SCENARIOS_USD_MONTH.items()
        }
        if meta_live:
            scenarios["live"] = model_pnl(actual, None, "live", live_media_usd=live)
        periods[key] = {"label": label, "start": start.isoformat(), "end": end.isoformat(),
                        "actual": actual, "pnl": scenarios}
    return {
        "feed": "revenue_profit",
        "as_of": as_of.isoformat(),
        "source": source,
        "shop": C.SHOP_DOMAIN,
        "meta_status": "live" if meta_live else "not_connected",
        "unit_economics": {
            "cogs_per_pair_usd": C.COGS_PER_PAIR_USD,
            "shipping_per_order_usd": C.SHIPPING_PER_ORDER_USD,
            "fixed_salaries_usd_month": C.FIXED_SALARIES_USD_MONTH,
            "media_scenarios_usd_month": C.MEDIA_SCENARIOS_USD_MONTH,
            "target_net_margin": C.TARGET_NET_MARGIN,
        },
        "periods": periods,
        "monthly_trend": monthly_trend(revenue_daily, as_of),
        "north_star": gap_to_north_star(periods["30d"]["actual"]),
        "waves": waves,
    }
