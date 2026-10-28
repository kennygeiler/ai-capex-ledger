"""python -m ledger extract --stage N --pack | --load   (T41–T44)

--pack  writes one task file per filing to data/extract/tasks/ (statement tables only; no XBRL).
        Agents (Claude Code subagents, in-session) answer each task into data/extract/outputs/<accession>.json.
--load  validates each output (schema, then citation), dates each period from the company's filing calendar, and
        writes `extractions`. A filing with no valid output, and each citation that doesn't resolve, becomes an
        `extraction_failed` exception: nothing is guessed.
"""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone

from .. import store
from ..config import STAGES
from ..extract import OUTPUTS, PROMPT_VERSION, Invalid, period_start, resolve, validate_output, write_tasks
from ..ingest.filings import report_period_ends

DOCS = store.ROOT / "data" / "docs"


def _parsed(con, tickers):
    rows = con.execute("SELECT tables_path FROM documents WHERE ticker IN (SELECT unnest(?)) ORDER BY ticker, period", [tickers]).fetchall()
    return [json.loads((store.ROOT / r[0]).read_text()) for r in rows]


def _exc(rule, ticker, subject, message):
    h = hashlib.sha256(f"{subject}|{message}".encode()).hexdigest()[:16]
    return {"exception_id": f"{rule}|{subject}", "rule_id": rule, "severity": "block", "ticker": ticker, "field": None,
            "period": None, "subject": subject, "message": message, "input_hash": h}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger extract")
    ap.add_argument("--stage", type=int, default=1, choices=sorted(STAGES))
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", action="store_true")
    g.add_argument("--load", action="store_true")
    ap.add_argument("--find", action="store_true", help="with --pack: give agents every table, not the located statements")
    a = ap.parse_args(argv)
    tickers = STAGES[a.stage]["tickers"]
    con = store.init(a.db)
    docs = _parsed(con, tickers)
    if a.pack:
        paths = write_tasks(docs, a.find)
        print(f"{len(paths)} tasks in {paths[0].parent.relative_to(store.ROOT)} ({PROMPT_VERSION})")
        return 0

    run_id = f"extract-{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    cals = {t: report_period_ends(t) for t in tickers}
    rows, excs, runs = [], [], []
    for p in docs:
        t0 = time.monotonic()
        out = OUTPUTS / f"{p['accession']}.json"
        try:
            if not out.exists():
                raise Invalid("no output (task not run)")
            obj = json.loads(out.read_text())
            validate_output(obj, p["accession"])
        except (Invalid, json.JSONDecodeError) as e:
            excs.append(_exc("extraction_failed", p["ticker"], p["accession"], f"{p['form']} {p['period']}: {getattr(e, 'reason', e)}"))
            runs.append({"run_id": run_id, "step": "extract", "subject": p["accession"], "started_at": run_id[8:], "seconds": 0.0,
                         "outcome": "failed", "versions": json.dumps({"prompt": PROMPT_VERSION}), "detail": json.dumps({"error": str(getattr(e, 'reason', e))})})
            continue
        bad = 0
        for i, v in enumerate(obj["values"]):
            try:
                unit = resolve(v, p)
            except Invalid as e:
                bad += 1
                excs.append(_exc("extraction_failed", p["ticker"], f"{p['accession']}|values[{i}]", f"{v['field']} {v['column_label']}: citation does not resolve: {e.reason}"))
                continue
            start = period_start(v["period_end"], v["months"], cals[p["ticker"]])
            rows.append({"extraction_id": f"{p['accession']}|{v['field']}|{start}|{v['period_end']}", "accession": p["accession"],
                         "ticker": p["ticker"], "field": v["field"], "period_start": start, "period_end": v["period_end"],
                         "value": v["value"], "unit_stated": unit["unit_stated"], "unit_source": unit["unit_source"], "scale": unit["scale"],
                         "table_id": v["table_id"], "row_label": v["row_label"], "column_label": v["column_label"],
                         "cell_text": v["cell_text"], "confidence": float(v["confidence"]), "notes": v.get("notes"),
                         "prompt_version": PROMPT_VERSION, "run_id": run_id})
        meta = obj.get("_run", {})
        runs.append({"run_id": run_id, "step": "extract", "subject": p["accession"], "started_at": run_id[8:],
                     "seconds": round(time.monotonic() - t0, 3), "outcome": "ok" if not bad else "failed",
                     "versions": json.dumps({"prompt": PROMPT_VERSION, "model": meta.get("model")}),
                     "detail": json.dumps({"values": len(obj["values"]), "unresolved": bad, "not_found": obj["not_found"], **meta})})
    # Duplicate period/field within one filing (e.g. two columns read as the same period) is itself a failure.
    seen, uniq = {}, []
    for r in rows:
        if r["extraction_id"] in seen:
            excs.append(_exc("extraction_failed", r["ticker"], r["extraction_id"], f"two values for {r['field']} {r['period_start']}..{r['period_end']} in one filing"))
            continue
        seen[r["extraction_id"]] = r
        uniq.append(r)
    con.execute("DELETE FROM extractions WHERE ticker IN (SELECT unnest(?))", [tickers])
    con.execute("DELETE FROM exceptions WHERE rule_id = 'extraction_failed' AND ticker IN (SELECT unnest(?))", [tickers])
    store.write(con, "extractions", uniq)
    store.write(con, "exceptions", excs, replace=True)
    store.write(con, "runs", runs, replace=True)
    print(f"stage {a.stage}: {len(uniq)} extractions loaded from {len(docs)} filings; {len(excs)} extraction_failed exceptions")
    for e in excs:
        print("  FAILED", e["subject"], "-", e["message"])
    return 0
