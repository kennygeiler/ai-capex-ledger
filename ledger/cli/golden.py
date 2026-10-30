"""python -m ledger golden --freeze | --check [--keep] [--verbose]

The golden test (docs/PROOF.md): --freeze captures the proven set's inputs and the tables the code makes from them;
--check runs the code stages on those inputs in a temporary root and compares. Exit 1 on any difference."""
import argparse
import json

from .. import store
from ..golden import FIXTURES, check, freeze


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger golden")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--freeze", action="store_true", help="capture fixtures and expected tables from the working database for the proven set")
    g.add_argument("--check", action="store_true", help="run the code stages on the fixtures and compare with the expected tables")
    ap.add_argument("--ticker", nargs="+", help="with --freeze: a different set than config.PROVEN")
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    ap.add_argument("--keep", action="store_true", help="with --check: keep the temporary root for a look")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args(argv)
    if a.freeze:
        import duckdb
        con = duckdb.connect(a.db, read_only=True)
        try:
            r = freeze(con, a.ticker)
        finally:
            con.close()
        print(f"froze {len(r['tickers'])} companies ({', '.join(r['tickers'])}): {r['documents']} filings, {r['texts']} texts, {r['xbrl_facts']} XBRL facts, {r['files']} files into {FIXTURES.relative_to(store.ROOT)}/")
        return 0
    r = check(keep=a.keep, verbose=a.verbose)
    from datetime import datetime, timezone
    rep = store.ROOT / "reports" / "golden.json"
    rep.parent.mkdir(parents=True, exist_ok=True)
    rep.write_text(json.dumps({"at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "ok": bool(r.get("ok")) and not r.get("failed_step"), "failed_step": r.get("failed_step"),
                               "diffs": {k: {kk: vv for kk, vv in v.items()} for k, v in r.get("diffs", {}).items()}, "steps": [{"step": l["step"], "exit": l["exit"]} for l in r["log"]],
                               "tickers": json.loads((FIXTURES / "seed.json").read_text())["tickers"]}, indent=1))
    if r.get("failed_step"):
        print(f"golden: step {r['failed_step']} failed; root kept at {r['root']}" if a.keep else f"golden: step {r['failed_step']} failed (rerun with --keep --verbose)")
        for l in r["log"]:
            if l["exit"] not in (0, 2):
                print(l["err"][-1500:] or l["out"][-1500:])
        return 1
    if r["ok"]:
        print(f"golden: every table equals fixtures/expected ({', '.join(t for t in ['values', 'facts', 'ai_statements', 'ai_spend', 'projects', 'extractions', 'note_extractions', 'exceptions'])}).")
        return 0
    print("golden: differences")
    for name, d in r["diffs"].items():
        print(f"  {name}: run {d['rows_got']} rows, expected {d['rows_want']}; {d['n_only_in_run']} only in the run, {d['n_only_in_expected']} only in expected")
        for x in d["only_in_run"]:
            print("    + " + x[:200])
        for x in d["only_in_expected"]:
            print("    - " + x[:200])
    if a.keep:
        print(f"root kept at {r['root']}")
    return 1
