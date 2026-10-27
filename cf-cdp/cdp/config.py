"""Locked business constants for the Comfort Fresh CDP.

Change these only when Sy / CoS change the locked unit economics.
"""

SHOP_DOMAIN = "md-diab.myshopify.com"
SHOP_NAME = "Comfort-Fresh |Bamboo Socks"

# North star (engraved 2026-10-27)
NORTH_STAR_MONTHLY_SALES_USD = 100_000
TARGET_NET_MARGIN = 0.15

# Unit economics (locked)
COGS_PER_PAIR_USD = 0.85
SHIPPING_PER_ORDER_USD = 7.50
RMB_PER_USD = 7.2
STAFF = 2
SALARY_RMB_PER_STAFF_MONTH = 6_000
FIXED_SALARIES_USD_MONTH = round(STAFF * SALARY_RMB_PER_STAFF_MONTH / RMB_PER_USD, 2)  # ~1666.67

# Media scenarios (ESTIMATE until live Meta is connected). Never invent live spend.
MEDIA_SCENARIOS_USD_MONTH = {"low": 5_000, "mid": 6_500, "high": 8_000}

# Meta floors for scaling winners
META_MAX_CPR_USD = (25, 35)
META_MIN_PURCHASE_ROAS = (3.5, 4.0)

DAYS_PER_MONTH = 30.4375

# Day-N waves
WAVE_PRECEDENCE = ["A", "B", "C60", "C90"]  # A wins on multi-match
WOOL_SKU = "CF22032"

# Messaging guardrails
MAX_MARKETING_EMAILS_PER_30D = 3
APPROVER = "Sy"
