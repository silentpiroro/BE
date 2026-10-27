"""push_omnisend_segment: dry-run by default.

Builds the exact contact list that would go to an Omnisend segment and checks
every guardrail. It never sends email. A live upsert needs --execute plus an
approval record naming Sy; even then it only upserts contacts/tags, and the
campaign stays a draft in Omnisend until Sy publishes it.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import config as C

MARKETING_EVENTS = {"email_sent"}  # channel=omnisend|gmail, kind=marketing


class GuardrailError(RuntimeError):
    pass


def plan_push(membership: list[dict], wave: str, events: list[dict], today: date,
              wool_status: str | None = None) -> dict:
    if wave == "WOOL_C" and wool_status != "READY":
        raise GuardrailError(f"Wool Wave C is on HOLD until {C.WOOL_SKU} available > 0")
    window_30 = today - timedelta(days=30)
    week_start = today - timedelta(days=today.weekday())
    sent_30: dict[str, int] = {}
    gmail_week: set[str] = set()
    for e in events:
        if e.get("event_type") not in MARKETING_EVENTS or e.get("kind") != "marketing":
            continue
        d = date.fromisoformat(e["occurred_at"][:10])
        email = e["email"].lower()
        if d >= window_30:
            sent_30[email] = sent_30.get(email, 0) + 1
        if e.get("channel") == "gmail" and d >= week_start:
            gmail_week.add(email)
    include, skipped = [], {"not_subscribed": 0, "freq_cap_30d": 0, "gmail_same_week": 0}
    for r in membership:
        if r["wave"] != wave:
            continue
        email = r["email"].lower()
        if not r.get("wave_sub_eligible") or r.get("email_marketing_state") != "SUBSCRIBED":
            skipped["not_subscribed"] += 1
        elif sent_30.get(email, 0) >= C.MAX_MARKETING_EMAILS_PER_30D:
            skipped["freq_cap_30d"] += 1
        elif email in gmail_week:
            skipped["gmail_same_week"] += 1
        else:
            include.append(email)
    return {"wave": wave, "as_of": today.isoformat(), "dry_run": True,
            "would_upsert": len(include), "skipped": skipped, "emails": include,
            "notes": ["Wave A offer: Club Starter ankle 6@$49 alone; no COMEBACK15 stack"] if wave == "A" else []}


def execute_push(plan: dict, approved_by: str | None, approval_ref: str | None):
    if approved_by != C.APPROVER or not approval_ref:
        raise GuardrailError(f"Live push needs --approved-by {C.APPROVER} and --approval-ref")
    # Live call goes through the Omnisend MCP (contacts upsert + tag cf_wave_<x>),
    # run from a Claude session with the connector. Not wired from this CLI.
    raise NotImplementedError("Run the live upsert via the Omnisend MCP with this plan file")
