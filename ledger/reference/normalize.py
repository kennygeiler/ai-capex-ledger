"""The XBRL answer key for one company: one value per fiscal year for revenue, capex, opex and operating income.

The agent never sees it; reconcile compares the agent's numbers with it. Built on demand from the SEC's companyfacts
(cached), plus the XBRL instance of any recent 10-K that companyfacts hasn't caught up with.

1. Collect full-year duration facts (USD) for each candidate concept, from 10-K filings.
2. Vintages: the same year appears in several 10-Ks (as comparatives, sometimes restated). Keep the latest filed,
   and remember the original and how many filings carried it.
3. One filing per year: the newest 10-K (or 10-K/A) that reports the year, then the best-ranked tag within it; a
   total revenue tag beats a component tag in the same 10-K.
4. Opex: revenue − operating income − cost of revenue, all from that one filing (derive_costs).
"""
import json
from collections import defaultdict
from datetime import date, timedelta

from ..config import CONCEPTS, FORMS_FALLBACK, FORMS_PRIMARY, PREDECESSORS, YEAR_DAYS
from ..ingest.edgar import fetch_json, fetch_tickers
from .xbrl_instance import fill_gaps


def _d(s: str) -> date:
    return date.fromisoformat(s)


def days(start: str, end: str) -> int:
    return (_d(end) - _d(start)).days + 1


def raw_facts(companyfacts: dict, concept: str) -> list[dict]:
    node = companyfacts.get("facts", {}).get("us-gaap", {}).get(concept)
    if not node:
        return []
    out = []
    for u in node.get("units", {}).get("USD", []):
        if "start" not in u or u.get("form") not in FORMS_PRIMARY | FORMS_FALLBACK:
            continue
        out.append({k: u.get(k) for k in ("start", "end", "val", "accn", "form", "filed")} | {"concept": concept, "src": u.get("src", "companyfacts")})
    return out


def best_vintages(facts: list[dict]) -> dict[tuple, dict]:
    """One fact per (start, end): the latest filed, preferring 10-Q/10-K over registration forms."""
    groups = defaultdict(list)
    for f in facts:
        groups[(f["start"], f["end"])].append(f)
    out = {}
    for key, g in groups.items():
        pool = [f for f in g if f["form"] in FORMS_PRIMARY] or g
        pool.sort(key=lambda f: (f["filed"], f["accn"]))
        first, chosen = pool[0], pool[-1]
        out[key] = chosen | {
            "vintages": len({f["accn"] for f in g}),
            "original": first["val"],
            "restated": abs(chosen["val"] - first["val"]) > max(1, abs(first["val"]) * 0.001),
            "fallback_form": chosen["form"] in FORMS_FALLBACK,
            "src": chosen.get("src", "companyfacts"),
        }
    return out


def _src(f: dict) -> dict:
    return {"accn": f["accn"], "form": f["form"], "filed": f["filed"], "start": f["start"], "end": f["end"], "val": f["val"], "src": f.get("src", "companyfacts")}


def fiscal_label(end: str, fye: str | None) -> tuple[int, int]:
    """(fiscal year, fiscal quarter) from the period end and the 'MMDD' fiscal-year-end."""
    fye = fye or "1231"
    m, dd = int(fye[:2]), int(fye[2:])
    e = _d(end)
    ends = []
    for y in (e.year - 1, e.year, e.year + 1):
        day = dd
        while True:
            try:
                ends.append(date(y, m, day))
                break
            except ValueError:
                day -= 1
    fy_end = min(x for x in ends if x >= e - timedelta(days=10))
    months_left = round((fy_end - e).days / 30.44)
    fq = min(4, max(1, 4 - round(months_left / 3)))
    return fy_end.year, fq


def derive_costs(m: dict[str, dict[str, dict]]) -> tuple[dict, dict]:
    """Comparable cost metrics for one period, with a written fallback chain.

    total_costs: revenue - operating income; else the reported CostsAndExpenses line.
    opex (excl. cost of revenue): total_costs - cost of revenue; else a reported OperatingExpenses line that is
    not just total costs; else SG&A + R&D; else banks' NoninterestExpense.
    """
    rev, oi, cor, oprep, cae = m["revenue"], m["operating_income"], m["cost_of_revenue"], m["opex_reported"], m["costs_and_expenses"]
    sga, rnd, nie = m["sga"], m["rnd"], m["noninterest_expense"]
    total, opex = {}, {}
    keep = ("fy_key", "period_start", "period_end", "days", "fiscal_year", "form", "accession", "filed")
    common = {"unit": "USD", "restated": False, "original_value": None, "vintages": None, "fallback_form": False}
    same = lambda d, key, r: key in d and d[key]["period_end"] == r["period_end"] and d[key]["accession"] == r["accession"]  # one filing
    src = lambda name, x: {"metric": name, "concept": x["concept"], "accn": x["accession"], "val": x["value"]}
    for key, r in rev.items():
        base = {f: r.get(f) for f in keep}
        tc = None
        if same(oi, key, r):
            tc, srcs, tmeth, tconcept = r["value"] - oi[key]["value"], [src("revenue", r), src("operating_income", oi[key])], "derived", "Revenue − OperatingIncomeLoss"
        elif same(cae, key, r):
            tc, srcs, tmeth, tconcept = cae[key]["value"], [src("costs_and_expenses", cae[key])], "reported_costs_and_expenses", cae[key]["concept"]
        if tc is not None:
            total[key] = base | common | {"metric": "total_costs", "value": tc, "method": tmeth, "concept": tconcept, "sources": srcs}
        if tc is not None and same(cor, key, r):
            opex[key] = base | common | {"metric": "opex", "value": tc - cor[key]["value"], "method": "derived",
                                          "concept": f"({tconcept}) − CostOfRevenue", "sources": srcs + [src("cost_of_revenue", cor[key])]}
        elif same(oprep, key, r) and (tc is None or abs(oprep[key]["value"] - tc) > abs(tc) * 0.01):
            opex[key] = oprep[key] | {"metric": "opex", "method": "reported_operating_expenses"}
        elif tc is not None and not any(_d(x["period_end"]) >= _d(r["period_end"]) - timedelta(days=730) for x in cor.values()):
            # The company never reports a cost-of-revenue line (railroads, payments, Oracle...): all its operating
            # costs are operating expenses.
            opex[key] = base | common | {"metric": "opex", "value": tc, "method": "no_cost_of_revenue_line", "concept": tconcept, "sources": srcs}
        elif same(sga, key, r):
            v = sga[key]["value"] + (rnd[key]["value"] if same(rnd, key, r) else 0)
            opex[key] = base | common | {"metric": "opex", "value": v, "method": "sga_plus_rnd", "concept": "SG&A + R&D",
                                          "sources": [src("sga", sga[key])] + ([src("rnd", rnd[key])] if same(rnd, key, r) else [])}
        elif same(nie, key, r):
            opex[key] = nie[key] | {"metric": "opex", "method": "noninterest_expense"}
    return total, opex


def annual_series(companyfacts: dict, metric: str, fye: str | None) -> dict[str, dict]:
    """One full-year value per fiscal year, from 10-K filings (latest vintage). Key: 'FY2025'."""
    per_concept: dict[str, dict[str, dict]] = {}
    for c in CONCEPTS[metric]:
        vint = best_vintages(raw_facts(companyfacts, c))
        rows = {}
        for (s, e), f in vint.items():
            if not (YEAR_DAYS[0] <= days(s, e) <= YEAR_DAYS[1]) or not f["form"].startswith("10-K"):
                continue
            fy = fiscal_label(e, fye)[0]
            rows[f"FY{fy}"] = {
                "metric": metric, "fy_key": f"FY{fy}", "value": f["val"], "unit": "USD", "method": "reported",
                "concept": c, "period_start": s, "period_end": e, "days": days(s, e), "fiscal_year": fy,
                "form": f["form"], "accession": f["accn"], "filed": f["filed"], "restated": f["restated"],
                "original_value": f["original"], "vintages": f["vintages"], "fallback_form": False, "sources": [_src(f)],
            }
        if rows:
            per_concept[c] = rows
    recent_cut = f"FY{date.today().year - 4}"
    ranking = sorted(per_concept, key=lambda c: (-sum(k >= recent_cut for k in per_concept[c]), CONCEPTS[metric].index(c), -len(per_concept[c])))
    merged: dict[str, dict] = {}
    for k in sorted({k for rows in per_concept.values() for k in rows}):
        # The newest filing that reports the year wins, as in reconcile: one filing per year, never a tag from an
        # older 10-K next to one from a newer one. Within that filing, the best-ranked tag.
        cands = [per_concept[c][k] for c in ranking if k in per_concept[c]]
        newest = max((r["filed"], r["accession"]) for r in cands)
        here = [r for r in cands if (r["filed"], r["accession"]) == newest]
        # A total revenue tag beats a component tag in the same 10-K (WULF: contract revenue leaves out lease revenue).
        merged[k] = max(here, key=lambda x: x["value"]) if metric == "revenue" else here[0]
    return merged


def merge_facts(new: dict, old: dict) -> dict:
    """Merge a predecessor CIK's facts into the current company's (vintage selection dedupes overlaps)."""
    out = json.loads(json.dumps(new))
    for ns, concepts in old.get("facts", {}).items():
        tgt = out["facts"].setdefault(ns, {})
        for name, node in concepts.items():
            t = tgt.setdefault(name, {"label": node.get("label"), "description": node.get("description"), "units": {}})
            for unit, vals in node.get("units", {}).items():
                t["units"].setdefault(unit, []).extend(vals)
    return out


def company_years(ticker: str) -> dict[str, dict[str, dict]]:
    """{metric: {"FY2025": row}} for one company, built from cached SEC data."""
    cik = fetch_tickers()[0][ticker]["cik"]
    cf, sub = fetch_json("companyfacts", cik)[0], fetch_json("submissions", cik)[0]
    for p in PREDECESSORS.get(ticker, []):
        cf = merge_facts(cf, fetch_json("companyfacts", p["cik"])[0])
    rec = sub["filings"]["recent"]
    tenks = [{"form": f, "filed": fd, "period": rd, "accession": ac}
             for f, fd, rd, ac in zip(rec["form"], rec["filingDate"], rec["reportDate"], rec["accessionNumber"]) if f == "10-K"]
    fill_gaps(cf, cik, tenks[:3], since="2024-01-01")
    years = {m: annual_series(cf, m, sub.get("fiscalYearEnd")) for m in CONCEPTS}
    years["total_costs"], years["opex"] = derive_costs(years)
    return years
