"""Day-N wave assignment (build_day_n_audiences).

Input: profile rows (profiles schema). Output: wave_membership rows + summary.
Pure and offline: no Shopify or Omnisend calls here.
"""

from __future__ import annotations

from . import config as C

SUB = "SUBSCRIBED"


def _styles(p: dict) -> set[str]:
    raw = p.get("styles_bought") or []
    if isinstance(raw, str):
        raw = [s for s in raw.replace(";", "|").split("|") if s]
    return {s.strip().lower() for s in raw}


def _truthy(v) -> bool:
    return str(v).strip().lower() in {"1", "true", "yes", "y"}


def day_n_band(days: int | None) -> str:
    if days is None:
        return "none"
    if days < 28:
        return "d0-27"
    if days <= 45:
        return "d28-45"
    if days <= 59:
        return "d46-59"
    if days <= 89:
        return "d60-89"
    return "d90+"


def candidate_waves(p: dict) -> list[str]:
    """All waves this profile qualifies for, before precedence."""
    orders = int(p.get("order_count_paid") or 0)
    if orders < 1 or p.get("days_since_last") in (None, ""):
        return []
    days = int(p["days_since_last"])
    styles = _styles(p)
    ankle_only = styles == {"ankle"}
    prefers_ankle = _truthy(p.get("ankle_pref")) or p.get("primary_style") == "ankle"
    sub = p.get("email_marketing_state") == SUB
    out = []
    if orders == 1 and sub and 28 <= days <= 45 and prefers_ankle:
        out.append("A")
    if ankle_only and 46 <= days <= 59:
        out.append("B")
    if ankle_only and 60 <= days <= 89:
        out.append("C60")
    if ankle_only and days >= 90:
        out.append("C90")
    return out


def assign_wave(p: dict) -> str:
    cands = candidate_waves(p)
    for w in C.WAVE_PRECEDENCE:
        if w in cands:
            return w
    return "none"


def build_membership(profiles: list[dict], as_of: str) -> list[dict]:
    rows = []
    for p in profiles:
        wave = assign_wave(p)
        if wave == "none":
            continue
        days = p.get("days_since_last")
        rows.append({
            "email": p["email"].strip().lower(),
            "wave": wave,
            "day_n_band": day_n_band(int(days) if days not in (None, "") else None),
            "email_marketing_state": p.get("email_marketing_state"),
            "ankle_pref": _truthy(p.get("ankle_pref")),
            "wave_sub_eligible": p.get("email_marketing_state") == SUB,
            "as_of": as_of,
        })
    return rows


def wool_hold_list(profiles: list[dict], wool_available: int | None) -> dict:
    """Wool Wave C: buyers missing merino. HOLD unless CF22032 available > 0."""
    members = [p["email"].strip().lower() for p in profiles
               if int(p.get("order_count_paid") or 0) >= 1 and "wool" not in _styles(p)
               and p.get("email_marketing_state") == SUB]
    hold = wool_available is None or wool_available <= 0
    return {"status": "HOLD" if hold else "READY", "sku": C.WOOL_SKU,
            "sku_available": wool_available, "sub_eligible_count": len(members)}


def summarize(rows: list[dict], profile_counts: dict, as_of: str, wool: dict | None = None,
              source: str = "build_day_n_audiences") -> dict:
    waves = []
    for w in C.WAVE_PRECEDENCE:
        members = [r for r in rows if r["wave"] == w]
        waves.append({"wave": w, "members_all": len(members),
                      "members_sub_eligible": sum(1 for r in members if r["wave_sub_eligible"])})
    return {"as_of": as_of, "source": source, "profiles": profile_counts,
            "waves": waves, "wool_c": wool}
