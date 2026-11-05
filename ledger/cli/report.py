"""python -m ledger report --stage N | --ticker X …   ->  reports/<name>-validation.html

A self-contained page for checking a run by eye and recording any hand-check:
  - summary tiles and, per field, a chart of agent vs XBRL by fiscal year,
  - every fiscal-year value with its arithmetic, down to the cited statement cells (highlighted in the parsed table),
  - for a restated or disputed value, the filing's own sentence explaining why past years changed,
  - a link per source that opens the SEC filing scrolled to the cited row (Chrome text fragments),
  - a Verified checkbox and note per value, kept in the browser, exportable as golden/<stage>-handcheck.json.
"""
import argparse
import html
import json
from datetime import date, datetime, timezone
from urllib.parse import quote

from ..core import store
from ..core.ids import split_ids
from ..ingest.notes import restatement_note
from ..core.config import MVP_YEARS, RELEASE_FIELDS, STAGES, add_scope, scope
from ..release.release import to_check
from ..review.review import decisions, latest, open_items
from ..checks.rules import load
from ..checks.scorecard import scorecard
from ..checks.evidence import load_all

FIELD_LABEL = {"revenue": "Revenue", "capex": "Capex", "opex": "Opex", "cost_of_revenue": "Cost of revenue", "operating_income": "Operating income"}
METHOD_LABEL = {"reported": "As filed (one 10-K cell)", "computed": "Opex = revenue − cost of revenue − operating income, all from the same 10-K column"}


def _days(s, e):
    return (date.fromisoformat(e) - date.fromisoformat(s)).days + 1


def build(con, tickers: list[str], name: str) -> dict:
    stage = next((n for n in STAGES if f"stage{n}" == name), None)
    q = lambda sql, *p: [dict(zip([c[0] for c in con.execute(sql, list(p)).description], r)) for r in con.execute(sql, list(p)).fetchall()]
    docs = {d["accession"]: d for d in q("select * from documents where ticker in (select unnest(?))", tickers)}
    ext = {x["extraction_id"]: x for x in q("select * from extractions where ticker in (select unnest(?))", tickers)}
    ref = {(r["ticker"], r["field"], r["period"]): r for r in q("select * from reference_values where ticker in (select unnest(?))", tickers)}
    vals = q('select * from "values" where ticker in (select unnest(?)) order by ticker, field, period', tickers)
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

    notes = {}

    def explain(accn):  # the 10-K's own reason for changing past years, with a link that scrolls to it
        if accn not in notes:
            d = docs[accn]
            path = store.ROOT / "data" / "raw" / f"{d['cik']:010d}" / "docs" / f"{accn}.htm"
            n = path.exists() and restatement_note(path.read_text(errors="ignore"))
            notes[accn] = n and {"text": n, "url": d["url"] + "#:~:text=" + quote(" ".join(n.split()[:8]))}
        return notes[accn]

    ev = load_all()
    check, cur = to_check(vals), latest(decisions())
    decided = {(e["ticker"], e["field"], e["period"]): cur[e["exception_id"]] for e in excs
               if e["period"] and cur.get(e["exception_id"], {}).get("input_hash") == e["input_hash"]}
    rows = []
    for v in vals:
        srcs = []
        for i in split_ids(v["extraction_ids"]):
            x = ext.get(i)
            if not x:
                continue
            d = docs[x["accession"]]
            num = x["cell_text"].strip("()$ ").replace("—", "")
            frag = f"#:~:text={quote(x['row_label'])},{quote(num)}" if num else f"#:~:text={quote(x['row_label'])}"
            srcs.append({"id": i, "field": x["field"], "accession": x["accession"], "form": d["form"], "doc_period": d["period"], "filed": d["filed"],
                         "url": d["url"], "deep": d["url"] + frag, "start": x["period_start"], "end": x["period_end"],
                         "days": _days(x["period_start"], x["period_end"]), "value": x["value"], "table": table(x["accession"], x["table_id"]),
                         "table_id": x["table_id"], "row": x["row_label"], "col": x["column_label"], "cell": x["cell_text"],
                         "unit": x["unit_stated"], "unit_source": x["unit_source"], "scale": x["scale"], "confidence": x["confidence"],
                         "notes": x["notes"], "prompt": x["prompt_version"],
                         "machine": (m := ev.get(i)) and m["cell"] == x["cell_text"] and {"match": m["match"], "seen": m["seen"], "img": m["img"] and f"evidence/{m['img']}"} or None})
        r = ref.get((v["ticker"], v["field"], v["period"]))
        rows.append({"ticker": v["ticker"], "field": v["field"], "period": v["period"], "period_end": v["period_end"], "value": v["value"], "method": v["method"],
                     "label": v["label"], "basis": v["basis"], "first_reported": v["first_reported"], "ref": r and r["value"], "ref_concept": r and r["concept"], "ref_accession": r and r["accession"],
                     "input_hash": v["input_hash"], "sources": srcs,
                     "check": check.get((v["ticker"], v["field"], v["period"])),
                     "decision": (d := decided.get((v["ticker"], v["field"], v["period"]))) and {k: d[k] for k in ("kind", "reviewer", "reason")},
                     "why": explain(srcs[0]["accession"]) if srcs and (v["basis"] == "restated" or v["label"] == "unresolved") else None})
    return {"stage": stage, "name": name, "tickers": tickers, "fields": RELEASE_FIELDS, "years": MVP_YEARS,
            "rules": {r["id"]: {k: r[k] for k in ("title", "plain", "action")} for r in load()},
            "scorecard": scorecard(con, tickers, name), "field_label": FIELD_LABEL, "method_label": METHOD_LABEL, "values": rows, "tables": tables, "exceptions": open_items(excs, decisions()) + [e for e in excs if e["severity"] == "info"],
            "counts": {"filings": len(docs), "extractions": len(ext), "values": len(vals),
                       "agree": sum(v["label"] == "agree" for v in vals),
                       "open_exceptions": len(open_items(excs, decisions())), "info_notes": sum(e["severity"] == "info" for e in excs)},
            "generated": datetime.now(timezone.utc).isoformat(timespec="minutes")}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger report")
    add_scope(ap)
    ap.add_argument("--db", default=str(store.DEFAULT_DB))
    a = ap.parse_args(argv)
    con = store.init(a.db)
    tickers, name = scope(a)
    data = build(con, tickers, name)
    page = (store.ROOT / "ledger" / "cli" / "report_template.html").read_text()
    title = f"{'Stage ' + str(data['stage']) if data['stage'] else 'Run'} validation · {', '.join(tickers)}"
    page = page.replace("__TITLE__", html.escape(title)).replace("__DATA__", json.dumps(data).replace("</", "<\\/"))
    out = store.ROOT / "reports" / f"{name}-validation.html"
    out.parent.mkdir(exist_ok=True)
    out.write_text(page)
    print(f"wrote {out.relative_to(store.ROOT)} ({len(page) // 1024} KB): {data['counts']}")
    return 0
