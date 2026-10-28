"""What each company cost the pipeline: agent time and tokens, what came out, and what still needs a person.
Code changes per company aren't measurable here; they are logged by hand in docs/INGESTION.md."""
import json

from .review import decisions, open_items
from .store import ROOT
from .evidence import load_all


def scorecard(con, tickers: list[str], name: str) -> list[dict]:
    q = lambda sql: [dict(zip([c[0] for c in con.execute(sql, [tickers]).description], r)) for r in con.execute(sql, [tickers]).fetchall()]
    docs = q("select accession, ticker from documents where ticker in (select unnest(?))")
    runs = {}  # accession -> latest extract run detail
    for r in q("select subject, started_at, detail from runs where step = 'extract' and subject in (select accession from documents where ticker in (select unnest(?))) order by started_at"):
        runs[r["subject"]] = json.loads(r["detail"] or "{}")
    vals = q('select ticker, label, value, extraction_ids from "values" where ticker in (select unnest(?))')
    excs = q("select * from exceptions where ticker in (select unnest(?))")
    todo = open_items(excs, decisions())
    ev = load_all()
    out = []
    for t in tickers:
        mine = [d["accession"] for d in docs if d["ticker"] == t]
        rs = [runs.get(a, {}) for a in mine]
        headless = [r for r in rs if r.get("attempts")]
        ids = [i for v in vals if v["ticker"] == t and v["extraction_ids"] for i in v["extraction_ids"].split(",")]
        vs = [v for v in vals if v["ticker"] == t]
        out.append({"ticker": t, "filings": len(mine),
                    "agent": f"{len(headless)} headless" + (f", {len(mine) - len(headless)} in-session" if len(headless) < len(mine) else ""),
                    "agent_minutes": round(sum(r["seconds"] for r in headless) / 60, 1), "tokens": sum(r["input_tokens"] + r["output_tokens"] for r in headless),
                    "retries": sum(r["attempts"] - 1 for r in headless),
                    "values": sum(v["value"] is not None for v in vs), "agree": sum(v["label"] == "agree" for v in vs),
                    "explained_by_code": sum(v["label"] in ("definition_gap", "not_reported") for v in vs),
                    "cells_confirmed": f"{sum(bool(ev.get(i, {}).get('match')) for i in ids)}/{len(ids)}",
                    "for_a_person": sum(e["ticker"] == t and e["severity"] == "block" for e in todo),
                    "warnings": sum(e["ticker"] == t and e["severity"] == "warn" for e in todo)})
    return out


def table(rows: list[dict]) -> str:
    cols = list(rows[0]) if rows else []
    w = {c: max(len(c), *(len(str(r[c])) for r in rows)) for c in cols}
    return "\n".join(["  ".join(c.ljust(w[c]) for c in cols)] + ["  ".join(str(r[c]).ljust(w[c]) for c in cols) for r in rows])
