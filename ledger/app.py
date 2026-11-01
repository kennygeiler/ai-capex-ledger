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
from .config import ADDED, INDUSTRIES, SCOPE, added, industry, stage_tickers, tracked
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
            "release": rel[-1].name if rel else None, "released": len(released), "ai_spend": ai, "facts": facts}


def agents_view() -> dict:
    """Every live agent with its charter (agents/charters, as blocks), prompt history with `by`, every saved prompt,
    and its runs per proven company from the `runs` table (T48). The retired attributor is left out."""
    from .cost import by_agent
    cfg = agents.load()
    con = _con()
    try:
        h = snapshot(con, STAGE)["health"][0]
        runs = {aid: by_agent(con, aid, SCOPE) for aid, a in cfg.items() if not a.get("retired")}
    finally:
        con.close()
    cost = h["per_company_minutes"] is not None and {"minutes": h["per_company_minutes"], "tokens": h["per_company_tokens"], "companies": h["measured_companies"]} or None
    out = {}
    for aid, a in cfg.items():
        if a.get("retired"):
            continue
        vs = agents.versions(aid)
        out[aid] = {**a, "id": aid, "versions": vs, "prompts": {v: agents.prompt_text(v) for v in vs}, "charter_blocks": agents.charter(aid), "runs": runs[aid], "cost": cost}
    return out


def latest_signed():
    signed = [d for d in releases() if (d / "SIGNOFF.json").exists()]
    return signed[-1] if signed else None


FIELD_KIND = {"revenue": "spent", "capex": "spent", "opex": "spent", "segment_capex": "spent", "segment_revenue": "spent", "ppe_category": "derived",
              "finance_lease_liability": "committed", "purchase_commitments": "committed"}  # the taxonomy measure of each read field (docs/TAXONOMY.md)


def data(q: dict) -> dict:
    """The dataset in long format for the data screen: one row per entity, field, dimension, year and kind, with its
    provenance ids. Filters: t (tickers, comma; the scope, config.SCOPE, when absent), f (fields, comma), y (years, comma),
    k (spent|committed|derived|planned)."""
    want_t = set(q.get("t", "").upper().split(",")) - {""} or set(SCOPE)
    want_f = set(q.get("f", "").split(",")) - {""}
    want_y = set(q.get("y", "").upper().split(",")) - {""}
    want_k = set(q.get("k", "").split(",")) - {""}
    con = _con()
    try:
        rows = []
        for v in _rows(con, 'select ticker, field, period, value, label, basis, extraction_ids, source from "values" where value is not null'):
            rows.append({"ticker": v["ticker"], "field": v["field"], "dimension": "", "period": v["period"], "kind": "spent", "value": v["value"], "unit": "usd",
                         "check": v["label"], "basis": v["basis"], "prov": {"extractions": v["extraction_ids"], "table": "values"}})
        for f in _rows(con, "select ticker, field, dimension, period, value, label, reference, accession, extraction_ids, basis from facts"):
            rows.append({"ticker": f["ticker"], "field": f["field"], "dimension": f["dimension"], "period": f["period"], "kind": FIELD_KIND.get(f["field"], "spent"), "value": f["value"], "unit": "usd",
                         "check": f["label"], "basis": f["basis"], "prov": {"extractions": f["extraction_ids"], "accession": f["accession"], "table": "facts", "xbrl": f["reference"]}})
        urls = {d["accession"]: d["url"] for d in _rows(con, "select accession, url from documents")}
    finally:
        con.close()
    idx = resolutions.by_row()
    for r in rows:
        acc = r["prov"].get("accession") or (r["prov"].get("extractions") or "").split("|")[0]
        r["prov"]["url"] = urls.get(acc)
        t = r["prov"]["table"]
        r["status"] = (resolutions.status_of(idx, "facts", r["ticker"], r["field"], r["dimension"], r["period"]) if t == "facts"
                       else resolutions.status_of(idx, "values", r["ticker"], r["field"], "", r["period"]) if t == "values" else "")
        r["flag"] = "differs_from_xbrl" if r.get("check") == "unresolved" else ""
    rows = [r for r in rows if (not want_t or r["ticker"] in want_t) and (not want_f or r["field"] in want_f) and (not want_y or r["period"] in want_y) and (not want_k or r["kind"] in want_k)]
    cos = [c for c in tracked() if c["ticker"] in want_t]
    names = {c["ticker"]: c["name"] for c in cos}
    fields = sorted({r["field"] for r in rows} if q.get("t") else set(FIELD_KIND))
    return {"rows": rows, "names": names, "industries": {c["ticker"]: industry(c["ticker"]) for c in cos}, "roles": {c["ticker"]: c.get("role", "other") for c in cos},
            "scope": list(SCOPE), "fields": fields, "kinds": ["spent", "committed", "derived", "planned"]}


def usd_(n) -> str:
    return "—" if n is None else f"${n / 1e6:,.0f}M"


_FLOW: dict = {}


def _stamp() -> tuple:
    """What the app depends on: the database, the resolutions, the releases, the added companies, the evidence."""
    paths = [store.DEFAULT_DB, resolutions.LOG, RELEASES, ADDED, EVIDENCE]
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
    """The queue for a scope (all = config.SCOPE, a layer within it, or any one ticker the database holds): new filings,
    blocks, facts that differ from the filing's tag, facts that changed since the signed release, findings the SEC's data
    can't confirm. Nothing here is an estimate."""
    present = {c["ticker"] for c in tracked()}
    if scope in INDUSTRIES or scope == "other":
        tickers = sorted(t for t in SCOPE if industry(t) == scope)
    elif scope and scope != "all":
        tickers = [scope.upper()] if scope.upper() in present else []
    else:
        tickers = sorted(SCOPE)
    con = _con()
    try:
        hqd = snapshot(con, STAGE, tickers)
        facts = _rows(con, "select ticker, field, dimension, period, value, label from facts where ticker in (select unnest(?))", tickers)
        cites = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, accession, table_id, row_label, column_label, cell_text from note_extractions where ticker in (select unnest(?))", tickers)}
        urls = {d["accession"]: d["url"] for d in _rows(con, "select accession, url from documents where ticker in (select unnest(?))", tickers)}
        fact_ref = {(f["ticker"], f["field"], f["dimension"], f["period"]): f for f in _rows(con, "select ticker, field, dimension, period, reference, extraction_ids from facts where ticker in (select unnest(?))", tickers)}
    finally:
        con.close()
    rel = latest_signed()
    rel_facts = {(r["ticker"], r["field"], r["dimension"], r["period"]): r["value"] for r in csv.DictReader((rel / "facts.csv").open())} if rel and (rel / "facts.csv").exists() else {}
    facts_changed = [f for f in facts if rel_facts and str(f["value"]) != rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"]), "")]
    since = hqd["since"] or {}
    changed = {"new_filings": [f for f in (hqd["watch"] or {}).get("new", []) if f["ticker"] in tickers],
               "filings_read": [f for f in since.get("new_filings", []) if f.split("|")[0] in tickers], "facts_changed": len(facts_changed),
               "release": rel.name if rel else None, "last_run": hqd["health"][0]["run_at"]}
    res = resolutions.latest()
    queue = []
    for f in changed["new_filings"]:
        queue.append({"kind": "new_filing", "state": "new", "ticker": f["ticker"], "where": f"{f['form']} for the year ended {f['period']}", "impact": "values, facts and statements for the year", "action": "run", "detail": f})
    for e in hqd["questions"]:
        if e["ticker"] in tickers:
            queue.append({"kind": "blocked", "state": "blocked", "ticker": e["ticker"], "where": f"{e['field'] or ''} {e['period'] or ''}".strip() or e["rule"], "impact": "blocks the release", "action": "definition", "detail": e})
    for f in facts_changed[:30]:
        queue.append({"kind": "fact_changed", "state": "moved", "ticker": f["ticker"], "where": f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " "), "impact": "the next release", "dollars": 0, "new": True, "action": "release",
                      "detail": {**f, "release_value": (lambda v: None if v in (None, "") else float(v))(rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"])))}})
    for f in facts:
        if f["label"] == "unresolved":
            fr = fact_ref.get((f["ticker"], f["field"], f["dimension"], f["period"]), {})
            cite = cites.get((fr.get("extraction_ids") or "").split(",")[-1])
            key = f"{f['ticker']}|{f['field']}|{f['dimension']}|{f['period']}"
            queue.append({"kind": "fact_differs", "state": "disagrees", "ticker": f["ticker"], "where": f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " "),
                          "impact": "a cited cell against the filing's tag", "dollars": abs((f["value"] or 0) - (float(fr["reference"]) if fr.get("reference") not in (None, "") else (f["value"] or 0))),
                          "new": key not in {"|".join(k) for k in rel_facts}, "action": "definition",
                          "detail": {**f, "reference": fr.get("reference"), "cite": cite, "url": urls.get((cite or {}).get("accession")), "release_value": rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"]))}})
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
    queue.sort(key=lambda q_: (0 if q_["state"] == "blocked" else 1, -q_["dollars"], order[q_["state"]], q_["ticker"]))
    open_ = [q_ for q_ in queue if not q_["resolution"] or q_["resolution"]["state"] == "fix"]
    blocks = [q_ for q_ in queue if q_["state"] == "blocked"]
    release = {"last": rel.name if rel else None, "blocks": len(blocks), "unresolved": len(open_), "facts_changed": len(facts_changed)}
    return {"scope": scope or "all", "tickers": tickers, "changed": changed, "queue": queue, "release": release,
            "industries": sorted(INDUSTRIES) + ["other"], "scope_tickers": list(SCOPE), "names": {c["ticker"]: c["name"] for c in tracked()}}


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
        from .checklist import summary
        out.append({"version": d.name, "signed_by": sig.get("signed_by"), "signed_at": sig.get("signed_at"), "packet": bool(sig) and (d / "README.md").exists(),
                    "checklist": summary(sig["checklist"]) if sig.get("checklist") else None,  # T7: what the signature meant; None before the checklist existed
                    "published": sig.get("published"),  # False: signed from the page, the publish failed (SIGNOFF.json says why); None: signed before the page recorded it
                    "rows": [{**r, "company": names.get(r["ticker"], r["ticker"])} for r in csv.DictReader((d / "values.csv").open())]})
    return {"releases": out}


# ── Adding a company: one pipeline run at a time, in the background, its log read back as progress ───────────
JOB = store.ROOT / "data" / "jobs" / "current.json"
_proc = None


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
    for cmd, extra, label in progress.STEPS:
        s = done.get((cmd, tuple(extra)))
        steps.append({"label": label, "state": "done" if s else "running" if running and next_up else "waiting", "summary": s["summary"] if s else ""})
        next_up = next_up and bool(s)
    lines = Path(meta["log"]).read_text(errors="ignore").splitlines() if Path(meta["log"]).exists() else []
    return {**meta, "running": running, "exit": code, "steps": steps, "tail": lines[-4:]}


READONLY = os.environ.get("LEDGER_READONLY") == "1"  # a hosted copy: every page reads, no POST lands (decisions, views and prompts change only in a checkout)


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
        if u.path.startswith("/api/agents/") and u.path.endswith("/runs"):  # one live agent's runs per company (T48); ?t=MSFT,NVDA narrows, default the proven set
            aid = u.path[len("/api/agents/"):-len("/runs")]

            def agent_runs():
                from .cost import by_agent
                if aid not in agents.load() or agents.load()[aid].get("retired"):
                    raise KeyError(aid)
                tickers = [t for t in q.get("t", "").upper().split(",") if t] or SCOPE
                con = _con()
                try:
                    return by_agent(con, aid, tickers)
                finally:
                    con.close()
            return self._guard(lambda: self._json(agent_runs()))
        if u.path == "/api/job":
            return self._json(job())
        if u.path == "/api/flow":
            return self._guard(lambda: self._json(flow(q.get("scope", "all"))))
        if u.path == "/api/data":
            return self._guard(lambda: self._json(data(q)))
        if u.path == "/api/v1/release/checklist":  # the Release page (T5): the next version's checklist, or ?version=
            from .checklist import checklist

            def cl():
                con = _con()
                try:
                    return checklist(con, q.get("version") or None, STAGE)
                finally:
                    con.close()
            return self._guard(lambda: self._json(cl()))
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
        if u.path.startswith("/evidence/"):
            f = EVIDENCE / u.path.removeprefix("/evidence/")
            if f.parent == EVIDENCE and f.suffix == ".png" and f.exists():
                return self._send(HTTPStatus.OK, f.read_bytes(), mimetypes.guess_type(f.name)[0])
        if u.path.startswith("/pages/"):  # the page scripts app.html loads: ledger/pages/<name>.js, one file per page (T0)
            f = PAGE.parent / "pages" / u.path.removeprefix("/pages/")
            if f.parent == PAGE.parent / "pages" and f.suffix == ".js" and f.is_file():
                return self._send(HTTPStatus.OK, f.read_bytes(), "application/javascript; charset=utf-8")
        self._json({"error": "not found"}, HTTPStatus.NOT_FOUND)

    def _v1(self, path: str, q: dict):
        parts = path.split("/")
        name, fmt = parts[0], q.get("format", "json")
        if name.endswith(".csv"):
            name, fmt = name[:-4], "csv"
        if name in ("proof", "rules", "golden"):  # the proof pages, docs/PROOF.md
            from . import proof
            if name == "golden":
                f = store.ROOT / "reports" / "golden.json"
                return self._json({**(json.loads(f.read_text()) if f.exists() else {"ok": None, "at": None}), "fixtures": (store.ROOT / "fixtures" / "seed.json").exists()})
            con = _con()
            try:
                if name == "rules":
                    return self._json(proof.rules(con))
                return self._json(proof.company(con, parts[1]) if len(parts) == 2 else proof.board(con))
            finally:
                con.close()
        if name == "reconcile":  # the workbench, docs/DATAHQ.md
            from . import workbench
            f = flow(q.get("scope", "all"))
            con = _con()
            try:
                return self._json(workbench.items(con, f))
            finally:
                con.close()
        if name == "cost":
            from .cost import report
            con = _con()
            try:
                return self._json(report(con))
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
        if name == "views":
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
            return {**snapshot(con, STAGE), "readonly": READONLY}
        finally:
            con.close()

    def _own_origins(self) -> set:
        port = self.server.server_address[1]
        return {f"http://127.0.0.1:{port}", f"http://localhost:{port}", f"http://[::1]:{port}"}

    def do_POST(self):
        u = urlparse(self.path)
        if READONLY:
            return self._json({"error": "this copy of DATAHQ is read-only; decisions, views and prompts change in a checkout of the repository"}, HTTPStatus.FORBIDDEN)
        # Every POST is a write (a decision, a view, a prompt, a signature). A page on any other site can send a text/plain
        # POST to 127.0.0.1 without a preflight, so a write needs the JSON content type and, when the browser names an
        # Origin, this server's own; anything else is refused before any route.
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if ctype != "application/json":
            return self._json({"error": "a write needs Content-Type: application/json"}, HTTPStatus.FORBIDDEN)
        origin = self.headers.get("Origin")
        if origin and origin.rstrip("/") not in self._own_origins():
            return self._json({"error": "a write is accepted from this DATAHQ's own pages only"}, HTTPStatus.FORBIDDEN)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n < 0:
                raise ValueError(n)
            body = json.loads(self.rfile.read(n) or b"{}")
        except ValueError:  # a Content-Length that is not a number, or a body that is not JSON (JSONDecodeError is one)
            return self._json({"error": "send JSON with a numeric Content-Length"}, HTTPStatus.BAD_REQUEST)
        if not isinstance(body, dict):
            return self._json({"error": "send a JSON object"}, HTTPStatus.BAD_REQUEST)
        if u.path == "/api/release/sign":  # the Sign button (T6): refused 403 above on the read-only copy, 400 while any required line is red
            from .checklist import sign

            def do_sign():
                con = _con()
                try:
                    return sign(con, body.get("version") or None, body.get("by", ""), STAGE)
                finally:
                    con.close()
            return self._guard(lambda: self._json(do_sign()))
        if u.path == "/api/resolve/bulk":  # one reason for many items, each logged on its own
            def bulk():
                out = [resolutions.resolve(i.get("key", ""), i.get("hash", ""), body.get("state", ""), body.get("reason", ""), body.get("by", "")) for i in body.get("items") or []]
                if not out:
                    raise ValueError("no items")
                return {"saved": len(out)}
            return self._guard(lambda: self._json(bulk()))
        if u.path == "/api/resolve":
            return self._guard(lambda: self._json(resolutions.resolve(body.get("key", ""), body.get("hash", ""), body.get("state", ""), body.get("reason", ""), body.get("by", ""))))
        if u.path == "/api/mapping":  # T33: a person's approval is the one writer of taxonomy/asset_types.yaml; 400 on a member off the list or a duplicate
            from . import mapper
            return self._guard(lambda: self._json(mapper.approve(str(body.get("ticker", "")), str(body.get("reported_name", "")), str(body.get("standard_type", "")), str(body.get("evidence", "")), str(body.get("by", "")))))
        if u.path == "/api/mapping/reject":  # the member proposed is logged as rejected; the next mapper run does not propose it again
            from . import mapper
            return self._guard(lambda: self._json(mapper.reject(str(body.get("ticker", "")), str(body.get("reported_name", "")), str(body.get("standard_type", "")), str(body.get("by", "")), str(body.get("reason", "")))))
        if u.path == "/api/v1/views":
            return self._guard(lambda: self._json(views.save(body.get("view") or body, body.get("by", ""))))
        if u.path.startswith("/api/v1/views/") and u.path.endswith("/delete"):
            vid = u.path[len("/api/v1/views/"):-len("/delete")]
            return self._guard(lambda: self._json((views.delete(vid, body.get("by", "")), {"ok": True})[1]))
        parts = u.path.strip("/").split("/")  # api/agents/<id>/<prompt|use|model>, api/models/<industry>/<save|use>
        if len(parts) != 4 or parts[:2] != ["api", "agents"] or parts[2] not in agents.load() or agents.load()[parts[2]].get("retired"):
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


def serve(port: int, host: str = "127.0.0.1") -> None:
    srv = ThreadingHTTPServer((host, port), Handler)
    print(f"DATAHQ on http://{host}:{port}" + ("  (read-only)" if READONLY else "") + "  (Ctrl-C to stop)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
