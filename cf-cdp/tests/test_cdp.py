import csv
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cdp import config as C  # noqa: E402
from cdp import omnisend_push, pnl, sources, waves  # noqa: E402


def row(d, orders=10, gross=500.0, pairs=60, disc=0.0, ref=0.0, rep=2):
    return {"date": d, "orders_paid": orders, "gross_sales_usd": gross, "discounts_usd": disc,
            "refunds_usd": ref, "net_sales_usd": gross - disc - ref, "pairs_sold": pairs,
            "new_customer_orders": orders - rep, "repeat_customer_orders": rep}


class PnlTest(unittest.TestCase):
    def test_line_math(self):
        actual = pnl.sum_period([row("2026-10-01", disc=20, ref=10)], date(2026, 10, 1), date(2026, 10, 1))
        m = pnl.model_pnl(actual, 6000, "x")
        L = {ln["key"]: ln["usd"] for ln in m["lines"]}
        self.assertEqual(L["net_sales"], 470.0)
        self.assertEqual(L["cogs"], -51.0)          # 60 pairs x 0.85
        self.assertEqual(L["shipping"], -75.0)      # 10 orders x 7.50
        self.assertEqual(L["contribution"], 344.0)
        frac = 1 / C.DAYS_PER_MONTH
        self.assertAlmostEqual(L["media"], round(-6000 * frac, 2), places=2)
        self.assertAlmostEqual(L["net"], round(344 - 6000 * frac - C.FIXED_SALARIES_USD_MONTH * frac, 2), places=1)

    def test_live_media_replaces_scenario(self):
        actual = pnl.sum_period([row("2026-10-01")], date(2026, 10, 1), date(2026, 10, 1))
        m = pnl.model_pnl(actual, None, "live", live_media_usd=123.0)
        c = pnl.model_pnl(actual, None, "CAC", cac_usd=70.0)
        self.assertEqual(next(ln for ln in c["lines"] if ln["key"] == "media")["usd"], -8 * 70.0)
        self.assertIn("profit_split", c)
        media = next(ln for ln in m["lines"] if ln["key"] == "media")
        self.assertEqual(media["usd"], -123.0)
        self.assertTrue(media["basis"].startswith("ACTUAL"))

    def test_feed_without_meta_has_no_live_scenario(self):
        rows = [row(f"2026-10-{d:02d}") for d in range(1, 28)]
        feed = pnl.build_feed(rows, [], {}, date(2026, 10, 27), "test")
        self.assertEqual(feed["meta_status"], "not_connected")
        self.assertNotIn("live", feed["periods"]["30d"]["pnl"])
        self.assertEqual(feed["periods"]["mtd"]["actual"]["orders_paid"], 270)

    def test_gap(self):
        actual = pnl.sum_period([row(f"2026-10-{d:02d}") for d in range(1, 31)], date(2026, 10, 1), date(2026, 10, 30))
        g = pnl.gap_to_north_star(actual)
        self.assertAlmostEqual(g["run_rate_month_usd"], 500 * C.DAYS_PER_MONTH, places=1)


class WaveTest(unittest.TestCase):
    def p(self, **kw):
        base = {"email": "X@Example.invalid", "order_count_paid": 1, "email_marketing_state": "SUBSCRIBED",
                "days_since_last": 30, "primary_style": "ankle", "styles_bought": "ankle", "ankle_pref": "True"}
        base.update(kw)
        return base

    def test_rules(self):
        self.assertEqual(waves.assign_wave(self.p()), "A")
        self.assertEqual(waves.assign_wave(self.p(email_marketing_state="NOT_SUBSCRIBED")), "none")
        self.assertEqual(waves.assign_wave(self.p(order_count_paid=2)), "none")  # A needs exactly 1
        self.assertEqual(waves.assign_wave(self.p(days_since_last=50)), "B")
        self.assertEqual(waves.assign_wave(self.p(days_since_last=60)), "C60")
        self.assertEqual(waves.assign_wave(self.p(days_since_last=90)), "C90")
        self.assertEqual(waves.assign_wave(self.p(days_since_last=70, styles_bought="ankle|crew")), "none")

    def test_membership_lowercases_and_flags_sub(self):
        rows = waves.build_membership([self.p(days_since_last=50, email_marketing_state="UNSUBSCRIBED")], "2026-10-28")
        self.assertEqual(rows[0]["email"], "x@example.invalid")
        self.assertFalse(rows[0]["wave_sub_eligible"])

    def test_wool_hold(self):
        self.assertEqual(waves.wool_hold_list([self.p()], 0)["status"], "HOLD")
        self.assertEqual(waves.wool_hold_list([self.p()], None)["status"], "HOLD")
        self.assertEqual(waves.wool_hold_list([self.p()], 5)["status"], "READY")


class OmnisendGuardTest(unittest.TestCase):
    mem = [
        {"email": "a@x.invalid", "wave": "A", "email_marketing_state": "SUBSCRIBED", "wave_sub_eligible": True},
        {"email": "b@x.invalid", "wave": "A", "email_marketing_state": "SUBSCRIBED", "wave_sub_eligible": True},
        {"email": "c@x.invalid", "wave": "A", "email_marketing_state": "SUBSCRIBED", "wave_sub_eligible": True},
        {"email": "d@x.invalid", "wave": "A", "email_marketing_state": "NOT_SUBSCRIBED", "wave_sub_eligible": False},
    ]

    def test_caps(self):
        ev = lambda e, d, ch="omnisend": {"event_type": "email_sent", "kind": "marketing", "email": e,
                                           "occurred_at": d, "channel": ch}
        events = [ev("b@x.invalid", "2026-10-05"), ev("b@x.invalid", "2026-10-12"), ev("b@x.invalid", "2026-10-20"),
                  ev("c@x.invalid", "2026-10-27", "gmail")]
        plan = omnisend_push.plan_push(self.mem, "A", events, date(2026, 10, 28))
        self.assertEqual(plan["emails"], ["a@x.invalid"])
        self.assertEqual(plan["skipped"], {"not_subscribed": 1, "freq_cap_30d": 1, "gmail_same_week": 1})
        self.assertTrue(plan["dry_run"])

    def test_execute_needs_sy(self):
        plan = omnisend_push.plan_push(self.mem, "A", [], date(2026, 10, 28))
        with self.assertRaises(omnisend_push.GuardrailError):
            omnisend_push.execute_push(plan, "someone", "ref")
        with self.assertRaises(omnisend_push.GuardrailError):
            omnisend_push.plan_push(self.mem, "WOOL_C", [], date(2026, 10, 28), "HOLD")


class SourcesTest(unittest.TestCase):
    def test_shopify_export(self):
        cols = ["Name", "Email", "Financial Status", "Paid at", "Subtotal", "Discount Amount",
                "Refunded Amount", "Lineitem quantity", "Lineitem name", "Lineitem sku"]
        data = [
            ["#1001", "A@x.invalid", "paid", "2026-10-01 10:00:00 -0400", "49.00", "0", "0", "1", "Ankle Socks - 6 Pairs", "S1"],
            ["#1001", "", "", "", "", "", "", "1", "Crew Socks 3-Pack", "S2"],
            ["#1002", "a@x.invalid", "paid", "2026-10-02 09:00:00 -0400", "41.65", "7.35", "0", "1", "Ankle Socks - 6 Pairs", "S1"],
            ["#1003", "z@x.invalid", "pending", "", "49.00", "0", "0", "1", "Ankle Socks - 6 Pairs", "S1"],
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as fh:
            w = csv.writer(fh); w.writerow(cols); w.writerows(data)
        rows = sources.revenue_daily_from_shopify_csv(fh.name)
        self.assertEqual([r["date"] for r in rows], ["2026-10-01", "2026-10-02"])
        self.assertEqual(rows[0]["pairs_sold"], 9)
        self.assertEqual(rows[1]["gross_sales_usd"], 49.0)
        self.assertEqual(rows[1]["repeat_customer_orders"], 1)

    def test_order_summary_export(self):
        cols = ["order_id", "processed_at_utc", "financial_status", "cancelled_at", "subtotal_original",
                "total_discounts_original", "total_refunded", "customer_id", "customer_lifetime_orders",
                "total_quantity", "skus"]
        data = [
            ["1", "2026-10-02T03:00:00Z", "PAID", "", "40.00", "10.00", "0", "c1", "3", "2",
             "CF17180-4Black-10-13; CF17180-1315-B12W6-AID"],          # local date 10-01 (CDT); 2 units x avg 11
            ["2", "2026-10-05T15:00:00Z", "PARTIALLY_REFUNDED", "", "20.00", "0", "5.00", "c1", "3", "1", "CF17180-1315-N12"],
            ["3", "2026-10-05T16:00:00Z", "REFUNDED", "2026-10-06T00:00:00Z", "15.00", "0", "15.00", "c2", "1", "1", "CF368-1Black-XL"],
        ]
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as fh:
            w = csv.writer(fh); w.writerow(cols); w.writerows(data)
        rows, q = sources.revenue_daily_from_order_summary_csv(fh.name)
        self.assertEqual(q["cancelled_excluded"], 1)
        d = {r["date"]: r for r in rows}
        self.assertEqual(d["2026-10-01"]["gross_sales_usd"], 50.0)
        self.assertEqual(d["2026-10-01"]["pairs_sold"], 22)
        self.assertEqual(d["2026-10-01"]["repeat_customer_orders"], 1)  # c1's 2nd lifetime order
        self.assertEqual(d["2026-10-05"]["net_sales_usd"], 15.0)
        self.assertEqual(d["2026-10-05"]["pairs_sold"], 12)

    def test_meta_period_export(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Reporting starts", "Reporting ends", "Ad set name", "Amount spent (USD)", "Purchases",
                        "Purchase ROAS (return on ad spend)", "Adds to cart"])
            w.writerow(["2026-10-22", "2026-10-23", "A", "300", "2", "3.0", "4"])
            w.writerow(["2026-10-22", "2026-10-23", "B", "100", "", "", "0"])
        r = sources.meta_period_from_ads_export(fh.name)
        self.assertEqual((r["days"], r["spend_usd"], r["purchases"], r["cpr_usd"]), (2, 400.0, 2, 200.0))
        self.assertEqual(r["purchase_value_usd"], 900.0)

    def test_meta_dump(self):
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Day", "Campaign name", "Amount spent (USD)", "Purchases", "Purchases conversion value"])
            w.writerow(["2026-10-26", "Large feet", "200.00", "8", "720.00"])
        r = sources.meta_daily_from_ads_manager_csv(fh.name)[0]
        self.assertEqual((r["cpr_usd"], r["purchase_roas"]), (25.0, 3.6))


class PlaybookTest(unittest.TestCase):
    def test_every_segment_respects_cap(self):
        from datetime import timedelta
        from cdp import playbook
        for seg in ["vip_lapsed", "vip_active", "second_order", "wave_a", "household", "bundle_clock",
                    "large_feet", "ladder", "repeat_lapsed", "dormant", "other"]:
            ds = [date.fromisoformat(x["date"]) for x in playbook.schedule(seg)["sends"]]
            for d0 in ds:
                self.assertLessEqual(sum(d0 <= x < d0 + timedelta(days=30) for x in ds), C.MAX_MARKETING_EMAILS_PER_30D, seg)
        self.assertEqual(playbook.schedule("service")["sends"], [])

    def test_segment_priority(self):
        from cdp import playbook
        base = {"refunded": False, "reordered_after_refund": False, "household": False, "last_pairs": 6, "size": "9-11"}
        a = lambda **kw: playbook.assign({**base, **kw}, date(2026, 10, 27))
        self.assertEqual(a(lifetime_orders=5, days_since=90), "vip_lapsed")
        self.assertEqual(a(lifetime_orders=1, days_since=12), "second_order")
        self.assertEqual(a(lifetime_orders=1, days_since=30), "wave_a")
        self.assertEqual(a(lifetime_orders=1, days_since=200), "dormant")
        self.assertEqual(a(lifetime_orders=1, days_since=3), "recent")


class PageScriptTest(unittest.TestCase):
    def test_page_scripts_parse(self):
        import shutil
        import subprocess
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        root = Path(__file__).resolve().parents[1] / "ui" / "templates"
        for page in root.glob("*.html"):
            html = page.read_text()
            js = html[html.rindex("<script>") + 8: html.rindex("</script>")].replace("/*__CDP_FEED__*/null", "null")
            with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as fh:
                fh.write(js)
            r = subprocess.run([node, "--check", fh.name], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, f"{page.name}: {r.stderr[:300]}")


class WarRoomTest(unittest.TestCase):
    def test_every_send_action_needs_sy(self):
        from cdp import warroom
        sb = {"plan_months": [{"month": "2027-02", "pairs": 4000}], "segments": []}
        acts = warroom.actions(sb)
        self.assertEqual(len({a["id"] for a in acts}), len(acts))
        for a in acts:
            if a["title"].lower().startswith("send") or "send to" in a["title"].lower():
                self.assertTrue(a["needs_sy"], a["title"])


class MagnetTest(unittest.TestCase):
    def metrics(self):
        return {"repeat_hazard_by_month": [0.10, 0.025, 0.02] + [0.01] * 9,
                "existing_cohorts": {"0": 100, "1": 100, "2": 100},
                "last30": {"new_customers": 100, "repeat_orders": 25},
                "pairs_per_order_recent": 10}

    def test_path_reaches_target_and_flags_band(self):
        from cdp import magnet
        sim = magnet.simulate(self.metrics())
        self.assertIsNotNone(sim["hits_target"])
        rows = sim["months"]
        hit = next(r for r in rows if r["month"] == sim["hits_target"])
        self.assertGreaterEqual(hit["revenue_usd"], 99_500)
        for a, b in zip(rows, rows[1:]):  # growth cap respected before the target month
            if b["month"] <= sim["hits_target"]:
                self.assertLessEqual(b["new_customers"], a["new_customers"] * 1.35 + 1)
        self.assertTrue(any(r["over_band"] for r in rows))
        self.assertEqual(rows[3]["po_month"], rows[0]["month"])  # 3-month lead time

    def test_cac_media_and_profit_split(self):
        from cdp import magnet
        sim = magnet.simulate(self.metrics())
        r = sim["months"][0]
        self.assertAlmostEqual(r["media_usd"], r["new_customers"] * C.CAC_USD, delta=C.CAC_USD)
        # first order roughly breaks even at $70 CAC; repeat orders carry the profit
        self.assertLess(abs(sim["first_order_profit_per_customer_usd"]), 15)
        self.assertGreater(r["repeat_profit_usd"], r["first_order_profit_usd"])

    def test_steady_state_repeat_needed(self):
        from cdp import magnet
        ss = magnet.steady_state(self.metrics())
        k = ss["repeat_orders_per_customer_needed_15pct"]
        a = magnet.ASSUMPTIONS
        c = 10 * C.COGS_PER_PAIR_USD + C.SHIPPING_PER_ORDER_USD
        n = 100_000 / (a["first_aov_usd"] + k * a["repeat_aov_usd"])
        net = n * ((a["first_aov_usd"] - c - a["cac_usd"]) + k * (a["repeat_aov_usd"] - c)) - C.FIXED_SALARIES_USD_MONTH
        self.assertAlmostEqual(net / 100_000, 0.15, places=2)


if __name__ == "__main__":
    unittest.main()
