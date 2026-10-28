"""python -m ledger faults --stage N | --ticker X …   ->  reports/<name>-faults.json"""
import argparse
import json
from collections import Counter

from .. import store
from ..config import add_scope, scope
from ..reconcile import fiscal_year_end
from ..faults import inject
from ..rules import load
from .rules import context


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger faults")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    rules, docs = load(), {r[0]: (r[1], r[2]) for r in con.execute("select accession, sha256, parser_version from documents").fetchall()}
    rows = []
    for t in scope(a)[0]:
        ctx = context(con, [t])
        cur = con.execute("select e.*, d.form, d.filed from extractions e join documents d using(accession) where e.ticker = ? order by extraction_id", [t])
        xs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
        ref = {(k[1], k[2]): r["value"] for k, r in ctx.reference.items()}
        rows += inject(t, xs, ref, fiscal_year_end(t), docs, ctx, rules)
    out = store.ROOT / "reports" / f"{scope(a)[1]}-faults.json"
    out.write_text(json.dumps(rows, indent=1))
    by = Counter((r["fault"], r["outcome"]) for r in rows)
    print(f"{'fault':16} {'trials':>6} {'no effect':>9} {'rule':>5} {'xbrl only':>9} {'escaped':>7}")
    for f in dict.fromkeys(r["fault"] for r in rows):
        n = sum(v for (ff, _), v in by.items() if ff == f)
        print(f"{f:16} {n:6} {by[(f, 'no_effect')]:9} {by[(f, 'rule')]:5} {by[(f, 'xbrl_only')]:9} {by[(f, 'escaped')]:7}")
    caught = Counter(rule for r in rows for rule in r["caught_by"])
    print("rules that caught faults:", dict(caught.most_common()))
    return 0
