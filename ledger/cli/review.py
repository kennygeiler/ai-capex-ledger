"""python -m ledger review --stage N | --ticker X …                      list open exceptions
python -m ledger review --stage N | --ticker X … decide <id> accept|override|reject --reason "..." --by "..." [--value N] [--run]

--by is a person on config.PEOPLE; --run records an agent's or a run's decision (author_kind run): it closes no block
finding, which stays open and Proposed until a person decides it (F14)."""
import argparse

from ..core import store
from ..core.config import add_scope, scope
from ..review.review import decide, decisions, open_items


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger review")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    ap.add_argument("action", nargs="?", choices=["decide"])
    ap.add_argument("exception_id", nargs="?")
    ap.add_argument("kind", nargs="?")
    ap.add_argument("--reason", default="")
    ap.add_argument("--by", default="")
    ap.add_argument("--value", type=int)
    ap.add_argument("--run", action="store_true", help="an agent's or a run's decision: recorded, closes no block until a person decides")
    a = ap.parse_args(argv)
    con = store.init(a.db)
    cur = con.execute("select * from exceptions where ticker in (select unnest(?))", [scope(a)[0]])
    excs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    if a.action == "decide":
        exc = next((e for e in excs if e["exception_id"] == a.exception_id), None)
        if not exc or not a.by:
            ap.error("give an open exception id and --by")
        try:
            d = decide(exc, a.kind, a.reason, a.by, a.value, author_kind="run" if a.run else "person")
        except ValueError as e:
            print(e)
            return 1
        print(f"recorded {d['kind']} on {exc['exception_id']} by {d['reviewer']} ({d['author_kind']})")
        return 0
    todo = open_items(excs, decisions())
    print(f"{scope(a)[1]}: {len(todo)} open")
    for e in todo:
        print(f"  [{e['severity']}] {e['exception_id']}\n      {e['message']}")
    return 0
