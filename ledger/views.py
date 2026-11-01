"""Saved views: a question a person built in DATAHQ, kept as a query another system can call (docs/THESIS.md).

A view is {id, name, measure, filters, group, show, by, at, note}. `measure` is one of the API's lists
(taxonomy, values, facts, statements, projects); `filters` are that list's filters (ticker, layer, period,
field, kind, method, scope); `group` is a column to roll up by (ticker, layer, period, field, method) or null for
rows; `show` is grid, bars (by group), lines (by year per company) or shares. Views live in data/views.json, tracked, so a view
travels with the repo. Saving a view with an existing id replaces it; the old one is kept in `history`."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
import os
from pathlib import Path

ROOT = Path(os.environ["LEDGER_ROOT"]).resolve() if os.environ.get("LEDGER_ROOT") else Path(__file__).resolve().parents[1]
FILE = ROOT / "data" / "views.json"
MEASURES = ("taxonomy", "values", "facts", "statements", "projects")
GROUPS = (None, "ticker", "layer", "period", "field", "method", "kind", "scope")
SHOWS = ("grid", "bars", "lines", "shares", "chart")  # chart: the Explorer's spec in `chart` {x, series, type}
CHART_AXES = ("period", "fiscal_year", "ticker", "layer", "field", "category", "measure", "standard_type", "kind", "dimension", "status", "scope", "source", "source_kind", "period_kind", "check")  # schema v11: no `group`
CHART_TYPES = ("bars", "stacked", "lines", "share")


def load() -> dict:
    return json.loads(FILE.read_text()) if FILE.exists() else {"views": [], "history": []}


def _save(d: dict) -> None:
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(d, indent=1) + "\n")


def get(view_id: str) -> dict:
    v = next((v for v in load()["views"] if v["id"] == view_id), None)
    if v is None:
        raise KeyError(f"no view {view_id}")
    return v


def save(view: dict, by: str) -> dict:
    name = (view.get("name") or "").strip()
    if not name or not by.strip():
        raise ValueError("a view needs a name and who saved it")
    vid = view.get("id") or re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:40]
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,39}", vid):
        raise ValueError("a view id is lowercase letters, digits and dashes")
    if view.get("measure") not in MEASURES:
        raise ValueError(f"measure must be one of {MEASURES}")
    if view.get("group") not in GROUPS:
        raise ValueError(f"group must be one of {GROUPS}")
    if view.get("show", "grid") not in SHOWS:
        raise ValueError(f"show must be one of {SHOWS}")
    filters = view.get("filters") or {}
    if not isinstance(filters, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in filters.items()):
        raise ValueError("filters is a map of column to comma-separated values")
    chart = view.get("chart")
    if view.get("show") == "chart":
        if not isinstance(chart, dict) or chart.get("x") not in CHART_AXES or chart.get("series", "") not in CHART_AXES + ("",) or chart.get("type") not in CHART_TYPES:
            raise ValueError(f"a chart view needs chart = {{x: one of {CHART_AXES}, series: one of those or empty, type: one of {CHART_TYPES}}}")
        chart = {"x": chart["x"], "series": chart.get("series") or "", "type": chart["type"], "value": str(chart.get("value") or "")}
    else:
        chart = None
    new = {"id": vid, "name": name, "measure": view["measure"], "filters": filters, "group": view.get("group"), "show": view.get("show", "grid"),
           "note": (view.get("note") or "").strip(), "by": by.strip(), "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    if chart:
        new["chart"] = chart
    d = load()
    old = next((v for v in d["views"] if v["id"] == vid), None)
    if old:
        d["history"].append(old)
        d["views"] = [v for v in d["views"] if v["id"] != vid]
    d["views"].append(new)
    _save(d)
    return new


def delete(view_id: str, by: str) -> None:
    d = load()
    old = get(view_id)
    d["history"].append({**old, "deleted_by": by, "deleted_at": datetime.now(timezone.utc).isoformat(timespec="seconds")})
    d["views"] = [v for v in d["views"] if v["id"] != view_id]
    _save(d)
