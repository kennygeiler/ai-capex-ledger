"""python -m ledger eval   ->  reports/evaluation.json and reports/EVALUATION.md

Scores the attribution against the reference set (gold/ai_capex.yaml): coverage, agreement, and an error band per
method. Runs in seconds; no agent."""
import argparse
import json

from .. import store
from ..evaluation import OUT, load, render, score


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger eval")
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    cur = con.execute("select ticker, field, period, kind, method, ai_amount, ai_share, confidence from attribution")
    attribution = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    capex = {(t, p): v for t, p, v in con.execute('select ticker, period, value from "values" where field = \'capex\' and value is not null').fetchall()}
    con.close()
    ev = score(load(), attribution, capex)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(ev, indent=1, default=str))
    (OUT.parent / "EVALUATION.md").write_text(render(ev))
    print(f"{ev['n']} reference entries: {ev['with_estimate']} with an estimate ({ev['agree']} agree, {ev['disagree']} disagree), {ev['no_estimate']} without")
    for m, b in sorted(ev["bands"].items()):
        print(f"  {m:14} n={b['n']} agree={b['agree']}" + (f" median abs error={b['median_abs_error']:.0%} (n={b['n_eq']})" if b["median_abs_error"] is not None else ""))
    for r in ev["rows"]:
        print(f"  {r['ticker']} {r['period']}: {r['outcome']:12} ref {r['relation']} {r['reference']}  ours {r['ours']}")
    return 0
