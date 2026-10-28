"""python -m ledger reconcile --stage N   (T45, T60)"""
import argparse
from collections import Counter

from .. import store
from ..config import STAGES
from ..derive import fiscal_year_end
from ..reconcile import values_for


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger reconcile")
    ap.add_argument("--stage", type=int, default=1, choices=sorted(STAGES))
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    tickers = STAGES[a.stage]["tickers"]
    docs = {r[0]: (r[1], r[2]) for r in con.execute("select accession, sha256, parser_version from documents").fetchall()}
    values = []
    for t in tickers:
        cur = con.execute("select e.*, d.form, d.filed from extractions e join documents d using(accession) where e.ticker = ?", [t])
        xs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
        ref = {(f, q): v for f, q, v in con.execute("select field, cal_q, value from reference_values where ticker = ?", [t]).fetchall()}
        values += values_for(t, xs, ref, fiscal_year_end(t), docs)
    con.execute('DELETE FROM "values" WHERE ticker IN (SELECT unnest(?))', [tickers])
    store.write(con, "values", values)
    print(f"stage {a.stage}: {len(values)} quarterly values; labels {dict(Counter(v['label'] for v in values))}")
    return 0
