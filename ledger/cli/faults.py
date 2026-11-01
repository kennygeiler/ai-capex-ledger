"""python -m ledger faults --stage N | --ticker X … [--xbrl-off]   ->  reports/<name>-faults.json

Plants every fault kind (ledger/faults.py FAULTS) on the companies' extractions and records what caught each trial.
`--xbrl-off` runs the same trials with xbrl_reconcile removed from the rule set and writes
reports/<name>-faults-xbrl-off.json beside the normal report (T67): the two together say how much of the catch rate
depends on XBRL. Each report is {subject, written, xbrl, rules, kinds, planted, caught, rule, xbrl_only, no_effect,
escaped, by_kind, rows}; a runs row (step faults, subject <name>) records the pass."""
import argparse
import json
import time
from datetime import datetime, timezone

from .. import store
from ..config import add_scope, scope
from ..reconcile import fiscal_year_end
from ..faults import FAULTS, inject, rule_set, tally
from ..rules import load
from .rules import context


def report_path(name: str, xbrl: bool = True):
    return store.ROOT / "reports" / f"{name}-faults{'' if xbrl else '-xbrl-off'}.json"


def report(name: str, xbrl: bool, rules: list[dict], rows: list[dict]) -> dict:
    """The report file's content: what ran (subject, written, the rule set, the kinds), the tally, the rows."""
    written = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return {"subject": name, "written": written, "xbrl": xbrl, "rules": [r["id"] for r in rules], "kinds": list(FAULTS), **tally(rows), "rows": rows}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger faults")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    ap.add_argument("--xbrl-off", action="store_true", help="run with xbrl_reconcile removed from the rule set; writes <name>-faults-xbrl-off.json")
    a = ap.parse_args(argv)
    xbrl = not a.xbrl_off
    started, t0 = datetime.now(timezone.utc).isoformat(timespec="seconds"), time.monotonic()
    con = store.init(a.db)
    rules = rule_set(load(), xbrl)
    docs = {r[0]: (r[1], r[2]) for r in con.execute("select accession, sha256, parser_version from documents").fetchall()}
    tickers, name = scope(a)
    rows = []
    for t in tickers:
        ctx = context(con, [t])
        cur = con.execute("select e.*, d.form, d.filed from extractions e join documents d using(accession) where e.ticker = ? order by extraction_id", [t])
        xs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
        ref = {(k[1], k[2]): r["value"] for k, r in ctx.reference.items()}
        rows += inject(t, xs, ref, fiscal_year_end(t), docs, ctx, rules)
        print(f"{t}: {len(xs)} extractions, {len(rows)} trials so far", flush=True)
    rep = report(name, xbrl, rules, rows)
    out = report_path(name, xbrl)
    out.write_text(json.dumps(rep, indent=1))
    store.write(con, "runs", [{"run_id": f"faults-{started}", "step": "faults", "subject": name, "started_at": started,
                               "seconds": round(time.monotonic() - t0, 1), "outcome": "ok", "versions": json.dumps({}),
                               "detail": json.dumps({"exit_code": 0, "xbrl": xbrl, "report": str(out.relative_to(store.ROOT))})}], replace=True)
    print(f"{out.relative_to(store.ROOT)} ({'xbrl_reconcile counted' if xbrl else 'XBRL off: xbrl_reconcile removed'})")
    print(f"{'fault':16} {'trials':>6} {'no effect':>9} {'rule':>5} {'xbrl only':>9} {'escaped':>7}")
    for f, c in rep["by_kind"].items():
        print(f"{f:16} {c['planted']:6} {c['no_effect']:9} {c['rule']:5} {c['xbrl_only']:9} {c['escaped']:7}")
    print(f"{'all':16} {rep['planted']:6} {rep['no_effect']:9} {rep['rule']:5} {rep['xbrl_only']:9} {rep['escaped']:7}")
    caught = {}
    for r in rows:
        for rule in r["caught_by"]:
            caught[rule] = caught.get(rule, 0) + 1
    print("rules that caught faults:", dict(sorted(caught.items(), key=lambda kv: -kv[1])))
    return 0
