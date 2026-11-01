"""Per-company definitions (definitions/companies.yaml): judgements a person made once, applied by code every run.

A definition replaces a question. Where the SEC's tag measures something wider than the ledger's field, or a company
reports no cost-of-revenue total, the file says what the field means for that company, who decided and why; reconcile
and the rules read it, and nobody is asked again."""
import re
from pathlib import Path

import yaml

from .store import ROOT

FILE = ROOT / "definitions" / "companies.yaml"


def load(path: Path = FILE) -> dict:
    """{ticker: {revenue: {...}, cost_lines: {...}, opex: {...}}}, validated: every entry names who decided and why.
    opex: the SEC's OperatingExpenses tag measures something wider than revenue minus cost of revenue minus operating
    income (Iron Mountain's includes cost of sales); the definition says so, and the gap is a definition, not a misread."""
    defs = yaml.safe_load(path.read_text()) if path.exists() else {}
    for t, d in (defs or {}).items():
        for k, e in d.items():
            if k not in ("revenue", "cost_lines", "opex") or not e.get("by") or not e.get("why"):
                raise ValueError(f"definitions: {t}.{k} needs by and why")
            if k == "cost_lines" and not e.get("lines"):
                raise ValueError(f"definitions: {t}.cost_lines needs lines")
            if "periods" in e and (k == "cost_lines" or not isinstance(e["periods"], list) or not e["periods"]
                                   or not all(isinstance(q, str) and PERIOD.fullmatch(q) for q in e["periods"])):
                raise ValueError(f"definitions: {t}.{k}.periods must be a non-empty list of fiscal years (FY2024), on revenue or opex only")
    return defs or {}


PERIOD = re.compile(r"FY\d{4}")


def _applies(e: dict | None, period: str | None) -> bool:
    """T36: an entry with `periods` applies only to those fiscal years (the item a person saw); one without applies to
    every year of the company, as every entry written before T36 does. With no period asked, any entry counts."""
    if e is None:
        return False
    return "periods" not in e or period is None or period in e["periods"]


def revenue_gap_explained(defs: dict, ticker: str, period: str | None = None) -> bool:
    return _applies(defs.get(ticker, {}).get("revenue"), period)


def opex_gap_explained(defs: dict, ticker: str, period: str | None = None) -> bool:
    return _applies(defs.get(ticker, {}).get("opex"), period)


def cost_lines(defs: dict, ticker: str) -> set[str] | None:
    e = defs.get(ticker, {}).get("cost_lines")
    return set(e["lines"]) if e else None
