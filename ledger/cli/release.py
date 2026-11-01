"""python -m ledger release <version>   ->  releases/<version>/ for the scope (config.SCOPE); refuses while a gate fails

The packet is built by `checklist.packet`, the same code the Release page runs in memory, so the page's files and
hash are the ones this command writes (T5, T8)."""
import argparse

from .. import store
from ..checklist import packet, write
from ..config import SCOPE, STAGES
from ..release import GATES, failing, table


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger release")
    ap.add_argument("version")
    ap.add_argument("--stage", type=int, default=3, choices=STAGES, help="which hand-check file to read (golden/stage{N}-handcheck.json); the rows are always the scope")
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    p = packet(con, a.version, a.stage)
    g = p["gates"]
    print(table(g))
    bad = failing(g)
    if bad:
        print(f"{a.version} not built: {len(bad)} compan{'y' if len(bad) == 1 else 'ies'} fail{'s' if len(bad) == 1 else ''} a gate.")
        for t, by_gate in bad.items():
            for gate, items in by_gate.items():
                print(f"  {t} {gate} {GATES[gate]}: {len(items)} item(s), e.g. {items[0]}")
        if any(items == ["no hand-check file"] for items in g["G5"].values()):
            print(f"  (export the hand-check from reports/stage{a.stage}-validation.html to golden/stage{a.stage}-handcheck.json)")
        return 1
    try:
        w = write(p)
    except ValueError as e:
        print(e)
        return 1
    if not w["written"]:
        print(f"{a.version} exists unchanged.")
        return 0
    print(f"built {a.version}: {p['values']} values, hash {p['hash'][:12]}. Sign from the Release page (#release), or: python -m ledger signoff {a.version} --by \"<name>\"")
    return 0
