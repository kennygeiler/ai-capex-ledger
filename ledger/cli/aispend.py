"""python -m ledger aispend --stage N | --ticker X …  --pack | --run | --load

What every gathered text (`texts`: 10-K MD&A, 8-K earnings releases, transcripts, CFO commentary) says about AI's
part of capex and opex (ledger/guidance.py).
--pack  writes one task per text to data/aispend/tasks/: only the passages that mention AI next to spending.
--run   packs, then runs the AI spend reader headless on every text whose task changed (--rerun: all), writing
        data/aispend/outputs/<text_id>.json; a text the agent can't answer gets {"error": reason}.
--load  validates each output (schema, then every quote against its passage), writes `ai_statements` (table A) and
        derives `ai_spend` (table B). A text with no valid output becomes an `ai_extraction_failed` exception.
"""
import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import agent, store
from ..config import add_scope, scope
from ..guidance import OUTPUTS, Invalid, period_of, prompt_version, spend_rows, task_passages, validate_output, write_tasks


def _exc(ticker, subject, message):
    return {"exception_id": f"ai_extraction_failed|{subject}", "rule_id": "ai_extraction_failed", "severity": "block", "ticker": ticker,
            "field": None, "period": None, "subject": subject, "message": message, "input_hash": hashlib.sha256(f"{subject}|{message}".encode()).hexdigest()[:16]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger aispend")
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
    cur = con.execute("select * from texts where ticker in (select unnest(?)) order by ticker, kind, period_end", [tickers])
    docs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]  # one task per text
    pv = prompt_version()
    if a.pack or a.run:
        con.close()  # the agent run takes minutes; don't hold the database (DATAHQ reads it)
        paths = write_tasks(docs)
        print(f"{len(paths)} tasks in data/aispend/tasks ({pv})")
    if a.pack:
        return 0
    if a.run:
        sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()[:16]

        def stale(d, path):
            out = OUTPUTS / f"{d['text_id']}.json"
            if not out.exists():
                return True
            o = json.loads(out.read_text())
            return "error" in o or (o.get("_run") or {}).get("task_sha") != sha(path)  # an errored output is always re-asked (type 60)

        todo = [(d, p) for d, p in zip(docs, paths) if a.rerun or stale(d, p)]
        OUTPUTS.mkdir(parents=True, exist_ok=True)

        def one(item):
            d, path = item
            task = path.read_text()
            ps = task_passages(task)
            try:
                if not ps:
                    obj = {"accession": d["text_id"], "prompt_version": pv, "statements": [], "none_found": [{"field": f, "reason": "no passage in the text mentions AI next to spending"} for f in ("capex", "opex")],
                           "_run": {"model": None, "seconds": 0.0, "input_tokens": 0, "output_tokens": 0, "attempts": 0, "task_sha": sha(path)}}
                    note = "no passages; nothing asked"
                else:
                    obj = agent.ask("ai_reader", task, lambda o: validate_output(o, d["text_id"], ps))
                    obj["_run"]["task_sha"] = sha(path)
                    note = f"{len(obj['statements'])} statements, {obj['_run']['seconds']:.0f}s, {obj['_run']['attempts']} attempt(s)"
            except Invalid as e:
                obj, note = {"accession": d["text_id"], "error": e.reason, "rejected": getattr(e, "answer", None)}, f"FAILED: {e.reason}"
            (OUTPUTS / f"{d['text_id']}.json").write_text(json.dumps(obj, indent=1))
            return f"  {d['text_id']}: {note}"

        print(f"running the AI spend reader on {len(todo)} text(s); {len(docs) - len(todo)} already have an output for this exact task")
        try:
            with ThreadPoolExecutor(a.workers) as pool:
                for line in pool.map(one, todo):
                    print(line, flush=True)
        except agent.AgentUnavailable as e:
            print(f"stopped: {e}")
            return 2
        return 0

    run_id = f"aispend-{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    filed = {d["text_id"]: d["date"] for d in docs}
    rows, excs, runs = [], [], []
    for d in docs:
        t0 = time.monotonic()
        out = OUTPUTS / f"{d['text_id']}.json"
        task = (store.ROOT / "data" / "aispend" / "tasks" / f"{d['text_id']}.md")
        try:
            if not out.exists():
                raise Invalid("no output (task not run)")
            obj = json.loads(out.read_text())
            if "error" in obj:
                raise Invalid(f"the agent couldn't answer: {obj['error']}")
            validate_output(obj, d["text_id"], task_passages(task.read_text()) if task.exists() else {})
        except (Invalid, json.JSONDecodeError) as e:
            excs.append(_exc(d["ticker"], d["text_id"], f"{d['kind']} {d['period_end']}: {getattr(e, 'reason', e)}"))
            runs.append({"run_id": run_id, "step": "aispend", "subject": d["text_id"], "started_at": run_id[8:], "seconds": 0.0, "outcome": "failed",
                         "versions": json.dumps({"prompt": pv}), "detail": json.dumps({"error": str(getattr(e, "reason", e))})})
            continue
        for i, s in enumerate(obj["statements"]):
            period, assigned = period_of(s, d["fiscal_year"])
            rows.append({"statement_id": f"{d['text_id']}|{s['field']}|{period}|{s['kind']}|{i}", "text_id": d["text_id"], "source": d["kind"],
                         "accession": d["accession"], "ticker": d["ticker"],
                         "field": s["field"], "period": period, "kind": s["kind"], "scope": s["scope"], "class": s["class"],
                         "amount_low": s.get("amount_low"), "amount_high": s.get("amount_high"), "share": float(s["share"]) if s.get("share") is not None else None,
                         "quote": s["quote"], "passage": s["passage"], "confidence": float(s["confidence"]), "notes": "; ".join(x for x in (s.get("notes"), assigned) if x) or None,
                         "prompt_version": obj["prompt_version"], "run_id": run_id})
        meta = obj.get("_run", {})
        runs.append({"run_id": run_id, "step": "aispend", "subject": d["text_id"], "started_at": run_id[8:], "seconds": round(time.monotonic() - t0, 3),
                     "outcome": "ok", "versions": json.dumps({"prompt": pv, "model": meta.get("model")}),
                     "detail": json.dumps({"statements": len(obj["statements"]), "none_found": obj["none_found"], **meta})})
    spend = []
    for t in tickers:
        mine = [r for r in rows if r["ticker"] == t]
        spend += spend_rows(t, mine, filed)
    for tbl in ("ai_statements", "ai_spend"):
        con.execute(f"DELETE FROM {tbl} WHERE ticker IN (SELECT unnest(?))", [tickers])
    con.execute("DELETE FROM exceptions WHERE rule_id = 'ai_extraction_failed' AND ticker IN (SELECT unnest(?))", [tickers])
    store.write(con, "ai_statements", rows)
    store.write(con, "ai_spend", spend)
    store.write(con, "exceptions", excs, replace=True)
    store.write(con, "runs", runs, replace=True)
    print(f"{name}: {len(rows)} statements from {len(docs)} texts; {len(spend)} AI-spend rows; {len(excs)} failed")
    for e in excs:
        print("  FAILED", e["subject"], "-", e["message"])
    return 0
