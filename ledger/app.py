"""DATAHQ, the ledger's web app: the morning dashboard, each company through every pipeline step, the named agents
(model, prompt, every run), and an outputs explorer over the signed releases.

Reads the database read-only on every request, so it always shows the latest run. It writes only three things, all
attributed: agent changes (agents/agents.json, new prompt versions), a reviewer's decision to accept warnings
(decisions/decisions.jsonl, the same log as `ledger review`), and a company added to data/companies.json, which starts
`ledger run` for it in the background. Serves on 127.0.0.1 only."""
import csv
import hashlib
import io
import json
import mimetypes
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import zipfile
from urllib.parse import parse_qs, urlparse

import duckdb

from . import agents, progress, store
from .cli.report import build
from .config import ADDED, INDUSTRIES, added, industry, stage_tickers, tracked
from .ingest.edgar import fetch_tickers
from .extract import OUTPUTS
from .evidence import load_all
from .hq import snapshot
from . import api, resolutions, views
from .publish import NotPublishable
from .release import RELEASES, releases
from .review import decisions, latest, open_items
from .rules import load as load_rules

PAGE = store.ROOT / "ledger" / "app.html"
EVIDENCE = store.ROOT / "reports" / "evidence"
STAGE = 3


class Busy(Exception):
    """The pipeline holds the database while it runs."""


def _con():
    try:
        return duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    except duckdb.Error as e:
        raise Busy("the pipeline is writing to the database; try again when the run ends") from e


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def company(ticker: str) -> dict:
    if ticker not in {c["ticker"] for c in tracked()}:
        raise KeyError(ticker)
    con = _con()
    try:
        docs = _rows(con, "select accession, form, period, filed, url, sha256, bytes, parser_version, table_count, income_tables, cash_flow_tables "
                          "from documents where ticker = ? order by period", ticker)
        runs = {}
        for r in _rows(con, "select step, subject, started_at, outcome, versions, detail from runs where subject in "
                            "(select accession from documents where ticker = ?) order by started_at", ticker):
            runs[(r["step"], r["subject"])] = {**r, "versions": json.loads(r["versions"] or "{}"), "detail": json.loads(r["detail"] or "{}")}
        for d in docs:
            d["parse"], d["agent"] = runs.get(("parse", d["accession"])), runs.get(("extract", d["accession"]))
        excs = _rows(con, "select * from exceptions where ticker = ? order by severity, rule_id, period", ticker)
        skipped = [{**json.loads(r["detail"]), "accession": r["subject"]} for r in _rows(con, "select subject, detail from runs where step = 'parse' and outcome = 'skipped'")
                   if json.loads(r["detail"] or "{}").get("ticker") == ticker]
        report = build(con, [ticker], f"stage{STAGE}")
        ai = _rows(con, "select * from ai_spend where ticker = ? order by field, period, kind", ticker)
        attribution = _rows(con, "select * from attribution where ticker = ? order by field, period, kind", ticker)
        facts = _rows(con, "select f.*, e.table_id, e.row_label, e.column_label, e.cell_text from facts f left join note_extractions e on e.extraction_id = split_part(f.extraction_ids, ',', -1) "
                           "where f.ticker = ? order by f.field, f.dimension, f.period", ticker)
    finally:
        con.close()
    cur, still = latest(decisions()), {e["exception_id"] for e in open_items(excs, decisions())}
    rules = {r["id"]: r for r in load_rules()}
    for e in excs:
        d = cur.get(e["exception_id"])
        e["status"] = "note" if e["severity"] == "info" else "open" if e["exception_id"] in still else "decided"
        e["decision"] = d and d.get("input_hash") == e["input_hash"] and {k: d[k] for k in ("kind", "reason", "reviewer", "decided_at")} or None
        e["rule_title"] = rules.get(e["rule_id"], {}).get("title", e["rule_id"])
    rel = releases()
    released = [r for r in csv.DictReader((rel[-1] / "values.csv").open()) if r["ticker"] == ticker] if rel else []
    info = next(c for c in tracked() if c["ticker"] == ticker)
    return {"ticker": ticker, "name": info["name"], "note": info.get("note"), "documents": docs, "skipped": skipped, "exceptions": excs,
            "values": report["values"], "tables": report["tables"], "scorecard": report["scorecard"][0],
            "release": rel[-1].name if rel else None, "released": len(released), "ai_spend": ai, "facts": facts, "attribution": attribution}


def agents_view() -> dict:
    cfg = agents.load()
    con = _con()
    try:
        runs = _rows(con, "select r.subject as accession, d.ticker, d.period, r.started_at, r.outcome, r.versions, r.detail from runs r "
                          "join documents d on d.accession = r.subject where r.step = 'extract' order by r.started_at desc")  # one row per filing read, not the step log
    finally:
        con.close()
    for r in runs:
        r["versions"], r["detail"] = json.loads(r["versions"] or "{}"), json.loads(r["detail"] or "{}")
    con = _con()
    try:
        h = snapshot(con, STAGE)["health"][0]
    finally:
        con.close()
    cost = h["per_company_minutes"] is not None and {"minutes": h["per_company_minutes"], "tokens": h["per_company_tokens"], "companies": h["measured_companies"]} or None
    out = {}
    for aid, a in cfg.items():
        vs = agents.versions(aid)
        out[aid] = {**a, "id": aid, "versions": vs, "prompts": {v: agents.prompt_text(v) for v in vs}, "runs": runs, "cost": cost}
    return out


def latest_signed():
    signed = [d for d in releases() if (d / "SIGNOFF.json").exists()]
    return signed[-1] if signed else None


def attribution_view() -> dict:
    """The Attribution tab: every model with its versions, the attributor's prompt, every row, and the last load's diff."""
    cfg = agents.load()["attributor"]
    con = _con()
    try:
        rows = _rows(con, "select * from attribution order by ticker, field, period, kind")
    finally:
        con.close()
    present = {c["ticker"] for c in tracked()}
    models = {}
    for ind, ver in cfg["models"].items():
        vs = agents.model_versions(ind)
        models[ind] = {"version": ver, "versions": vs, "texts": {v: agents.model_text(v) for v in vs},
                       "companies": sorted(t for t in INDUSTRIES.get(ind, []) if t in present) if ind != "other" else sorted(t for t in present if industry(t) == "other")}
    diff_path = store.ROOT / "data" / "attribution" / "diff.json"
    return {"models": models, "prompt": cfg["prompt"], "history": cfg["history"], "rows": rows,
            "diff": json.loads(diff_path.read_text()) if diff_path.exists() else None}


DC = re.compile(r"data ?cent|ai cloud|cloud|compute", re.I)


def insights() -> dict:
    """The Insights tab, from the live tables: buyers' AI capex against their total capex by year, sellers' data-center
    revenue, every company's latest attribution, and the method mix. Labelled against the signed release."""
    con = _con()
    try:
        vals = _rows(con, 'select ticker, field, period, value from "values" where value is not null')
        attr = _rows(con, "select ticker, period, method, ai_amount, ai_share, confidence from attribution where field = 'capex' and kind = 'actual'")
        segs = _rows(con, "select ticker, dimension, period, value from facts where field = 'segment_revenue'")
    finally:
        con.close()
    roles = {c["ticker"]: c.get("role", "other") for c in tracked()}
    names = {c["ticker"]: c["name"] for c in tracked()}
    years = sorted({v["period"] for v in vals})
    capex = {(v["ticker"], v["period"]): v["value"] for v in vals if v["field"] == "capex"}
    ai = {(a["ticker"], a["period"]): a for a in attr}
    by_year = []
    for y in years:
        buyers = [t for t in roles if roles[t] == "buyer" and (t, y) in capex]
        total = sum(capex[(t, y)] for t in buyers)
        attributed = sum(ai[(t, y)]["ai_amount"] for t in buyers if (t, y) in ai and ai[(t, y)]["ai_amount"] is not None)
        covered = sum(capex[(t, y)] for t in buyers if (t, y) in ai and ai[(t, y)]["ai_amount"] is not None)
        dc = {}
        for s in segs:
            if roles.get(s["ticker"]) == "seller" and s["period"] == y and DC.search(s["dimension"] or ""):
                dc[s["ticker"]] = max(dc.get(s["ticker"], 0), s["value"])  # one line per seller: the biggest data-center-like line
        by_year.append({"period": y, "buyers": len(buyers), "capex": total, "ai_capex": attributed, "capex_covered": covered, "sellers_dc": sum(dc.values()), "sellers": len(dc)})
    latest = []
    for t in sorted(roles):
        mine = sorted((k[1] for k in ai if k[0] == t and ai[k]["ai_amount"] is not None))
        if not mine:
            continue
        y = mine[-1]
        a = ai[(t, y)]
        latest.append({"ticker": t, "company": names[t], "role": roles[t], "industry": industry(t), "period": y, "ai_amount": a["ai_amount"], "capex": capex.get((t, y)),
                       "share": a["ai_share"], "method": a["method"], "confidence": a["confidence"]})
    methods = {}
    for a in attr:
        methods[a["method"]] = methods.get(a["method"], 0) + 1
    series = {}  # per buyer with any attributed amount: year -> capex, AI amount, method
    for (t, y), a in ai.items():
        if roles.get(t) == "buyer" and any(x["ai_amount"] is not None for (tt, _), x in ai.items() if tt == t):
            series.setdefault(t, {})[y] = {"capex": capex.get((t, y)), "ai_amount": a["ai_amount"], "share": a["ai_share"], "method": a["method"]}
    rel = latest_signed()
    sig = json.loads((rel / "SIGNOFF.json").read_text()) if rel else {}
    return {"years": years, "by_year": by_year, "latest": sorted(latest, key=lambda x: -x["ai_amount"]), "methods": methods, "series": series, "names": names,
            "release": rel.name if rel else None, "signed_by": sig.get("signed_by"), "signed_at": sig.get("signed_at"),
            "release_has_attribution": bool(rel and (rel / "attribution.csv").exists())}


FIELD_KIND = {"revenue": "spent", "capex": "spent", "opex": "spent", "ai_capex": "spent", "ai_opex": "spent", "segment_capex": "spent", "segment_revenue": "spent",
              "ppe_category": "spent", "finance_lease_liability": "committed", "purchase_commitments": "committed", "ai_capex_outlook": "planned", "ai_opex_outlook": "planned",
              "capex_guidance": "planned"}


def data(q: dict) -> dict:
    """The dataset in long format for the data screen: one row per entity, field, dimension, year and kind, with its
    provenance ids. Filters: t (tickers, comma), f (fields, comma), y (years, comma), k (spent|committed|planned)."""
    want_t = set(q.get("t", "").upper().split(",")) - {""}
    want_f = set(q.get("f", "").split(",")) - {""}
    want_y = set(q.get("y", "").upper().split(",")) - {""}
    want_k = set(q.get("k", "").split(",")) - {""}
    con = _con()
    try:
        rows = []
        for v in _rows(con, 'select ticker, field, period, value, label, basis, extraction_ids, source from "values" where value is not null'):
            rows.append({"ticker": v["ticker"], "field": v["field"], "dimension": "", "period": v["period"], "kind": "spent", "value": v["value"], "unit": "usd",
                         "check": v["label"], "method": "cell", "confidence": None, "basis": v["basis"], "prov": {"extractions": v["extraction_ids"], "table": "values"}})
        for f in _rows(con, "select ticker, field, dimension, period, value, label, reference, accession, extraction_ids, basis from facts"):
            rows.append({"ticker": f["ticker"], "field": f["field"], "dimension": f["dimension"], "period": f["period"], "kind": FIELD_KIND.get(f["field"], "spent"), "value": f["value"], "unit": "usd",
                         "check": f["label"], "method": "cell", "confidence": None, "basis": f["basis"], "prov": {"extractions": f["extraction_ids"], "accession": f["accession"], "table": "facts", "xbrl": f["reference"]}})
        for a in _rows(con, "select * from attribution"):
            if a["ai_amount"] is None:
                continue
            rows.append({"ticker": a["ticker"], "field": f"ai_{a['field']}" + {"outlook": "_outlook", "committed": "_committed"}.get(a["kind"], ""), "dimension": "", "period": a["period"],
                         "kind": {"outlook": "planned", "committed": "committed"}.get(a["kind"], "spent"), "value": a["ai_amount"], "unit": "usd", "check": None, "method": a["method"], "confidence": a["confidence"],
                         "basis": a["basis"], "share": a["ai_share"], "prov": {"inputs": a["inputs"], "model": a["model"], "prompt": a["prompt_version"], "table": "attribution"}})
        for s in _rows(con, "select * from ai_spend where class = 'explicit_amount' and scope = 'total'"):
            rows.append({"ticker": s["ticker"], "field": f"{s['field']}_guidance", "dimension": "", "period": s["period"], "kind": "planned" if s["kind"] == "outlook" else "spent",
                         "value": (s["amount_low"] + s["amount_high"]) // 2, "unit": "usd", "check": None, "method": "stated", "confidence": None, "basis": s["quote"],
                         "range": [s["amount_low"], s["amount_high"]], "prov": {"text": s["text_id"], "source": s["source"], "accession": s["accession"], "table": "ai_spend"}})
        urls = {d["accession"]: d["url"] for d in _rows(con, "select accession, url from documents")}
    finally:
        con.close()
    idx = resolutions.by_row()
    for r in rows:
        acc = r["prov"].get("accession") or (r["prov"].get("extractions") or "").split("|")[0]
        r["prov"]["url"] = urls.get(acc)
        t = r["prov"]["table"]
        r["status"] = (resolutions.status_of(idx, "attribution", r["ticker"], r["field"].replace("ai_", "").replace("_outlook", "").replace("_committed", ""), "", r["period"], {"planned": "outlook", "committed": "committed"}.get(r["kind"], "actual")) if t == "attribution"
                       else resolutions.status_of(idx, "facts", r["ticker"], r["field"], r["dimension"], r["period"]) if t == "facts"
                       else resolutions.status_of(idx, "values", r["ticker"], r["field"], "", r["period"]) if t == "values" else "")
        r["flag"] = "share_over_total" if r.get("share") is not None and r["share"] > 1 else "differs_from_xbrl" if r.get("check") == "unresolved" else ""
    rows = [r for r in rows if (not want_t or r["ticker"] in want_t) and (not want_f or r["field"] in want_f) and (not want_y or r["period"] in want_y) and (not want_k or r["kind"] in want_k)]
    names = {c["ticker"]: c["name"] for c in tracked()}
    fields = sorted({r["field"] for r in rows} if want_t else set(FIELD_KIND) | {"opex_guidance"})
    return {"rows": rows, "names": names, "industries": {c["ticker"]: industry(c["ticker"]) for c in tracked()}, "roles": {c["ticker"]: c.get("role", "other") for c in tracked()},
            "fields": fields, "kinds": ["spent", "committed", "planned"]}


def usd_(n) -> str:
    return "—" if n is None else f"${n / 1e6:,.0f}M"


_FLOW: dict = {}


def _stamp() -> tuple:
    """What the Flow page depends on: the database, the resolutions, the attribution diff, the evaluation, the releases, the company list."""
    paths = [store.DEFAULT_DB, resolutions.LOG, store.ROOT / "data" / "attribution" / "diff.json", store.ROOT / "reports" / "evaluation.json", RELEASES, ADDED, EVIDENCE]
    return tuple(p.stat().st_mtime_ns if p.exists() else 0 for p in paths)


def flow(scope: str) -> dict:
    """`_flow` cached by scope while nothing it reads has changed; the first load after a run pays once."""
    key = (scope, _stamp())
    if key not in _FLOW:
        if len(_FLOW) > 24:
            _FLOW.clear()
        _FLOW[key] = _flow(scope)
    return _FLOW[key]


def _flow(scope: str) -> dict:
    """The flow screen: what changed, then each stage's artifacts and checks, for a scope (all, an industry, or a
    ticker). Everything from what the pipeline already wrote."""
    present = {c["ticker"] for c in tracked()}
    if scope in INDUSTRIES or scope == "other":
        tickers = sorted(t for t in present if industry(t) == scope)
    elif scope and scope != "all":
        tickers = [scope.upper()] if scope.upper() in present else []
    else:
        tickers = sorted(present)
    con = _con()
    try:
        hqd = snapshot(con, STAGE)
        t = [tickers]
        vals = _rows(con, 'select ticker, field, period, value, label from "values" where ticker in (select unnest(?))', tickers)
        facts = _rows(con, "select ticker, field, dimension, period, value, label from facts where ticker in (select unnest(?))", tickers)
        stmts = con.execute("select count(*), count(distinct source) from ai_statements where ticker in (select unnest(?))", t).fetchone()
        texts = con.execute("select kind, count(*) from texts where ticker in (select unnest(?)) group by 1", t).fetchall()
        docs = con.execute("select count(*) from documents where ticker in (select unnest(?))", t).fetchone()[0]
        exts = _rows(con, "select extraction_id from extractions where ticker in (select unnest(?))", tickers)
        attr = _rows(con, "select * from attribution where ticker in (select unnest(?))", tickers)
    finally:
        con.close()
    ev_path, diff_path = store.ROOT / "reports" / "evaluation.json", store.ROOT / "data" / "attribution" / "diff.json"
    ev = json.loads(ev_path.read_text()) if ev_path.exists() else None
    diff = json.loads(diff_path.read_text()) if diff_path.exists() else None
    rel = latest_signed()
    # what changed since the signed release: values and facts that differ from the release files
    rel_vals = {(r["ticker"], r["field"], r["period"]): r["value"] for r in csv.DictReader((rel / "values.csv").open())} if rel else {}
    rel_facts = {(r["ticker"], r["field"], r["dimension"], r["period"]): r["value"] for r in csv.DictReader((rel / "facts.csv").open())} if rel and (rel / "facts.csv").exists() else {}
    vals_changed = [v for v in vals if rel_vals and str(v["value"] if v["value"] is not None else "") != rel_vals.get((v["ticker"], v["field"], v["period"]), "")]
    facts_changed = [f for f in facts if rel_facts and str(f["value"]) != rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"]), "")]
    ev_rows = [r for r in (ev["rows"] if ev else []) if r["ticker"] in tickers]
    since = hqd["since"] or {}
    ev_load = load_all()
    changed = {"new_filings": [f for f in (hqd["watch"] or {}).get("new", []) if f["ticker"] in tickers],
               "filings_read": [f for f in since.get("new_filings", []) if f.split("|")[0] in tickers],
               "values_changed": [{"key": f"{v['ticker']}|{v['field']}|{v['period']}", "before": rel_vals.get((v["ticker"], v["field"], v["period"])), "after": v["value"]} for v in vals_changed][:50],
               "facts_changed": len(facts_changed),
               "attribution_changed": [r for r in (diff or {}).get("rows", []) if r["key"].split("|")[0] in tickers],
               "references_disagree": [r for r in ev_rows if r["outcome"] == "disagree"],
               "release": rel.name if rel else None, "last_run": hqd["health"][0]["run_at"]}
    # the queue: every issue for the scope, with where it is, what it touches, the dollars at stake, and the action
    con = _con()
    try:
        cites = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, accession, table_id, row_label, column_label, cell_text from note_extractions where ticker in (select unnest(?))", tickers)}
        urls = {d["accession"]: d["url"] for d in _rows(con, "select accession, url from documents where ticker in (select unnest(?))", tickers)}
        fact_ref = {(f["ticker"], f["field"], f["dimension"], f["period"]): f for f in _rows(con, "select ticker, field, dimension, period, reference, extraction_ids from facts where ticker in (select unnest(?))", tickers)}
    finally:
        con.close()
    uses = {}  # pack input id -> attributions that rest on it
    for a in attr:
        for i in (a["inputs"] or "").split(","):
            if i:
                uses.setdefault(i, []).append(a)
    capex_of = {(v["ticker"], v["period"]): v["value"] for v in vals if v["field"] == "capex" and v["value"] is not None}
    res = resolutions.latest()
    signed_at = json.loads((rel / "SIGNOFF.json").read_text())["signed_at"] if rel else ""
    queue = []
    for f in changed["new_filings"]:
        queue.append({"kind": "new_filing", "state": "new", "ticker": f["ticker"], "where": f"{f['form']} for the year ended {f['period']}", "impact": "values, facts, statements and attribution for the year", "action": "run", "detail": f})
    for e in hqd["questions"]:
        if e["ticker"] in tickers:
            queue.append({"kind": "blocked", "state": "blocked", "ticker": e["ticker"], "where": f"{e['field'] or ''} {e['period'] or ''}".strip() or e["rule"], "impact": "blocks the release", "action": "definition", "detail": e})
    for r in ev_rows:
        if r["outcome"] == "disagree":
            cap = capex_of.get((r["ticker"], r["period"]))
            at_stake = round(abs((r["ours"] or 0) - r["reference"]) * cap) if r["measure"] == "share" and cap else (abs((r["ours"] or 0) - r["reference"]) if r["measure"] == "amount" else 0)
            queue.append({"kind": "reference_disagrees", "state": "disagrees", "ticker": r["ticker"], "where": f"AI {r.get('field', 'capex')} {r['period']}", "impact": f"the attribution by {r['method']}: {usd_(at_stake)} between ours and the stated figure",
                          "dollars": at_stake, "new": True, "action": "method", "detail": r})
    for f in facts_changed[:30]:
        queue.append({"kind": "fact_changed", "state": "moved", "ticker": f["ticker"], "where": f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " "), "impact": "attribution inputs; the next release", "dollars": 0, "new": True, "action": "release",
                      "detail": {**f, "release_value": (lambda v: None if v in (None, "") else float(v))(rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"])))}})
    for f in facts:
        if f["label"] == "unresolved":
            fid = f"fact:{f['ticker']}|{f['field']}|{f['dimension']}|{f['period']}"
            used_by = uses.get(fid, [])
            fr = fact_ref.get((f["ticker"], f["field"], f["dimension"], f["period"]), {})
            cite = cites.get((fr.get("extraction_ids") or "").split(",")[-1])
            key = f"{f['ticker']}|{f['field']}|{f['dimension']}|{f['period']}"
            queue.append({"kind": "fact_differs", "state": "disagrees", "ticker": f["ticker"], "where": f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " "),
                          "impact": (f"feeds {len(used_by)} attribution{'s' * (len(used_by) != 1)} worth {usd_(sum(a['ai_amount'] or 0 for a in used_by))}" if used_by else "feeds no attribution"),
                          "dollars": sum(a["ai_amount"] or 0 for a in used_by), "new": key not in {"|".join(k) for k in rel_facts}, "action": "definition",
                          "detail": {**f, "reference": fr.get("reference"), "cite": cite, "url": urls.get((cite or {}).get("accession")), "used_by": [{"field": a["field"], "period": a["period"], "ai_amount": a["ai_amount"], "method": a["method"]} for a in used_by],
                                     "release_value": rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"]))}})
    for r in changed["attribution_changed"]:
        b, a_ = r["before"][1] or 0, r["after"][1] or 0
        if not b and not a_:
            continue  # none to words-only, or back: no dollars moved, nothing to judge
        queue.append({"kind": "attribution_moved", "state": "moved", "ticker": r["key"].split("|")[0], "where": " ".join(r["key"].split("|")[1:]), "impact": f"the dataset: {usd_(abs(a_ - b))} moved; the change note", "dollars": abs(a_ - b), "new": (diff or {}).get("at", "") > signed_at, "action": "release", "detail": r})
    for x in hqd["findings"]:
        if x["ticker"] in tickers and not x.get("confirmed", True):
            queue.append({"kind": "finding_unconfirmed", "state": "look", "ticker": x["ticker"], "where": f"{x['field'] or ''} {x['period'] or ''}".strip(), "impact": "a value the SEC's data can't confirm", "action": "open", "detail": x})
    for q_ in queue:
        q_.setdefault("dollars", 0); q_.setdefault("new", False)
        q_["key"] = f"{q_['kind']}|{q_['ticker']}|{q_['where']}"
        q_["hash"] = hashlib.sha256(json.dumps(q_["detail"], sort_keys=True, default=str).encode()).hexdigest()[:12]
        r_ = res.get(q_["key"])
        q_["resolution"] = r_ if r_ and r_["hash"] == q_["hash"] else None
        if q_["resolution"] and q_["resolution"]["state"] == "blocks":
            q_["state"] = "blocked"
    order = {"blocked": 0, "disagrees": 1, "new": 2, "moved": 3, "look": 4}
    noise = [q_ for q_ in queue if q_["kind"] == "fact_differs" and not q_["dollars"]]
    queue = [q_ for q_ in queue if not (q_["kind"] == "fact_differs" and not q_["dollars"])]
    queue.sort(key=lambda q_: (0 if q_["state"] == "blocked" else 1, -q_["dollars"], order[q_["state"]], q_["ticker"]))
    open_ = [q_ for q_ in queue if not q_["resolution"] or q_["resolution"]["state"] == "fix"]
    # release: what blocks (the gates' blocks plus what a person marked), the diff against the last signed release, a change note
    blocks = [q_ for q_ in queue if q_["state"] == "blocked"]
    note = []
    if rel:
        if vals_changed: note.append(f"{len(vals_changed)} values changed since {rel.name}.")
        if facts_changed: note.append(f"{len(facts_changed)} facts from the notes changed or were added since {rel.name}.")
        if diff and diff.get("changed"): note.append(f"{diff['changed']} attribution rows moved in the last load ({diff['at'][:10]}).")
        if changed["references_disagree"]: note.append(f"{len(changed['references_disagree'])} attributions disagree with a stated reference and ship marked as such.")
    release = {"last": rel.name if rel else None, "blocks": len(blocks), "unresolved": len(open_), "values_changed": len(vals_changed), "facts_changed": len(facts_changed),
               "attribution_moved": len(changed["attribution_changed"]), "note": " ".join(note) or "Nothing has changed since the last signed release.",
               "commands": [f"uv run python -m ledger release vX.Y.Z --stage 3", "uv run python -m ledger signoff vX.Y.Z --by \"Kenny Geiler\""]}
    kinds = {"spent": 0, "committed": 0, "planned": 0}
    for a in attr:
        if a["ai_amount"] is not None:
            kinds["planned" if a["kind"] == "outlook" else "spent"] += 1
    kinds["committed"] = sum(f["field"] in ("purchase_commitments", "finance_lease_liability") for f in facts)
    inds = sorted({industry(x) for x in tickers})
    cfg = agents.load()["attributor"]
    method = [{"industry": i, "version": cfg["models"][i], "companies": sorted(x for x in tickers if industry(x) == i),
               "text": agents.model_text(cfg["models"][i]), "versions": agents.model_versions(i)} for i in inds]
    by_method = {}
    for a in attr:
        if a["kind"] == "actual" and a["field"] == "capex":
            by_method[a["method"]] = by_method.get(a["method"], 0) + 1
    confirmed = sum(bool(ev_load.get(e["extraction_id"], {}).get("match")) for e in exts)
    return {"scope": scope or "all", "tickers": tickers, "changed": changed,
            "extracted": {"filings": docs, "texts": {k: n for k, n in texts}, "values": len(vals), "values_agree": sum(v["label"] == "agree" for v in vals),
                          "values_explained": sum(v["label"] in ("definition_gap", "not_reported") for v in vals), "facts": len(facts), "facts_agree": sum(f["label"] == "agree" for f in facts),
                          "facts_differ": sum(f["label"] == "unresolved" for f in facts), "statements": stmts[0], "cells": len(exts), "cells_confirmed": confirmed},
            "method": {"models": method, "prompt": cfg["prompt"], "history": cfg["history"][-6:]},
            "attribution": {"rows": len([a for a in attr if a["kind"] == "actual" and a["field"] == "capex"]), "amounts": sum(a["ai_amount"] is not None and a["kind"] == "actual" and a["field"] == "capex" for a in attr),
                            "by_method": by_method, "diff": {"at": diff.get("at"), "changed": diff.get("changed"), "new": diff.get("new"), "removed": diff.get("removed")} if diff else None},
            "insight": {"by_year": [y for y in insights()["by_year"] if y["buyers"] > 0], "evaluation": {"n": len(ev_rows), "agree": sum(r["outcome"] == "agree" for r in ev_rows),
                        "disagree": sum(r["outcome"] == "disagree" for r in ev_rows), "no_estimate": sum(r["outcome"] == "no_estimate" for r in ev_rows), "rows": ev_rows}},
            "queue": queue, "noise": len(noise), "release": release, "kinds": kinds,
            "industries": sorted(INDUSTRIES) + ["other"], "names": {c["ticker"]: c["name"] for c in tracked()}}


def packet(version: str) -> bytes | None:
    d = RELEASES / version
    if not re.fullmatch(r"v\d+\.\d+\.\d+", version) or not (d / "SIGNOFF.json").exists():
        return None
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(d.iterdir()):
            z.write(f, f"capex-ledger-{version}/{f.name}")
    return buf.getvalue()


def outputs() -> dict:
    names = {c["ticker"]: c["name"] for c in tracked()}
    out = []
    for d in releases():
        sig = json.loads((d / "SIGNOFF.json").read_text()) if (d / "SIGNOFF.json").exists() else {}
        out.append({"version": d.name, "signed_by": sig.get("signed_by"), "signed_at": sig.get("signed_at"), "packet": bool(sig) and (d / "README.md").exists(),
                    "rows": [{**r, "company": names.get(r["ticker"], r["ticker"])} for r in csv.DictReader((d / "values.csv").open())]})
    return {"releases": out}


# ── Adding a company: one pipeline run at a time, in the background, its log read back as progress ───────────
JOB = store.ROOT / "data" / "jobs" / "current.json"
_proc = None


def attribute(industry_: str | None, by: str) -> dict:
    """Rerun the attributor (run, then load) for one industry or every company, in the background; nothing is re-read
    from filings. The job page shows the log's last lines and the diff when it ends."""
    global _proc
    if _proc and _proc.poll() is None:
        raise ValueError("a run is already going; wait for it to finish")
    if industry_ and industry_ not in INDUSTRIES and industry_ != "other":
        raise ValueError(f"no industry {industry_}")
    tickers = [t for t in stage_tickers(3) if not industry_ or industry(t) == industry_]
    if not tickers:
        raise ValueError("no company in that industry")
    log = JOB.parent / f"attribution-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.log"
    JOB.parent.mkdir(parents=True, exist_ok=True)
    cmd = " && ".join(f"{sys.executable} -m ledger attribution --ticker {' '.join(tickers)} {step}" for step in ("--run", "--load"))
    _proc = subprocess.Popen(["sh", "-c", cmd], cwd=store.ROOT, env=os.environ.copy(), stdout=log.open("w"), stderr=subprocess.STDOUT)
    JOB.write_text(json.dumps({"kind": "attribution", "ticker": industry_ or "all", "by": by, "log": str(log), "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pid": _proc.pid}))
    return job()


def dryrun(version: str, by: str) -> dict:
    """Run a saved model version against its industry in the background and compare; the table is untouched."""
    global _proc
    if _proc and _proc.poll() is None:
        raise ValueError("a run is already going; wait for it to finish")
    ind = version.split("@")[0]
    if version not in agents.model_versions(ind):
        raise ValueError(f"no model {version}")
    tickers = [t for t in stage_tickers(3) if industry(t) == ind]
    log = JOB.parent / f"dryrun-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.log"
    JOB.parent.mkdir(parents=True, exist_ok=True)
    _proc = subprocess.Popen([sys.executable, "-m", "ledger", "attribution", "--ticker", *tickers, "--run", "--model-version", version, "--dry-run"], cwd=store.ROOT, env=os.environ.copy(), stdout=log.open("w"), stderr=subprocess.STDOUT)
    JOB.write_text(json.dumps({"kind": "dryrun", "ticker": version, "by": by, "log": str(log), "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pid": _proc.pid}))
    return job()


def add_company(ticker: str, by: str) -> dict:
    """Add a company the SEC knows and run the whole pipeline on it. Agent work runs on the subscription (claude -p)."""
    global _proc
    t = ticker.strip().upper()
    if not re.fullmatch(r"[A-Z][A-Z0-9.\-]{0,9}", t):
        raise ValueError("a ticker looks like AVGO")
    if _proc and _proc.poll() is None:
        raise ValueError("a company is already being run; wait for it to finish")
    sec = fetch_tickers()[0]
    if t not in sec:
        raise ValueError(f"{t} isn't a ticker the SEC lists")
    if t not in {c["ticker"] for c in tracked()}:
        name = re.sub(r"\b(Inc|Corp|Corporation|Holdings|Ltd|Co|Plc)\b\.?", "", sec[t]["title"].title()).strip(" ,.")
        ADDED.parent.mkdir(parents=True, exist_ok=True)
        ADDED.write_text(json.dumps(added() + [{"ticker": t, "name": name, "group": "Added in DATAHQ", "added_by": by or "unknown",
                                                "added_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}], indent=1))
    log = JOB.parent / f"{t}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}.log"
    JOB.parent.mkdir(parents=True, exist_ok=True)
    _proc = subprocess.Popen([sys.executable, "-m", "ledger", "run", "--ticker", t], cwd=store.ROOT, env=os.environ.copy(),
                             stdout=log.open("w"), stderr=subprocess.STDOUT)
    JOB.write_text(json.dumps({"kind": "run", "ticker": t, "log": str(log), "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pid": _proc.pid}))
    return job()


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def job() -> dict | None:
    """The latest run started from the app: which step it is on and what each step left, from data/jobs/progress.json
    (written by `ledger run` after every step), plus the log's last lines for anything that went wrong."""
    if not JOB.exists():
        return None
    meta = json.loads(JOB.read_text())
    p = progress.read()
    mine = p if p and p.get("scope") == meta["ticker"] and meta.get("kind", "run") == "run" else None
    done = {(s["step"], tuple(s["extra"])): s for s in (mine or {}).get("steps", [])}
    ours = _proc is not None and _proc.pid == meta["pid"]
    running = _proc.poll() is None if ours else bool(mine and mine["running"] and _alive(meta["pid"]))
    if running:
        code = None
    elif ours:
        code = _proc.returncode
    else:
        code = (2 if any(s["code"] == 2 for s in done.values()) else 0) if mine and not mine["running"] else None
    steps, next_up = [], True
    for cmd, extra, label in (progress.STEPS if meta.get("kind", "run") == "run" else [("attribution", ["--run"], "The Attributor reads the model and each company's data")] + ([("attribution", ["--load"], "Recompute every number from its inputs and write the diff")] if meta.get("kind") == "attribution" else [("attribution", ["--dry-run"], "Compare with the table and score against the reference set; nothing written")])):
        s = done.get((cmd, tuple(extra)))
        steps.append({"label": label, "state": "done" if s else "running" if running and next_up else "waiting", "summary": s["summary"] if s else ""})
        next_up = next_up and bool(s)
    lines = Path(meta["log"]).read_text(errors="ignore").splitlines() if Path(meta["log"]).exists() else []
    if meta.get("kind") in ("attribution", "dryrun"):  # two steps, read from the log's own headings
        done_run, done_load = any(l.startswith("running the attributor") for l in lines) and any(": " in l and ("rows," in l or "FAILED" in l) for l in lines), any(" rows for " in l or "dry run " in l for l in lines)
        steps = [{"label": steps[0]["label"], "state": "done" if (done_run and (done_load or not running)) else "running" if running else "waiting", "summary": next((l.strip() for l in lines if l.startswith("running the attributor")), "")},
                 {"label": steps[1]["label"], "state": "done" if done_load else "running" if running and done_run else "waiting", "summary": next((l.strip() for l in lines if " rows for " in l or l.startswith("dry run ")), "")}]
    return {**meta, "running": running, "exit": code, "steps": steps, "tail": lines[-4:]}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body: bytes, kind="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data, code=HTTPStatus.OK):
        self._send(code, json.dumps(data, default=str).encode())

    def _guard(self, fn):
        try:
            return fn()
        except Busy as e:
            self._json({"error": str(e)}, HTTPStatus.SERVICE_UNAVAILABLE)
        except (KeyError, ValueError) as e:
            self._json({"error": str(e).strip("'")}, HTTPStatus.BAD_REQUEST)
        except NotPublishable as e:  # ?release= on an unsigned release
            self._json({"error": str(e)}, HTTPStatus.BAD_REQUEST)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if u.path in ("/", "/index.html"):
            return self._send(HTTPStatus.OK, PAGE.read_bytes(), "text/html; charset=utf-8")
        if u.path == "/api/hq":
            return self._guard(lambda: self._json(self._hq()))
        if u.path == "/api/company":
            return self._guard(lambda: self._json(company(q.get("t", ""))))
        if u.path == "/api/agents":
            return self._guard(lambda: self._json(agents_view()))
        if u.path == "/api/job":
            return self._json(job())
        if u.path == "/api/insights":
            return self._guard(lambda: self._json(insights()))
        if u.path == "/api/flow":
            return self._guard(lambda: self._json(flow(q.get("scope", "all"))))
        if u.path == "/api/data":
            return self._guard(lambda: self._json(data(q)))
        if u.path == "/api/evaluation":
            f = store.ROOT / "reports" / "evaluation.json"
            return self._json(json.loads(f.read_text()) if f.exists() else None)
        if u.path == "/api/dryrun":
            f = store.ROOT / "data" / "attribution" / "dryrun" / q.get("version", "") / "result.json"
            return self._json(json.loads(f.read_text()) if f.exists() and re.fullmatch(r"[a-z_]+@v\d+", q.get("version", "")) else None)
        if u.path == "/api/attribution":
            return self._guard(lambda: self._json(attribution_view()))
        if u.path.startswith("/api/v1/"):  # the read API, docs/API.md
            return self._guard(lambda: self._v1(u.path[len("/api/v1/"):].strip("/"), q))
        if u.path.startswith("/packet/") and u.path.endswith(".zip"):
            z = packet(u.path[len("/packet/"):-4])
            if z:
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", f'attachment; filename="capex-ledger-{u.path[len("/packet/"):]}"')
                self.send_header("Content-Length", str(len(z)))
                self.end_headers()
                return self.wfile.write(z)
        if u.path == "/api/outputs":
            return self._guard(lambda: self._json(outputs()))
        if u.path == "/api/output":  # the agent's raw answer for one filing, exactly as saved
            f = OUTPUTS / f"{q.get('accession', '')}.json"
            if f.parent == OUTPUTS and f.exists():
                return self._send(HTTPStatus.OK, f.read_bytes())
        if u.path.startswith("/evidence/"):
            f = EVIDENCE / u.path.removeprefix("/evidence/")
            if f.parent == EVIDENCE and f.suffix == ".png" and f.exists():
                return self._send(HTTPStatus.OK, f.read_bytes(), mimetypes.guess_type(f.name)[0])
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def _v1(self, path: str, q: dict):
        parts = path.split("/")
        name, fmt = parts[0], q.get("format", "json")
        if name.endswith(".csv"):
            name, fmt = name[:-4], "csv"
        if name == "reconcile":  # the workbench, docs/DATAHQ.md
            from . import workbench
            f = flow(q.get("scope", "all"))
            con = _con()
            try:
                return self._json(workbench.items(con, f))
            finally:
                con.close()
        if name in ("coverage", "cost"):
            from .cost import report
            con = _con()
            try:
                return self._json(api.coverage(con) if name == "coverage" else report(con))
            finally:
                con.close()
        if name not in api.LISTS:
            return self._json({"error": f"no list {name!r}", "lists": api.LISTS}, HTTPStatus.NOT_FOUND)
        if name == "views" and len(parts) == 3 and parts[2] == "data":
            con = _con()
            try:
                out = api.view_data(con, parts[1])
            finally:
                con.close()
            return self._send(HTTPStatus.OK, api.to_csv(out["rows"]).encode(), "text/csv; charset=utf-8") if fmt == "csv" else self._json(out)
        if len(parts) != 1:
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        if name in ("companies", "theses", "views"):
            rows = api.apply(api.fetch(None, name), q)
        else:
            con = _con()
            try:
                rows = api.query(con, name, q)
            finally:
                con.close()
        if fmt == "csv":
            return self._send(HTTPStatus.OK, api.to_csv(rows).encode(), "text/csv; charset=utf-8")
        return self._json({"list": name, "count": len(rows), "filters": {k: v for k, v in q.items() if k in api.FILTERS or k == "group"}, "rows": rows})

    def _hq(self):
        con = _con()
        try:
            return snapshot(con, STAGE)
        finally:
            con.close()

    def do_POST(self):
        u = urlparse(self.path)
        try:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
        except json.JSONDecodeError:
            return self._json({"error": "send JSON"}, HTTPStatus.BAD_REQUEST)
        if u.path == "/api/companies":
            return self._guard(lambda: self._json(add_company(body.get("ticker", ""), body.get("by", ""))))
        if u.path == "/api/resolve/bulk":  # one reason for many items, each logged on its own
            def bulk():
                out = [resolutions.resolve(i.get("key", ""), i.get("hash", ""), body.get("state", ""), body.get("reason", ""), body.get("by", "")) for i in body.get("items") or []]
                if not out:
                    raise ValueError("no items")
                return {"saved": len(out)}
            return self._guard(lambda: self._json(bulk()))
        if u.path == "/api/resolve":
            return self._guard(lambda: self._json(resolutions.resolve(body.get("key", ""), body.get("hash", ""), body.get("state", ""), body.get("reason", ""), body.get("by", ""))))
        if u.path == "/api/dryrun":
            return self._guard(lambda: self._json(dryrun(body.get("version", ""), body.get("by", ""))))
        if u.path == "/api/attribute":
            return self._guard(lambda: self._json(attribute(body.get("industry") or None, body.get("by", ""))))
        if u.path == "/api/v1/views":
            return self._guard(lambda: self._json(views.save(body.get("view") or body, body.get("by", ""))))
        if u.path.startswith("/api/v1/views/") and u.path.endswith("/delete"):
            vid = u.path[len("/api/v1/views/"):-len("/delete")]
            return self._guard(lambda: self._json((views.delete(vid, body.get("by", "")), {"ok": True})[1]))
        parts = u.path.strip("/").split("/")  # api/agents/<id>/<prompt|use|model>, api/models/<industry>/<save|use>
        if len(parts) == 4 and parts[:2] == ["api", "models"]:
            ind, what = parts[2], parts[3]
            if what == "save":
                return self._guard(lambda: self._json({"version": agents.save_model(ind, body.get("text", ""), body.get("by", ""), body.get("note", ""))}))
            if what == "use":
                return self._guard(lambda: self._json((agents.use_model(ind, body.get("version", ""), body.get("by", "")), {"ok": True})[1]))
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        if len(parts) != 4 or parts[:2] != ["api", "agents"] or parts[2] not in agents.load():
            return self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        aid, what = parts[2], parts[3]

        def act():
            if what == "prompt":
                return {"version": agents.save_prompt(aid, body.get("text", ""), body.get("by", ""), body.get("note", ""))}
            if what == "use":
                agents.use_prompt(aid, body.get("version", ""), body.get("by", ""))
                return {"ok": True}
            if what == "model":
                agents.set_model(aid, body.get("model", ""), body.get("by", ""))
                return {"ok": True}
            raise KeyError(what)
        self._guard(lambda: self._json(act()))

    def log_message(self, *a):
        pass


def serve(port: int) -> None:
    srv = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"DATAHQ on http://127.0.0.1:{port}  (Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
