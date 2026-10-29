"""python -m ledger notes --stage N | --ticker X …  --pack | --run | --load

Facts from the notes (ledger/notes.py): segment capex and revenue, PP&E by category, finance lease liabilities,
purchase commitments.
--pack  writes one task per filing to data/notes/tasks/: the candidate note tables, nothing else.
--run   packs, then runs the Notes reader headless on every filing whose task changed (--rerun: all), writing
        data/notes/outputs/<accession>.json.
--load  validates each output (schema, then every citation against the parsed table), writes `note_extractions`
        (table A) and derives `facts` (table B), labelled against each filing's XBRL instance where a member matches.
"""
import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import agent, store
from ..config import add_scope, scope
from ..extract import Invalid
from ..notes import DIMENSIONED, OUTPUTS, fact_rows, norm_dim, prompt_version, resolve_note, validate_output, write_tasks
from ..reconcile import fiscal_year_end
from ..reference.dimensions import CONCEPTS, instance_facts
from ..reference.normalize import fiscal_label


def _exc(ticker, subject, message):
    return {"exception_id": f"note_extraction_failed|{subject}", "rule_id": "note_extraction_failed", "severity": "block", "ticker": ticker,
            "field": None, "period": None, "subject": subject, "message": message, "input_hash": hashlib.sha256(f"{subject}|{message}".encode()).hexdigest()[:16]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger notes")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--pack", action="store_true")
    g.add_argument("--run", action="store_true")
    g.add_argument("--load", action="store_true")
    ap.add_argument("--rerun", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args(argv)
    tickers, name = scope(a)
    con = store.init(a.db)
    cur = con.execute("select accession, ticker, cik, form, period, filed, sha256, parser_version, tables_path from documents where ticker in (select unnest(?)) order by ticker, period", [tickers])
    meta = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    docs = [json.loads((store.ROOT / m["tables_path"]).read_text()) for m in meta]
    pv = prompt_version()
    if a.pack or a.run:
        con.close()  # the agent run takes minutes; don't hold the database (DATAHQ reads it)
        paths = write_tasks(docs)
        print(f"{len(paths)} tasks in data/notes/tasks ({pv})")
    if a.pack:
        return 0
    if a.run:
        sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()[:16]

        def stale(p, path):
            out = OUTPUTS / f"{p['accession']}.json"
            return not out.exists() or (json.loads(out.read_text()).get("_run") or {}).get("task_sha") != sha(path)

        todo = [(p, path) for p, path in zip(docs, paths) if a.rerun or stale(p, path)]
        OUTPUTS.mkdir(parents=True, exist_ok=True)

        def one(item):
            p, path = item

            def check(obj):
                validate_output(obj, p["accession"])
                bad = []
                for i, v in enumerate(obj["values"]):
                    try:
                        resolve_note(v, p)
                    except Invalid as e:
                        bad.append(f"values[{i}] ({v['field']} {v.get('dimension') or ''} {v['column_label']}): {e.reason}")
                if bad:
                    raise Invalid("these citations don't match the tables: " + "; ".join(bad[:10]))
            try:
                obj = agent.ask("notes_reader", path.read_text(), check)
                obj["_run"]["task_sha"] = sha(path)
                note = f"{len(obj['values'])} values, {obj['_run']['seconds']:.0f}s, {obj['_run']['attempts']} attempt(s)"
            except Invalid as e:
                obj, note = {"accession": p["accession"], "error": e.reason}, f"FAILED: {e.reason}"
            (OUTPUTS / f"{p['accession']}.json").write_text(json.dumps(obj, indent=1))
            return f"  {p['ticker']} {p['accession']}: {note}"

        print(f"running the Notes reader on {len(todo)} filing(s); {len(docs) - len(todo)} already have an output for this exact task")
        try:
            with ThreadPoolExecutor(a.workers) as pool:
                for line in pool.map(one, todo):
                    print(line, flush=True)
        except agent.AgentUnavailable as e:
            print(f"stopped: {e}")
            return 2
        return 0

    run_id = f"notes-{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    fye = {t: fiscal_year_end(t) for t in tickers}
    by_accn = {m["accession"]: m for m in meta}
    rows, excs, runs = [], [], []
    for p in docs:
        m, t0 = by_accn[p["accession"]], time.monotonic()
        out = OUTPUTS / f"{p['accession']}.json"
        try:
            if not out.exists():
                raise Invalid("no output (task not run)")
            obj = json.loads(out.read_text())
            if "error" in obj:
                raise Invalid(f"the agent couldn't answer: {obj['error']}")
            validate_output(obj, p["accession"])
        except (Invalid, json.JSONDecodeError) as e:
            excs.append(_exc(p["ticker"], p["accession"], f"{p['form']} {p['period']}: {getattr(e, 'reason', e)}"))
            runs.append({"run_id": run_id, "step": "notes", "subject": p["accession"], "started_at": run_id[6:], "seconds": 0.0, "outcome": "failed",
                         "versions": json.dumps({"prompt": pv}), "detail": json.dumps({"error": str(getattr(e, "reason", e))})})
            continue
        bad = 0
        for i, v in enumerate(obj["values"]):
            try:
                unit = resolve_note(v, p)
            except Invalid as e:
                bad += 1
                excs.append(_exc(p["ticker"], f"{p['accession']}|values[{i}]", f"{v['field']} {v.get('dimension') or ''} {v['column_label']}: citation does not resolve: {e.reason}"))
                continue
            dim = v["dimension"] if v["field"] in DIMENSIONED else None
            rows.append({"extraction_id": f"{p['accession']}|{v['field']}|{dim or ''}|{v['period_end']}", "accession": p["accession"], "ticker": p["ticker"],
                         "field": v["field"], "dimension": dim, "period_end": v["period_end"], "months": v["months"], "value": v["value"],
                         "unit_stated": unit["unit_stated"], "unit_source": unit["unit_source"], "scale": unit["scale"],
                         "table_id": v["table_id"], "row_label": v["row_label"], "column_label": v["column_label"], "cell_text": v["cell_text"],
                         "confidence": float(v["confidence"]), "notes": v.get("notes"), "prompt_version": obj["prompt_version"], "run_id": run_id, "filed": m["filed"]})
        meta_run = obj.get("_run", {})
        runs.append({"run_id": run_id, "step": "notes", "subject": p["accession"], "started_at": run_id[6:], "seconds": round(time.monotonic() - t0, 3),
                     "outcome": "ok" if not bad else "failed", "versions": json.dumps({"prompt": pv, "model": meta_run.get("model")}),
                     "detail": json.dumps({"values": len(obj["values"]), "unresolved": bad, "not_found": obj["not_found"], **meta_run})})
    # Two citations for the same fact in one filing is a failure, not a choice.
    seen, uniq = set(), []
    for r in rows:
        if r["extraction_id"] in seen:
            excs.append(_exc(r["ticker"], r["extraction_id"], f"two values for {r['field']} {r['dimension'] or ''} {r['period_end']} in one filing"))
            continue
        seen.add(r["extraction_id"])
        uniq.append(r)
    # The answer key: each filing's instance, newest filing winning per (field, member, fiscal year), the same vintage the
    # fact itself comes from (a recast segment in a later 10-K is compared with that 10-K's tags, not the first ones).
    docs_hash = {m["accession"]: (m["sha256"], m["parser_version"]) for m in meta}
    facts = []
    for t in tickers:
        mine = [r for r in uniq if r["ticker"] == t]
        label = lambda end: fiscal_label(end, fye[t])[0]
        ref = {}
        for m in sorted((x for x in meta if x["ticker"] == t), key=lambda x: x["filed"], reverse=True):
            inst = instance_facts(m["cik"], m["accession"])
            for f, concepts in CONCEPTS.items():
                for c in concepts:
                    for (concept, member, end), val in inst.items():
                        if concept == c and (bool(member) == (f in DIMENSIONED)):
                            ref.setdefault((f, norm_dim(member), f"FY{label(end)}"), val)
        facts += fact_rows(t, mine, ref, label, docs_hash)
    for r in uniq:
        r.pop("filed")
    for tbl in ("note_extractions", "facts"):
        con.execute(f"DELETE FROM {tbl} WHERE ticker IN (SELECT unnest(?))", [tickers])
    con.execute("DELETE FROM exceptions WHERE rule_id = 'note_extraction_failed' AND ticker IN (SELECT unnest(?))", [tickers])
    store.write(con, "note_extractions", uniq)
    store.write(con, "facts", [{**f, "dimension": f["dimension"] or ""} for f in facts])
    store.write(con, "exceptions", excs, replace=True)
    store.write(con, "runs", runs, replace=True)
    agree = sum(f["label"] == "agree" for f in facts)
    print(f"{name}: {len(uniq)} cited cells from {len(docs)} filings; {len(facts)} facts, {agree} agree with the filing's XBRL, "
          f"{sum(f['label'] == 'unresolved' for f in facts)} differ, {sum(f['label'] == 'no_reference' for f in facts)} untagged; {len(excs)} failed")
    for e in excs:
        print("  FAILED", e["subject"], "-", e["message"])
    return 0
