"""python -m ledger reconcile --stage N | --ticker X …"""
import argparse
from collections import Counter

from ..core import store
from ..core.config import add_scope, scope
from ..review.definitions import load as load_definitions
from ..checks.reconcile import fiscal_year_end, values_for


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger reconcile")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    tickers, name = scope(a)
    docs = {r[0]: (r[1], r[2]) for r in con.execute("select accession, sha256, parser_version from documents").fetchall()}
    values, defs = [], load_definitions()
    for t in tickers:
        cur = con.execute("select e.*, d.form, d.filed from extractions e join documents d using(accession) where e.ticker = ?", [t])
        xs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
        ref = {(f, p): v for f, p, v in con.execute("select field, period, value from reference_values where ticker = ?", [t]).fetchall()}
        values += values_for(t, xs, ref, fiscal_year_end(t), docs, defs)
    con.execute('DELETE FROM "values" WHERE ticker IN (SELECT unnest(?))', [tickers])
    store.write(con, "values", values)
    print(f"{scope(a)[1]}: {len(values)} fiscal-year values; labels {dict(Counter(v['label'] for v in values))}")
    return 0
