"""python -m ledger ingest --stage N | --ticker X …

For the companies: list filings, fetch primary documents (cached), parse tables, locate statements, write
data/docs/<cik>/<accession>.tables.json and a `documents` row each, load reference values, log a `runs` row per step.
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone

from .. import store
from ..config import MVP_YEARS, add_scope, scope

from ..ingest.filings import fetch_documents, list_filings
from ..ingest.statements import assemble, locate
from ..ingest.tables import PARSER_VERSION, document_units, parse_tables
from ..reference.normalize import company_years

DOCS = store.ROOT / "data" / "docs"


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def parse_one(f) -> dict:
    """Parse one filing into its stored JSON. Deterministic: no timestamps inside, sorted keys."""
    doc = f.path.read_bytes()
    tables = parse_tables(doc)
    loc = locate(tables)
    units = document_units(doc)
    statements = {k: assemble(tables, loc[k], units) if loc[k] else None for k in ("income", "cash_flow")}
    return {"accession": f.accession, "ticker": f.ticker, "form": f.form, "period": f.period, "url": f.url,
            "sha256": hashlib.sha256(doc).hexdigest(), "parser_version": PARSER_VERSION,
            "statements": statements, "located": loc, "table_count": len(tables), "tables": tables}


def load_reference(con, tickers: list[str]) -> int:
    """The XBRL answer key for these companies (ledger/reference), for the fiscal years in the window."""
    rows = []
    for t in tickers:
        for metric, years in company_years(t).items():
            if metric not in ("revenue", "capex", "opex", "operating_income"):
                continue
            for k, r in years.items():
                if k in MVP_YEARS:
                    rows.append({"ticker": t, "field": metric, "period": k, "value": int(r["value"]), "method": r["method"], "concept": r["concept"],
                                 "period_start": r["period_start"], "period_end": r["period_end"], "accession": r["accession"],
                                 "restated": bool(r["restated"]), "original_value": r["original_value"]})
    con.execute("DELETE FROM reference_values WHERE ticker IN (SELECT unnest(?))", [tickers])
    return store.write(con, "reference_values", rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger ingest")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    tickers, name = scope(a)
    con = store.init(a.db)
    run_id = f"ingest-{_now()}"
    t0 = time.monotonic()
    filings = list_filings(tickers)
    manifest = {m["accession"]: m for m in fetch_documents(filings)}
    store.write(con, "runs", [{"run_id": run_id, "step": "ingest", "subject": scope(a)[1], "started_at": _now(),
                               "seconds": round(time.monotonic() - t0, 2), "outcome": "ok", "versions": json.dumps({}),
                               "detail": json.dumps({"filings": len(filings), "network": sum(m["cache"] == "miss" for m in manifest.values())})}], replace=True)
    doc_rows, run_rows, missing = [], [], []
    for f in filings:
        t1 = time.monotonic()
        parsed = parse_one(f)
        out = DOCS / f"{f.cik:010d}" / f"{f.accession}.tables.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(parsed, sort_keys=True, indent=1))
        loc = parsed["located"]
        for k in ("income", "cash_flow"):
            if not loc[k]:
                missing.append(f"{f.ticker} {f.form} {f.period} {k}")
        doc_rows.append({"accession": f.accession, "ticker": f.ticker, "cik": f.cik, "form": f.form, "period": f.period,
                         "filed": f.filed, "url": f.url, "sha256": parsed["sha256"], "bytes": manifest[f.accession]["bytes"],
                         "parser_version": PARSER_VERSION, "table_count": parsed["table_count"],
                         "tables_path": str(out.relative_to(store.ROOT)),
                         "income_tables": ",".join(loc["income"] or []) or None, "cash_flow_tables": ",".join(loc["cash_flow"] or []) or None})
        run_rows.append({"run_id": run_id, "step": "parse", "subject": f.accession, "started_at": _now(),
                         "seconds": round(time.monotonic() - t1, 3), "outcome": "ok" if all(loc[k] for k in ("income", "cash_flow")) else "failed",
                         "versions": json.dumps({"parser": PARSER_VERSION}), "detail": None})
    store.write(con, "documents", doc_rows, replace=True)
    store.write(con, "runs", run_rows, replace=True)
    n_ref = load_reference(con, tickers)
    print(f"{scope(a)[1]} ({', '.join(tickers)}): {len(filings)} filings parsed with {PARSER_VERSION}, "
          f"{len(missing)} statements not located, {n_ref} reference values loaded -> {a.db}")
    for m in missing:
        print("  not located:", m)
    return 1 if missing else 0
