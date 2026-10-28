"""python -m ledger reconcile --stage N   (T45, T60, T61)

Derives quarterly values from the stage's extractions, lines each up with the reference (XBRL) value, labels it,
and writes `values`. Labels decided here:
  agree         agent and reference within the coarser rounding of the two (a later filing may round to millions)
  no_reference  no XBRL value for that quarter
  unresolved    they differ: goes to review, where a person labels it agent_wrong / xbrl_wrong / definition_gap
An `unresolved` value is also written as a blocking `xbrl_reconcile` exception.
"""
import argparse
import hashlib
import json

from .. import store
from ..config import MVP_FIELDS, MVP_QUARTERS, STAGES
from ..derive import fiscal_year_end, quarters


def rounding(v: int) -> int:
    return 1_000_000 if v % 1_000_000 == 0 else 1_000 if v % 1_000 == 0 else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger reconcile")
    ap.add_argument("--stage", type=int, default=1, choices=sorted(STAGES))
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    tickers = STAGES[a.stage]["tickers"]
    q = "select e.*, d.form, d.filed from extractions e join documents d using(accession) where e.ticker = ?"
    values, excs, counts = [], [], {}
    for t in tickers:
        cur = con.execute(q, [t])
        cols = [c[0] for c in cur.description]
        xs = [dict(zip(cols, r)) for r in cur.fetchall()]
        derived = quarters(xs, fiscal_year_end(t))
        ref = {(f, c): (v, s) for f, c, v, s in con.execute("select field, cal_q, value, scale from (select *, 1 as scale from reference_values) where ticker = ?", [t]).fetchall()}
        scale_of = {x["extraction_id"]: x["scale"] for x in xs}
        for f in MVP_FIELDS:
            for cq in MVP_QUARTERS:
                d, r = derived[f].get(cq), ref.get((f, cq))
                if d is None:
                    continue  # coverage gap: reported by the coverage rule, not shipped as a value
                tol = max([scale_of[i] for i in d["extraction_ids"]] + ([rounding(r[0])] if r else [])) // 2
                label = "no_reference" if r is None else "agree" if abs(d["value"] - r[0]) <= tol else "unresolved"
                h = hashlib.sha256(json.dumps([d["value"], d["method"], d["extraction_ids"], r and r[0]]).encode()).hexdigest()[:16]
                values.append({"ticker": t, "field": f, "cal_q": cq, "value": d["value"], "source": "agent", "method": d["method"],
                               "label": label, "extraction_ids": ",".join(d["extraction_ids"]), "input_hash": h})
                counts[label] = counts.get(label, 0) + 1
                if label == "unresolved":
                    excs.append({"exception_id": f"xbrl_reconcile|{t}|{f}|{cq}", "rule_id": "xbrl_reconcile", "severity": "block",
                                 "ticker": t, "field": f, "cal_q": cq, "subject": None, "input_hash": h,
                                 "message": f"agent {d['value']:,} vs XBRL {r[0]:,} (diff {d['value'] - r[0]:+,}; tolerance ±{tol:,})"})
    con.execute('DELETE FROM "values" WHERE ticker IN (SELECT unnest(?))', [tickers])
    con.execute("DELETE FROM exceptions WHERE rule_id = 'xbrl_reconcile' AND ticker IN (SELECT unnest(?))", [tickers])
    store.write(con, "values", values)
    store.write(con, "exceptions", excs)
    print(f"stage {a.stage}: {len(values)} quarterly values; labels {counts}; {len(excs)} sent to review")
    return 0
