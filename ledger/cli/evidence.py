"""python -m ledger evidence --stage N | --ticker X …   ->  reports/evidence/<name>.json and boxed screenshots

Re-reads every cited cell from the 10-K as rendered in Chrome, and screenshots the cells of the values a person checks.
--faults also points each citation at a neighbouring row or column and reports how often the re-read notices.
--crops makes a picture of every cited cell, statements and notes (ledger/checks/crops.py) -> reports/evidence/crops/ and crops.json."""
import argparse
import json

from ..core import store
from ..core.config import add_scope, scope
from ..checks.evidence import read
from ..release.release import to_check

OUT = store.ROOT / "reports" / "evidence"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger evidence")
    add_scope(ap)
    ap.add_argument("--faults", action="store_true")
    ap.add_argument("--crops", action="store_true", help="crop every cited cell, statements and notes, boxed")
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    tickers, name = scope(a)
    if a.crops:  # reads only: the database stays open to the app while the crops run
        import duckdb
        con = duckdb.connect(a.db, read_only=True)
        from ..checks.crops import CROPS, run
        res = run(con, tickers)
        miss = {k: v for k, v in res.items() if not v["located"]}
        size = sum(f.stat().st_size for f in CROPS.glob("*.png"))
        print(f"{name}: {len(res) - len(miss)} of {len(res)} cited cells located and cropped; {len(miss)} not located; crops on disk {size / 1e6:.1f} MB"
              + "".join(f"\n  not located: {k}: {v['reason']}" for k, v in sorted(miss.items())))
        return 0
    con = store.init(a.db)
    q = lambda sql: [dict(zip([c[0] for c in con.execute(sql, [tickers]).description], r)) for r in con.execute(sql, [tickers]).fetchall()]
    exts = q("select e.*, d.cik from extractions e join documents d using(accession) where e.ticker in (select unnest(?))")
    vals = q('select * from "values" where ticker in (select unnest(?))')
    want = to_check(vals)
    shots = {i for v in vals if (v["ticker"], v["field"], v["period"]) in want for i in (v["extraction_ids"] or "").split(",")}
    by_doc = {}
    for e in exts:
        by_doc.setdefault((e["cik"], e["accession"]), []).append(e)
    OUT.mkdir(parents=True, exist_ok=True)
    res, caught, tried = {}, 0, 0
    for (cik, accn), es in sorted(by_doc.items()):
        doc = store.ROOT / "data" / "raw" / f"{cik:010d}" / "docs" / f"{accn}.htm"
        if a.faults:  # the same cell text, cited at a neighbouring column or row that shows something else
            bad = [{**e, k: o[k], "extraction_id": f"{e['extraction_id']}>{k}>{o[k]}"} for e in es for o in es
                   for k in ("column_label", "row_label") if o["table_id"] == e["table_id"] and o[k] != e[k] and o["cell_text"] != e["cell_text"]
                   and o["column_label" if k == "row_label" else "row_label"] == e["column_label" if k == "row_label" else "row_label"]]
            r = read(doc, bad, set(), OUT)
            tried, caught = tried + len(r), caught + sum(not x["match"] for x in r.values())
        else:
            res |= read(doc, es, shots, OUT)
    if a.faults:
        print(f"{name}: {caught} of {tried} citations moved to a neighbouring row or column were noticed by the re-read")
        return 0 if caught == tried else 1
    (OUT / f"{name}.json").write_text(json.dumps(res, indent=1, sort_keys=True))
    miss = [k for k, v in res.items() if not v["match"]]
    print(f"{name}: {len(res) - len(miss)} of {len(res)} cited cells confirmed on the rendered 10-K; {len(shots & set(res))} screenshots"
          + "".join(f"\n  not confirmed: {k} (cited {res[k]['cell']!r}, page shows {res[k]['seen']!r})" for k in miss))
    return 0
