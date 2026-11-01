"""Fiscal-year values from 10-K cells, labelled against the XBRL reference.

Each value is one cell; opex is three cells of the same 10-K column (revenue − cost of revenue − operating income).
Every field of a company-year comes from the newest 10-K that reports that year, so a year never mixes filings;
the first 10-K's figure is kept as first_reported.

Labels: agree (within the coarser rounding of the two sources), unresolved (they differ: the xbrl_reconcile rule
raises it for a person), definition_gap (opex built from summed cost lines differs only because XBRL draws cost of
revenue differently: revenue and operating income both agree, so code explains it and no person is asked),
no_reference (no XBRL value), not_reported (the 10-K has no line to build it from, and XBRL tags no value either),
not_extracted (no cell to build it from, while XBRL tags a value: the reader missed a line or the statement table was
mislocated; open until it is read, never explained by the label; T65).
"""
import hashlib
import json
from datetime import date

from .config import MVP_YEARS, RELEASE_FIELDS, restated, rounding_unit
from .definitions import revenue_gap_explained, opex_gap_explained
from .ingest.edgar import fetch_json
from .ingest.filings import fetch_tickers
from .reference.normalize import fiscal_label


def fiscal_year_end(ticker: str) -> str | None:
    cik = fetch_tickers()[0][ticker]["cik"]
    return fetch_json("submissions", cik, max_age_h=24 * 7)[0].get("fiscalYearEnd")


def _rounding(v: int) -> int:
    return rounding_unit(v)


def _restated(first: int, latest: int, scale: int) -> bool:
    """Any change beyond rounding is a restatement (Meta's 0.8% capex change counts); how big it is shows beside it.
    The one threshold is config.RESTATEMENT_TOLERANCE (half a rounding unit, T64): here the unit is the cell's scale."""
    return restated(first, latest, scale)


def _agrees(e: dict, r: int | None) -> bool:
    return r is not None and abs(e["value"] - r) <= max(e["scale"], _rounding(r)) // 2


def values_for(ticker: str, extractions: list[dict], reference: dict, fye: str | None, docs: dict, defs: dict | None = None) -> list[dict]:
    """extractions: 12-month cells joined with their filing date. reference: (field, period) -> value.
    docs: accession -> (sha256, parser_version), folded into each value's input hash so a reparse reopens decisions.
    defs: per-company definitions (ledger/definitions.py); a revenue definition turns an XBRL gap into definition_gap."""
    cells = {}  # (period_end, accession) -> {field: extraction}
    for e in extractions:
        if 350 <= (date.fromisoformat(e["period_end"]) - date.fromisoformat(e["period_start"])).days <= 380:
            fs = cells.setdefault((e["period_end"], e["accession"]), {})
            if e["field"] == "cost_of_revenue_part":
                fs.setdefault("parts", []).append(e)
            else:
                fs[e["field"]] = e
    for fs in cells.values():
        # No total cost-of-revenue line: the cost lines the agent classified are added up (standard practice).
        if "cost_of_revenue" not in fs and fs.get("parts"):
            ps = fs["parts"]
            fs["cost_of_revenue"] = {**ps[0], "value": sum(x["value"] for x in ps), "parts": ps}
    filings = {}  # period_end -> [(filed, fields)] oldest first
    for (end, _), fs in cells.items():
        filings.setdefault(end, []).append((next(v for v in fs.values() if isinstance(v, dict))["filed"], fs))
    out = []
    for end, fl in sorted(filings.items()):
        fl.sort(key=lambda x: (x[0], len(x[1])))  # newest filing; on the same day, the more complete one (a 10-K over a partial 10-K/A)
        period = f"FY{fiscal_label(end, fye)[0]}"
        if period not in MVP_YEARS:
            continue
        newest = fl[-1][1]  # every field of a company-year comes from the newest 10-K that reports it: one basis per year
        for f in RELEASE_FIELDS:
            parts = ("revenue", "cost_of_revenue", "operating_income") if f == "opex" else (f,)
            if not all(p in newest for p in parts):  # no cell for it in the newest 10-K
                # not_reported only when XBRL has no value either (a bank's capex); a value the filer tagged and the reader
                # did not extract is not_extracted: open (AMZN's income statement located as its cash-flow table, T65)
                label = "not_extracted" if reference.get((f, period)) is not None else "not_reported"
                out.append(_row(ticker, f, period, end, None, None, [], label, "as_reported", docs))
                continue
            val = lambda fs: fs["revenue"]["value"] - fs["cost_of_revenue"]["value"] - fs["operating_income"]["value"] if f == "opex" else fs[f]["value"]
            day0 = next(d for d, fs in fl if all(p in fs for p in parts))  # filings on the same day are one vintage:
            first = [fs for d, fs in fl if d == day0 and all(p in fs for p in parts)][-1]  # the most complete of them
            latest = newest
            used = [x for p in parts for x in latest[p].get("parts", [latest[p]])]
            v, r = val(latest), reference.get((f, period))
            if f == "opex" and v < 0:  # operating income holds fair-value gains (bitcoin miners), so revenue − cost − operating income is not opex (type 65)
                out.append(_row(ticker, f, period, end, None, None, used, "not_reported", "as_reported", docs))
                continue
            tol = max([e["scale"] for e in used] + ([_rounding(r)] if r is not None else [])) // 2 * len(used)
            label = "no_reference" if r is None else "agree" if abs(v - r) <= tol else "unresolved"
            if label == "unresolved" and f == "opex" and "parts" in latest["cost_of_revenue"] and all(
                    _agrees(latest[p], reference.get((p, period))) for p in ("revenue", "operating_income")):
                label = "definition_gap"  # the gap can only be which lines count as cost of revenue; a person confirms those once per company
            if label == "unresolved" and f == "opex" and opex_gap_explained(defs or {}, ticker, period) and all(
                    _agrees(latest[p], reference.get((p, period))) for p in ("revenue", "operating_income")):
                label = "definition_gap"  # the SEC's opex tag is wider than ours (it includes cost of sales); the definition says so
            if label == "unresolved" and f == "revenue" and revenue_gap_explained(defs or {}, ticker, period):
                label = "definition_gap"  # the SEC's tag measures something wider than the sales line; the definition says so
            basis = "restated" if _restated(val(first), v, max(e["scale"] for e in used)) else "as_reported"
            out.append(_row(ticker, f, period, end, v, val(first), used, label, basis, docs))
    return out


def _row(ticker, field, period, end, value, first, used, label, basis, docs):
    ids = sorted(e["extraction_id"] for e in used)  # sorted: the golden test showed the cost-line order varied run to run
    h = hashlib.sha256(json.dumps([value, ids, label, sorted({docs[i.split("|")[0]] for i in ids})]).encode()).hexdigest()[:16]
    return {"ticker": ticker, "field": field, "period": period, "period_end": end, "value": value,
            "source": "agent" if value is not None else "missing", "method": "computed" if field == "opex" else "reported",
            "label": label, "basis": basis, "first_reported": first, "extraction_ids": ",".join(ids), "input_hash": h}
