"""Which companies, years and fields; how XBRL tags map to fields (the answer key); and the company sets.

Every choice here is a data decision, so each one is written down rather than buried in code.
Tickers are resolved to CIKs live from https://www.sec.gov/files/company_tickers.json.
"""
import json
from pathlib import Path


# The brief's AI-trade set, plus Nasdaq-listed names outside the S&P 500. role: a buyer spends capex on the AI buildout,
# a seller supplies it (chips, networking, memory). The Insights page sums by role.
AI_SET = [
    {"ticker": "NVDA", "name": "Nvidia", "group": "AI trade", "role": "seller"},
    {"ticker": "MSFT", "name": "Microsoft", "group": "AI trade", "role": "buyer"},
    {"ticker": "GOOGL", "name": "Alphabet", "group": "AI trade", "role": "buyer"},
    {"ticker": "AMZN", "name": "Amazon", "group": "AI trade", "role": "buyer"},
    {"ticker": "META", "name": "Meta", "group": "AI trade", "role": "buyer"},
    {"ticker": "ORCL", "name": "Oracle", "group": "AI trade", "role": "buyer"},
    {"ticker": "TSLA", "name": "Tesla", "group": "AI trade", "role": "buyer"},
    {"ticker": "MU", "name": "Micron", "group": "AI trade", "role": "seller"},
    {"ticker": "AMD", "name": "AMD", "group": "AI trade", "role": "seller"},
    {"ticker": "SPCX", "name": "SpaceX", "group": "AI trade", "role": "buyer", "note": "Nasdaq IPO June 2026"},
    {"ticker": "CRWV", "name": "CoreWeave", "group": "Nasdaq, not S&P 500", "role": "buyer", "note": "IPO March 2025"},
    {"ticker": "MRVL", "name": "Marvell", "group": "Nasdaq, not S&P 500", "role": "seller"},
    {"ticker": "ALAB", "name": "Astera Labs", "group": "Nasdaq, not S&P 500", "role": "seller", "note": "IPO March 2024"},
    {"ticker": "CRDO", "name": "Credo", "group": "Nasdaq, not S&P 500", "role": "seller"},
    {"ticker": "IREN", "name": "IREN", "group": "Nasdaq, not S&P 500", "role": "buyer", "note": "Moved from 20-F to 10-K in 2025"},
    {"ticker": "APLD", "name": "Applied Digital", "group": "Nasdaq, not S&P 500", "role": "buyer"},
    {"ticker": "CIFR", "name": "Cipher Digital", "group": "Nasdaq, not S&P 500", "role": "buyer"},
    {"ticker": "WULF", "name": "TeraWulf", "group": "Nasdaq, not S&P 500", "role": "buyer"},
    {"ticker": "CORZ", "name": "Core Scientific", "group": "Nasdaq, not S&P 500", "role": "buyer"},
]

# How money flows to AI in each company's business: which money-flow model (agents/models/<industry>@vN.md) the
# attributor reads. A company not listed here gets "other" (no AI attribution beyond what it states).
INDUSTRIES = {
    "hyperscaler": ["MSFT", "GOOGL", "AMZN", "META", "ORCL"],
    "neocloud": ["CRWV", "NBIS"],
    "miner_to_hpc": ["IREN", "APLD", "CIFR", "WULF", "CORZ", "HUT", "RIOT", "MARA", "CLSK", "BTBT", "SLNH", "GLXY", "BTDR"],
    "chip_seller": ["NVDA", "AMD", "AVGO", "MRVL", "ALAB", "CRDO", "INTC", "QCOM", "TXN", "ARM", "MPWR", "RMBS", "SITM", "SNPS", "CDNS"],
    "chip_equipment": ["LRCX", "AMAT", "KLAC", "TER", "ENTG", "ONTO", "AEIS", "ACLS"],
    "component_supplier": ["MU", "ANET", "CSCO", "WDC", "STX", "SNDK", "SMCI", "DELL", "HPE", "NTAP", "CIEN", "COHR", "LITE", "AAOI", "FN", "JBL", "FLEX", "CLS", "PENG"],
    "datacenter_build": ["VRT", "ETN", "NVT", "MOD", "JCI", "PWR", "FIX", "EME", "GEV", "POWL", "BE"],
    "datacenter_landlord": ["EQIX", "DLR", "IRM"],
    "power": ["VST", "CEG", "NRG", "TLN"],
    "ai_software": ["CRM", "NOW", "ADBE", "SNOW", "PLTR", "DDOG"],
}


def industry(ticker: str) -> str:
    return next((k for k, ts in INDUSTRIES.items() if ticker in ts), "other")


# Companies whose history sits under an older CIK (reorganizations). Facts from these CIKs are merged in.
PREDECESSORS = {
    "XOM": [{"cik": 34088, "name": "Exxon Mobil Corp", "note": "Reorganized under ExxonMobil Holdings Corp (new CIK) in 2026."}],
}

# XBRL concepts tried for each line item, in priority order. Per company the pipeline ranks them by recent
# coverage and takes the best one available for each fiscal year. The bank revenue tag sits last.
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

# Forms whose XBRL facts the answer key accepts (it keeps full-year facts only). S-1 / 424B4 fill history for recent IPOs.
FORMS_PRIMARY = {"10-Q", "10-K", "10-Q/A", "10-K/A", "10-KT"}
FORMS_FALLBACK = {"S-1", "S-1/A", "424B4"}

# A full fiscal year, in days (52/53-week years included).
YEAR_DAYS = (350, 380)


# ── MVP (docs/PRD.md) ──────────────────────────────────────────────────────────
# The AI set, 5 fiscal years from 10-K filings only.
# Companies added in DATAHQ (or `ledger add`), kept in data/companies.json. They run through the same pipeline and
# join the full set, so the next release includes them once a person signs it.
ADDED = Path(__file__).resolve().parents[1] / "data" / "companies.json"


def added() -> list[dict]:
    return json.loads(ADDED.read_text()) if ADDED.exists() else []


def tracked() -> list[dict]:
    """Every company the ledger follows: the AI set plus any added since. Read fresh, so the app sees a new one."""
    known = {c["ticker"] for c in AI_SET}
    return AI_SET + [c for c in added() if c["ticker"] not in known]


MVP_YEARS = ["FY2022", "FY2023", "FY2024", "FY2025", "FY2026"]
RELEASE_FIELDS = ["revenue", "capex", "opex"]  # what ships; opex = revenue − cost of revenue − operating income (docs/FIELDS.md)
GOLDEN_SEED = 20261027  # seeds the random spot-checks a person (or the rendered-10-K re-read) confirms

# Named company sets: one company, then 5, then every tracked company. Stage 3 is read at call time, so a company
# added in DATAHQ joins it without a restart.
STAGES = (1, 2, 3)
_FIXED = {1: ["NVDA"], 2: ["NVDA", "MSFT", "CRWV", "ORCL", "APLD"]}


def stage_tickers(n: int) -> list[str]:
    return list(_FIXED[n]) if n in _FIXED else [c["ticker"] for c in tracked()]


def add_scope(ap) -> None:
    """Every command runs on a stage or on any tickers (`--ticker X Y`)."""
    ap.add_argument("--stage", type=int, choices=STAGES, help="a named company set (default 1)")
    ap.add_argument("--ticker", nargs="+", help="any tickers, instead of a stage")


def scope(a) -> tuple[list[str], str]:
    """(tickers, name). The name labels output files: 'stage2', or the tickers joined, e.g. 'AMD'."""
    if a.ticker:
        ts = sorted({t.upper() for t in a.ticker})
        return ts, "-".join(ts)
    return stage_tickers(a.stage or 1), f"stage{a.stage or 1}"
