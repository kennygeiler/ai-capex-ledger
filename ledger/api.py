"""The read API, /api/v1 (docs/API.md): what the pipeline holds now, for the visualizer and for any system that
ingests it. JSON by default, CSV with format=csv. Every list takes the same filters (ticker, layer, period, field,
kind, method, scope: comma-separated values) and an optional group (ticker, layer, period, field, method, kind,
scope) that rolls amounts up. Read-only; the writes (views, resolutions, models) stay on their own endpoints."""
from __future__ import annotations

import csv
import io
import re

from .config import INDUSTRIES, PROVEN, industry, tracked
from .plans import plans as _plans
from . import resolutions as _resolutions
from . import views as _views

FILTERS = ("ticker", "layer", "period", "field", "kind", "method", "scope", "dimension", "source", "measure", "category", "fiscal_year", "standard_type", "check", "group")
SUM_COLS = {"attribution": "ai_amount", "values": "value", "facts": "value", "statements": "amount_mid", "plans": "gap", "projects": "amount", "taxonomy": "value"}
LISTS = ("companies", "values", "facts", "attribution", "statements", "plans", "projects", "theses", "views", "taxonomy")
RELEASE_LISTS = ("companies", "values", "facts", "attribution", "statements", "plans", "projects", "taxonomy")  # the files a release holds, one per list (C7)


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _table(con, name: str) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def companies(con=None) -> list[dict]:
    from .taxonomy import sic
    return [{"ticker": c["ticker"], "name": c["name"], "layer": industry(c["ticker"]), "group": c["group"], "role": c.get("role"), "note": c.get("note"),
             **(sic(con, c["ticker"]) if con is not None else {"sic": None, "sic_description": None})} for c in tracked()]


def theses() -> list[dict]:
    from . import agents
    cfg = agents.load()["attributor"]
    return [{"layer": layer, "version": v, "versions": agents.model_versions(layer), "text": agents.model_text(v),
             "companies": sorted(INDUSTRIES.get(layer, [c["ticker"] for c in tracked() if industry(c["ticker"]) == "other"]))}
            for layer, v in cfg["models"].items()]


def fetch(con, name: str) -> list[dict]:
    """One list, unfiltered, with `layer` on every row that has a ticker."""
    if name == "companies":
        rows = companies(con)
    elif name == "taxonomy":
        from .taxonomy import rows as _tax
        rows = _tax(con)
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
    idx = _resolutions.by_row() if name in ("values", "facts", "attribution") else None
    for r in rows:
        if "ticker" in r and "layer" not in r:
            r["layer"] = industry(r["ticker"])
        if "ticker" in r and name != "views":
            r["proven"] = r["ticker"] in PROVEN  # docs/PROOF.md: every number of a proven company is checked or explained; the rest are as they are
        if name == "attribution":  # status: a person's latest decision on the row; flag: what the numbers say by themselves
            r["status"] = _resolutions.status_of(idx, "attribution", r["ticker"], r["field"], "", r["period"], r["kind"])
            r["flag"] = "share_over_total" if r.get("ai_share") is not None and r["ai_share"] > 1 else ""
        elif name == "values":
            r["status"] = _resolutions.status_of(idx, "values", r["ticker"], r["field"], "", r["period"])
            r["flag"] = "differs_from_xbrl" if r.get("check_label") == "unresolved" else ""
        elif name == "facts":
            r["status"] = _resolutions.status_of(idx, "facts", r["ticker"], r["field"], r.get("dimension") or "", r["period"])
            r["flag"] = "differs_from_xbrl" if r.get("check_label") == "unresolved" else ""
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


def release_rows(version: str, name: str) -> list[dict]:
    """A signed release's file for a list, typed back from CSV: the same shape the live API serves, unchanged."""
    import csv
    from .publish import NUMERIC, check
    d = check(version)["dir"]
    f = d / f"{name}.csv"
    if name not in RELEASE_LISTS or not f.exists():
        raise KeyError(f"release {version} has no {name}")
    with f.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    for r in rows:
        for k, v in r.items():
            if v == "":
                r[k] = None
            elif k in NUMERIC or k in ("gap", "plan_low", "plan_high", "plan_mid", "actual", "gap_share", "capacity_mw", "gpus", "amount_mid"):
                try:
                    r[k] = int(v) if re.fullmatch(r"-?\d+", v) else float(v)
                except ValueError:
                    pass
            elif v in ("True", "False"):
                r[k] = v == "True"
        r["release"] = version
    return rows


def query(con, name: str, q: dict) -> list[dict]:
    if q.get("release"):
        return apply(release_rows(q["release"], name), q)
    return apply(fetch(con, name), q)


def coverage(con) -> dict:
    """Per layer and field: companies with an AI amount, with words only, with nothing, with no row at all (C4)."""
    cos = companies()
    att = _rows(con, "select ticker, field, method, ai_amount from attribution where kind = 'actual'")
    state = {}
    for a in att:
        k = (a["ticker"], a["field"])
        cur = state.get(k, "none")
        new = "amount" if a["ai_amount"] is not None else ("words" if a["method"] == "qualitative" else "none")
        state[k] = {"amount": 2, "words": 1, "none": 0}[new] > {"amount": 2, "words": 1, "none": 0}[cur] and new or cur
    out = []
    for layer in sorted({c["layer"] for c in cos}):
        mine = [c["ticker"] for c in cos if c["layer"] == layer]
        for field in ("capex", "opex", "revenue"):
            counts = {"amount": 0, "words": 0, "none": 0, "no_row": 0}
            for t in mine:
                counts[state.get((t, field), "no_row")] += 1
            out.append({"layer": layer, "field": field, "companies": len(mine), **counts})
    return {"rows": out, "note": "amount: an AI dollar figure with a method; words: the company links it to AI without a number; none: the thesis says it is not AI spend; no row: not run yet."}


def view_data(con, view_id: str) -> dict:
    v = _views.get(view_id)
    q = {**v["filters"], **({"group": v["group"]} if v.get("group") else {})}
    return {"view": v, "rows": query(con, v["measure"], q)}


def to_csv(rows: list[dict]) -> str:
    if not rows:
        return ""
    cols = list(dict.fromkeys(k for r in rows for k in r))
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore", lineterminator="\n")  # LF like every other release file; CRLF broke the signoff hash on read_text (v1.5.0)
    w.writeheader()
    for r in rows:
        w.writerow({k: ("" if v is None else v) for k, v in r.items()})
    return buf.getvalue()
