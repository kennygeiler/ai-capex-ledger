"""python -m ledger run --ticker X [Y …] | --stage N

One command from a ticker to its validation page, with nobody in the loop: fetch and parse the 10-Ks, run the agent
headless on any filing without an output, load and check every citation, build fiscal-year values, run the rules and
the fault test, re-read every cited cell on the rendered 10-K, write the page, and print the scorecard. Safe to rerun:
documents and agent outputs are cached (--rerun re-asks the agent)."""
import argparse
import importlib
import json
import time
from datetime import datetime, timezone

from .. import progress, store
from ..config import add_scope, scope, tracked
from ..progress import STEPS
from ..scorecard import scorecard, table
from ..snapshots import save, take


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger run")
    add_scope(ap)
    ap.add_argument("--rerun", action="store_true", help="re-ask the agent even where an output exists")
    a = ap.parse_args(argv)
    tickers, name = scope(a)
    where = ["--ticker", *tickers] if a.ticker else ["--stage", str(a.stage or 1)]
    now = lambda: datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id, steps, t_run = f"run-{now()}", [], time.monotonic()
    progress.write(run_id, name, tickers, steps, running=True)  # DATAHQ shows the run as it goes
    for cmd, extra, label in STEPS:
        print(f"\n== {cmd} {' '.join(extra)}", flush=True)
        t0, at = time.monotonic(), now()
        code = importlib.import_module(f".{cmd}", __package__).main(where + extra + (["--rerun"] if a.rerun and extra == ["--run"] else []))
        con = store.init(str(store.DEFAULT_DB))
        steps.append({"step": cmd, "extra": extra, "label": label, "subject": f"{name} {' '.join(extra)}".strip(), "started_at": at,
                      "seconds": round(time.monotonic() - t0, 1), "code": code or 0, "summary": progress.summary(con, cmd, extra, tickers, name, at)})
        con.close()
        progress.write(run_id, name, tickers, steps, running=code != 2)
        if code == 2:  # the agent can't run at all: nothing after this means anything
            break
    # Every step of the run is logged, so "last run" means the whole pipeline; then a snapshot for "since last run".
    con = store.init(str(store.DEFAULT_DB))
    store.write(con, "runs", [{"run_id": run_id, "step": s["step"], "subject": s["subject"],
                               "started_at": s["started_at"], "seconds": s["seconds"], "outcome": "ok" if s["code"] == 0 else "failed",
                               "versions": json.dumps({}), "detail": json.dumps({"exit_code": s["code"]})} for s in steps]
                + [{"run_id": run_id, "step": "run", "subject": name, "started_at": steps[0]["started_at"], "seconds": round(time.monotonic() - t_run, 1),
                    "outcome": "ok" if all(s["code"] in (0, 1) for s in steps) else "failed", "versions": json.dumps({}),
                    "detail": json.dumps({"steps": [{k: s[k] for k in ("step", "subject", "seconds", "code")} for s in steps]})}], replace=True)
    save(take(con, [c["ticker"] for c in tracked()]))  # the whole ledger, so "since last run" compares like with like
    progress.write(run_id, name, tickers, steps, running=False)
    if any(s["code"] == 2 for s in steps):
        return 2
    print(f"\n== scorecard ({name})\n" + table(scorecard(con, tickers, name)))
    print(f"\npage: reports/{name}-validation.html")
    return 0
