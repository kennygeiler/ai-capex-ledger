"""python -m ledger extract --stage N | --ticker X …  --pack | --run | --load

--pack  writes one task file per filing to data/extract/tasks/ (statement tables only; no XBRL).
--run   packs, then runs the agent headless (`claude -p`, ledger/agent.py) on every filing with no output yet
        (--rerun: all of them), writing data/extract/outputs/<accession>.json; a filing the agent can't answer
        gets {"error": reason} there, so the failure is recorded, not guessed.
--load  refuses an output whose `_run.task_sha` is not the current task's (T100: stale, answered an older task),
        validates each output (schema, then citation), dates each period from the company's filing calendar, and
        writes `extractions`. A filing with no valid output, and each citation that doesn't resolve, becomes an
        `extraction_failed` exception: nothing is guessed.
"""
import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import agent, store
from ..config import add_scope, scope
from ..extract import OUTPUTS, Invalid, make_task, period_start, prompt_version, resolve, validate_output, write_tasks
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
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--load", action="store_true")
    ap.add_argument("--rerun", action="store_true", help="with --run: also re-read filings that already have an output")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    tickers, name = scope(a)
    con = store.init(a.db)
    docs, pv = _parsed(con, tickers), prompt_version()
    if a.pack or a.run:
        con.close()  # the agent run takes minutes; don't hold the database (DATAHQ reads it)
        paths = write_tasks(docs)
        print(f"{len(paths)} tasks in {paths[0].parent.relative_to(store.ROOT)} ({pv})")
    if a.pack:
        return 0
    if a.run:
        def stale(p, path):  # no output, or a headless output that answered a different task (e.g. the locator changed)
            out = OUTPUTS / f"{p['accession']}.json"
            if not out.exists():
                return True
            o = json.loads(out.read_text())
            if "error" in o:
                return True  # an errored output is always re-asked (type 60)
            run = o.get("_run")
            return bool(run) and run.get("task_sha") != hashlib.sha256(path.read_bytes()).hexdigest()[:16]

        todo = [(p, path) for p, path in zip(docs, paths) if a.rerun or stale(p, path)]

        def one(item):
            p, path = item
            try:
                obj = agent.extract(path.read_text(), p)
                obj["_run"]["task_sha"] = hashlib.sha256(path.read_bytes()).hexdigest()[:16]
                note = f"{len(obj['values'])} values, {obj['_run']['seconds']:.0f}s, {obj['_run']['attempts']} attempt(s)"
            except Invalid as e:
                obj, note = {"accession": p["accession"], "error": e.reason, "rejected": getattr(e, "answer", None)}, f"FAILED: {e.reason}"
            (OUTPUTS / f"{p['accession']}.json").write_text(json.dumps(obj, indent=1))
            return f"  {p['ticker']} {p['accession']}: {note}"

        print(f"running the agent on {len(todo)} filing(s); {len(docs) - len(todo)} already have an output for this exact task")
        try:
            with ThreadPoolExecutor(a.workers) as pool:
                for line in pool.map(one, todo):
                    print(line, flush=True)
        except agent.AgentUnavailable as e:
            print(f"stopped: {e}\n  If it says 'revoked' or 'not logged in', run `claude` in a terminal and type /login.")
            return 2
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
            if "error" in obj:
                raise Invalid(f"the agent couldn't answer: {obj['error']}")
            if why := agent.stale(obj, make_task(p)):  # T100: an answer to a task repacked since never loads
                raise Invalid(why)
            validate_output(obj, p["accession"])
        except (Invalid, json.JSONDecodeError) as e:
            excs.append(_exc("extraction_failed", p["ticker"], p["accession"], f"{p['form']} {p['period']}: {getattr(e, 'reason', e)}"))
            runs.append({"run_id": run_id, "step": "extract", "subject": p["accession"], "started_at": run_id[8:], "seconds": 0.0,
                         "outcome": "failed", "versions": json.dumps({"prompt": pv}), "detail": json.dumps({"error": str(getattr(e, 'reason', e))})})
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
            part = f"|{v['row_label']}" if v["field"] == "cost_of_revenue_part" else ""  # several parts per column
            rows.append({"extraction_id": f"{p['accession']}|{v['field']}|{start}|{v['period_end']}{part}", "accession": p["accession"],
                         "ticker": p["ticker"], "field": v["field"], "period_start": start, "period_end": v["period_end"],
                         "value": v["value"], "unit_stated": unit["unit_stated"], "unit_source": unit["unit_source"], "scale": unit["scale"],
                         "table_id": v["table_id"], "row_label": v["row_label"], "column_label": v["column_label"],
                         "cell_text": v["cell_text"], "confidence": float(v["confidence"]), "notes": v.get("notes"),
                         "prompt_version": obj["prompt_version"], "run_id": run_id})
        meta = obj.get("_run", {})
        runs.append({"run_id": run_id, "step": "extract", "subject": p["accession"], "started_at": run_id[8:],
                     "seconds": round(time.monotonic() - t0, 3), "outcome": "ok" if not bad else "failed",
                     "versions": json.dumps({"prompt": pv, "model": meta.get("model")}),
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
    print(f"{scope(a)[1]}: {len(uniq)} extractions loaded from {len(docs)} filings; {len(excs)} extraction_failed exceptions")
    for e in excs:
        print("  FAILED", e["subject"], "-", e["message"])
    return 0
