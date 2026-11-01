"""The mapping assistant (docs/TICKETS.md T33): for a company's reported PP&E categories with no entry in
taxonomy/asset_types.yaml, an agent proposes the nearest us-gaap PropertyPlantAndEquipmentByTypeAxis member with the
note's own words as evidence and a confidence. A proposal is a proposal: it lands in decisions/mapping_proposals.jsonl
(append-only) and on Reconcile's "asset types" group, where a person approves, edits or rejects it. Only the approval
(`approve`, behind POST /api/mapping) writes taxonomy/asset_types.yaml, with `by` = the person. A rejection is a line
in the same log, so the next run does not propose the same member again. Charter: agents/charters/mapper.md."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from . import agents, store
from .extract import render_statement
from .taxonomy import ASSET_TYPES, asset_types, unmapped

ROOT = store.ROOT
TASKS = ROOT / "data" / "mapper" / "tasks"
PROPOSALS = ROOT / "decisions" / "mapping_proposals.jsonl"
CONFIDENCES = ("high", "medium", "low")
NONE = "none"


@dataclass
class Invalid(Exception):
    reason: str


def prompt_version() -> str:
    return agents.load()["mapper"]["prompt"]


def prompt_versions() -> tuple[str, ...]:
    return tuple(agents.versions("mapper"))


def members(path: Path = ASSET_TYPES) -> list[str]:
    """The allowed us-gaap members: the list in the comment header of taxonomy/asset_types.yaml ("us-gaap members used: ...")."""
    text = path.read_text() if path.exists() else ""
    head = "\n".join(l[1:].strip() for l in text.splitlines() if l.startswith("#"))
    m = re.search(r"us-gaap members used:(.*?)(?:\.\s*$|\n\s*\n|\Z)", head, re.S)
    return re.findall(r"[A-Z][A-Za-z]+Member", m.group(1)) if m else []


# ── the log ───────────────────────────────────────────────────────────────────

def load_proposals(path: Path | None = None) -> list[dict]:
    p = path or PROPOSALS
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _append(line: dict, path: Path | None = None) -> dict:
    p = path or PROPOSALS
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(line) + "\n")
    return line


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def by_name(ticker: str, lines: list[dict] | None = None) -> dict[str, dict]:
    """Per reported_name of `ticker`: {"proposal": the latest proposed line not rejected since, or None; "rejected": the members
    a person rejected for it; "approved": the latest approval line, if any}."""
    out: dict[str, dict] = {}
    for l in lines if lines is not None else load_proposals():
        if l.get("ticker") != ticker:
            continue
        e = out.setdefault(l["reported_name"], {"proposal": None, "rejected": [], "approved": None})
        if l.get("kind") == "proposed":
            e["proposal"] = l
        elif l.get("kind") == "rejected":
            if l.get("standard_type") and l["standard_type"] not in e["rejected"]:
                e["rejected"].append(l["standard_type"])
            if e["proposal"] and e["proposal"].get("standard_type") == l.get("standard_type"):
                e["proposal"] = None
        elif l.get("kind") == "approved":
            e["approved"] = l
    return out


def reject(ticker: str, reported_name: str, standard_type: str, by: str, reason: str = "", path: Path | None = None) -> dict:
    if not ticker.strip() or not reported_name.strip() or not standard_type.strip() or not by.strip():
        raise ValueError("a rejection needs the ticker, the reported name, the member rejected and a name")
    return _append({"kind": "rejected", "ticker": ticker.upper(), "reported_name": reported_name, "standard_type": standard_type, "by": by, "reason": reason, "at": _now()}, path)


# ── the task ──────────────────────────────────────────────────────────────────

def note_words(con, ticker: str, names: list[str]) -> list[dict]:
    """The note's words the categories were cited from: per (newest filing, table) one block with the text that introduces
    the table and the table as the notes reader saw it (the parsed filing at documents.tables_path). Empty when the
    parsed filing is not on disk (a clone without data/docs): the task then carries the category names alone."""
    if not names or not con.execute("select count(*) from information_schema.tables where table_name = 'note_extractions'").fetchone()[0]:
        return []
    cur = con.execute("""select n.accession, n.table_id, n.row_label, d.tables_path, d.filed from note_extractions n join documents d on d.accession = n.accession
                         where n.ticker = ? and n.field = 'ppe_category' and n.dimension in (select unnest(?)) order by d.filed desc""", [ticker, names])
    rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    out, seen = [], set()
    for r in rows:
        key = (r["accession"], r["table_id"])
        if key in seen or r["table_id"] is None:
            continue
        p = ROOT / (r["tables_path"] or "")
        if not r["tables_path"] or not p.exists():
            continue
        parsed = json.loads(p.read_text())
        t = next((t for t in parsed["tables"] if t["id"] == r["table_id"]), None)
        if not t:
            continue
        seen.add(key)
        out.append({"accession": r["accession"], "table_id": r["table_id"], "filed": r["filed"], "before": re.sub(r"\s+", " ", (t.get("before") or "")[-1500:]).strip(),
                    "table": render_statement(f"PP&E table {r['table_id']} of filing {r['accession']} (filed {r['filed']})", [{**t, "unit_text": t.get("unit_text"), "unit_source": t.get("unit_source", "table")}])})
        if len(out) >= 3:  # the newest filings say what the categories hold today; older ones repeat them
            break
    return out


def make_task(ticker: str, names: list[str], blocks: list[dict], rejected: dict[str, list[str]] | None = None, allowed: list[str] | None = None) -> str:
    allowed = allowed or members()
    rejected = rejected or {}
    head = f"# Task: {ticker}, reported PP&E categories with no us-gaap member\n\nTicker: {ticker}\nPrompt version: {prompt_version()}\n"
    lst = "\n".join(f"- {m}" for m in allowed)
    cats = "\n".join(f"- \"{n}\"" + (f"  (a person rejected: {', '.join(rejected[n])}; propose another member or none)" if rejected.get(n) else "") for n in names)
    body = [f"## Allowed members (PropertyPlantAndEquipmentByTypeAxis)\n\n{lst}", f"## Categories to map\n\n{cats}"]
    if blocks:
        body.append("## The note's words\n\n" + "\n\n".join(f"Text before the table: \"{b['before']}\"\n\n{b['table']}" for b in blocks))
    else:
        body.append("## The note's words\n\n(the parsed note is not on disk; the category names above are all the note's words you have)")
    return head + "\n" + "\n\n".join(body) + "\n"


def write_task(ticker: str, text: str) -> Path:
    TASKS.mkdir(parents=True, exist_ok=True)
    p = TASKS / f"{ticker}.md"
    p.write_text(text)
    return p


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def validate_output(obj: dict, ticker: str, names: list[str], task: str, allowed: list[str] | None = None) -> None:
    allowed = allowed or members()
    if not isinstance(obj, dict):
        raise Invalid("output is not a JSON object")
    for k in ("ticker", "prompt_version", "proposals"):
        if k not in obj:
            raise Invalid(f"missing '{k}'")
    if obj["ticker"] != ticker:
        raise Invalid(f"ticker {obj['ticker']!r} is not the task's {ticker!r}")
    if obj["prompt_version"] not in (known := prompt_versions()):
        raise Invalid(f"prompt_version {obj['prompt_version']!r}, expected one of {known}")
    if not isinstance(obj["proposals"], list):
        raise Invalid("'proposals' must be a list")
    notes = _norm(task.partition("## The note's words")[2]) + " " + " ".join(_norm(n) for n in names)  # the note's words and the category names: never the headings or the member list
    seen = set()
    for i, p in enumerate(obj["proposals"]):
        missing = [k for k in ("reported_name", "standard_type", "evidence", "confidence", "reason") if k not in p]
        if missing:
            raise Invalid(f"proposals[{i}] missing {missing}")
        if p["reported_name"] not in names:
            raise Invalid(f"proposals[{i}].reported_name {p['reported_name']!r} is not one of the categories to map")
        if p["reported_name"] in seen:
            raise Invalid(f"proposals[{i}]: a second proposal for {p['reported_name']!r}")
        seen.add(p["reported_name"])
        if p["standard_type"] != NONE and p["standard_type"] not in allowed:
            raise Invalid(f"proposals[{i}].standard_type {p['standard_type']!r} is not on the allowed list (or none)")
        if not isinstance(p["evidence"], str) or not p["evidence"].strip() or not re.search(r"(?<!\S)" + re.escape(_norm(p["evidence"])) + r"(?!\S)", notes):
            raise Invalid(f"proposals[{i}].evidence is not whole words of the note: {str(p['evidence'])[:80]!r}")
        if p["confidence"] not in CONFIDENCES:
            raise Invalid(f"proposals[{i}].confidence must be one of {CONFIDENCES}")
    left = [n for n in names if n not in seen]
    if left:
        raise Invalid(f"no proposal for {left}")


def propose(ticker: str, obj: dict, run: dict, path: Path | None = None) -> list[dict]:
    """Append one `proposed` line per proposal, with the prompt version, the model and when."""
    at = _now()
    return [_append({"kind": "proposed", "ticker": ticker, **{k: p[k] for k in ("reported_name", "standard_type", "evidence", "confidence", "reason")},
                     "prompt_version": obj["prompt_version"], "model": run.get("model"), "at": at}, path) for p in obj["proposals"]]


# ── the approval: the one writer of taxonomy/asset_types.yaml ─────────────────

def _scalar(s: str) -> str:
    return s if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .\-']*", s) else json.dumps(s)


def approve(ticker: str, reported_name: str, standard_type: str, evidence: str, by: str, path: Path | None = None, log: Path | None = None, at: str | None = None, con=None) -> dict:
    """Write one entry to taxonomy/asset_types.yaml, in the file's own format (one flow-mapping line under the ticker's
    block; the comment header untouched); refuse a member off the header's list, a second entry for the same
    (ticker, reported_name), and a name that is not one of the company's unmapped reported categories (taxonomy.unmapped
    on `con`, the database read-only when none is given). Logged as an `approved` line in the proposals log."""
    p = path or ASSET_TYPES
    ticker, reported_name, standard_type, evidence, by = ticker.strip().upper(), reported_name.strip(), standard_type.strip(), " ".join(evidence.split()), by.strip()
    if not ticker or not reported_name or not evidence or not by:
        raise ValueError("a mapping needs the ticker, the reported name, the evidence and the name of the person approving it")
    allowed = members(p)
    if standard_type not in allowed:
        raise ValueError(f"{standard_type!r} is not a member on the list in taxonomy/asset_types.yaml")
    current = (yaml_load(p).get(ticker) or {}) if p.exists() else {}
    if reported_name in current:
        raise ValueError(f"{ticker} {reported_name!r} is already mapped to {current[reported_name].get('standard_type')}")
    if reported_name not in {u["reported_name"] for u in _unmapped(con, ticker)}:
        raise ValueError(f"{ticker} {reported_name!r} is not one of the company's reported PP&E categories with no mapping; nothing written")
    line = f"  {json.dumps(reported_name)}: {{standard_type: {standard_type}, evidence: {json.dumps(evidence)}, by: {_scalar(by)}, at: {at or date.today().isoformat()}}}"
    lines = p.read_text().splitlines() if p.exists() else []
    starts = [i for i, l in enumerate(lines) if l == f"{ticker}:"]
    if starts:
        i = starts[0] + 1
        while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
            i += 1
        while i > starts[0] + 1 and not lines[i - 1].strip():  # insert before any blank line that ends the block
            i -= 1
        lines.insert(i, line)
    else:
        lines += [f"{ticker}:", line]
    text = "\n".join(lines) + "\n"
    import yaml
    parsed = yaml.safe_load(text)  # the file must still parse, or nothing is written
    if (parsed.get(ticker) or {}).get(reported_name, {}).get("standard_type") != standard_type:
        raise ValueError("the entry did not land where expected; nothing written")
    p.write_text(text)
    entry = {"ticker": ticker, "reported_name": reported_name, "standard_type": standard_type, "evidence": evidence, "by": by, "at": at or date.today().isoformat()}
    _append({"kind": "approved", **entry}, log)
    return entry


def _unmapped(con, ticker: str) -> list[dict]:
    """The company's reported categories with no mapping (taxonomy.unmapped), on `con` or on the database read-only."""
    if con is not None:
        return unmapped(con, [ticker])
    import duckdb
    c = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    try:
        return unmapped(c, [ticker])
    finally:
        c.close()


def yaml_load(p: Path) -> dict:
    import yaml
    return yaml.safe_load(p.read_text()) or {}


# ── what Reconcile shows ──────────────────────────────────────────────────────

def pending(con, tickers: list[str] | None, lines: list[dict] | None = None) -> list[dict]:
    """Every unmapped reported asset type in `tickers` (None: every company) with its latest proposal, if one stands, the
    members a person rejected for it, and the note's words around it."""
    out = []
    um = unmapped(con, tickers)
    by_t: dict[str, list[str]] = {}
    for u in um:
        by_t.setdefault(u["ticker"], []).append(u["reported_name"])
    for t, names in by_t.items():
        idx = by_name(t, lines)
        blocks = note_words(con, t, names)
        for n in names:
            e = idx.get(n) or {"proposal": None, "rejected": [], "approved": None}
            note = next((b for b in blocks if _norm(n) in _norm(b["table"])), blocks[0] if blocks else None)
            out.append({"ticker": t, "reported_name": n, "proposal": e["proposal"], "rejected": e["rejected"],
                        "note": {"accession": note["accession"], "table_id": note["table_id"], "before": note["before"][-400:]} if note else None})
    return out
