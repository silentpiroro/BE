"""Seed data for the Comfort Fresh CDP app (artifact db).

- cust/c00..c15: customers with their order history, sharded by email hash. The app
  computes LTV, segments, revenue and P&L from these in the browser, and merges new
  uploads into the same shards.
- board/magnet: the modeled path to $100k, ranked moves, findings and the measured
  90-day reorder rates per segment (aggregates only).

Customer shards contain emails and names (PII): they live only in the artifact's
private database, never in git.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from datetime import date

from . import magnet, playbook
from .sources import _local_date, pairs_per_unit_from_sku

SHARDS = 16


def shard_of(email: str) -> str:
    h = int(hashlib.sha1(email.encode()).hexdigest(), 16) % SHARDS
    return f"c{h:02d}"


def _src(tags: str) -> str:
    t = (tags or "").lower()
    if "facebook" in t or "meta" in t or re.search(r"\big\b", t):
        return "meta"
    if "google" in t or "adwords" in t:
        return "google"
    if "omnisend" in t or "shopify_email" in t:
        return "email"
    return ""


def _f(v):
    try:
        return float(v or 0)
    except ValueError:
        return 0.0


def customer_shards(rows: list[dict]) -> dict[str, list[dict]]:
    """rows: one-row-per-order export (cancelled orders already excluded)."""
    by = defaultdict(list)
    for r in rows:
        email = (r.get("customer_email") or "").strip().lower()
        if email:
            by[email].append(r)
    shards: dict[str, list[dict]] = defaultdict(list)
    for email, v in by.items():
        v.sort(key=lambda r: r["processed_at_utc"])
        life = int(_f(v[-1].get("customer_lifetime_orders")) or len(v))
        orders = []
        for i, r in enumerate(v):
            skus = [s.strip() for s in (r.get("skus") or "").split(";") if s.strip()]
            packs = [pairs_per_unit_from_sku(s) or 1 for s in skus]
            units = int(_f(r.get("total_quantity")))
            pairs = round(units * (sum(packs) / len(packs) if packs else 1))
            seq = max(life - (len(v) - 1 - i), i + 1)
            orders.append({
                "id": str(r.get("order_id")), "n": r.get("order_name"),
                "d": _local_date(r["processed_at_utc"], "America/Chicago"),
                "g": round(_f(r["subtotal_original"]) + _f(r["total_discounts_original"]), 2),
                "disc": round(_f(r["total_discounts_original"]), 2),
                "ref": round(min(_f(r.get("total_refunded")), _f(r["subtotal_original"])), 2),
                "p": pairs, "u": units, "s": skus[:6], "src": _src(r.get("tags")),
                "seq": seq,
            })
        shards[shard_of(email)].append({
            "e": email, "fn": v[-1].get("customer_first_name") or "", "ln": v[-1].get("customer_last_name") or "",
            "cid": str(v[-1].get("customer_id") or ""), "lo": life, "o": orders,
        })
    return {k: sorted(v, key=lambda c: c["e"]) for k, v in sorted(shards.items())}


def magnet_doc(orders_csv: str, as_of: date) -> dict:
    feed, _aud = magnet.build_feed(orders_csv, as_of)
    m = feed["metrics"]
    pb = feed["playbook"]
    return {
        "as_of": feed["as_of"],
        "path": feed["path"],
        "steady_state": feed["steady_state"],
        "opportunities": feed["opportunities"],
        "findings": {k: m[k] for k in ("gap_to_2nd_days", "repeat_hazard_by_month", "repeat_by_source",
                                       "repeat_by_first_order_size", "month_mix", "size_line_share",
                                       "discounted_order_share", "avg_discount_pct", "subscription_orders", "last30")},
        "segment_baselines": {s["key"]: s["baseline_90d"] for s in pb["segments"]},
        "segment_meta": {s["key"]: {"label": s["label"], "when": s["when"], "offer": s["incentive"],
                                    "channel": s["channel"], "why": s["why"], "schedule": s["schedule"]}
                         for s in pb["segments"]},
        "transitions": pb["transitions"],
        "economics": pb["economics"],
    }


def build(orders_csv: str, as_of: date) -> tuple[dict[str, list[dict]], dict]:
    rows = magnet.load(orders_csv)
    return customer_shards(rows), magnet_doc(orders_csv, as_of)


PLACEHOLDER = "/*SNAPSHOT*/null"
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def embed_snapshot(template_html: str, bundle: dict) -> str:
    """Bake a totals-only snapshot into the app page for viewers outside claude.ai.

    bundle: {snapshot, sb, mag, meta, actions}. Refuses anything that looks like an email
    address, so customer PII can never end up in the public page.
    """
    allowed = {"snapshot", "sb", "mag", "meta", "actions"}
    extra = set(bundle) - allowed
    if extra:
        raise ValueError(f"unexpected keys in bundle: {sorted(extra)}")
    for a in bundle.get("actions") or []:
        for k in ("updated_by", "sy_ok_by", "created_by"):
            a.pop(k, None)
    payload = json.dumps(bundle, separators=(",", ":"))
    hits = [m for m in _EMAIL.findall(payload) if not m.endswith("@comfortfresh.shop")]
    if hits:
        raise ValueError(f"snapshot contains {len(hits)} email-like strings; refusing to embed")
    if template_html.count(PLACEHOLDER) != 1:
        raise ValueError("snapshot placeholder not found exactly once in the template")
    return template_html.replace(PLACEHOLDER, payload.replace("</", "<\\/"))
