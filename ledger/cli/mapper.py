"""python -m ledger mapper <TICKER> [--dry-run]

The mapping assistant (ledger/mapper.py, T33): for the ticker's reported PP&E categories with no entry in
taxonomy/asset_types.yaml, write the task (the category names, the allowed us-gaap members, the note's words) to
data/mapper/tasks/<TICKER>.md and run the mapper headless; its proposals go to decisions/mapping_proposals.jsonl and
a `runs` row records the call. A person approves, edits or rejects each on Reconcile (#reconcile?scope=<TICKER>).
--dry-run writes the task and stops: no call, nothing appended.
"""
import argparse
import json
import time
from datetime import datetime, timezone

from .. import agent, store
from ..mapper import Invalid, by_name, make_task, members, note_words, propose, prompt_version, validate_output, write_task
from ..taxonomy import unmapped


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger mapper", description=__doc__.split("\n\n")[1])
    ap.add_argument("ticker", help="one company")
    ap.add_argument("--dry-run", action="store_true", help="write the task file only; no agent call")
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    t = a.ticker.upper()
    con = store.init(a.db)
    names = [u["reported_name"] for u in unmapped(con, [t])]
    if not names:
        con.close()
        print(f"{t}: every reported asset type is mapped; nothing to propose")
        return 0
    idx = by_name(t)
    blocks = note_words(con, t, names)
    con.close()  # the call takes minutes; don't hold the database
    allowed = members()
    task = make_task(t, names, blocks, {n: e["rejected"] for n, e in idx.items() if e["rejected"]}, allowed)
    path = write_task(t, task)
    pv = prompt_version()
    print(f"{t}: {len(names)} unmapped asset type(s), {len(blocks)} note table(s) in the task; {path.relative_to(store.ROOT)} ({pv})")
    if a.dry_run:
        print("dry run: no call made, nothing appended")
        return 0
    t0 = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = f"mapper-{t0}"
    started = time.monotonic()
    try:
        obj = agent.ask("mapper", task, lambda o: validate_output(o, t, names, task, allowed))
    except agent.AgentUnavailable as e:
        print(f"stopped: {e}")
        return 2
    except Invalid as e:
        _record(a.db, run_id, t, t0, time.monotonic() - started, "failed", pv, {"error": e.reason})
        print(f"FAILED: {e.reason}")
        return 1
    meta = obj.get("_run", {})
    lines = propose(t, obj, meta)
    _record(a.db, run_id, t, t0, time.monotonic() - started, "ok", pv, {"proposals": len(lines), **meta})
    for l in lines:
        print(f"  {l['reported_name']!r} -> {l['standard_type']} ({l['confidence']}): {l['evidence'][:80]!r}")
    print(f"{len(lines)} proposal(s) appended to decisions/mapping_proposals.jsonl; approve on #reconcile?scope={t}")
    return 0


def _record(db, run_id, ticker, started_at, seconds, outcome, pv, detail):
    con = store.init(db)
    try:
        store.write(con, "runs", [{"run_id": run_id, "step": "mapper", "subject": ticker, "started_at": started_at, "seconds": round(seconds, 3), "outcome": outcome,
                                   "versions": json.dumps({"prompt": pv, "model": detail.get("model")}), "detail": json.dumps(detail)}], replace=True)
    finally:
        con.close()
