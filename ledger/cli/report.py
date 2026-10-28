"""python -m ledger report --stage N   ->  reports/stage<N>-validation.html

A self-contained page for checking a stage by eye and recording the hand-check (T80/T81):
  - summary tiles and, per field, a chart of agent vs XBRL by quarter,
  - every quarterly value with its arithmetic, down to the cited statement cells (highlighted in the parsed table),
  - a link per source that opens the SEC filing scrolled to the cited row (Chrome text fragments),
  - a Verified checkbox and note per value, kept in the browser, exportable as golden/<stage>-handcheck.json.
"""
import argparse
import html
import json
from datetime import date, datetime, timezone
from urllib.parse import quote

from .. import store
from ..config import MVP_FIELDS, MVP_QUARTERS, STAGES
from ..rules import load

FIELD_LABEL = {"revenue": "Revenue", "cost_of_revenue": "Cost of revenue", "operating_income": "Operating income", "capex": "Capex"}
METHOD_LABEL = {"reported": "As filed (three-month column)", "ytd_diff": "Year-to-date difference", "q4_derived": "Full year minus nine months",
                "fy_minus_quarters": "Full year minus three quarters"}


def _days(s, e):
    return (date.fromisoformat(e) - date.fromisoformat(s)).days + 1


def build(con, stage: int) -> dict:
    tickers = STAGES[stage]["tickers"]
    q = lambda sql, *p: [dict(zip([c[0] for c in con.execute(sql, list(p)).description], r)) for r in con.execute(sql, list(p)).fetchall()]
    docs = {d["accession"]: d for d in q("select * from documents where ticker in (select unnest(?))", tickers)}
    ext = {x["extraction_id"]: x for x in q("select * from extractions where ticker in (select unnest(?))", tickers)}
    ref = {(r["ticker"], r["field"], r["cal_q"]): r for r in q("select * from reference_values where ticker in (select unnest(?))", tickers)}
    vals = q('select * from "values" where ticker in (select unnest(?)) order by ticker, field, cal_q', tickers)
    excs = q("select * from exceptions where ticker in (select unnest(?)) order by severity, exception_id", tickers)
    parsed = {a: json.loads((store.ROOT / d["tables_path"]).read_text()) for a, d in docs.items()}
    tables = {}

    def table(accn, tid):
        k = f"{accn}|{tid}"
        if k not in tables:
            for kind in ("income", "cash_flow"):
                for t in parsed[accn]["statements"][kind] or []:
                    if t["id"] == tid:
                        tables[k] = {"columns": t["columns"], "unit": t["unit_text"], "unit_source": t["unit_source"],
                                     "rows": [{"l": r["label"], "c": [[c["col"], c["text"]] for c in r["cells"]]} for r in t["rows"]]}
        return k

    rows = []
    for v in vals:
        srcs = []
        for i in (v["extraction_ids"] or "").split(","):
            x = ext.get(i)
            if not x:
                continue
            d = docs[x["accession"]]
            num = x["cell_text"].strip("()$ ").replace("—", "")
            frag = f"#:~:text={quote(x['row_label'])},{quote(num)}" if num else f"#:~:text={quote(x['row_label'])}"
            srcs.append({"id": i, "accession": x["accession"], "form": d["form"], "doc_period": d["period"], "filed": d["filed"],
                         "url": d["url"], "deep": d["url"] + frag, "start": x["period_start"], "end": x["period_end"],
                         "days": _days(x["period_start"], x["period_end"]), "value": x["value"], "table": table(x["accession"], x["table_id"]),
                         "table_id": x["table_id"], "row": x["row_label"], "col": x["column_label"], "cell": x["cell_text"],
                         "unit": x["unit_stated"], "unit_source": x["unit_source"], "scale": x["scale"], "confidence": x["confidence"],
                         "notes": x["notes"], "prompt": x["prompt_version"]})
        srcs.sort(key=lambda s: -s["days"])
        r = ref.get((v["ticker"], v["field"], v["cal_q"]))
        rows.append({"ticker": v["ticker"], "field": v["field"], "cal_q": v["cal_q"], "fiscal_period": v["fiscal_period"], "value": v["value"], "method": v["method"],
                     "label": v["label"], "ref": r and r["value"], "ref_concept": r and r["concept"], "ref_accession": r and r["accession"],
                     "input_hash": v["input_hash"], "sources": srcs})
    return {"stage": stage, "tickers": tickers, "release": STAGES[stage]["release"], "fields": list(MVP_FIELDS), "quarters": MVP_QUARTERS,
            "rules": {r["id"]: {k: r[k] for k in ("title", "plain", "action")} for r in load()},
            "field_label": FIELD_LABEL, "method_label": METHOD_LABEL, "values": rows, "tables": tables, "exceptions": excs,
            "counts": {"filings": len(docs), "extractions": len(ext), "values": len(vals),
                       "agree": sum(v["label"] == "agree" for v in vals),
                       "open_exceptions": sum(e["severity"] != "info" for e in excs), "info_notes": sum(e["severity"] == "info" for e in excs)},
            "generated": datetime.now(timezone.utc).isoformat(timespec="minutes")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger report")
    ap.add_argument("--stage", type=int, default=1, choices=sorted(STAGES))
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    data = build(con, a.stage)
    page = (store.ROOT / "ledger" / "cli" / "report_template.html").read_text()
    title = f"Stage {a.stage} validation · {', '.join(data['tickers'])}"
    page = page.replace("__TITLE__", html.escape(title)).replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    out = store.ROOT / "reports" / f"stage{a.stage}-validation.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    print(f"wrote {out.relative_to(store.ROOT)} ({len(page) // 1024} KB): {data['counts']}")
    return 0
