"""DATAHQ's numbers: pipeline health, steps, the company scorecard, rule findings and releases.

Read only from what the pipeline already wrote: the database, the evidence and fault reports, and releases/.
Used by the app (`python -m ledger app`)."""
import json
from collections import Counter
from datetime import date, timedelta

from . import store
from .config import AI_SET, STAGES
from .review import decisions, open_items
from .scorecard import scorecard
from .evidence import load_all


def rows(con, sql, p=()):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def snapshot(con, stage: int = 3) -> dict:
    """Everything DATAHQ shows, from what the pipeline already wrote."""
    tickers, name = STAGES[stage]["tickers"], f"stage{stage}"
    t = [tickers]
    docs = rows(con, "select * from documents where ticker in (select unnest(?))", t)
    exts = rows(con, "select extraction_id from extractions where ticker in (select unnest(?))", t)
    vals = rows(con, 'select label from "values" where ticker in (select unnest(?))', t)
    excs = rows(con, "select * from exceptions where ticker in (select unnest(?))", t)
    todo = open_items(excs, decisions())
    ev = load_all()
    faults = json.loads((store.ROOT / "reports" / f"{name}-faults.json").read_text())
    last_run = con.execute("select max(started_at) from runs").fetchone()[0]
    names = {c["ticker"]: c["name"] for c in AI_SET}

    companies = []
    for s in scorecard(con, tickers, name):
        mine = sorted((d for d in docs if d["ticker"] == s["ticker"]), key=lambda d: d["period"])
        nxt = None
        if mine:  # the next fiscal year ends a year later; the company files after the same lag as last time
            p, f = date.fromisoformat(str(mine[-1]["period"])), date.fromisoformat(str(mine[-1]["filed"]))
            nxt = (p + timedelta(days=364 if p.weekday() != 6 or p.day > 7 else 371) + (f - p)).isoformat()
        done, total = map(int, s["cells_confirmed"].split("/"))
        companies.append({"ticker": s["ticker"], "company": names.get(s["ticker"], s["ticker"]), "filings": s["filings"],
                          "values": s["values"], "agree": s["agree"], "explained": s["explained_by_code"],
                          "decided": s["values"] - s["agree"] - s["explained_by_code"], "cells_confirmed": done, "cells": total,
                          "agent_minutes": s["agent_minutes"], "tokens": s["tokens"], "retries": s["retries"],
                          "for_a_person": s["for_a_person"], "warnings": s["warnings"],
                          "last_10k_period": str(mine[-1]["period"]) if mine else None, "last_10k_filed": str(mine[-1]["filed"]) if mine else None,
                          "next_10k_expected": nxt})

    escaped = sum(f["outcome"] == "escaped" for f in faults)
    confirmed = sum(bool(ev.get(e["extraction_id"], {}).get("match")) for e in exts)
    located = sum(bool(d["income_tables"]) and bool(d["cash_flow_tables"]) for d in docs)
    answered = len({e["extraction_id"].split("|")[0] for e in exts})
    labels = Counter(v["label"] for v in vals)
    pipeline = [
        {"step": "Find 10-Ks", "detail": "listed and fetched from SEC EDGAR", "done": len(docs), "of": len(docs), "unit": "10-Ks"},
        {"step": "Locate statements", "detail": "income statement and cash-flow statement found", "done": located, "of": len(docs), "unit": "10-Ks"},
        {"step": "Agent reads", "detail": "answer accepted with every citation resolving", "done": answered, "of": len(docs), "unit": "10-Ks"},
        {"step": "Re-read on filing", "detail": "cited cell found on the rendered 10-K", "done": confirmed, "of": len(exts), "unit": "cells"},
        {"step": "Match the SEC's data", "detail": "fiscal-year value agrees with XBRL; the rest are explained by code or decided",
         "done": labels["agree"], "of": len(vals), "unit": "values", "ok": not any(e["severity"] == "block" for e in todo)},
        {"step": "Fault test", "detail": "planted mistakes caught", "done": len(faults) - escaped, "of": len(faults), "unit": "faults"},
    ]
    for s in pipeline:
        s.setdefault("ok", s["done"] == s["of"])

    rule_meta = {r["rule_id"]: r for r in rows(con, "select rule_id, severity, description from rules")}
    hits, open_by = Counter(e["rule_id"] for e in excs), Counter(e["rule_id"] for e in todo)
    rules = [{"rule": r, "severity": m["severity"], "description": m["description"], "raised": hits[r], "open": open_by[r]}
             for r, m in sorted(rule_meta.items(), key=lambda kv: -hits[kv[0]])]

    releases = []
    for d in sorted((store.ROOT / "releases").glob("v*")):
        m, s = json.loads((d / "manifest.json").read_text()), d / "SIGNOFF.json"
        sig = json.loads(s.read_text()) if s.exists() else {}
        vs = (d / "values.csv").read_text().splitlines()[1:]
        releases.append({"version": m["version"], "companies": len(STAGES[m["stage"]]["tickers"]), "values": len(vs),
                         "hash": m["hash"][:12], "signed_by": sig.get("signed_by"), "signed_at": sig.get("signed_at"),
                         "prompt": m["prompt"], "parser": m["parser"]})

    health = [{"run_at": last_run, "companies": len(tickers), "filings": len(docs), "values": len(vals), "agree": labels["agree"],
               "cells_confirmed": confirmed, "cells": len(exts), "faults": len(faults), "faults_escaped": escaped,
               "for_a_person": sum(e["severity"] == "block" for e in todo), "warnings": sum(e["severity"] == "warn" for e in todo),
               "agent_minutes": round(sum(c["agent_minutes"] for c in companies), 1), "tokens": sum(c["tokens"] for c in companies),
               "latest_release": releases[-1]["version"] if releases else None,
               "latest_release_signed": bool(releases and releases[-1]["signed_by"])}]

    return {"health": health, "pipeline": pipeline, "companies": companies, "rules": rules, "releases": releases}
