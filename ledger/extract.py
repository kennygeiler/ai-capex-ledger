"""Pack extraction tasks, validate agent outputs, resolve citations, load extractions.

A task holds only what a reader of the filing would see: the located statement tables (row labels, column labels,
cell text, unit line). No XBRL values and no XBRL tag names, so the agent cannot copy the answer key.
"""
from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from . import agents
from .store import ROOT

TASKS = ROOT / "data" / "extract" / "tasks"
OUTPUTS = ROOT / "data" / "extract" / "outputs"
FIELDS = ("revenue", "cost_of_revenue", "cost_of_revenue_part", "operating_income", "capex")


def prompt_version() -> str:
    """The active prompt, as agents/agents.json says right now (the app can switch it while a server runs)."""
    return agents.load()["reader"]["prompt"]


def prompt_versions() -> tuple[str, ...]:
    """Every saved version: an output from any of them stays valid."""
    return tuple(agents.versions("reader"))


# ── tasks ──────────────────────────────────────────────────────────────────────────────────────────────────────────
def render_statement(name: str, tables: list[dict]) -> str:
    out = [f"### {name}"]
    for t in tables:
        unit = t["unit_text"] or "(no unit stated)"
        src = {"table": "stated with the table", "statement": "stated on the first page of this statement",
               "document": f"NOT stated with the table; found elsewhere in the filing: \"{t.get('unit_context', '')[:160]}\""}.get(t.get("unit_source"), "")
        out += ["", f"Table `{t['id']}`. Unit: {unit} ({src}).", "", "Columns:"]
        out += [f"  [{i}] {c}" for i, c in enumerate(t["columns"])]
        out += ["", "Rows (label | [column] cell text):"]
        for r in t["rows"]:
            cells = "  ".join(f"[{c['col']}] {c['text']}" for c in r["cells"])
            out.append(f"  {r['label'] or '(no label)'} | {cells}" if cells else f"  {r['label']}")
    return "\n".join(out)


def make_task(parsed: dict) -> str:
    """The agent's task for one filing: its income and cash-flow statements, as a reader sees them, and nothing else."""
    head = (f"# Task: {parsed['ticker']} {parsed['form']} for the period ended {parsed['period']}\n\n"
            f"Accession: {parsed['accession']}\nPrompt version: {prompt_version()}\n")
    body = [render_statement("Income statement", parsed["statements"]["income"] or []),
            render_statement("Cash-flow statement", parsed["statements"]["cash_flow"] or [])]
    return head + "\n" + "\n\n".join(body) + "\n"


def write_tasks(parsed_docs: list[dict]) -> list[Path]:
    TASKS.mkdir(parents=True, exist_ok=True)
    paths = []
    for p in parsed_docs:
        path = TASKS / f"{p['accession']}.md"
        path.write_text(make_task(p))
        paths.append(path)
    return paths


# ── output validation ──────────────────────────────────────────────────────────────────────────────────────────────
@dataclass
class Invalid(Exception):
    reason: str


def validate_output(obj: dict, accession: str) -> None:
    """Check one agent output against the output contract (agents/schemas/extraction@v2.json; v1 outputs stay valid). Raises Invalid(reason)."""
    if not isinstance(obj, dict):
        raise Invalid("output is not a JSON object")
    for k in ("accession", "prompt_version", "values", "not_found"):
        if k not in obj:
            raise Invalid(f"missing '{k}'")
    if obj["accession"] != accession:
        raise Invalid(f"accession {obj['accession']!r} is not the task's {accession!r}")
    if obj["prompt_version"] not in (known := prompt_versions()):
        raise Invalid(f"prompt_version {obj['prompt_version']!r}, expected one of {known}")
    if not isinstance(obj["values"], list) or not isinstance(obj["not_found"], list):
        raise Invalid("'values' and 'not_found' must be lists")
    req = ("field", "table_id", "row_label", "column_label", "cell_text", "period_end", "months", "value", "confidence")
    for i, v in enumerate(obj["values"]):
        missing = [k for k in req if k not in v]
        if missing:
            raise Invalid(f"values[{i}] missing {missing}")
        if v["field"] not in FIELDS:
            raise Invalid(f"values[{i}].field {v['field']!r} is not one of {FIELDS}")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v["period_end"])):
            raise Invalid(f"values[{i}].period_end {v['period_end']!r} is not YYYY-MM-DD")
        if v["months"] not in (3, 6, 9, 12):
            raise Invalid(f"values[{i}].months {v['months']!r} is not 3, 6, 9 or 12")
        if not isinstance(v["value"], int) or isinstance(v["value"], bool):
            raise Invalid(f"values[{i}].value must be an integer number of dollars")
        if not (isinstance(v["confidence"], (int, float)) and 0 <= v["confidence"] <= 1):
            raise Invalid(f"values[{i}].confidence must be between 0 and 1")
    for i, n in enumerate(obj["not_found"]):
        if not isinstance(n, dict) or "field" not in n or "reason" not in n:
            raise Invalid(f"not_found[{i}] needs 'field' and 'reason'")


# ── citation resolution ────────────────────────────────────────────────────────────────────────────────────────────
def resolve(v: dict, parsed: dict) -> dict:
    """Check the citation against the parsed document. Returns the cited table's unit info, or raises Invalid."""
    tables = {t["id"]: t for t in parsed.get("tables", [])} | {t["id"]: t for k in ("income", "cash_flow") for t in (parsed["statements"][k] or [])}
    t = tables.get(v["table_id"])
    if not t:
        raise Invalid(f"table {v['table_id']} is not in the filing")
    if v["column_label"] not in t["columns"]:
        raise Invalid(f"column {v['column_label']!r} not in table {t['id']} columns {t['columns']}")
    col = t["columns"].index(v["column_label"])
    rows = [r for r in t["rows"] if r["label"] == v["row_label"]]
    if not rows:
        raise Invalid(f"row {v['row_label']!r} not in table {t['id']}")
    cells = [c for r in rows for c in r["cells"] if c["col"] == col]
    if not any(c["text"] == v["cell_text"] for c in cells):
        raise Invalid(f"cell text {v['cell_text']!r} not found at row {v['row_label']!r}, column {v['column_label']!r} (found {[c['text'] for c in cells]})")
    cell = next(c for c in cells if c["text"] == v["cell_text"])
    if not t["scale"]:
        raise Invalid(f"table {t['id']} has no unit")
    shown = round(cell["value"] * t["scale"])
    # Sign conventions: capex is cash spent, shown in parentheses, stored positive (a positive cell is a mismatch to
    # review, not something to silently flip). Cost of revenue is stored positive however the table shows it.
    capex_label = re.search(r"capital expenditure|purchases? of property|additions to property", v["row_label"], re.I)
    expected = (abs(shown) if capex_label else -shown) if v["field"] == "capex" else abs(shown) if v["field"].startswith("cost_of_revenue") else shown  # a positive cell is accepted only when its own label says capex (Freeport's summary table, type 57)
    if v["value"] != expected:
        raise Invalid(f"value {v['value']} != cell {v['cell_text']} × {t['scale']:,} = {expected} ({v['field']} sign convention)")
    # unit_source is set on located statement tables only; a citation of another table (an older read whose statement
    # was re-located since, T65) still resolves, with no unit source to name
    return {"unit_stated": t.get("unit_text"), "unit_source": t.get("unit_source"), "scale": t["scale"]}


# ── period start from the company's own filing calendar ───────────────────────────────────────────────────────────
def period_start(end: str, months: int, calendar: list[str]) -> str:
    """Start date for a period of `months` ending on `end`, from the company's report-period ends (submissions API,
    not XBRL). The start is the day after the calendar entry nearest to end − months (within 10 days); if the
    calendar has no entry that early, it falls back to end − months + 1 day."""
    e = date.fromisoformat(end)
    target = _minus_months(e, months)
    near = [date.fromisoformat(c) for c in calendar if abs((date.fromisoformat(c) - target).days) <= 10]
    base = min(near, key=lambda d: abs((d - target).days)) if near else target
    return (base + timedelta(days=1)).isoformat()


def _minus_months(d: date, m: int) -> date:
    """d moved back m months; a month-end stays a month-end (30 Jun − 6 months = 31 Dec, not 30 Dec)."""
    y, mo = divmod(d.month - 1 - m, 12)
    year, month = d.year + y, mo + 1
    last = calendar.monthrange(year, month)[1]
    return date(year, month, last if d.day == calendar.monthrange(d.year, d.month)[1] else min(d.day, last))
