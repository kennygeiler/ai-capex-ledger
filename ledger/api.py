"""The read API, /api/v1 (docs/API.md): what the pipeline holds now, for the visualizer and for any system that
ingests it. JSON by default, CSV with format=csv. Every list takes the same filters (ticker, layer, period, field,
kind, method, scope: comma-separated values) and an optional group (ticker, layer, period, field, method, kind,
scope) that rolls amounts up. Read-only; the writes (views, resolutions, models) stay on their own endpoints."""
from __future__ import annotations

import csv
import io

from .config import INDUSTRIES, industry, tracked
from .plans import plans as _plans
from . import views as _views

FILTERS = ("ticker", "layer", "period", "field", "kind", "method", "scope", "dimension", "source")
SUM_COLS = {"attribution": "ai_amount", "values": "value", "facts": "value", "statements": "amount_mid", "plans": "gap", "projects": "amount"}
LISTS = ("companies", "values", "facts", "attribution", "statements", "plans", "projects", "theses", "views")


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _table(con, name: str) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def companies() -> list[dict]:
    return [{"ticker": c["ticker"], "name": c["name"], "layer": industry(c["ticker"]), "group": c["group"], "role": c.get("role"), "note": c.get("note")} for c in tracked()]


def theses() -> list[dict]:
    from . import agents
    cfg = agents.load()["attributor"]
    return [{"layer": layer, "version": v, "versions": agents.model_versions(layer), "text": agents.model_text(v),
             "companies": sorted(INDUSTRIES.get(layer, [c["ticker"] for c in tracked() if industry(c["ticker"]) == "other"]))}
            for layer, v in cfg["models"].items()]


def fetch(con, name: str) -> list[dict]:
    """One list, unfiltered, with `layer` on every row that has a ticker."""
    if name == "companies":
        rows = companies()
    elif name == "values":
        rows = _rows(con, 'select ticker, field, period, period_end, value, label as check_label, basis, source, extraction_ids from "values" where value is not null order by ticker, field, period')
    elif name == "facts":
        rows = _rows(con, "select ticker, field, dimension, period, period_end, value, label as check_label, reference as xbrl, accession, basis from facts order by ticker, field, dimension, period")
    elif name == "attribution":
        rows = _rows(con, "select ticker, field, period, kind, method, ai_amount, ai_share, confidence, basis, inputs, model, prompt_version, run_id from attribution order by ticker, field, period, kind")
    elif name == "statements":
        rows = _rows(con, """select s.statement_id, s.ticker, s.field, s.period, s.kind, s.scope, s.class, s.amount_low, s.amount_high,
                                    case when s.amount_low is null then null else (s.amount_low + s.amount_high) // 2 end as amount_mid,
                                    s.share, s.quote, s.source, t.date, t.url from ai_statements s join texts t on t.text_id = s.text_id order by s.ticker, s.field, s.period, t.date""")
    elif name == "plans":
        rows = _plans(con)
    elif name == "projects":
        rows = _rows(con, "select * from projects order by ticker, period, name") if _table(con, "projects") else []
    elif name == "theses":
        rows = theses()
    elif name == "views":
        rows = _views.load()["views"]
    else:
        raise KeyError(f"no list {name}; one of {LISTS}")
    for r in rows:
        if "ticker" in r and "layer" not in r:
            r["layer"] = industry(r["ticker"])
    return rows


def _split(v: str) -> set[str]:
    return {x.strip() for x in v.split(",") if x.strip()}


def apply(rows: list[dict], q: dict) -> list[dict]:
    """Filters, then group. Filter values match case-insensitively; a row without the column is kept."""
    for k in FILTERS:
        if q.get(k):
            want = {x.upper() for x in _split(q[k])}
            rows = [r for r in rows if k not in r or str(r.get(k) or "").upper() in want]
    g = q.get("group")
    if g:
        if g not in FILTERS:
            raise ValueError(f"group must be one of {FILTERS}")
        out: dict = {}
        for r in rows:
            key = r.get(g)
            o = out.setdefault(key, {g: key, "rows": 0, "amount": 0, "with_amount": 0})
            o["rows"] += 1
            for col in SUM_COLS.values():
                if col in r and isinstance(r[col], (int, float)) and r[col] is not None:
                    o["amount"] += r[col]
                    o["with_amount"] += 1
                    break
        rows = sorted(out.values(), key=lambda o: str(o[g]))
    return rows


def query(con, name: str, q: dict) -> list[dict]:
    return apply(fetch(con, name), q)


def view_data(con, view_id: str) -> dict:
    v = _views.get(view_id)
    q = {**v["filters"], **({"group": v["group"]} if v.get("group") else {})}
    return {"view": v, "rows": query(con, v["measure"], q)}


def to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols = list(dict.fromkeys(k for r in rows for k in r))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    return buf.getvalue()
