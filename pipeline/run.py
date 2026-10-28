"""Run the pipeline: ingest -> normalize -> validate -> export.

    python3 -m pipeline.run                # AI set + S&P 100, raw files cached for 24h
    python3 -m pipeline.run --refresh      # re-download everything from SEC
    python3 -m pipeline.run --only NVDA,MSFT
"""
import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone

from . import config, edgar
from .edgar import ROOT, fetch_json, fetch_tickers
from .normalize import CONCEPTS, REJECTED, best_vintages, build_company, raw_facts
from .validate import check_company
from .xbrl_instance import fill_gaps

CLEAN = ROOT / "data" / "clean"
EXPORT_METRICS = ["revenue", "capex", "opex", "total_costs", "cost_of_revenue", "operating_income"]
METRIC_DEFS = {
    "revenue": "Total revenue, as filed. Banks: revenue net of interest expense where that is the tag they use.",
    "capex": "Cash paid for property, plant and equipment (cash-flow statement). Finance leases are not included.",
    "opex": "Operating expenses excluding cost of revenue: revenue − cost of revenue − operating income. Comparable across companies, unlike the reported OperatingExpenses line (Amazon's includes cost of sales).",
    "total_costs": "All operating costs including cost of revenue: revenue − operating income. Use it where a company has no cost-of-revenue line (Oracle).",
    "cost_of_revenue": "Cost of revenue / cost of goods and services sold, as filed. Component of opex.",
    "operating_income": "Operating income (loss), as filed. Component of opex.",
}
METHOD_DEFS = {
    "reported": "Value taken straight from a filing (a three-month figure, or a 10-K full year in the annual view).",
    "ytd_diff": "Cash-flow lines are year-to-date in 10-Qs: this quarter = YTD minus the previous YTD with the same start date.",
    "q4_derived": "There is no 10-Q for Q4: this quarter = full year (10-K) minus the first nine months.",
    "fy_minus_quarters": "Full year minus the three quarters already held (used when no nine-month figure exists, or when the nine-month figure is on an older basis than restated quarters).",
    "derived": "Computed from other metrics of the same period (see the metric definition).",
    "reported_costs_and_expenses": "The company's total CostsAndExpenses line, used as total costs when there is no operating-income line.",
    "sga_plus_rnd": "Opex as SG&A plus R&D, used when the company reports neither operating income nor total costs (common in pharma).",
    "noninterest_expense": "Banks: non-interest expense, the bank equivalent of operating expenses.",
    "no_cost_of_revenue_line": "The company reports no cost-of-revenue line at all (e.g. railroads, payment networks, Oracle), so its total operating costs are its opex.",
    "reported_operating_expenses": "The company's own OperatingExpenses line, used when cost of revenue is not tagged.",
}
SIC_DIVISIONS = [(100, 999, "Agriculture"), (1000, 1499, "Mining & energy"), (1500, 1799, "Construction"), (2000, 3999, "Manufacturing"),
                 (4000, 4999, "Transport, telecom & utilities"), (5000, 5199, "Wholesale"), (5200, 5999, "Retail"),
                 (6000, 6799, "Finance & real estate"), (7000, 8999, "Services"), (9100, 9999, "Public administration")]


NAME_OVERRIDES = {"T": "AT&T", "IBM": "IBM", "UPS": "UPS", "MMM": "3M", "JPM": "JPMorgan Chase", "BNY": "BNY", "MA": "Mastercard", "V": "Visa",
                  "KO": "Coca-Cola", "PEP": "PepsiCo", "PG": "Procter & Gamble", "HD": "Home Depot", "BRK-B": "Berkshire Hathaway", "GE": "GE Aerospace",
                  "RTX": "RTX", "CVS": "CVS Health", "UNH": "UnitedHealth", "TMUS": "T-Mobile US", "NEE": "NextEra Energy", "AIG": "AIG", "COF": "Capital One",
                  "USB": "U.S. Bancorp", "SO": "Southern Company", "GS": "Goldman Sachs", "MS": "Morgan Stanley", "BAC": "Bank of America", "WFC": "Wells Fargo",
                  "C": "Citigroup", "AXP": "American Express", "MET": "MetLife", "BLK": "BlackRock", "SCHW": "Charles Schwab", "XOM": "ExxonMobil",
                  "CVX": "Chevron", "COP": "ConocoPhillips", "LLY": "Eli Lilly", "JNJ": "Johnson & Johnson", "MRK": "Merck", "BMY": "Bristol-Myers Squibb",
                  "ABBV": "AbbVie", "ABT": "Abbott", "TMO": "Thermo Fisher", "DHR": "Danaher", "MDT": "Medtronic", "ISRG": "Intuitive Surgical",
                  "COST": "Costco", "WMT": "Walmart", "TGT": "Target", "LOW": "Lowe's", "MCD": "McDonald's", "SBUX": "Starbucks", "NKE": "Nike",
                  "DIS": "Disney", "CMCSA": "Comcast", "CHTR": "Charter", "VZ": "Verizon", "NFLX": "Netflix", "BKNG": "Booking", "UBER": "Uber",
                  "CRM": "Salesforce", "ADBE": "Adobe", "NOW": "ServiceNow", "INTU": "Intuit", "CSCO": "Cisco", "INTC": "Intel", "QCOM": "Qualcomm",
                  "TXN": "Texas Instruments", "AVGO": "Broadcom", "AAPL": "Apple", "ACN": "Accenture", "PLTR": "Palantir", "PYPL": "PayPal",
                  "LIN": "Linde", "CAT": "Caterpillar", "DE": "Deere", "HON": "Honeywell", "LMT": "Lockheed Martin", "GD": "General Dynamics", "BA": "Boeing",
                  "EMR": "Emerson", "UNP": "Union Pacific", "FDX": "FedEx", "F": "Ford", "GM": "General Motors", "DUK": "Duke Energy", "AMT": "American Tower",
                  "SPG": "Simon Property", "MO": "Altria", "PM": "Philip Morris", "MDLZ": "Mondelez", "CL": "Colgate-Palmolive", "AMGN": "Amgen",
                  "GILD": "Gilead", "PFE": "Pfizer"}


def sector(sic) -> str:
    try:
        n = int(sic)
    except (TypeError, ValueError):
        return "Unclassified"
    return next((name for lo, hi, name in SIC_DIVISIONS if lo <= n <= hi), "Unclassified")


def universe() -> list[dict]:
    ai = {c["ticker"]: c | {"sets": ["AI set"]} for c in config.AI_SET}
    for t in config.SP100:
        if t in ai:
            ai[t]["sets"].append("S&P 100")
        else:
            ai[t] = {"ticker": t, "name": None, "group": "S&P 100", "sets": ["S&P 100"]}
    return list(ai.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--only", default="")
    args = ap.parse_args()
    started, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), time.monotonic()
    only = {t.strip().upper() for t in args.only.split(",") if t.strip()}

    tickers, tick_meta = fetch_tickers(refresh=args.refresh)
    companies, failures = [], []
    for c in universe():
        if only and c["ticker"] not in only:
            continue
        hit = tickers.get(c["ticker"]) or tickers.get(c["ticker"].replace("-", "."))
        if not hit:
            failures.append({"ticker": c["ticker"], "stage": "resolve", "error": "Ticker not in SEC company_tickers.json"})
            continue
        companies.append(c | {"cik": hit["cik"], "sec_title": hit["title"]})

    raw_manifest = [tick_meta | {"ticker": "*", "kind": "company_tickers"}]
    built = []
    for c in companies:
        try:
            cf, m1 = fetch_json("companyfacts", c["cik"], refresh=args.refresh)
            sub, m2 = fetch_json("submissions", c["cik"], refresh=args.refresh)
            for p in config.PREDECESSORS.get(c["ticker"], []):
                old, mp = fetch_json("companyfacts", p["cik"], refresh=args.refresh)
                raw_manifest.append(mp | {"ticker": c["ticker"], "kind": f"companyfacts (predecessor CIK {p['cik']})"})
                cf = merge_facts(cf, old)
        except Exception as e:  # keep going; the admin view lists the failure
            failures.append({"ticker": c["ticker"], "stage": "fetch", "error": str(e)})
            print(f"  {c['ticker']:6} FAILED {e}")
            continue
        raw_manifest += [m1 | {"ticker": c["ticker"], "kind": "companyfacts"}, m2 | {"ticker": c["ticker"], "kind": "submissions"}]
        rec = sub["filings"]["recent"]
        periodic = [(f, fd, rd, ac) for f, fd, rd, ac in zip(rec["form"], rec["filingDate"], rec["reportDate"], rec["accessionNumber"]) if f in ("10-Q", "10-K")]
        # companyfacts can lag new filings: parse the XBRL instance XML of any recent filing it doesn't cover.
        try:
            gap_fills = fill_gaps(cf, c["cik"], [{"form": f, "filed": fd, "period": rd, "accession": ac} for f, fd, rd, ac in periodic[:6]], since="2024-01-01")
        except Exception as e:
            gap_fills = [{"status": f"failed: {e}"}]
        n_before = len(REJECTED)
        metrics, notes, annual = build_company(cf, sub.get("fiscalYearEnd"))
        built.append({
            "c": c, "name": c.get("name") or NAME_OVERRIDES.get(c["ticker"]) or (cf.get("entityName") or sub.get("name")), "legal_name": cf.get("entityName"),
            "fye": sub.get("fiscalYearEnd"), "exchanges": sub.get("exchanges"), "sic": sub.get("sic"), "sic_desc": sub.get("sicDescription"),
            "metrics": metrics, "annual": annual, "notes": notes, "cf": cf,
            "vint": {m: best_vintages(raw_facts(cf, notes["concepts"][m][0])) if notes["concepts"][m] else {} for m in ("revenue", "capex")},
            "first_filed": min((fd for _, fd, _, _ in periodic), default=None),
            "last_period_end": max((rd for _, _, rd, _ in periodic if rd), default=None),
            "filings": [{"form": f, "filed": fd, "period": rd, "accession": ac} for f, fd, rd, ac in periodic[:8]],
            "rejected": REJECTED[n_before:], "gap_fills": gap_fills,
            "n_concepts": len(cf.get("facts", {}).get("us-gaap", {})),
        })
        if gap_fills:
            print(f"  {c['ticker']:6} parsed {len([g for g in gap_fills if g.get('status') == 'parsed'])} filing(s) from XBRL instance XML")
        print(f"  {c['ticker']:6} {len(metrics['revenue']):3} rev q, {len(metrics['capex']):3} capex q, {len(annual['revenue']):2} rev FY  ({m1['cache']})")

    # Quarterly window: 8 calendar quarters ending at the latest one where enough companies report revenue.
    cov = Counter(cq for b in built for cq in b["metrics"]["revenue"])
    need = max(1, round(len(built) * config.WINDOW_COVERAGE))
    end_q = max(cq for cq, n in cov.items() if n >= need)
    window = [q for q in sorted(cov) if q <= end_q][-config.WINDOW_QUARTERS:]
    # Annual window: last 5 fiscal years where enough companies have a 10-K.
    fy_cov = Counter(k for b in built for k in b["annual"]["revenue"])
    end_fy = max(k for k, n in fy_cov.items() if n >= need)
    years = [k for k in sorted(fy_cov) if k <= end_fy][-config.WINDOW_YEARS:]

    issues, tiling = [], Counter()
    for b in built:
        t = b["c"]["ticker"]
        iss, st = check_company(t, b["metrics"], b["vint"], window, b["first_filed"], b["last_period_end"])
        issues += iss
        tiling.update(st)
        for rj in b["rejected"]:
            issues.append({"severity": "info", "check": "mistagged_fact_dropped", "ticker": t, "metric": rj["concept"], "cal_q": None,
                           "message": f"Dropped {rj['start']} to {rj['end']} value {rj['val']:,} from {rj['accn']}: {rj['reason']}. Quarter derived instead."})
        for col in b["notes"]["collisions"]:
            if col["cal_q"] < window[0] or col["metric"] not in EXPORT_METRICS:
                continue
            if col.get("moved_to"):
                issues.append({"severity": "info", "check": "calendar_shift", "ticker": t, "metric": col["metric"], "cal_q": col["moved_to"],
                               "message": f"Fiscal quarter ending {col['moved_end']} shares most days with {col['cal_q']} (taken by the quarter ending {col['kept_end']}), so it is placed in {col['moved_to']}."})
            else:
                issues.append({"severity": "warn", "check": "calendar_collision", "ticker": t, "metric": col["metric"], "cal_q": col["cal_q"],
                               "message": f"Two fiscal quarters map to {col['cal_q']}; kept the one ending {col['kept_end']}."})

    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
    pull = {
        "started_at": started, "finished_at": finished, "seconds": round(time.monotonic() - t0, 1),
        "user_agent": "Set in .env (name and contact email, as SEC requires)", "rate_limit": f"{1 / edgar.MIN_INTERVAL:.1f} requests per second at most",
        "network_requests": sum(1 for x in edgar.LOG if x["source"] == "network"),
        "cache_reads": sum(1 for x in edgar.LOG if x["source"] == "cache"),
        "bytes_downloaded": sum(x["bytes"] for x in edgar.LOG if x["source"] == "network"),
        "http_errors": sum(1 for x in edgar.LOG if x.get("error")),
        "failures": failures, "log": edgar.LOG,
    }
    export(built, window, years, issues, tiling, raw_manifest, pull)


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


def trace_for(b: dict, metric: str, cq: str) -> dict | None:
    """Every raw XBRL fact (from every filing) behind one cleaned quarter: the parsing proof."""
    r = b["metrics"][metric].get(cq)
    if not r or r["method"] == "derived":
        return None
    node = b["cf"]["facts"]["us-gaap"].get(r["concept"], {})
    raw = node.get("units", {}).get("USD", [])
    steps = []
    for s in r["sources"]:
        rows = [{k: x.get(k) for k in ("start", "end", "val", "accn", "form", "filed", "fy", "fp", "frame")}
                for x in raw if x.get("start") == s["start"] and x.get("end") == s["end"]]
        for x in rows:
            x["chosen"] = x["accn"] == s["accn"] and x["val"] == s["val"]
        steps.append({"start": s["start"], "end": s["end"], "value": s["val"], "vintages": sorted(rows, key=lambda x: x["filed"])})
    return {"concept": r["concept"], "label": node.get("label"), "description": (node.get("description") or "")[:400], "method": r["method"], "steps": steps}


def export(built, window, years, issues, tiling, raw_manifest, pull):
    CLEAN.mkdir(parents=True, exist_ok=True)
    rows = []
    for b in built:
        t = b["c"]["ticker"]
        for metric in EXPORT_METRICS:
            for cq, r in b["metrics"][metric].items():
                rows.append({"ticker": t, "period_type": "quarter", **{k: v for k, v in r.items() if k not in ("sources", "fy_key")}, "fy_key": None,
                             "in_window": cq in window, "sources": r["sources"]})
            for k, r in b["annual"][metric].items():
                rows.append({"ticker": t, "period_type": "year", **{kk: v for kk, v in r.items() if kk != "sources"}, "cal_q": None,
                             "in_window": k in years, "sources": r["sources"]})
    rows.sort(key=lambda r: (r["ticker"], r["metric"], r["period_type"], r["cal_q"] or r["fy_key"] or ""))

    cols = ["ticker", "period_type", "metric", "cal_q", "fy_key", "value", "unit", "method", "source_api", "basis_conflict", "concept", "period_start", "period_end",
            "days", "days_outside_cal_q", "fiscal_year", "fiscal_quarter", "form", "accession", "filed", "restated", "original_value", "vintages",
            "fallback_form", "in_window"]
    with open(CLEAN / "facts.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols + ["sources"], extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r | {"sources": json.dumps(r["sources"], separators=(",", ":"))})
    with open(CLEAN / "quarterly_wide.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "name", "cal_q", "revenue", "capex", "opex", "total_costs"])
        for b in built:
            for cq in window:
                w.writerow([b["c"]["ticker"], b["name"], cq] + [b["metrics"][m].get(cq, {}).get("value", "") for m in ("revenue", "capex", "opex", "total_costs")])
    with open(CLEAN / "annual_wide.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "name", "fiscal_year", "period_end", "revenue", "capex", "opex", "total_costs"])
        for b in built:
            for k in years:
                r = b["annual"]["revenue"].get(k, {})
                w.writerow([b["c"]["ticker"], b["name"], k, r.get("period_end", "")] + [b["annual"][m].get(k, {}).get("value", "") for m in ("revenue", "capex", "opex", "total_costs")])

    with open(CLEAN / "companies.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ticker", "name", "cik", "sets", "group", "sector", "fiscal_year_end", "revenue_q", "capex_q", "opex_q", "revenue_fy", "capex_fy", "opex_fy", "revenue_tag", "capex_tag"])
        for b in built:
            c = b["c"]
            w.writerow([c["ticker"], b["name"], c["cik"], "+".join(c["sets"]), c["group"], sector(b["sic"]), b["fye"]]
                       + [sum(q in b["metrics"][m] for q in window) for m in ("revenue", "capex", "opex")]
                       + [sum(k in b["annual"][m] for k in years) for m in ("revenue", "capex", "opex")]
                       + [(b["notes"]["concepts"]["revenue"] or [""])[0], (b["notes"]["concepts"]["capex"] or [""])[0]])
    sev = Counter(i["severity"] for i in issues)
    ai_tickers = {c["ticker"] for c in config.AI_SET}
    companies = [{
        "ticker": b["c"]["ticker"], "cik": b["c"]["cik"], "name": b["name"], "legal_name": b["legal_name"], "group": b["c"]["group"],
        "sets": b["c"]["sets"], "note": b["c"].get("note"), "sector": sector(b["sic"]), "sic": b["sic_desc"], "fiscal_year_end": b["fye"],
        "exchanges": b["exchanges"], "gap_fills": b["gap_fills"], "concepts": b["notes"]["concepts"], "n_concepts": b["n_concepts"], "recent_filings": b["filings"],
        "discovery": b["notes"]["discovery"],
        "coverage": {m: sum(cq in b["metrics"][m] for cq in window) for m in EXPORT_METRICS},
        "coverage_annual": {m: sum(k in b["annual"][m] for k in years) for m in EXPORT_METRICS},
    } for b in built]
    traces = {}
    for b in built:
        if b["c"]["ticker"] not in ai_tickers:
            continue
        for metric in ("revenue", "capex", "cost_of_revenue", "operating_income"):
            for cq in window:
                tr = trace_for(b, metric, cq)
                if tr:
                    traces[f"{b['c']['ticker']}|{metric}|{cq}"] = tr
    meta = {
        "generated_at": pull["finished_at"],
        "source": "SEC EDGAR XBRL company facts (data.sec.gov/api/xbrl/companyfacts) and submissions",
        "window": window, "years": years,
        "calendar_rule": "A fiscal quarter belongs to the calendar quarter that holds most of its days.",
        "metrics": METRIC_DEFS, "methods": METHOD_DEFS, "concept_candidates": CONCEPTS, "discovery_patterns": config.DISCOVERY,
        "excluded": config.EXCLUDED, "predecessors": config.PREDECESSORS,
        "quality": {"errors": sev["error"], "warnings": sev["warn"], "info": sev["info"],
                    "tiling_checks": tiling["tiling_checks"], "tiling_failures": tiling["tiling_failures"]},
        "raw_files": raw_manifest,
    }
    dataset = {"meta": meta, "pull": pull, "companies": companies, "issues": issues, "traces": traces, "facts": rows}
    (CLEAN / "dataset.json").write_text(json.dumps(dataset, separators=(",", ":")))
    (CLEAN / "pull_log.json").write_text(json.dumps(pull, indent=1))

    # viz.json: what the explorer loads. Core metrics only, quarters from 4 before the window (so YoY works),
    # fiscal years from 1 before; lineage sources only inside the windows; facts packed as rows of a column list.
    VIZ_METRICS = {"revenue", "capex", "opex", "total_costs"}
    q_from = sorted({r["cal_q"] for r in rows if r["cal_q"] and r["cal_q"] < window[0]})[-4:][:1] or window[:1]
    y_from = sorted({r["fy_key"] for r in rows if r["fy_key"] and r["fy_key"] < years[0]})[-1:] or years[:1]
    fact_cols = ["ticker", "period_type", "metric", "cal_q", "fy_key", "value", "method", "source_api", "concept", "period_start", "period_end",
                 "days", "days_outside_cal_q", "fiscal_year", "fiscal_quarter", "form", "accession", "filed", "restated", "original_value",
                 "vintages", "basis_conflict", "in_window", "sources"]
    packed = []
    for r in rows:
        if r["metric"] not in VIZ_METRICS:
            continue
        if (r["period_type"] == "quarter" and r["cal_q"] >= q_from[0]) or (r["period_type"] == "year" and r["fy_key"] >= y_from[0]):
            packed.append([r.get(c) if (c != "sources" or r["in_window"]) else None for c in fact_cols])
    viz = {"meta": meta, "pull": pull, "companies": companies,
           "issues": [i for i in issues if i["cal_q"] is None or i["cal_q"] >= q_from[0]], "traces": traces,
           "fact_cols": fact_cols, "facts": packed}
    (CLEAN / "viz.json").write_text(json.dumps(viz, separators=(",", ":")))
    (CLEAN / "quality.json").write_text(json.dumps({"meta": meta["quality"], "issues": issues}, indent=1))
    write_quality_md(meta, companies, issues, pull)
    print(f"\n{len(built)} companies  quarters {window[0]}..{window[-1]}  years {years[0]}..{years[-1]}  facts {len(rows)}  "
          f"errors {sev['error']}  warnings {sev['warn']}  info {sev['info']}  tiling {tiling['tiling_checks'] - tiling['tiling_failures']}/{tiling['tiling_checks']}  "
          f"network {pull['network_requests']} cache {pull['cache_reads']} failures {len(pull['failures'])}  {pull['seconds']}s")


def write_quality_md(meta, companies, issues, pull):
    L = ["# Data quality report\n", f"Generated {meta['generated_at']}. Quarters {meta['window'][0]} to {meta['window'][-1]}; fiscal years {meta['years'][0]} to {meta['years'][-1]}.\n",
         f"- Companies: {len(companies)}; pull failures: {len(pull['failures'])}",
         f"- Errors: {meta['quality']['errors']}, warnings: {meta['quality']['warnings']}, info: {meta['quality']['info']}",
         f"- Tiling checks: {meta['quality']['tiling_checks'] - meta['quality']['tiling_failures']} of {meta['quality']['tiling_checks']} pass\n",
         "## Coverage (quarters of 8 / fiscal years of 5)\n", "| Ticker | Sector | Revenue | Capex | Opex | Total costs | Revenue tag | Capex tag |", "|---|---|---|---|---|---|---|---|"]
    for c in companies:
        cv, ca, cn = c["coverage"], c["coverage_annual"], c["concepts"]
        L.append(f"| {c['ticker']} | {c['sector']} | {cv['revenue']}/{ca['revenue']} | {cv['capex']}/{ca['capex']} | {cv['opex']}/{ca['opex']} | {cv['total_costs']}/{ca['total_costs']} | {(cn['revenue'] or ['–'])[0]} | {(cn['capex'] or ['–'])[0]} |")
    if pull["failures"]:
        L += ["\n## Pull failures\n"] + [f"- {f['ticker']} ({f['stage']}): {f['error']}" for f in pull["failures"]]
    L += ["\n## Excluded\n"] + [f"- **{e['ticker']}** ({e['name']}): {e['reason']}" for e in meta["excluded"]]
    for s in ("error", "warn", "info"):
        sub = [i for i in issues if i["severity"] == s]
        if sub:
            L.append(f"\n## {s.title()} ({len(sub)})\n")
            L += [f"- {i['ticker']} {i['metric']} {i['cal_q'] or ''} [{i['check']}]: {i['message']}" for i in sub]
    (CLEAN / "quality.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
