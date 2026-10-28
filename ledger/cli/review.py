"""python -m ledger review --stage N                      list open exceptions
python -m ledger review --stage N decide <id> accept|override|reject --reason "..." --by "..." [--value N]"""
import argparse

from .. import store
from ..config import STAGES
from ..review import decide, decisions, open_items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger review")
    ap.add_argument("--stage", type=int, default=1, choices=sorted(STAGES))
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    ap.add_argument("action", nargs="?", choices=["decide"])
    ap.add_argument("exception_id", nargs="?")
    ap.add_argument("kind", nargs="?")
    ap.add_argument("--reason", default="")
    ap.add_argument("--by", default="")
    ap.add_argument("--value", type=int)
    a = ap.parse_args(argv)
    con = store.init(a.db)
    cur = con.execute("select * from exceptions where ticker in (select unnest(?))", [STAGES[a.stage]["tickers"]])
    excs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    if a.action == "decide":
        exc = next((e for e in excs if e["exception_id"] == a.exception_id), None)
        if not exc or not a.by:
            ap.error("give an open exception id and --by")
        d = decide(exc, a.kind, a.reason, a.by, a.value)
        print(f"recorded {d['kind']} on {exc['exception_id']} by {d['reviewer']}")
        return 0
    todo = open_items(excs, decisions())
    print(f"stage {a.stage}: {len(todo)} open")
    for e in todo:
        print(f"  [{e['severity']}] {e['exception_id']}\n      {e['message']}")
    return 0
