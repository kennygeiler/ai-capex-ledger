"""python -m ledger run --ticker X [Y …] | --stage N

One command from a ticker to its validation page, with nobody in the loop: fetch and parse the 10-Ks, run the agent
headless on any filing without an output, load and check every citation, build fiscal-year values, run the rules and
the fault test, re-read every cited cell on the rendered 10-K, write the page, and print the scorecard. Safe to rerun:
documents and agent outputs are cached (--rerun re-asks the agent)."""
import argparse
import importlib

from .. import store
from ..config import add_scope, scope
from ..scorecard import scorecard, table

STEPS = [("ingest", []), ("extract", ["--run"]), ("extract", ["--load"]), ("reconcile", []), ("rules", []),
         ("faults", []), ("evidence", []), ("report", [])]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger run")
    add_scope(ap)
    ap.add_argument("--rerun", action="store_true", help="re-ask the agent even where an output exists")
    a = ap.parse_args(argv)
    tickers, name = scope(a)
    where = ["--ticker", *tickers] if a.ticker else ["--stage", str(a.stage or 1)]
    for cmd, extra in STEPS:
        print(f"\n== {cmd} {' '.join(extra)}", flush=True)
        code = importlib.import_module(f".{cmd}", __package__).main(where + extra + (["--rerun"] if a.rerun and extra == ["--run"] else []))
        if code == 2:  # the agent can't run at all: nothing after this means anything
            return 2
    print(f"\n== scorecard ({name})\n" + table(scorecard(store.init(str(store.DEFAULT_DB)), tickers, name)))
    print(f"\npage: reports/{name}-validation.html")
    return 0
