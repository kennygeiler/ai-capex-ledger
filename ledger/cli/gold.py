"""python -m ledger gold --draw [--version vX.Y.Z] [--ticker ...] | --status

The gold set (T82, ledger/gold.py): --draw writes gold/<TICKER>.json, about 10 values and 10 facts per proven company,
seeded with the release version, never overwriting a verdict on file; --status prints the verdicts, the error rate with
n and a Wilson 95% interval, and compares every verdict with the working database. `ledger golden --check` runs the
same comparison against the tables the code produces from the frozen inputs."""
import argparse

from .. import store
from ..config import PROVEN


def main(argv=None) -> int:
    from .. import gold
    ap = argparse.ArgumentParser(prog="python -m ledger gold")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--draw", action="store_true", help="write the sample files into gold/ (verdicts on file are kept)")
    g.add_argument("--status", action="store_true", help="verdicts, error rate, and the comparison with the working database")
    ap.add_argument("--version", help="the release version the seed includes (default: the next version to sign, checklist.next_version)")
    ap.add_argument("--ticker", nargs="+", help="a different set than config.PROVEN")
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    import duckdb
    con = duckdb.connect(a.db, read_only=True)
    try:
        if a.draw:
            from ..checklist import next_version
            version = a.version or next_version()
            r = gold.draw(con, version, [t.upper() for t in a.ticker] if a.ticker else PROVEN)
            for t, s in r.items():
                print(f"{t}: {s['items']} items ({s['values']} values, {s['facts']} facts, {s['untagged']} untagged), {s['kept']} verdicts kept, {'written' if s['written'] else 'unchanged'}")
            print(f"gold: seed {gold.seed(version, '<TICKER>')} into gold/")
            return 0
        docs = gold.load_all()
        items = [i for d in docs.values() for i in d["items"]]
        for t, d in docs.items():
            print(f"{t} ({d['release']}): {gold.rate_line(gold.error_rate(d['items']))}")
        print(f"all: {gold.rate_line(gold.error_rate(items))}")
        c = gold.compare_db(con, docs)
        print(gold.summary_line(c))
        return 0 if not c["failures"] else 1  # unverified exits 0 and says "Not a pass"; a failing verdict exits 1
    finally:
        con.close()
