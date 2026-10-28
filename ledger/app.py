"""DATAHQ, the ledger's web app: the morning dashboard, each company through every pipeline step, the named agents
(model, prompt, every run), and an outputs explorer over the signed releases.

Reads the database read-only on every request, so it always shows the latest run. It writes only three things, all
attributed: agent changes (agents/agents.json, new prompt versions), a reviewer's decision to accept warnings
(decisions/decisions.jsonl, the same log as `ledger review`), and a company added to data/companies.json, which starts
`ledger run` for it in the background. Serves on 127.0.0.1 only."""
import csv
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
from urllib.parse import parse_qs, urlparse

import duckdb

from . import agents, store
from .cli.report import build
from .config import ADDED, STAGES, added, tracked
from .ingest.edgar import fetch_tickers
from .extract import OUTPUTS
from .hq import snapshot
from .review import decide, decisions, latest, open_items
from .rules import load as load_rules

PAGE = store.ROOT / "ledger" / "app.html"
EVIDENCE = store.ROOT / "reports" / "evidence"
RELEASES = store.ROOT / "releases"
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
    finally:
        con.close()
    cur, still = latest(decisions()), {e["exception_id"] for e in open_items(excs, decisions())}
    rules = {r["id"]: r for r in load_rules()}
    for e in excs:
        d = cur.get(e["exception_id"])
        e["status"] = "note" if e["severity"] == "info" else "open" if e["exception_id"] in still else "decided"
        e["decision"] = d and d.get("input_hash") == e["input_hash"] and {k: d[k] for k in ("kind", "reason", "reviewer", "decided_at")} or None
        e["rule_title"] = rules.get(e["rule_id"], {}).get("title", e["rule_id"])
    rel = sorted(RELEASES.glob("v*"), key=lambda p: [int(x) for x in p.name[1:].split(".")])
    released = [r for r in csv.DictReader((rel[-1] / "values.csv").open()) if r["ticker"] == ticker] if rel else []
    info = next(c for c in tracked() if c["ticker"] == ticker)
    return {"ticker": ticker, "name": info["name"], "note": info.get("note"), "documents": docs, "skipped": skipped, "exceptions": excs,
            "values": report["values"], "tables": report["tables"], "scorecard": report["scorecard"][0],
            "release": rel[-1].name if rel else None, "released": len(released)}


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


def outputs() -> dict:
    rel = sorted(RELEASES.glob("v*"), key=lambda p: [int(x) for x in p.name[1:].split(".")])
    names = {c["ticker"]: c["name"] for c in tracked()}
    out = []
    for d in rel:
        sig = json.loads((d / "SIGNOFF.json").read_text()) if (d / "SIGNOFF.json").exists() else {}
        out.append({"version": d.name, "signed_by": sig.get("signed_by"), "signed_at": sig.get("signed_at"),
                    "rows": [{**r, "company": names.get(r["ticker"], r["ticker"])} for r in csv.DictReader((d / "values.csv").open())]})
    return {"releases": out}


def accept_warnings(ids: list[str], reason: str, by: str) -> dict:
    """One reason covers several items with the same cause."""
    if not ids or not reason.strip() or not by.strip():
        raise ValueError("pick warnings and give a reason and your name")
    con = _con()
    try:
        excs = _rows(con, "select * from exceptions where exception_id in (select unnest(?))", ids)
    finally:
        con.close()
    # Warnings, and the one-time cost-line judgement. Other blocking items (a value XBRL disagrees with) may need an
    # override value, so they stay with `ledger review decide`.
    if len(excs) != len(set(ids)) or any(e["severity"] != "warn" and e["rule_id"] != "cost_lines_summed" for e in excs):
        raise ValueError("only current warnings and cost-line confirmations can be decided here")
    for e in excs:
        decide(e, "accept", reason, by)
    return {"accepted": len(excs)}


# ── Adding a company: one pipeline run at a time, in the background, its log read back as progress ───────────
JOB = store.ROOT / "data" / "jobs" / "current.json"
STEPS = [("ingest", "", "Find the 10-Ks at the SEC and locate the statements"),
         ("extract", "--run", "The Reader agent reads each filing and cites every cell"),
         ("extract", "--load", "Check every citation against the parsed table"),
         ("reconcile", "", "Clean: one value per year, units and signs, newest filing, compare with SEC data"),
         ("rules", "", "Run the 15 checks"),
         ("faults", "", "Plant mistakes and confirm the checks catch them"),
         ("evidence", "", "Re-read every cited cell on the rendered 10-K"),
         ("report", "", "Write the review page")]
_proc = None


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
    JOB.write_text(json.dumps({"ticker": t, "log": str(log), "started": datetime.now(timezone.utc).isoformat(timespec="seconds"), "pid": _proc.pid}))
    return job()


def _summary(cmd: str, extra: str, lines: list[str]) -> str:
    """One plain sentence for a step, from what it printed."""
    text = "\n".join(lines)
    num = lambda rx: (m := re.search(rx, text)) and m.groups()
    if cmd == "ingest" and (g := num(r"(\d+) filings parsed.*?(\d+) statements not located")):
        return f"{g[0]} filings found; " + ("statements located in every one" if g[1] == "0" else f"{g[1]} statements not located")
    if cmd == "extract" and extra == "--run":
        read = re.findall(r": (\d+) values, [\d.]+s, (\d+) attempt", text)
        return f"Read {len(read)} filing{'s' * (len(read) != 1)}, {sum(int(a) - 1 for _, a in read)} retries" if read else "Every filing was already read"
    if cmd == "extract" and (g := num(r"(\d+) extractions loaded from (\d+) filings; (\d+) extraction_failed")):
        return f"{g[0]} cited cells checked against the tables; {g[2]} failed"
    if cmd == "reconcile" and (g := num(r"(\d+) fiscal-year values; labels (\{.*\})")):
        agree = re.search(r"'agree': (\d+)", g[1])
        return f"{g[0]} yearly values; {agree.group(1) if agree else 0} match the SEC's data"
    if cmd == "rules" and (g := num(r"(\d+) rules, \d+ exceptions \((\d+) block, (\d+) warn, (\d+) info\)")):
        return f"{g[0]} checks: {g[1]} blocking, {g[2]} warnings, {g[3]} note{'s' * (g[3] != '1')}"
    if cmd == "faults":
        rows = re.findall(r"^\w+\s+(\d+)\s+\d+\s+\d+\s+\d+\s+(\d+)$", text, re.M)
        if rows:
            return f"{sum(int(a) for a, _ in rows):,} planted mistakes, {sum(int(b) for _, b in rows)} got through"
    if cmd == "evidence" and (g := num(r"(\d+) of (\d+) cited cells confirmed")):
        return f"{g[0]} of {g[1]} cited cells confirmed on the rendered 10-K"
    if cmd == "report" and "wrote" in text:
        return "Review page written"
    return lines[0] if lines else ""


def job() -> dict | None:
    """The latest run started from the app, read from its log: which step it is on and what each step said."""
    if not JOB.exists():
        return None
    meta = json.loads(JOB.read_text())
    lines = Path(meta["log"]).read_text(errors="ignore").splitlines() if Path(meta["log"]).exists() else []
    out, cur = [], None
    for line in lines:
        m = re.match(r"^== (\w+)\s*(\S*)", line)
        if m and m.group(1) != "scorecard":
            cur = next((s for s in out if (s["cmd"], s["extra"]) == (m.group(1), m.group(2))), None)
            if not cur:
                cur = {"cmd": m.group(1), "extra": m.group(2), "lines": []}
                out.append(cur)
        elif m:
            cur = None
        elif cur is not None and line.strip():
            cur["lines"].append(line.rstrip())
    running = _proc is not None and _proc.pid == meta["pid"] and _proc.poll() is None
    code = None if running else (_proc.returncode if _proc is not None and _proc.pid == meta["pid"] else (0 if any("scorecard" in l for l in lines) else None))
    steps = []
    for i, (cmd, extra, label) in enumerate(STEPS):
        s = next((x for x in out if (x["cmd"], x["extra"]) == (cmd, extra)), None)
        last = out and (out[-1]["cmd"], out[-1]["extra"]) == (cmd, extra)
        state = "waiting" if not s else ("running" if running and last else "done")
        steps.append({"label": label, "state": state, "summary": _summary(cmd, extra, (s or {}).get("lines", [])) if s else ""})
    return {**meta, "running": running, "exit": code, "steps": steps, "tail": lines[-3:]}


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
        if u.path == "/api/decide":
            return self._guard(lambda: self._json(accept_warnings(body.get("ids", []), body.get("reason", ""), body.get("by", ""))))
        parts = u.path.strip("/").split("/")  # api/agents/<id>/<prompt|use|model>
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
