"""Turn raw XBRL company facts into one clean value per company, metric and calendar quarter.

The steps, in order:
1. Collect duration facts (USD, with start and end) for each candidate concept, from 10-Q/10-K
   (and S-1/424B4 as a flagged fallback for recent IPOs).
2. Vintages: the same period appears in many filings (as comparatives, and sometimes restated).
   Keep the latest-filed value and remember the original and how many filings carried it.
3. Discrete quarters: take 3-month facts as filed. Where a quarter is only implied (cash-flow
   lines are year-to-date in 10-Qs; Q4 exists only inside the 10-K), subtract the shorter
   period from the longer one that shares its start date.
4. Calendar alignment: a fiscal quarter goes to the calendar quarter holding most of its days.
5. Concept choice: per company, candidate tags are ranked by how many quarters they cover;
   each quarter takes the best-ranked tag that has it.
6. Derived metrics: total_costs = revenue - operating income; opex = total_costs - cost of revenue.
"""
from collections import defaultdict
from datetime import date, timedelta

REJECTED: list[dict] = []  # filled during a run; reported in the quality file

from ..config import CONCEPTS, FORMS_FALLBACK, FORMS_PRIMARY, QUARTER_DAYS, YEAR_DAYS


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


def discrete_quarters(vint: dict[tuple, dict]) -> dict[str, dict]:
    """Map quarter end date -> {start, end, value, method, sources, fact}."""
    q: dict[str, dict] = {}
    years = {e: f for (s, e), f in vint.items() if YEAR_DAYS[0] <= days(s, e) <= YEAR_DAYS[1]}
    for (s, e), f in vint.items():
        if QUARTER_DAYS[0] <= days(s, e) <= QUARTER_DAYS[1]:
            fy = years.get(e)
            # Filer tagging error: a "quarter" carrying the full-year value (seen in Oracle 10-Ks). Drop it; derive instead.
            if fy and f["val"] and abs(f["val"] - fy["val"]) <= abs(fy["val"]) * 0.01:
                REJECTED.append({"concept": f["concept"], "start": s, "end": e, "val": f["val"], "accn": f["accn"], "reason": "quarter equals full-year value"})
                continue
            q[e] = {"start": s, "end": e, "value": f["val"], "method": "reported", "sources": [_src(f)], "fact": f}

    by_start = defaultdict(list)
    for (s, e), f in vint.items():
        by_start[s].append((e, f))
    for s, lst in by_start.items():
        lst.sort(key=lambda x: x[0])
        for e2, f2 in lst:
            dur2 = days(s, e2)
            if dur2 <= QUARTER_DAYS[1] or e2 in q:
                continue
            for e1, f1 in lst:
                gap = (_d(e2) - _d(e1)).days
                if QUARTER_DAYS[0] <= gap <= QUARTER_DAYS[1]:
                    is_year = YEAR_DAYS[0] <= dur2 <= YEAR_DAYS[1]
                    q[e2] = {
                        "start": (_d(e1) + timedelta(days=1)).isoformat(), "end": e2,
                        "value": f2["val"] - f1["val"],
                        "method": "q4_derived" if is_year else "ytd_diff",
                        "sources": [_src(f2), _src(f1)], "fact": f2,
                    }
                    break

    # Q4 from full year minus three quarters: a last resort when nothing else exists, and the
    # preferred route when FY - 9M mixes bases (restated quarters filed after the nine-month figure).
    for (s, e), f in vint.items():
        if not (YEAR_DAYS[0] <= days(s, e) <= YEAR_DAYS[1]):
            continue
        inner = sorted((x for x in q.values() if x["start"] >= s and x["end"] < e), key=lambda x: x["end"])
        if e in q:
            cur = q[e]
            if cur["method"] != "q4_derived" or len(inner) != 3 or any(x["method"] != "reported" for x in inner):
                continue
            alt = f["val"] - sum(x["value"] for x in inner)
            nine_filed = cur["sources"][1]["filed"]
            restated_after = all(x["sources"][0]["filed"] > nine_filed for x in inner)
            if abs(alt - cur["value"]) > max(1e6, abs(cur["value"]) * 0.02) and (cur["value"] < 0 or restated_after):
                q[e] = cur | {"value": alt, "method": "fy_minus_quarters", "basis_conflict": True,
                              "sources": [_src(f)] + [x["sources"][0] for x in inner]}
            continue
        if len(inner) == 3:
            last_end = _d(inner[-1]["end"])
            q[e] = {
                "start": (last_end + timedelta(days=1)).isoformat(), "end": e,
                "value": f["val"] - sum(x["value"] for x in inner),
                "method": "fy_minus_quarters",
                "sources": [_src(f)] + [s_ for x in inner for s_ in x["sources"][:1]], "fact": f,
            }
    return q


def calendar_quarters_ranked(start: str, end: str) -> list[tuple[str, int]]:
    """Calendar quarters overlapping [start, end], most-overlapping first: [(quarter, days outside it)]."""
    s, e = _d(start), _d(end)
    out = []
    cur = date(s.year, 3 * ((s.month - 1) // 3) + 1, 1)
    while cur <= e:
        nm = cur.month + 3
        nxt = date(cur.year + (nm > 12), (nm - 1) % 12 + 1, 1)
        overlap = (min(e, nxt - timedelta(days=1)) - max(s, cur)).days + 1
        if overlap > 0:
            out.append((f"{cur.year}Q{(cur.month - 1) // 3 + 1}", (e - s).days + 1 - overlap))
        cur = nxt
    return sorted(out, key=lambda x: x[1])


def calendar_quarter(start: str, end: str) -> tuple[str, int]:
    """Calendar quarter holding most days of [start, end]; also returns days outside it."""
    return calendar_quarters_ranked(start, end)[0]


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


RECENT_FROM = (date.today() - timedelta(days=3 * 365)).isoformat()


def concept_series(companyfacts: dict, metric: str) -> tuple[dict[str, dict], list[str]]:
    """Best quarter per end date across candidate concepts. Returns (quarters, concept ranking)."""
    per_concept = {}
    for c in CONCEPTS[metric]:
        facts = raw_facts(companyfacts, c)
        if facts:
            per_concept[c] = discrete_quarters(best_vintages(facts))
    # Rank by coverage of the last three years first (tags change over time), then by all history.
    recent = lambda c: sum(1 for e in per_concept[c] if e >= RECENT_FROM)
    ranking = sorted(per_concept, key=lambda c: (-recent(c), CONCEPTS[metric].index(c), -len(per_concept[c])))
    merged: dict[str, dict] = {}
    for c in ranking:
        for end, qv in per_concept[c].items():
            merged.setdefault(end, qv | {"concept": c})
    return merged, ranking


def build_company(companyfacts: dict, fye: str | None):
    """Returns ({metric: {calQ: row}}, notes, {metric: {FYkey: row}})."""
    out: dict[str, dict[str, dict]] = {}
    notes = {"concepts": {}, "collisions": []}
    for metric in CONCEPTS:
        series, ranking = concept_series(companyfacts, metric)
        notes["concepts"][metric] = ranking
        rows: dict[str, dict] = {}
        # Quarters some fiscal period naturally maps to: a shifted quarter may never take one of these,
        # which stops one historical collision from cascading through every later quarter.
        natural = {calendar_quarters_ranked(qv["start"], end)[0][0] for end, qv in series.items()}
        for end, qv in sorted(series.items()):
            ranked = calendar_quarters_ranked(qv["start"], end)
            cq, outside = ranked[0]
            if cq in rows:
                # Two fiscal quarters land in one calendar quarter (non-13-week calendars such as Costco's
                # 12/12/12/16 weeks). Move this one to its next-best calendar quarter if that is free.
                alt = next(((q, o) for q, o in ranked[1:] if q not in rows and q not in natural and o <= (days(qv["start"], end) * 0.6)), None)
                if alt:
                    notes["collisions"].append({"metric": metric, "cal_q": cq, "kept_end": rows[cq]["period_end"], "moved_to": alt[0], "moved_end": end})
                    cq, outside = alt
                else:
                    notes["collisions"].append({"metric": metric, "cal_q": cq, "kept_end": rows[cq]["period_end"]})
                    continue
            fy, fq = fiscal_label(end, fye)
            f = qv["fact"]
            rows[cq] = {
                "metric": metric, "cal_q": cq, "value": qv["value"], "unit": "USD",
                "method": qv["method"], "concept": qv["concept"],
                "period_start": qv["start"], "period_end": end, "days": days(qv["start"], end), "days_outside_cal_q": outside,
                "fiscal_year": fy, "fiscal_quarter": fq,
                "form": f["form"], "accession": f["accn"], "filed": f["filed"],
                "basis_conflict": qv.get("basis_conflict", False), "restated": f["restated"], "original_value": f["original"] if qv["method"] == "reported" else None,
                "vintages": f["vintages"], "fallback_form": f["fallback_form"],
                "source_api": "xbrl_instance" if any(x.get("src") == "xbrl_instance" for x in qv["sources"]) else "companyfacts",
                "sources": qv["sources"],
            }
        out[metric] = rows

    out["total_costs"], out["opex"] = derive_costs(out, "cal_q")

    # Annual view (10-K full years), for the "last 5 years" reading of the brief.
    annual: dict[str, dict[str, dict]] = {}
    for metric in CONCEPTS:
        annual[metric] = annual_series(companyfacts, metric, fye)
    annual["total_costs"], annual["opex"] = derive_costs(annual, "fy_key")
    notes["discovery"] = discovery_scan(companyfacts)
    return out, notes, annual


def r_api(m) -> str:
    return "derived"


def derive_costs(m: dict[str, dict[str, dict]], k: str) -> tuple[dict, dict]:
    """Comparable cost metrics for one period, with a written fallback chain.

    total_costs: revenue - operating income; else the reported CostsAndExpenses line.
    opex (excl. cost of revenue): total_costs - cost of revenue; else a reported OperatingExpenses line that is
    not just total costs; else SG&A + R&D; else banks' NoninterestExpense.
    """
    rev, oi, cor, oprep, cae = m["revenue"], m["operating_income"], m["cost_of_revenue"], m["opex_reported"], m["costs_and_expenses"]
    sga, rnd, nie = m["sga"], m["rnd"], m["noninterest_expense"]
    total, opex = {}, {}
    keep = ("cal_q", "fy_key", "period_start", "period_end", "days", "days_outside_cal_q", "fiscal_year", "fiscal_quarter", "form", "accession", "filed")
    common = {"unit": "USD", "restated": False, "original_value": None, "vintages": None, "fallback_form": False, "basis_conflict": False, "source_api": r_api(m)}
    same = lambda d, key, r: key in d and d[key]["period_end"] == r["period_end"]
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
                "metric": metric, "fy_key": f"FY{fy}", "cal_q": None, "value": f["val"], "unit": "USD", "method": "reported",
                "concept": c, "period_start": s, "period_end": e, "days": days(s, e), "days_outside_cal_q": None,
                "fiscal_year": fy, "fiscal_quarter": None, "form": f["form"], "accession": f["accn"], "filed": f["filed"],
                "basis_conflict": False, "restated": f["restated"], "original_value": f["original"], "vintages": f["vintages"],
                "fallback_form": False, "source_api": f.get("src", "companyfacts"), "sources": [_src(f)],
            }
        if rows:
            per_concept[c] = rows
    recent_cut = f"FY{date.today().year - 4}"
    ranking = sorted(per_concept, key=lambda c: (-sum(k >= recent_cut for k in per_concept[c]), CONCEPTS[metric].index(c), -len(per_concept[c])))
    merged: dict[str, dict] = {}
    for c in ranking:
        for k, r in per_concept[c].items():
            merged.setdefault(k, r)
    return merged


def discovery_scan(companyfacts: dict) -> dict[str, list[dict]]:
    """Scan every us-gaap concept the company has ever reported against the DISCOVERY patterns.

    For each match: its label (from the filing taxonomy), how many discrete quarters it yields overall and
    in the last three years, and whether it is in our candidate list. This is how a company's label is found.
    """
    import re
    from ..config import DISCOVERY
    gaap = companyfacts.get("facts", {}).get("us-gaap", {})
    n_rejected = len(REJECTED)  # the scan re-runs quarter building; don't double-log rejections
    candidates = {c for cs in CONCEPTS.values() for c in cs}
    out = {}
    for family, pattern in DISCOVERY.items():
        rx = re.compile(pattern)
        hits = []
        for concept, node in gaap.items():
            if not rx.match(concept) or "USD" not in node.get("units", {}):
                continue
            q = discrete_quarters(best_vintages(raw_facts(companyfacts, concept)))
            hits.append({
                "concept": concept, "label": node.get("label"),
                "quarters_all": len(q), "quarters_recent": sum(1 for e in q if e >= RECENT_FROM),
                "last_period_end": max(q) if q else None, "candidate": concept in candidates,
            })
        out[family] = sorted(hits, key=lambda h: (-h["quarters_recent"], -h["quarters_all"]))
    del REJECTED[n_rejected:]
    return out
