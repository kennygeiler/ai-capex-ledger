"""python -m ledger texts --stage N | --ticker X …   ->  the `texts` table and data/text/

Gathers every text the AI spend reader reads (ledger/texts.py): each 10-K's MD&A, each 8-K earnings release
(Exhibit 99.1), and the transcripts and CFO commentary a company's investor page offers when sources/ir.yaml names
it. Cached on disk; a text already gathered is not fetched again. Investor pages open a Chrome window briefly."""
import argparse
import json
import time
from datetime import datetime, timezone

from .. import store, texts
from ..config import add_scope, scope
from ..reconcile import fiscal_year_end


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger texts")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    tickers, name = scope(a)
    con = store.init(a.db)
    cur = con.execute("select accession, ticker, cik, form, period, filed, url from documents where ticker in (select unnest(?)) order by ticker, period", [tickers])
    docs = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    con.close()  # fetching takes minutes; don't hold the database
    run_id, t0 = f"texts-{datetime.now(timezone.utc).isoformat(timespec='seconds')}", time.monotonic()
    rows, by_kind = [], {}
    for t in tickers:
        mine = [d for d in docs if d["ticker"] == t]
        if not mine:
            continue
        fye, ends = fiscal_year_end(t), texts.quarter_ends(t)
        got = texts.mdna(mine, fye) + texts.earnings_releases(t, mine[0]["cik"], fye, ends) + texts.ir_texts(t, fye, ends)
        rows += got
        for r in got:
            by_kind[r["kind"]] = by_kind.get(r["kind"], 0) + 1
        print(f"  {t}: " + ", ".join(f"{sum(r['kind'] == k for r in got)} {k}" for k in texts.KINDS if any(r["kind"] == k for r in got)), flush=True)
    con = store.init(a.db)
    con.execute("DELETE FROM texts WHERE ticker IN (SELECT unnest(?))", [tickers])
    store.write(con, "texts", rows)
    store.write(con, "runs", [{"run_id": run_id, "step": "texts", "subject": name, "started_at": run_id[6:], "seconds": round(time.monotonic() - t0, 1),
                               "outcome": "ok", "versions": json.dumps({}), "detail": json.dumps(by_kind)}], replace=True)
    print(f"{name}: {len(rows)} texts ({', '.join(f'{v} {k}' for k, v in sorted(by_kind.items()))})")
    return 0
