"""python -m ledger cost [--stage N | --ticker X …]  ->  reports/cost.json and the table

What the agents cost: calls, tokens, seconds, attempts, failures and an estimated price at list, per step and per
company (ledger/cost.py). The agents run on a subscription; the dollars are what the same work would cost on the API."""
import argparse
import json

from .. import store
from ..config import add_scope
from ..cost import render, report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger cost")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    rep = report(con, a.ticker if a.ticker else None)
    con.close()
    out = store.ROOT / "reports" / "cost.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(rep, indent=1, default=str))
    print(render(rep))
    return 0
