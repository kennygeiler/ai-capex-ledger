"""What to pull from EDGAR and how to map it.

Every choice here is a data decision, so each one is written down rather than buried in code.
Tickers are resolved to CIKs live from https://www.sec.gov/files/company_tickers.json.
"""

# The brief's AI-trade set, plus Nasdaq-listed names outside the S&P 500.
AI_SET = [
    {"ticker": "NVDA", "name": "Nvidia", "group": "AI trade"},
    {"ticker": "MSFT", "name": "Microsoft", "group": "AI trade"},
    {"ticker": "GOOGL", "name": "Alphabet", "group": "AI trade"},
    {"ticker": "AMZN", "name": "Amazon", "group": "AI trade"},
    {"ticker": "META", "name": "Meta", "group": "AI trade"},
    {"ticker": "ORCL", "name": "Oracle", "group": "AI trade"},
    {"ticker": "TSLA", "name": "Tesla", "group": "AI trade"},
    {"ticker": "MU", "name": "Micron", "group": "AI trade"},
    {"ticker": "AMD", "name": "AMD", "group": "AI trade"},
    {"ticker": "SPCX", "name": "SpaceX", "group": "AI trade", "note": "Nasdaq IPO June 2026"},
    {"ticker": "CRWV", "name": "CoreWeave", "group": "Nasdaq, not S&P 500", "note": "IPO March 2025"},
    {"ticker": "MRVL", "name": "Marvell", "group": "Nasdaq, not S&P 500"},
    {"ticker": "ALAB", "name": "Astera Labs", "group": "Nasdaq, not S&P 500", "note": "IPO March 2024"},
    {"ticker": "CRDO", "name": "Credo", "group": "Nasdaq, not S&P 500"},
    {"ticker": "IREN", "name": "IREN", "group": "Nasdaq, not S&P 500", "note": "Moved from 20-F to 10-K in 2025"},
    {"ticker": "APLD", "name": "Applied Digital", "group": "Nasdaq, not S&P 500"},
    {"ticker": "CIFR", "name": "Cipher Digital", "group": "Nasdaq, not S&P 500"},
    {"ticker": "WULF", "name": "TeraWulf", "group": "Nasdaq, not S&P 500"},
    {"ticker": "CORZ", "name": "Core Scientific", "group": "Nasdaq, not S&P 500"},
]

# "Then 100": the S&P 100 (the largest S&P 500 names). List as of 2025; check current membership before publishing.
# GOOG is dropped because GOOGL is the same company (same CIK). BK now trades as BNY.
SP100 = """AAPL ABBV ABT ACN ADBE AIG AMD AMGN AMT AMZN AVGO AXP BA BAC BNY BKNG BLK BMY BRK-B C CAT CHTR CL CMCSA
COF COP COST CRM CSCO CVS CVX DE DHR DIS DUK EMR F FDX GD GE GILD GM GOOGL GS HD HON IBM INTC INTU ISRG JNJ JPM KO
LIN LLY LMT LOW MA MCD MDLZ MDT MET META MMM MO MRK MS MSFT NEE NFLX NKE NOW NVDA ORCL PEP PFE PG PLTR PM PYPL QCOM
RTX SBUX SCHW SO SPG T TGT TMO TMUS TSLA TXN UBER UNH UNP UPS USB V VZ WFC WMT XOM""".split()

# Companies whose history sits under an older CIK (reorganizations). Facts from these CIKs are merged in.
PREDECESSORS = {
    "XOM": [{"cik": 34088, "name": "Exxon Mobil Corp", "note": "Reorganized under ExxonMobil Holdings Corp (new CIK) in 2026."}],
}

# Considered and left out, with the reason.
EXCLUDED = [
    {"ticker": "NBIS", "name": "Nebius Group", "reason": "Files 20-F and 6-K as a foreign private issuer: no quarterly XBRL facts."},
    {"ticker": "ARM", "name": "Arm Holdings", "reason": "Files 20-F and 6-K as a foreign private issuer: no quarterly XBRL facts."},
    {"ticker": "SMCI", "name": "Super Micro Computer", "reason": "In the S&P 500 since 2024, so outside the 'not in S&P 500' group."},
    {"ticker": "GOOG", "name": "Alphabet class C", "reason": "Same company and CIK as GOOGL."},
]

# XBRL concepts tried for each line item, in priority order. Per company the pipeline ranks them by recent
# coverage and takes the best one available for each period. The bank revenue tag sits last.
CONCEPTS = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "RevenuesNetOfInterestExpense",
    ],
    "cost_of_revenue": ["CostOfRevenue", "CostOfGoodsAndServicesSold", "CostOfGoodsSold", "CostOfServices"],
    "operating_income": ["OperatingIncomeLoss"],
    "opex_reported": ["OperatingExpenses"],
    "costs_and_expenses": ["CostsAndExpenses"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsToAcquireOtherPropertyPlantAndEquipment",
        "PaymentsToAcquireOtherProductiveAssets",  # Verizon
    ],
    # Fallback inputs for opex when a company has no operating-income line.
    "sga": ["SellingGeneralAndAdministrativeExpense"],
    "rnd": ["ResearchAndDevelopmentExpense", "ResearchAndDevelopmentExpenseExcludingAcquiredInProcessCost"],
    "noninterest_expense": ["NoninterestExpense"],  # banks' operating expenses
}

# Discovery: patterns that scan each company's full list of us-gaap concepts, so tags outside CONCEPTS
# still surface. This is the evidence for how each company's label was found.
DISCOVERY = {
    "revenue": r"^(Revenues?|RevenueFromContractWithCustomer\w*|SalesRevenue\w*|RevenuesNetOfInterestExpense|InterestAndDividendIncomeOperating)$",
    "capex": r"^PaymentsToAcquire(PropertyPlantAndEquipment|ProductiveAssets|OtherPropertyPlantAndEquipment|OtherProductiveAssets)\w*$|^PaymentsForCapitalImprovements$",
    "cost_of_revenue": r"^Cost(OfRevenue|OfGoodsAndServicesSold|OfGoodsSold|OfServices)$",
    "operating": r"^(OperatingExpenses|CostsAndExpenses|OperatingIncomeLoss|NoninterestExpense|SellingGeneralAndAdministrativeExpense|ResearchAndDevelopmentExpense)$",
}

# Forms whose facts we accept. S-1 / 424B4 fill history for recent IPOs (flagged as such).
FORMS_PRIMARY = {"10-Q", "10-K", "10-Q/A", "10-K/A", "10-KT"}
FORMS_FALLBACK = {"S-1", "S-1/A", "424B4"}

# Duration bands (days) used to classify a fact's period.
QUARTER_DAYS = (80, 120)  # up to 16 weeks: Costco's fiscal Q4 is 16 weeks
YEAR_DAYS = (350, 380)

WINDOW_QUARTERS = 8
WINDOW_YEARS = 5
# The quarterly window ends at the latest calendar quarter where at least this share of companies has revenue.
WINDOW_COVERAGE = 0.6

# ── MVP (docs/PRD.md) ──────────────────────────────────────────────────────────
# The AI set, 5 fiscal years from 10-K filings only.
MVP_TICKERS = [c["ticker"] for c in AI_SET]
MVP_YEARS = ["FY2022", "FY2023", "FY2024", "FY2025", "FY2026"]
MVP_FIELDS = ["revenue", "cost_of_revenue", "operating_income", "capex"]  # what agents read
RELEASE_FIELDS = ["revenue", "capex", "opex"]  # what ships; opex = revenue − cost of revenue − operating income (docs/FIELDS.md)
# Prompts are tuned only on the dev split. The golden set is drawn from the hold-out and never shown during tuning.
# Dev covers a January fiscal year (NVDA), a June fiscal year (MSFT) and a young, capex-heavy filer (CRWV).
DEV_SPLIT = ["NVDA", "MSFT", "CRWV"]
HOLDOUT = [t for t in MVP_TICKERS if t not in DEV_SPLIT]
GOLDEN_SEED = 20261027

# Delivery stages (PRD section 5): one company, then 5, then all 19. Each stage is a signed release.
STAGES = {
    1: {"tickers": ["NVDA"], "dev": ["NVDA"], "holdout": [], "release": "v0.1.0"},
    2: {"tickers": ["NVDA", "MSFT", "CRWV", "ORCL", "APLD"], "dev": ["NVDA", "MSFT", "CRWV"], "holdout": ["ORCL", "APLD"], "release": "v0.2.0"},
    3: {"tickers": MVP_TICKERS, "dev": DEV_SPLIT, "holdout": HOLDOUT, "release": "v1.0.0"},
}
