"""DATAHQ's numbers: what needs a person and why, what changed since the last run, what happened at the companies,
pipeline health, the company scorecard and releases.

Read only from what the pipeline already wrote: the database, the evidence and fault reports, and releases/.
Used by the app (`python -m ledger app`)."""
import csv
import json
from collections import Counter
from datetime import date, timedelta

from . import store
from .config import industry, stage_tickers, tracked
from .release import releases as release_dirs
from .review import apply, decisions, open_items
from .rules import load as load_rules
from .scorecard import scorecard
from .evidence import load_all
from .snapshots import diff, last_two

WATCH = store.ROOT / "data" / "watch.json"

# Why each kind of open item needs a person: the cause code could not name. Shown with every question. Only a block
# is a question; a warning is a finding about the company, flagged with whether the SEC's data confirms the number.
WHY = {
    "xbrl_reconcile": "The 10-K and the SEC's data disagree and code can't name why. A definition in definitions/companies.yaml settles it for good.",
    "cost_lines_summed": "Which lines count as cost of revenue is a judgement. Name the lines once in definitions/companies.yaml.",
}
CORROBORABLE = ("jump", "outlier_vs_own_history", "row_label_switch")  # a reading error would also disagree with XBRL; agreement rules it out



def rows(con, sql, p=()):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def snapshot(con, stage: int = 3) -> dict:
    """Everything DATAHQ shows, from what the pipeline already wrote."""
    companies_now = tracked()  # read fresh, so a company added in the app shows at once
    tickers, name = [c["ticker"] for c in companies_now], f"stage{stage}"
    t = [tickers]
    docs = rows(con, "select * from documents where ticker in (select unnest(?))", t)
    exts = rows(con, "select extraction_id from extractions where ticker in (select unnest(?))", t)
    vals = rows(con, 'select * from "values" where ticker in (select unnest(?))', t)
    excs = rows(con, "select * from exceptions where ticker in (select unnest(?))", t)
    todo = open_items(excs, decisions())
    ev = load_all()
    faults = json.loads((store.ROOT / "reports" / f"{name}-faults.json").read_text())
    last_run = con.execute("select max(started_at) from runs").fetchone()[0]
    names = {c["ticker"]: c["name"] for c in companies_now}
    ai = Counter(r[0] for r in con.execute("select ticker from ai_spend where ticker in (select unnest(?))", t).fetchall())
    nfacts = Counter(r[0] for r in con.execute("select ticker from facts where ticker in (select unnest(?))", t).fetchall())
    ntexts = Counter(r[0] for r in con.execute("select ticker from texts where ticker in (select unnest(?))", t).fetchall())

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
                          "ai_statements": ai[s["ticker"]], "facts": nfacts[s["ticker"]], "texts": ntexts[s["ticker"]],
                          "industry": industry(s["ticker"]),
                          "last_10k_period": str(mine[-1]["period"]) if mine else None, "last_10k_filed": str(mine[-1]["filed"]) if mine else None,
                          "next_10k_expected": nxt})

    escaped = sum(f["outcome"] == "escaped" for f in faults)
    confirmed = sum(bool(ev.get(e["extraction_id"], {}).get("match")) for e in exts)
    located = sum(bool(d["income_tables"]) and bool(d["cash_flow_tables"]) or (d["form"] == "10-K/A" and bool(d["income_tables"] or d["cash_flow_tables"])) for d in docs)
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
    for d in release_dirs():
        m, s = json.loads((d / "manifest.json").read_text()), d / "SIGNOFF.json"
        sig = json.loads(s.read_text()) if s.exists() else {}
        vs = (d / "values.csv").read_text().splitlines()[1:]
        releases.append({"version": m["version"], "companies": len(stage_tickers(m["stage"])), "values": len(vs),
                         "hash": m["hash"][:12], "signed_by": sig.get("signed_by"), "signed_at": sig.get("signed_at"),
                         "prompt": m["prompt"], "parser": m["parser"]})

    # Where every value stands: agrees with XBRL, a difference code explains, one a person decided, or one waiting on a person.
    waiting_keys = {(e["ticker"], e["field"], e["period"]) for e in todo if e["rule_id"] == "xbrl_reconcile"}
    unresolved = [v for v in vals if v["label"] == "unresolved"]
    waiting = sum((v["ticker"], v["field"], v["period"]) in waiting_keys for v in unresolved)
    explained = sum(v["label"] in ("definition_gap", "not_reported") for v in vals)

    # Is the latest release still what the pipeline would ship? Count values that differ from it.
    changed = None
    if releases:
        d = release_dirs()[-1]
        if json.loads((d / "manifest.json").read_text())["stage"] == stage:
            shipped = {(r["ticker"], r["field"], r["period"]): (r["value"], r["basis"]) for r in csv.DictReader((d / "values.csv").open())}
            now = {(v["ticker"], v["field"], v["period"]): ("" if v["value"] is None else str(v["value"]), v["basis"]) for v in apply(vals, excs, decisions())}
            changed = sum(shipped.get(k) != now.get(k) for k in shipped.keys() | now.keys())

    # Use a person's time only where it's needed. A jump or outlier on values that agree with the SEC's data can't be a
    # unit or column misread (XBRL is an independent read), so it's a finding about the company, not a question.
    label = {(v["ticker"], v["field"], v["period"]): v["label"] for v in vals}
    series = {}
    for v in vals:
        if v["value"] is not None:
            series.setdefault((v["ticker"], v["field"]), {})[v["period"]] = v["value"]
    def corroborated(e):
        if e["rule_id"] == "row_label_switch":  # the name changed; if the SEC's data confirms every year, it wasn't a misread
            f = "opex" if e["field"] in ("cost_of_revenue", "operating_income") else e["field"]
            ls = [l for (t, ff, _), l in label.items() if t == e["ticker"] and ff == f]
            return bool(ls) and all(l == "agree" for l in ls)
        if e["rule_id"] == "jump":
            s = sorted(series.get((e["ticker"], e["field"]), {}))
            prev = s[s.index(e["period"]) - 1] if e["period"] in s and s.index(e["period"]) else None
            keys = [(e["ticker"], e["field"], e["period"])] + ([(e["ticker"], e["field"], prev)] if prev else [])
        else:
            keys = [(e["ticker"], "capex", e["period"]), (e["ticker"], "revenue", e["period"])]
        return all(label.get(k) == "agree" for k in keys)
    rule_text = {r["id"]: r for r in load_rules()}
    parts = rows(con, "select ticker, accession, row_label from extractions where field = 'cost_of_revenue_part' and ticker in (select unnest(?))", t)
    ref = {(r["ticker"], r["field"], r["period"]): r["value"] for r in rows(con, "select ticker, field, period, value from reference_values where ticker in (select unnest(?))", t)}
    questions, moves = [], []
    for e in todo:
        if e["severity"] != "block":  # a warning is a finding, not a question; the flag says whether the SEC's data confirms it
            moves.append({**e, "confirmed": e["rule_id"] in CORROBORABLE and corroborated(e)})
            continue
        detail = None
        if e["rule_id"] == "cost_lines_summed":  # the lines and the size of the gap, so the judgement is easy to make
            ls = {}
            for x in parts:
                if x["ticker"] == e["ticker"]:
                    ls.setdefault(x["row_label"], set()).add(x["accession"])
            detail = {"lines": [{"label": k, "filings": len(v)} for k, v in sorted(ls.items(), key=lambda kv: -len(kv[1]))],
                      "gaps": [{"period": v["period"], "ours": v["value"], "sec": ref.get((v["ticker"], "opex", v["period"]))}
                               for v in sorted(vals, key=lambda v: v["period"]) if v["ticker"] == e["ticker"] and v["label"] == "definition_gap"]}
        questions.append({"detail": detail, "exception_id": e["exception_id"], "ticker": e["ticker"], "company": names.get(e["ticker"], e["ticker"]), "rule": e["rule_id"], "severity": e["severity"],
                          "title": rule_text.get(e["rule_id"], {}).get("title", e["rule_id"]), "why": WHY.get(e["rule_id"], "Code can't decide this."),
                          "field": e["field"], "period": e["period"], "message": e["message"]})

    # What happened at the companies: restatements, big moves the SEC's data confirms, opex above revenue.
    findings = []
    for v in vals:
        if v["basis"] == "restated" and v["value"] is not None and v["first_reported"]:
            pct = (v["value"] - v["first_reported"]) / abs(v["first_reported"])
            findings.append({"kind": "restated", "ticker": v["ticker"], "company": names.get(v["ticker"]), "field": v["field"], "period": v["period"],
                             "before": v["first_reported"], "after": v["value"], "size": abs(pct), "confirmed": v["label"] == "agree", "message": None})
    for e in moves:
        base = {"ticker": e["ticker"], "company": names.get(e["ticker"]), "field": e["field"], "period": e["period"], "confirmed": e["confirmed"], "message": e["message"]}
        if e["rule_id"] == "jump" and e["period"] in (s := series.get((e["ticker"], e["field"]), {})) and sorted(s).index(e["period"]):
            ks = sorted(s); prev = ks[ks.index(e["period"]) - 1]
            findings.append({**base, "kind": "jump", "before": s[prev], "after": s[e["period"]], "from": prev, "size": max(s[e["period"]] / s[prev], s[prev] / s[e["period"]])})
        elif e["rule_id"] == "outlier_vs_own_history" and (e["ticker"], "capex") in series and (e["ticker"], "revenue") in series:
            c, r = series[(e["ticker"], "capex")][e["period"]], series[(e["ticker"], "revenue")][e["period"]]
            findings.append({**base, "kind": "capex_intensity", "field": "capex", "before": r, "after": c, "size": c / r})
        elif e["rule_id"] == "row_label_switch":
            findings.append({**base, "kind": "row_switch", "before": None, "after": None, "size": 0})
        else:
            findings.append({**base, "kind": "other", "before": None, "after": None, "size": 0})
    for (t, f), s in series.items():
        if f == "opex":
            for q, v in s.items():
                r = series.get((t, "revenue"), {}).get(q)
                if r and v > r:
                    findings.append({"kind": "opex_over_revenue", "ticker": t, "company": names.get(t), "field": "opex", "period": q,
                                     "before": r, "after": v, "size": v / r, "confirmed": label.get((t, "opex", q)) == "agree", "message": None})
    order = {"restated": 0, "jump": 1, "capex_intensity": 2, "opex_over_revenue": 3, "row_switch": 4, "other": 5}
    findings.sort(key=lambda x: (x.get("confirmed", True), order[x["kind"]], -x["size"]))  # what the SEC's data can't confirm comes first

    watch = json.loads(WATCH.read_text()) if WATCH.exists() else None
    full = con.execute("select started_at, seconds, outcome, detail from runs where step = 'run' order by started_at desc limit 1").fetchone()

    run = [c for c in companies if c["tokens"]]  # companies read headless, so their cost was measured
    health = [{"run_at": last_run, "texts": sum(ntexts.values()), "facts": sum(nfacts.values()), "companies": len(tickers), "filings": len(docs), "values": len(vals), "agree": labels["agree"],
               "cells_confirmed": confirmed, "cells": len(exts), "faults": len(faults), "faults_escaped": escaped,
               "for_a_person": sum(e["severity"] == "block" for e in todo), "warnings": sum(e["severity"] == "warn" for e in todo),
               "agent_minutes": round(sum(c["agent_minutes"] for c in companies), 1), "tokens": sum(c["tokens"] for c in companies),
               "latest_release": releases[-1]["version"] if releases else None,
               "latest_release_signed": bool(releases and releases[-1]["signed_by"]), "latest_release_at": releases[-1]["signed_at"] if releases else None,
               "explained": explained, "decided": len(unresolved) - waiting, "waiting": waiting, "changed_since_release": changed,
               "warning_groups": len({(e["ticker"], e["rule_id"]) for e in todo if e["severity"] == "warn"}),
               "per_company_minutes": round(sum(c["agent_minutes"] for c in run) / len(run), 1) if run else None,
               "per_company_tokens": round(sum(c["tokens"] for c in run) / len(run)) if run else None, "measured_companies": len(run)}]

    per_q = Counter(q["ticker"] for q in questions)
    restated = Counter(f["ticker"] for f in findings if f["kind"] == "restated")
    for c in companies:
        c["questions"], c["restated"] = per_q[c["ticker"]], restated[c["ticker"]]
        c["note"] = next((x.get("note") for x in companies_now if x["ticker"] == c["ticker"]), None)
    health[0] |= {"questions": len(questions), "findings": len(findings),
                  "full_run": full and {"at": full[0], "seconds": full[1], "outcome": full[2]}}
    return {"health": health, "pipeline": pipeline, "companies": companies, "rules": rules, "releases": releases,
            "questions": questions, "findings": findings, "since": diff(*last_two()), "watch": watch}
