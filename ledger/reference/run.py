"""Run the pipeline: ingest -> normalize -> validate -> export.

    python -m ledger reference              # AI set + S&P 100, raw files cached for 24h
    python -m ledger reference --refresh    # re-download everything from SEC
    python -m ledger reference --only NVDA,MSFT
"""
import argparse
import csv
import json
import time
from collections import Counter
from datetime import datetime, timezone

from .. import config
from ..ingest import edgar
from ..ingest.edgar import ROOT, fetch_json, fetch_tickers
from .normalize import REJECTED, best_vintages, build_company, raw_facts
from .validate import check_company
from .xbrl_instance import fill_gaps

CLEAN = ROOT / "data" / "clean"
EXPORT_METRICS = ["revenue", "capex", "opex", "total_costs", "cost_of_revenue", "operating_income"]
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
    sev = Counter(i["severity"] for i in issues)
    (CLEAN / "pull_log.json").write_text(json.dumps(pull, indent=1))
    print(f"\n{len(built)} companies  quarters {window[0]}..{window[-1]}  years {years[0]}..{years[-1]}  facts {len(rows)}  "
          f"errors {sev['error']}  warnings {sev['warn']}  info {sev['info']}  tiling {tiling['tiling_checks'] - tiling['tiling_failures']}/{tiling['tiling_checks']}  "
          f"network {pull['network_requests']} cache {pull['cache_reads']} failures {len(pull['failures'])}  {pull['seconds']}s")


if __name__ == "__main__":
    main()
