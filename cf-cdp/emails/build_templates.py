"""Builds the per-audience Omnisend templates (HTML import). Every link and image below was
checked against the live Shopify catalog on 2026-10-28 (published, ACTIVE, in-stock 12/18-pair
variants). Offers used are ones Shopify fulfils automatically today:
  - Wild Habitat printed insoles included with any 18 or 24-pair pack (automatic discount)
  - Free US shipping over $50 (automatic discount)
No % codes: the plan keeps % off for the C90 COMEBACK15 send only."""
import json, pathlib

S = "https://comfort-fresh.com/products/"
CDN = "https://cdn.shopify.com/s/files/1/0556/9468/8343/files/"
P = {
  "widest_crew": ("Widest Non-Binding Bamboo Crew", S + "bamboo-widest-crew", CDN + "17181-1.png?v=1777276658"),
  "widest_ankle": ("Widest Non-Binding Ankle Socks", S + "bamboo-diabetic-ankle", CDN + "combo-20261017_021548_5e23fbc7-9d16-44fc-be3e-1c4d95ad0607.png?v=1792203971"),
  "everyday_crew": ("Everyday Non-Binding Crew", S + "bamboo-everyday-crew", CDN + "1001H-1.png?v=1777337497"),
  "everyday_ankle": ("Everyday Cotton Ankle", S + "bamboo-everyday-ankle", CDN + "Untitled_design_ecac333b-1ac2-44a5-9add-5912b91c86f7.png?v=1777275373"),
  "multicolor": ("Multi-Color Bamboo Ankle", S + "non-binding-bamboo-diabetic-socks-morandi-color-series-copy-5", CDN + "16-2_-_Edited.jpg?v=1780462898"),
  "cotton_ankle": ("Non-Binding Cotton Ankle", S + "wide-non-binding-cotton-ankle-diabetic-socks-seamless-toe-air-vent-with-cushion-sole-2-8-pairs", CDN + "17180_94f61133-c68c-4b4b-b1a7-9f6efa781874.png?v=1792205023"),
}
GREEN = "#0d5c45"

def para(t, size=16): return f'<p style="margin:0 0 16px;font-size:{size}px;line-height:1.55;color:#222222;">{t}</p>'
def btn(label, url): return f'<p style="margin:24px 0 12px;text-align:center;"><a href="{url}" style="display:inline-block;background:{GREEN};color:#ffffff;text-decoration:none;padding:14px 28px;border-radius:6px;font-weight:bold;font-size:16px;">{label}</a></p>'
def hero(key): n, u, img = P[key]; return f'<p style="margin:0 0 20px;text-align:center;"><a href="{u}"><img src="{img}" alt="{n}" width="536" style="width:100%;max-width:536px;height:auto;border:0;display:block;margin:0 auto;"></a></p>'
def duo(a, b):
    cell = lambda k: (lambda n, u, img: f'<td width="50%" style="padding:6px;vertical-align:top;text-align:center;"><a href="{u}"><img src="{img}" alt="{n}" width="250" style="width:100%;max-width:250px;height:auto;border:0;"></a><p style="margin:8px 0 0;font-size:14px;line-height:1.4;"><a href="{u}" style="color:{GREEN};font-weight:bold;text-decoration:none;">{n}</a></p></td>')(*P[k])
    return f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 16px;"><tr>{cell(a)}{cell(b)}</tr></table>'
PRICES = para('<strong>12 pairs $79 · 18 pairs $109 · 24 pairs $129.</strong> The 18 and 24-pair packs include <strong>free Wild Habitat printed insoles</strong>, and shipping is free over $50.', 15)

def page(preheader, body):
    return f'''<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Comfort Fresh</title></head>
<body style="margin:0;padding:0;background:#f5f5f5;"><div style="display:none;max-height:0;overflow:hidden;">{preheader}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f5f5f5;"><tr><td align="center" style="padding:16px 8px;">
<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:100%;max-width:600px;background:#ffffff;font-family:Arial,Helvetica,sans-serif;color:#222222;">
<tr><td style="padding:28px 32px 8px;text-align:center;"><p style="margin:0;font-size:20px;font-weight:bold;color:{GREEN};">Comfort Fresh</p><p style="margin:6px 0 0;color:#666666;font-size:14px;line-height:1.5;">Wide, non-binding bamboo socks for everyday comfort</p></td></tr>
<tr><td style="padding:8px 32px 28px;">{body}
<p style="margin:24px 0 0;font-size:15px;line-height:1.5;">Warmly,<br>Comfort Fresh<br><span style="color:#666666;font-size:14px;">brand@comfortfresh.shop</span></p></td></tr>
<tr><td style="padding:24px 32px 32px;border-top:1px solid #e5e5e5;text-align:center;color:#777777;font-size:12px;line-height:1.6;"><p style="margin:0 0 8px;"><strong>Comfort Fresh</strong> by All About Socks, LLC</p><p style="margin:0 0 12px;">2929 N Main Street, N Logan, UT 84341 · USA</p>
<p style="margin:0;"><a href="[[unsubscribe_link]]" style="color:#555555;text-decoration:underline;">Unsubscribe</a> · <a href="https://comfort-fresh.com/policies/privacy-policy" style="color:#555555;text-decoration:underline;">Privacy Policy</a> · <a href="https://comfort-fresh.com/policies/terms-of-service" style="color:#555555;text-decoration:underline;">Terms of Service</a></p></td></tr>
</table></td></tr></table></body></html>'''

HI = para("Hi [[contact.first_name]],", 18)
T = {
 "second_order": ("Second order", "Your first pairs have had a week or two. Here's the other half of the drawer.", HI +
   para("Your first Comfort Fresh pairs have had a week or two to prove themselves: no tight band, no marks at the ankle, soft all day.") +
   para("Most customers end up wearing two heights: <strong>ankle</strong> for everyday and <strong>crew</strong> for cooler days and longer wear. If you started with one, the other is the easy next step.") +
   duo("widest_crew", "everyday_ankle") + PRICES + btn("Shop crew and ankle", P["widest_crew"][1])),
 "vip_active": ("VIP active", "A thank-you, and the pack our regulars choose.", HI +
   para("You've ordered from us three times or more, and that means a lot to a small sock company. Thank you.") +
   para("Our regulars mostly stock up with the <strong>18-pair pack</strong>: it works out cheaper per pair and now comes with <strong>free Wild Habitat printed insoles</strong> matched to your size.") +
   hero("widest_crew") + PRICES + btn("Stock up with 18 pairs", P["widest_crew"][1]) +
   para('Prefer ankle height? <a href="' + P["widest_ankle"][1] + f'" style="color:{GREEN};">Shop the widest ankle socks</a>.', 15)),
 "household": ("Household", "Socks for everyone at home, one order, free shipping.", HI +
   para("Your last order had more than one sock size in it, so we're guessing you shop for more than one pair of feet.") +
   para("Every style comes in <strong>9–11, 10–13 and 13–15</strong>, so the whole household can share one order and one free-shipping box (free over $50). Pick an 18 or 24-pair pack per person and the <strong>Wild Habitat insoles are included</strong>.") +
   duo("everyday_crew", "multicolor") + PRICES + btn("Shop for the family", P["everyday_crew"][1])),
 "bundle_clock": ("Bundle restock", "Your bundle is about three months old. Time for fresh pairs?", HI +
   para("You bought a big pack a few months ago. Bamboo socks stay soft, but heels and toes thin out with daily wear, usually around the three-month mark.") +
   para("Restocking takes a minute: the <strong>same style and size</strong>, and the 18 and 24-pair packs now include <strong>free Wild Habitat printed insoles</strong>.") +
   hero("widest_ankle") + PRICES + btn("Restock my socks", P["widest_ankle"][1])),
 "large_feet": ("Large feet 13-15", "Made for big feet: sock size 13–15, no tight band.", HI +
   para("November 14 is World Diabetes Day, a good moment for a quick foot-care check: no marks from sock bands, no seams rubbing at the toes, feet dry by evening.") +
   para("Our socks are cut for <strong>sock size 13–15</strong> as standard, not stretched to fit. Wide, non-binding tops, seamless toes and soft bamboo, so nothing squeezes.") +
   duo("widest_crew", "widest_ankle") + PRICES + btn("Shop size 13–15", P["widest_crew"][1])),
 "ladder": ("Cross-sell", "Try the other half of the sock drawer.", HI +
   para("It's been a little while since your first order, so here's an easy way to round out the drawer: if you started with ankle socks, try <strong>crew</strong> for cooler days; if you started with crew, <strong>ankle</strong> socks are the everyday favorite.") +
   para("Same wide, non-binding fit you already know. Want some color? The <strong>Multi-Color ankle</strong> pack is our brightest.") +
   duo("everyday_crew", "multicolor") + PRICES + btn("Find your next pair", P["everyday_crew"][1])),
 "repeat_lapsed": ("Bundle upgrade", "The 18-pair pack costs less per pair, and the insoles are included.", HI +
   para("You've ordered from us twice. If you're restocking anyway, here's the math on bigger packs:") +
   para("<strong>12 pairs $79</strong> = $6.58 a pair · <strong>18 pairs $109</strong> = $6.06 a pair · <strong>24 pairs $129</strong> = $5.38 a pair.") +
   para("And the 18 and 24-pair packs come with <strong>free Wild Habitat printed insoles</strong>. Shipping is free over $50.") +
   hero("widest_ankle") + btn("Upgrade to 18 pairs", P["widest_ankle"][1]) +
   para('Prefer crew height? <a href="' + P["widest_crew"][1] + f'" style="color:{GREEN};">Shop the widest crew</a>.', 15)),
}
out = {}
for k, (code, pre, body) in T.items():
    html = page(pre, body)
    pathlib.Path(f"emails/{k}.html").write_text(html)
    out[k] = {"name": f"CF · {code} · v1", "html": html}
pathlib.Path("emails/templates.json").write_text(json.dumps(out))
print({k: (v["name"], len(v["html"])) for k, v in out.items()})
