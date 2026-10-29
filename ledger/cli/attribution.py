"""python -m ledger attribution --stage N | --ticker X …  --pack | --run | --load

AI's part of capex and opex per company (ledger/attribution.py): the attributor reads the industry's money-flow
model and the company's data pack, one task per company.
--pack  writes data/attribution/tasks/<TICKER>.md (model + pack).
--run   packs, then runs the attributor on every company whose task changed (a model edit or new data; --rerun: all),
        writing data/attribution/outputs/<TICKER>.json.
--load  validates each output (contract, inputs, arithmetic), writes `attribution`, and data/attribution/diff.json:
        what changed since the last load, so a model edit shows its effect.
"""
import argparse
import hashlib
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .. import agent, store
from ..attribution import Invalid, OUTPUTS, TASKS, model_for, model_text, pack, prompt_version, rows_for, validate_output, write_task
from ..config import add_scope, scope

DIFF = store.ROOT / "data" / "attribution" / "diff.json"


def _exc(ticker, message):
    return {"exception_id": f"attribution_failed|{ticker}", "rule_id": "attribution_failed", "severity": "block", "ticker": ticker, "field": None,
            "period": None, "subject": ticker, "message": message, "input_hash": hashlib.sha256(f"{ticker}|{message}".encode()).hexdigest()[:16]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger attribution")
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
    packs = {t: pack(con, t) for t in tickers}
    packs = {t: p for t, p in packs.items() if any(v["kind"] == "value" for v in p.values())}  # a company with no values has nothing to attribute
    pv = prompt_version()
    if a.pack or a.run:
        con.close()
        paths = {t: write_task(t, p) for t, p in packs.items()}
        print(f"{len(paths)} tasks in data/attribution/tasks ({pv}; models " + ", ".join(sorted({model_for(t) for t in paths})) + ")")
    if a.pack:
        return 0
    if a.run:
        sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()[:16]

        def stale(t):
            out = OUTPUTS / f"{t}.json"
            return not out.exists() or (json.loads(out.read_text()).get("_run") or {}).get("task_sha") != sha(paths[t])

        todo = [t for t in paths if a.rerun or stale(t)]
        OUTPUTS.mkdir(parents=True, exist_ok=True)

        def one(t):
            try:
                obj = agent.ask("attributor", paths[t].read_text(), lambda o: validate_output(o, t, packs[t]))
                obj["_run"]["task_sha"] = sha(paths[t])
                note = f"{len(obj['rows'])} rows, {sum(r['ai_amount'] is not None for r in obj['rows'])} with an amount, {obj['_run']['seconds']:.0f}s, {obj['_run']['attempts']} attempt(s)"
            except Invalid as e:
                obj, note = {"ticker": t, "error": e.reason}, f"FAILED: {e.reason}"
            (OUTPUTS / f"{t}.json").write_text(json.dumps(obj, indent=1))
            return f"  {t}: {note}"

        print(f"running the attributor on {len(todo)} compan{'ies' if len(todo) != 1 else 'y'}; {len(paths) - len(todo)} already attributed for this model and data")
        try:
            with ThreadPoolExecutor(a.workers) as pool:
                for line in pool.map(one, todo):
                    print(line, flush=True)
        except agent.AgentUnavailable as e:
            print(f"stopped: {e}")
            return 2
        return 0

    run_id = f"attribution-{datetime.now(timezone.utc).isoformat(timespec='seconds')}"
    before = {(r[0], r[1], r[2], r[3]): (r[4], r[5]) for r in con.execute("select ticker, field, period, kind, method, ai_amount from attribution where ticker in (select unnest(?))", [tickers]).fetchall()}
    rows, excs, runs = [], [], []
    for t, items in packs.items():
        t0, out = time.monotonic(), OUTPUTS / f"{t}.json"
        try:
            if not out.exists():
                raise Invalid("no output (task not run)")
            obj = json.loads(out.read_text())
            if "error" in obj:
                raise Invalid(f"the agent couldn't answer: {obj['error']}")
            validate_output(obj, t, items)
        except (Invalid, json.JSONDecodeError) as e:
            excs.append(_exc(t, str(getattr(e, "reason", e))))
            runs.append({"run_id": run_id, "step": "attribution", "subject": t, "started_at": run_id[12:], "seconds": 0.0, "outcome": "failed",
                         "versions": json.dumps({"prompt": pv}), "detail": json.dumps({"error": str(getattr(e, "reason", e))})})
            continue
        model = model_for(t)
        rows += rows_for(t, obj, model, hashlib.sha256(model_text(model).encode()).hexdigest()[:16], run_id)
        meta = obj.get("_run", {})
        runs.append({"run_id": run_id, "step": "attribution", "subject": t, "started_at": run_id[12:], "seconds": round(time.monotonic() - t0, 3), "outcome": "ok",
                     "versions": json.dumps({"prompt": pv, "model": model, "llm": meta.get("model")}), "detail": json.dumps({"rows": len(obj["rows"]), "none_found": obj["none_found"], **meta})})
    after = {(r["ticker"], r["field"], r["period"], r["kind"]): (r["method"], r["ai_amount"]) for r in rows}
    diff = {"at": run_id[12:], "scope": name,
            "changed": [{"key": "|".join(k), "before": before[k], "after": after[k]} for k in sorted(before.keys() & after.keys()) if before[k] != after[k]],
            "new": sorted("|".join(k) for k in after.keys() - before.keys()), "removed": sorted("|".join(k) for k in before.keys() - after.keys())}
    DIFF.parent.mkdir(parents=True, exist_ok=True)
    DIFF.write_text(json.dumps({**diff, "changed": len(diff["changed"]), "new": len(diff["new"]), "removed": len(diff["removed"]), "rows": diff["changed"][:200]}, indent=1))
    con.execute("DELETE FROM attribution WHERE ticker IN (SELECT unnest(?))", [tickers])
    con.execute("DELETE FROM exceptions WHERE rule_id = 'attribution_failed' AND ticker IN (SELECT unnest(?))", [tickers])
    store.write(con, "attribution", rows)
    store.write(con, "exceptions", excs, replace=True)
    store.write(con, "runs", runs, replace=True)
    by = {}
    for r in rows:
        by[r["method"]] = by.get(r["method"], 0) + 1
    print(f"{name}: {len(rows)} rows for {len({r['ticker'] for r in rows})} companies ({', '.join(f'{v} {k}' for k, v in sorted(by.items(), key=lambda kv: -kv[1]))}); "
          f"{sum(r['ai_amount'] is not None for r in rows)} with an AI amount; {len(diff['changed'])} changed, {len(diff['new'])} new, {len(diff['removed'])} removed since the last load; {len(excs)} failed")
    for e in excs:
        print("  FAILED", e["subject"], "-", e["message"][:300])
    return 0
