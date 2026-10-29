"""Per-company definitions (definitions/companies.yaml): judgements a person made once, applied by code every run.

A definition replaces a question. Where the SEC's tag measures something wider than the ledger's field, or a company
reports no cost-of-revenue total, the file says what the field means for that company, who decided and why; reconcile
and the rules read it, and nobody is asked again."""
from pathlib import Path

import yaml

from .store import ROOT

FILE = ROOT / "definitions" / "companies.yaml"


def load(path: Path = FILE) -> dict:
    """{ticker: {revenue: {...}, cost_lines: {...}}}, validated: every entry names who decided and why."""
    defs = yaml.safe_load(path.read_text()) if path.exists() else {}
    for t, d in (defs or {}).items():
        for k, e in d.items():
            if k not in ("revenue", "cost_lines") or not e.get("by") or not e.get("why"):
                raise ValueError(f"definitions: {t}.{k} needs by and why")
            if k == "cost_lines" and not e.get("lines"):
                raise ValueError(f"definitions: {t}.cost_lines needs lines")
    return defs or {}


def revenue_gap_explained(defs: dict, ticker: str) -> bool:
    return "revenue" in defs.get(ticker, {})


def cost_lines(defs: dict, ticker: str) -> set[str] | None:
    e = defs.get(ticker, {}).get("cost_lines")
    return set(e["lines"]) if e else None
