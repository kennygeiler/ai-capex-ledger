"""Fiscal-year values from 10-K cells, labelled against the XBRL reference.

Each value is one cell; opex is three cells of the same 10-K column (revenue − cost of revenue − operating income).
Every field of a company-year comes from the newest 10-K that reports that year, so a year never mixes filings;
the first 10-K's figure is kept as first_reported.

Labels: agree (within the coarser rounding of the two sources), unresolved (they differ: the xbrl_reconcile rule
raises it), no_reference (no XBRL value), not_reported (the company has no such line, e.g. Oracle's cost of revenue).
"""
import hashlib
import json
from datetime import date

from .config import MVP_YEARS, RELEASE_FIELDS
from .ingest.edgar import fetch_json
from .ingest.filings import fetch_tickers
from .reference.normalize import fiscal_label


def fiscal_year_end(ticker: str) -> str | None:
    cik = fetch_tickers()[0][ticker]["cik"]
    return fetch_json("submissions", cik, max_age_h=24 * 7)[0].get("fiscalYearEnd")


def _rounding(v: int) -> int:
    return 1_000_000 if v % 1_000_000 == 0 else 1_000 if v % 1_000 == 0 else 1


def _restated(first: int, latest: int, scale: int) -> bool:
    return abs(latest - first) > max(scale // 2, abs(first) // 100)


def values_for(ticker: str, extractions: list[dict], reference: dict, fye: str | None, docs: dict) -> list[dict]:
    """extractions: 12-month cells joined with their filing date. reference: (field, period) -> value.
    docs: accession -> (sha256, parser_version), folded into each value's input hash so a reparse reopens decisions."""
    cells = {}  # (period_end, accession) -> {field: extraction}
    for e in extractions:
        if 350 <= (date.fromisoformat(e["period_end"]) - date.fromisoformat(e["period_start"])).days <= 380:
            cells.setdefault((e["period_end"], e["accession"]), {})[e["field"]] = e
    filings = {}  # period_end -> [(filed, fields)] oldest first
    for (end, _), fs in cells.items():
        filings.setdefault(end, []).append((next(iter(fs.values()))["filed"], fs))
    out = []
    for end, fl in sorted(filings.items()):
        fl.sort(key=lambda x: x[0])
        period = f"FY{fiscal_label(end, fye)[0]}"
        if period not in MVP_YEARS:
            continue
        newest = fl[-1][1]  # every field of a company-year comes from the newest 10-K that reports it: one basis per year
        for f in RELEASE_FIELDS:
            parts = ("revenue", "cost_of_revenue", "operating_income") if f == "opex" else (f,)
            if not all(p in newest for p in parts):
                if any(p in newest for p in parts):  # the filing reports the year but not this line (e.g. no cost of revenue)
                    out.append(_row(ticker, f, period, end, None, None, [], "not_reported", "as_reported", docs))
                continue
            have = [fs for _, fs in fl if all(p in fs for p in parts)]
            val = lambda fs: fs["revenue"]["value"] - fs["cost_of_revenue"]["value"] - fs["operating_income"]["value"] if f == "opex" else fs[f]["value"]
            first, latest = have[0], newest
            used = [latest[p] for p in parts]
            v, r = val(latest), reference.get((f, period))
            tol = max([e["scale"] for e in used] + ([_rounding(r)] if r is not None else [])) // 2 * len(parts)
            label = "no_reference" if r is None else "agree" if abs(v - r) <= tol else "unresolved"
            basis = "restated" if _restated(val(first), v, max(e["scale"] for e in used)) else "as_reported"
            out.append(_row(ticker, f, period, end, v, val(first), used, label, basis, docs))
    return out


def _row(ticker, field, period, end, value, first, used, label, basis, docs):
    ids = [e["extraction_id"] for e in used]
    h = hashlib.sha256(json.dumps([value, ids, label, sorted({docs[i.split("|")[0]] for i in ids})]).encode()).hexdigest()[:16]
    return {"ticker": ticker, "field": field, "period": period, "period_end": end, "value": value,
            "source": "agent" if value is not None else "missing", "method": "computed" if field == "opex" else "reported",
            "label": label, "basis": basis, "first_reported": first, "extraction_ids": ",".join(ids), "input_hash": h}
