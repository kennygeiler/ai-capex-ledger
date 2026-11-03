"""python -m ledger projects --stage N | --ticker X …  --pack | --run | --load

Project-level investment (ledger/extract/projects.py): named projects with size and stage, read from every gathered text.
--pack  writes one task per text to data/projects/tasks/: the passages that name a project and give it a size.
--run   packs, then runs the projects reader on every text whose task changed (--rerun: all), writing
        data/projects/outputs/<text_id>.json.
--load  validates each output (schema, every quote against its passage) and writes `projects`: every mention, with
        `latest` marking the newest text's row per project so a project shows once at its latest status.
"""
import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from ..extract import agent
from ..core import store
from ..core.config import add_scope, scope
from ..extract.guidance import task_passages
from ..extract.projects import OUTPUTS, TASKS, Invalid, latest, prompt_version, rows_for, validate_output, write_tasks


def _exc(ticker, subject, message):
    return {"exception_id": f"projects_failed|{subject}", "rule_id": "projects_failed", "severity": "warn", "ticker": ticker,
            "field": None, "period": None, "subject": subject, "message": message, "input_hash": hashlib.sha256(f"{subject}|{message}".encode()).hexdigest()[:16]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger projects")
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
    docs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    pv = prompt_version()
    if a.pack or a.run:
        con.close()
        paths = write_tasks(docs)
        print(f"{len(paths)} tasks in data/projects/tasks ({pv})")
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
                    obj = {"accession": d["text_id"], "prompt_version": pv, "projects": [], "_run": {"model": None, "seconds": 0.0, "input_tokens": 0, "output_tokens": 0, "attempts": 0, "task_sha": sha(path)}}
                    note = "no passages; nothing asked"
                else:
                    obj = agent.ask("projects_reader", task, lambda o: validate_output(o, d["text_id"], ps))
                    obj["_run"]["task_sha"] = sha(path)
                    note = f"{len(obj['projects'])} projects, {obj['_run']['seconds']:.0f}s, {obj['_run']['attempts']} attempt(s)"
            except Invalid as e:
                obj, note = {"accession": d["text_id"], "error": e.reason, "rejected": getattr(e, "answer", None)}, f"FAILED: {e.reason}"
            (OUTPUTS / f"{d['text_id']}.json").write_text(json.dumps(obj, indent=1))
            return f"  {d['text_id']}: {note}"

        print(f"running the projects reader on {len(todo)} text(s); {len(docs) - len(todo)} already have an output for this exact task")
        try:
            with ThreadPoolExecutor(a.workers) as pool:
                for line in pool.map(one, todo):
                    print(line, flush=True)
        except agent.AgentUnavailable as e:
            print(f"stopped: {e}")
            return 2
        return 0

    run_id = f"projects-{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    rows, excs, runs = [], [], []
    for d in docs:
        t0 = time.monotonic()
        out = OUTPUTS / f"{d['text_id']}.json"
        task = TASKS / f"{d['text_id']}.md"
        try:
            if not out.exists():
                raise Invalid("no output (task not run)")
            obj = json.loads(out.read_text())
            if "error" in obj:
                raise Invalid(f"the agent couldn't answer: {obj['error']}")
            validate_output(obj, d["text_id"], task_passages(task.read_text()) if task.exists() else {})
        except (Invalid, json.JSONDecodeError) as e:
            excs.append(_exc(d["ticker"], d["text_id"], f"{d['kind']} {d['period_end']}: {getattr(e, 'reason', e)}"))
            runs.append({"run_id": run_id, "step": "projects", "subject": d["text_id"], "started_at": run_id[9:], "seconds": 0.0, "outcome": "failed",
                         "versions": json.dumps({"prompt": pv}), "detail": json.dumps({"error": str(getattr(e, "reason", e))})})
            continue
        rows += rows_for(d, obj, run_id)
        meta = obj.get("_run", {})
        runs.append({"run_id": run_id, "step": "projects", "subject": d["text_id"], "started_at": run_id[9:], "seconds": round(time.monotonic() - t0, 3),
                     "outcome": "ok", "versions": json.dumps({"prompt": pv, "model": meta.get("model")}), "detail": json.dumps({"projects": len(obj["projects"]), **meta})})
    keep = {r["project_id"] for r in latest(rows)}
    for r in rows:
        r["latest"] = r["project_id"] in keep
    con.execute("DELETE FROM projects WHERE ticker IN (SELECT unnest(?))", [tickers])
    con.execute("DELETE FROM exceptions WHERE rule_id = 'projects_failed' AND ticker IN (SELECT unnest(?))", [tickers])
    store.write(con, "projects", rows)
    store.write(con, "exceptions", excs, replace=True)
    store.write(con, "runs", runs, replace=True)
    print(f"{name}: {len(rows)} project mentions from {len(docs)} texts, {len(keep)} distinct projects ({sum(r['amount_low'] is not None for r in rows if r['latest'])} with a dollar size); {len(excs)} failed")
    for e in excs:
        print("  FAILED", e["subject"], "-", e["message"][:200])
    return 0
