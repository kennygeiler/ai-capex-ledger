"""T45: as-stated agent values -> calendar-quarter values, using the reference pipeline's own rules.

Agent extractions are shaped like companyfacts facts (one per field, period and filing) and passed through
ledger.reference.normalize.build_company, so vintages, YTD differencing, Q4 = year minus nine months, the
Oracle mistag guard and the Costco collision rule are the same code, not a re-implementation.
"""
from __future__ import annotations

from .ingest.edgar import fetch_json
from .ingest.filings import fetch_tickers
from .reference.normalize import build_company

# One stand-in concept per field: build_company ranks candidate concepts, so each field needs exactly one.
CONCEPT = {"revenue": "Revenues", "cost_of_revenue": "CostOfRevenue", "operating_income": "OperatingIncomeLoss",
           "capex": "PaymentsToAcquirePropertyPlantAndEquipment"}


def fiscal_year_end(ticker: str) -> str | None:
    cik = fetch_tickers()[0][ticker]["cik"]
    sub, _ = fetch_json("submissions", cik, max_age_h=24 * 7)
    return sub.get("fiscalYearEnd")


def quarters(extractions: list[dict], fye: str | None) -> dict[str, dict[str, dict]]:
    """{field: {cal_q: row}} with value, method, period, and the extraction IDs it was built from."""
    gaap: dict = {}
    by_key = {}
    filed = {}
    for x in extractions:
        filed.setdefault(x["accession"], x.get("filed") or x["accession"])
        u = {"start": x["period_start"], "end": x["period_end"], "val": x["value"], "accn": x["accession"],
             "form": x["form"], "filed": x["filed"]}
        gaap.setdefault(CONCEPT[x["field"]], {"units": {"USD": []}})["units"]["USD"].append(u)
        by_key[(x["field"], x["accession"], x["period_start"], x["period_end"])] = x["extraction_id"]
    m, _, _ = build_company({"facts": {"us-gaap": gaap}}, fye)
    out = {}
    for field in CONCEPT:
        rows = {}
        for cq, r in m.get(field, {}).items():
            ids = sorted({by_key.get((field, s["accn"], s["start"], s["end"])) for s in r["sources"]} - {None})
            rows[cq] = {"value": r["value"], "method": r["method"], "period_start": r["period_start"], "period_end": r["period_end"],
                        "accession": r["accession"], "restated": r["restated"], "extraction_ids": ids}
        out[field] = rows
    return out
