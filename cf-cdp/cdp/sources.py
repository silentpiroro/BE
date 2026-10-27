"""Offline source adapters.

- Shopify orders CSV export (Admin > Orders > Export) -> revenue_daily rows
- Meta Ads Manager CSV dump (daily breakdown)       -> meta_daily rows

Live connectors (Shopify Admin MCP run by CoS, Adspirer Meta) produce the same
row shapes; see docs/JOBS.md.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict

PAID_STATUSES = {"paid", "partially_refunded", "refunded", "partially_paid"}
_PAIRS_RE = re.compile(r"(\d+)\s*(?:-|\s)?\s*(?:pairs?|pack|pk)\b", re.I)


def pairs_in_title(title: str, pairs_by_sku: dict | None = None, sku: str = "") -> int:
    """Pairs per unit. Prefer an explicit SKU map; Store SKUs are not warehouse 1:1."""
    if pairs_by_sku and sku in pairs_by_sku:
        return int(pairs_by_sku[sku])
    m = _PAIRS_RE.search(title or "")
    return int(m.group(1)) if m else 1


def _f(v) -> float:
    try:
        return float(str(v).replace("$", "").replace(",", "") or 0)
    except ValueError:
        return 0.0


def revenue_daily_from_shopify_csv(path: str, pairs_by_sku: dict | None = None,
                                   as_of: str = "") -> list[dict]:
    orders: dict[str, dict] = {}
    with open(path, newline="", encoding="utf-8-sig") as fh:
        for row in csv.DictReader(fh):
            name = row.get("Name")
            if not name:
                continue
            o = orders.get(name)
            if o is None and row.get("Financial Status"):
                o = orders[name] = {
                    "email": (row.get("Email") or "").strip().lower(),
                    "status": row["Financial Status"].strip().lower(),
                    "paid_at": (row.get("Paid at") or row.get("Created at") or "")[:10],
                    "subtotal": _f(row.get("Subtotal")),
                    "discount": _f(row.get("Discount Amount")),
                    "refunded": _f(row.get("Refunded Amount")),
                    "pairs": 0,
                }
            if o is not None:
                qty = int(_f(row.get("Lineitem quantity")))
                o["pairs"] += qty * pairs_in_title(row.get("Lineitem name", ""), pairs_by_sku,
                                                   row.get("Lineitem sku", ""))
    seen_emails: set[str] = set()
    days: dict[str, dict] = defaultdict(lambda: {
        "orders_paid": 0, "gross_sales_usd": 0.0, "discounts_usd": 0.0, "refunds_usd": 0.0,
        "net_sales_usd": 0.0, "pairs_sold": 0, "new_customer_orders": 0, "repeat_customer_orders": 0})
    for o in sorted(orders.values(), key=lambda x: x["paid_at"]):
        if o["status"] not in PAID_STATUSES or not o["paid_at"]:
            continue
        d = days[o["paid_at"]]
        d["orders_paid"] += 1
        d["gross_sales_usd"] += o["subtotal"] + o["discount"]
        d["discounts_usd"] += o["discount"]
        d["refunds_usd"] += o["refunded"]
        d["net_sales_usd"] += o["subtotal"] - o["refunded"]
        d["pairs_sold"] += o["pairs"]
        # New vs repeat is only as good as the export's date range.
        if o["email"] and o["email"] in seen_emails:
            d["repeat_customer_orders"] += 1
        else:
            d["new_customer_orders"] += 1
        seen_emails.add(o["email"])
    out = []
    for day in sorted(days):
        r = {"date": day, **days[day], "source": "shopify_orders_csv", "as_of": as_of}
        for k in ("gross_sales_usd", "discounts_usd", "refunds_usd", "net_sales_usd"):
            r[k] = round(r[k], 2)
        out.append(r)
    return out


# Ads Manager column names vary by export settings; first match wins.
META_COLS = {
    "date": ["Day", "Reporting starts", "Date"],
    "campaign_name": ["Campaign name", "Campaign Name"],
    "adset_name": ["Ad set name", "Ad Set Name"],
    "spend_usd": ["Amount spent (USD)", "Amount spent", "Spend"],
    "impressions": ["Impressions"],
    "clicks": ["Link clicks", "Clicks (all)", "Clicks"],
    "purchases": ["Purchases", "Website purchases"],
    "purchase_value_usd": ["Purchases conversion value", "Website purchases conversion value",
                           "Purchase conversion value"],
}


def meta_daily_from_ads_manager_csv(path: str, as_of: str = "") -> list[dict]:
    out = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        cols = {k: next((c for c in opts if c in (reader.fieldnames or [])), None)
                for k, opts in META_COLS.items()}
        if not cols["date"] or not cols["spend_usd"]:
            raise ValueError("Meta dump needs a daily breakdown (Day) and Amount spent column")
        for row in reader:
            g = lambda k: row.get(cols[k]) if cols[k] else None
            spend = _f(g("spend_usd"))
            purchases = int(_f(g("purchases")))
            value = _f(g("purchase_value_usd"))
            out.append({
                "date": (g("date") or "")[:10],
                "campaign_name": g("campaign_name") or "",
                "adset_name": g("adset_name") or "",
                "spend_usd": round(spend, 2),
                "impressions": int(_f(g("impressions"))),
                "clicks": int(_f(g("clicks"))),
                "purchases": purchases,
                "purchase_value_usd": round(value, 2),
                "cpr_usd": round(spend / purchases, 2) if purchases else None,
                "purchase_roas": round(value / spend, 2) if spend else None,
                "source": "ads_manager_dump",
                "as_of": as_of,
            })
    return out
