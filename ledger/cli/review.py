"""python -m ledger review --stage N | --ticker X …                      list open exceptions
python -m ledger review --stage N | --ticker X … decide <id> accept|override|reject --reason "..." --by "..." --as person|run [--value N]

--as is required, so the command says who decides: person (--by a name on config.PEOPLE) or run (an agent's or a run's
decision, author_kind run): a run's decision closes no block finding, which stays open and Proposed until a person
decides it (F14)."""
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
    ap.add_argument("--as", dest="author_kind", choices=["person", "run"], help="required with decide: person (--by on config.PEOPLE) or run (an agent's decision; closes no block)")
    a = ap.parse_args(argv)
    con = store.init(a.db)
    cur = con.execute("select * from exceptions where ticker in (select unnest(?))", [scope(a)[0]])
    excs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    if a.action == "decide":
        exc = next((e for e in excs if e["exception_id"] == a.exception_id), None)
        if not exc or not a.by:
            ap.error("give an open exception id and --by")
        if not a.author_kind:
            ap.error("say who decides: --as person or --as run")
        try:
            d = decide(exc, a.kind, a.reason, a.by, a.value, author_kind=a.author_kind)
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
