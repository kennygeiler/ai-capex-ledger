"""Project-level investment (docs/THESIS.md): named projects a company is building, buying or contracting for the
AI buildout, read from the same texts the AI spend reader reads (10-K MD&A, 8-K releases, transcripts).

A project is a thing with a name or a place and a size: a data-center campus, a fab, a plant expansion, a nuclear
restart, a power purchase agreement, a GPU cluster, a multi-year cloud commitment. The reader returns one row per
project per text with a verbatim quote; code checks the quote is in the passage, and the loader keeps the newest
text's row per (ticker, project name) so a project that is announced, then built, then in service shows once at
its latest status. The thesis for the layer says what counts as a project there."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from . import agents
from .guidance import _norm, task_passages
from ..core.store import ROOT

TASKS = ROOT / "data" / "projects" / "tasks"
OUTPUTS = ROOT / "data" / "projects" / "outputs"
KINDS = ("data_center", "fab", "plant", "power", "gpu_cluster", "cloud_commitment", "network", "other")
STATUSES = ("announced", "under_construction", "in_service", "contracted", "cancelled")
PROJECT = re.compile(r"data ?cent(er|re)|campus|fab\b|fabrication|plant|facility|megawatt|\bMW\b|gigawatt|\bGW\b|power purchase|PPA\b|nuclear|restart|GPU|cluster|supercomputer|commitment|lease agreement|build-?out|construction|expansion|site\b", re.I)
SIZE = re.compile(r"\$\s?\d|\d+(\.\d+)?\s?(billion|million|MW|GW|megawatt|gigawatt|acres|square feet|GPUs)", re.I)


def prompt_version() -> str:
    return agents.load()["projects_reader"]["prompt"]


def prompt_versions() -> tuple[str, ...]:
    return tuple(agents.versions("projects_reader"))


def passages(text: str, limit: int = 30) -> list[str]:
    """Paragraphs that name a project-like thing and give it a size, in document order."""
    paras = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", text)]
    hits = [(i, p) for i, p in enumerate(paras) if len(p) > 60 and PROJECT.search(p) and SIZE.search(p)]
    return [p for _, p in hits[:limit]]


SOURCE_NAME = {"mdna": "Item 7 (MD&A) of the 10-K", "earnings_release": "the earnings release (8-K Exhibit 99.1)",
               "transcript": "the earnings-call transcript", "cfo_commentary": "the CFO commentary"}


def make_task(text: dict, ps: list[str]) -> str:
    head = (f"# Task: {text['ticker']}, projects named in {SOURCE_NAME[text['kind']]} for the period ended {text['period_end']} (fiscal year {text['fiscal_year']})\n\n"
            f"Accession: {text['text_id']}\nPrompt version: {prompt_version()}\nText date: {text['date']}\n\nPassages, in order:\n")
    body = "\n\n".join(f"[p{i:02d}] {p}" for i, p in enumerate(ps, 1)) or "(no passage in this text names a project with a size)"
    return head + "\n" + body + "\n"


def write_tasks(texts: list[dict]) -> list[Path]:
    TASKS.mkdir(parents=True, exist_ok=True)
    out = []
    for t in texts:
        path = TASKS / f"{t['text_id']}.md"
        path.write_text(make_task(t, passages((ROOT / t["path"]).read_text())))
        out.append(path)
    return out


@dataclass
class Invalid(Exception):
    reason: str


def validate_output(obj: dict, accession: str, ps: dict[str, str]) -> None:
    if not isinstance(obj, dict):
        raise Invalid("output is not a JSON object")
    for k in ("accession", "prompt_version", "projects"):
        if k not in obj:
            raise Invalid(f"missing '{k}'")
    if obj["accession"] != accession:
        raise Invalid(f"accession {obj['accession']!r} is not the task's {accession!r}")
    if obj["prompt_version"] not in (known := prompt_versions()):
        raise Invalid(f"prompt_version {obj['prompt_version']!r}, expected one of {known}")
    if not isinstance(obj["projects"], list):
        raise Invalid("'projects' must be a list")
    req = ("name", "kind", "status", "quote", "passage", "confidence")
    for i, p in enumerate(obj["projects"]):
        missing = [k for k in req if k not in p]
        if missing:
            raise Invalid(f"projects[{i}] missing {missing}")
        if not isinstance(p["name"], str) or not 3 <= len(p["name"]) <= 120:
            raise Invalid(f"projects[{i}].name must be 3 to 120 characters")
        if p["kind"] not in KINDS or p["status"] not in STATUSES:
            raise Invalid(f"projects[{i}]: kind {p['kind']!r} or status {p['status']!r} out of range")
        if p["passage"] not in ps:
            raise Invalid(f"projects[{i}].passage {p['passage']!r} is not in the task")
        if not isinstance(p["quote"], str) or len(p["quote"]) < 8 or _norm(p["quote"]) not in _norm(ps[p["passage"]]):  # a project is often a table cell ("WULF Den (2 MW)"); verbatim is the guard, not length (type 59)
            raise Invalid(f"projects[{i}].quote is not a verbatim sentence of passage {p['passage']}: {str(p['quote'])[:80]!r}")
        lo, hi = p.get("amount_low"), p.get("amount_high")
        if (lo is None) != (hi is None):
            raise Invalid(f"projects[{i}]: amount_low and amount_high go together")
        if lo is not None and not (isinstance(lo, int) and isinstance(hi, int) and not isinstance(lo, bool) and 0 < lo <= hi):
            raise Invalid(f"projects[{i}]: amounts are integer dollars, amount_low <= amount_high")
        for k in ("capacity_mw", "gpus"):
            if p.get(k) is not None and not (isinstance(p[k], (int, float)) and not isinstance(p[k], bool) and p[k] > 0):
                raise Invalid(f"projects[{i}].{k} must be a positive number or null")
        for k in ("announced", "in_service"):
            if p.get(k) is not None and not re.fullmatch(r"\d{4}(-\d{2})?(-\d{2})?", str(p[k])):
                raise Invalid(f"projects[{i}].{k} is a date (YYYY, YYYY-MM or YYYY-MM-DD) or null")
        if not (isinstance(p["confidence"], (int, float)) and 0 <= p["confidence"] <= 1):
            raise Invalid(f"projects[{i}].confidence must be between 0 and 1")


def rows_for(text: dict, obj: dict, run_id: str) -> list[dict]:
    out = []
    for i, p in enumerate(obj["projects"]):
        out.append({"project_id": f"{text['text_id']}|{i}", "ticker": text["ticker"], "text_id": text["text_id"], "source": text["kind"], "accession": text["accession"],
                    "date": text["date"], "period": f"FY{text['fiscal_year']}", "name": p["name"].strip(), "kind": p["kind"], "status": p["status"],
                    "location": (p.get("location") or None), "counterparty": (p.get("counterparty") or None),
                    "amount_low": p.get("amount_low"), "amount_high": p.get("amount_high"),
                    "capacity_mw": None if p.get("capacity_mw") is None else float(p["capacity_mw"]), "gpus": None if p.get("gpus") is None else int(p["gpus"]),
                    "announced": p.get("announced"), "in_service": p.get("in_service"), "quote": p["quote"], "passage": p["passage"], "confidence": float(p["confidence"]),
                    "prompt_version": obj["prompt_version"], "run_id": run_id})
    return out


def latest(rows: list[dict]) -> list[dict]:
    """One row per (ticker, name): the newest text's, so a project shows at its latest status; `mentions` counts the rest."""
    by: dict = {}
    for r in sorted(rows, key=lambda r: r["date"]):
        k = (r["ticker"], _norm(r["name"]))
        n = by[k]["mentions"] + 1 if k in by else 1
        by[k] = {**r, "mentions": n}
    return list(by.values())
