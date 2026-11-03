"""python -m ledger watch [--stage N | --ticker X …] [--run]   ->  data/watch.json

Asks the SEC what each company has filed (10-K and 10-K/A in the window) and lists every filing the ledger hasn't read
yet. Kenny's Data Emporium shows the result, so "nothing needs you" can't hide a filing that landed. --run reads them: `ledger run`
for each company with a new filing. Run it daily (cron or launchd); it makes one small request per company."""
import argparse
import json
from datetime import datetime, timezone

import duckdb

from ..core import store
from ..core.config import add_scope, scope
from ..ingest import edgar
from ..ingest.filings import list_filings
from .run import main as run

OUT = store.ROOT / "data" / "watch.json"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger watch")
    add_scope(ap)
    ap.add_argument("--run", action="store_true", help="read the new filings now (ledger run for those companies)")
    a = ap.parse_args(argv)
    if edgar.offline():  # a cached submissions file would be written as a check made now: watch.json would read fresh while it is not
        raise SystemExit("ledger watch asks the SEC what was filed; it does not run with LEDGER_OFFLINE=1 (unset it, or pass nothing offline)")
    if not a.ticker and not a.stage:
        a.stage = 3
    tickers, name = scope(a)
    con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    seen = {r[0] for r in con.execute("select accession from documents union select subject from runs where step = 'parse'").fetchall()}
    con.close()
    new = [{"ticker": f.ticker, "form": f.form, "period": f.period, "filed": f.filed, "accession": f.accession, "url": f.url}
           for f in list_filings(tickers, refresh=True) if f.accession not in seen]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "scope": name, "new": new}, indent=1))
    print(f"{name}: {len(new)} filing(s) not yet read" + "".join(f"\n  {n['ticker']} {n['form']} year ended {n['period']}, filed {n['filed']}" for n in new))
    if a.run and new:
        code = run(["--ticker", *sorted({n["ticker"] for n in new})])
        main([*(["--ticker", *tickers] if a.ticker else ["--stage", str(a.stage)])])  # check again, so watch.json reflects what was read
        return code
    return 0
