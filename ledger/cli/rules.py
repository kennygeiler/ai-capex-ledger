"""python -m ledger rules --stage N | --ticker X …

Loads rules/*.yaml, builds the context for the stage's companies from the store, runs every rule, and replaces the
stage's rule exceptions. (The loaders' failures, proof.FAILURES: `extraction_failed`, `note_extraction_failed`,
`ai_extraction_failed`, `projects_failed`, come from `extract`, `notes`, `aispend` and `projects --load` and are left
alone. Before T100 only `extraction_failed` was, so a refused notes or AI-spend output vanished at the next rules run.)
"""
import argparse
import json
from collections import Counter

from .. import store
from ..config import MVP_YEARS, add_scope, scope
from ..definitions import load as load_definitions
from ..proof import FAILURES
from ..rules import Context, load, run


def context(con, tickers) -> Context:
    q = lambda sql: [dict(zip([c[0] for c in con.execute(sql, [tickers]).description], r)) for r in con.execute(sql, [tickers]).fetchall()]
    docs = q("select accession, ticker, form, period, income_tables, cash_flow_tables, tables_path from documents where ticker in (select unnest(?))")
    return Context(values=q('select * from "values" where ticker in (select unnest(?))'),
                   extractions=q("select e.*, d.filed from extractions e join documents d using(accession) where e.ticker in (select unnest(?))"),
                   reference={(r["ticker"], r["field"], r["period"]): r for r in q("select * from reference_values where ticker in (select unnest(?))")},
                   parsed={d["accession"]: json.loads((store.ROOT / d["tables_path"]).read_text()) for d in docs},
                   ai_spend=q("select * from ai_spend where ticker in (select unnest(?))"),
                   documents=[{k: v for k, v in d.items() if k != "tables_path"} for d in docs],
                   years=MVP_YEARS, tickers=list(tickers), definitions=load_definitions())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger rules")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    tickers, name = scope(a)
    rules = load()
    excs = run(context(con, tickers), rules)
    con.execute("DELETE FROM rules")
    store.write(con, "rules", [{"rule_id": r["id"], "severity": r["severity"], "description": r["description"], "rationale": r["rationale"],
                                "check_name": r["check"], "params": json.dumps(r["params"], sort_keys=True), "file_sha256": r["file_sha256"]} for r in rules])
    con.execute("DELETE FROM exceptions WHERE rule_id NOT IN (SELECT unnest(?)) AND ticker IN (SELECT unnest(?))", [list(FAILURES), tickers])
    store.write(con, "exceptions", excs)
    by = Counter((e["severity"], e["rule_id"]) for e in excs)
    print(f"{scope(a)[1]}: {len(rules)} rules, {len(excs)} exceptions "
          f"({sum(e['severity'] == 'block' for e in excs)} block, {sum(e['severity'] == 'warn' for e in excs)} warn, {sum(e['severity'] == 'info' for e in excs)} info)")
    for (sev, rid), n in sorted(by.items()):
        print(f"  {sev:5} {rid:24} {n}")
    for e in excs:
        print(f"  - [{e['severity']}] {e['rule_id']}: {e['ticker']} {e['field'] or ''} {e['period'] or ''} {e['message'][:140]}")
    return 0
