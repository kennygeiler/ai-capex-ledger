"""The read API, /api/v1 (docs/API.md): what the pipeline holds now, for the visualizer and for any system that
ingests it. JSON by default, CSV with format=csv. Every list takes the same filters (ticker, layer, period, field,
kind, method, scope: comma-separated values) and an optional group (ticker, layer, period, field, method, kind,
scope) that rolls amounts up. Read-only; the writes (views, resolutions, models) stay on their own endpoints."""
from __future__ import annotations

import csv
import io
import re

from ..core.config import INDUSTRIES, PROVEN, SCOPE, industry, tracked
from ..review import resolutions as _resolutions
from . import views as _views

FILTERS = ("ticker", "layer", "period", "field", "kind", "method", "scope", "dimension", "source", "measure", "category", "fiscal_year", "standard_type", "check",
           "source_kind", "period_kind", "has_value", "mapped", "status",
           "as_of")  # schema v11: the taxonomy rows' own columns; a boolean filter takes true / false. as_of (T55): a date; the rows carry it back
RANGE = ("from", "to")  # F-BF7: a year range, inclusive, on a row's period or fiscal_year (FY2024); a row with neither is kept, as Explore's chart keeps it
AS_OF_LISTS = ("values", "taxonomy")  # the lists that answer ?as_of=D (ledger/web/pit.py): the figure the newest filing filed by D gave
AS_OF_NOTE = ("only the newest vintage of each figure is reconciled against XBRL; an as-of row from an older filing carries vintage_check "
              "'unchecked': its figure is the cell as read, not compared with its own filing's tags (docs/API.md, T55b)")  # for the response's top-level note
SUM_COLS = {"values": "value", "facts": "value", "statements": "amount_mid", "projects": "amount", "taxonomy": "value"}
LISTS = ("companies", "values", "facts", "statements", "projects", "views", "taxonomy")
RELEASE_LISTS = ("companies", "values", "facts", "statements", "projects", "taxonomy")  # the files a release holds, one per list


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _table(con, name: str) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def companies(con=None) -> list[dict]:
    from ..release.taxonomy import sic
    return [{"ticker": c["ticker"], "name": c["name"], "layer": industry(c["ticker"]), "group": c["group"], "role": c.get("role"), "note": c.get("note"),
             **(sic(con, c["ticker"]) if con is not None else {"sic": None, "sic_description": None})} for c in tracked()]


def fetch(con, name: str) -> list[dict]:
    """One list, unfiltered, with `layer` on every row that has a ticker."""
    if name == "companies":
        rows = companies(con)
    elif name == "taxonomy":
        from ..release.taxonomy import rows as _tax
        rows = _tax(con)
    elif name == "values":
        rows = _values(con)
    elif name == "facts":
        rows = _rows(con, "select ticker, field, dimension, period, period_end, value, label as check_label, reference as xbrl, accession, basis, first_reported from facts order by ticker, field, dimension, period")
    elif name == "statements":
        rows = _rows(con, """select s.statement_id, s.ticker, s.field, s.period, s.kind, s.scope, s.class, s.amount_low, s.amount_high,
                                    case when s.amount_low is null then null else (s.amount_low + s.amount_high) // 2 end as amount_mid,
                                    s.share, s.quote, s.source, t.date, t.url from ai_statements s join texts t on t.text_id = s.text_id order by s.ticker, s.field, s.period, t.date""")
    elif name == "projects":
        rows = _rows(con, "select * from projects order by ticker, period, name") if _table(con, "projects") else []
    elif name == "views":
        rows = _views.load()["views"]
    else:
        raise KeyError(f"no list {name}; one of {LISTS}")
    idx = _resolutions.index(con) if name in ("values", "facts") else None  # F15: matched to the item it was written for
    for r in rows:
        if "ticker" in r and "layer" not in r:
            r["layer"] = industry(r["ticker"])
        if "ticker" in r and name != "views":
            r["proven"] = r["ticker"] in PROVEN  # docs/PROOF.md: every number of a proven company is checked or explained; the rest are as they are
        if name == "values":  # status: a person's latest decision on the row; flag: what the numbers say by themselves
            r["status"] = _resolutions.status_of(idx, "values", r["ticker"], r["field"], "", r["period"])
            r["flag"] = "differs_from_xbrl" if r.get("check_label") == "unresolved" else ""
        elif name == "facts":
            r["status"] = _resolutions.status_of(idx, "facts", r["ticker"], r["field"], r.get("dimension") or "", r["period"])
            r["flag"] = "differs_from_xbrl" if r.get("check_label") == "unresolved" else ""
    return rows


def _values(con) -> list[dict]:
    """The values list, one row per (ticker, field, fiscal year) with a value: a row whose value is null (the newest 10-K
    has no such line, or the cell is not yet extracted) is not a value and does not ship (T64; QUALITY.md counts them).
    Beside the value: `first_reported` (the first 10-K's figure), `accession` and `filed` of the filing the value comes
    from, and `citations`, every cell behind it (accession, table, row label, column label, cell text)."""
    from ..core.ids import split_ids
    rows = _rows(con, 'select ticker, field, period, period_end, value, label as check_label, basis, first_reported, source, extraction_ids from "values" where value is not null order by ticker, field, period')
    ids = sorted({i for r in rows for i in split_ids(r["extraction_ids"] or "")})
    cells = {e["extraction_id"]: e for e in _rows(con, """select e.extraction_id, e.accession, d.filed, e.table_id, e.row_label, e.column_label, e.cell_text
                                                          from extractions e left join documents d on d.accession = e.accession where e.extraction_id in (select unnest(?))""", ids)} if ids else {}
    for r in rows:
        used = [cells[i] for i in split_ids(r["extraction_ids"] or "") if i in cells]
        r["accession"] = used[0]["accession"] if used else None  # every cell of a value comes from one filing (reconcile.values_for)
        r["filed"] = used[0]["filed"] if used else None
        r["citations"] = " ; ".join(f"{e['accession']} {e['table_id']} '{e['row_label']}' / '{e['column_label']}' = {e['cell_text']}" for e in used)
    return rows


def _split(v: str) -> set[str]:
    return {x.strip() for x in v.split(",") if x.strip()}


FISCAL_YEAR = re.compile(r"^FY\d{4}$")


def year_range(q: dict) -> tuple[str | None, str | None]:
    """(from, to) of a request, each FY plus four digits (FY2023), or None when not asked. A value of any other shape, or
    a from after the to, is a ValueError (400): a range read as text would compare "2024" or "fy24" wrongly (F-BF17)."""
    out = []
    for k in RANGE:
        v = str(q.get(k) or "").strip().upper()
        if v and not FISCAL_YEAR.match(v):
            raise ValueError(f"{k} must be a fiscal year like FY2024, not {q.get(k)!r}")
        out.append(v or None)
    if out[0] and out[1] and out[0] > out[1]:
        raise ValueError(f"from {out[0]} is after to {out[1]}")
    return out[0], out[1]


def column(r: dict, k: str) -> str:
    """The column a filter reads on a row: `check` is the verdict column of every list, `check` on the taxonomy and
    `check_label` on values and facts (report #13: one Verification filter, whatever the list calls the column)."""
    return "check_label" if k == "check" and "check" not in r and "check_label" in r else k


def apply(rows: list[dict], q: dict) -> list[dict]:
    """Filters, then group. Filter values match case-insensitively; a row without the column is kept."""
    for k in FILTERS:
        if q.get(k):
            want = {x.upper() for x in _split(q[k])}
            rows = [r for r in rows if column(r, k) not in r or ("" if r.get(column(r, k)) is None else str(r[column(r, k)])).upper() in want]  # False is a value, not empty (has_value=false)
    lo, hi = year_range(q)
    year = lambda r: str(r.get("period") or r.get("fiscal_year") or "").upper()
    if lo:
        rows = [r for r in rows if not year(r) or year(r) >= lo]
    if hi:
        rows = [r for r in rows if not year(r) or year(r) <= hi]
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
    from ..release.publish import BOOLEAN, NUMERIC, check
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
            elif k in BOOLEAN or v in ("True", "False"):
                r[k] = v == "True"
        r["release"] = version
    return rows


def in_scope(rows: list[dict], q: dict) -> list[dict]:
    """With no ticker filter a list shows the scope (config.SCOPE); `ticker=` asks for any company the database holds."""
    return rows if q.get("ticker") else [r for r in rows if "ticker" not in r or r["ticker"] in SCOPE]


def as_of_rows(con, name: str, day: str, q: dict) -> list[dict]:
    """The list on `day` (T55, ledger/web/pit.py): values re-pointed at the newest filing filed by `day` (first_reported and
    basis stay as `values` holds them; check_label and flag are left off, the XBRL comparison was made on the newest
    figure); the taxonomy through pit.taxonomy_as_of. A bad date or a list that has no history is a ValueError (400)."""
    from . import pit
    if name not in AS_OF_LISTS:
        raise ValueError(f"as_of applies to {' and '.join(AS_OF_LISTS)}, not {name}")
    day = pit.parse_day(day)
    tickers = sorted(_split(q["ticker"])) if q.get("ticker") else list(SCOPE)
    if name == "taxonomy":
        return pit.taxonomy_as_of(con, fetch(con, name), day, tickers)
    live = {(v["ticker"], v["field"], v["period"]): v for v in _rows(con, 'select ticker, field, period, basis, first_reported from "values"')}
    idx = _resolutions.index(con, tickers)
    out = []
    for r in pit.as_of(con, day, tickers):
        v = live.get((r["ticker"], r["field"], r["period"])) or {}
        out.append({"ticker": r["ticker"], "field": r["field"], "period": r["period"], "period_end": r["period_end"], "value": r["value"], "accession": r["accession"],
                    "filed": r["filed"], "restated_later": r["restated_later"], "vintage_check": r["vintage_check"], "basis": v.get("basis"), "first_reported": v.get("first_reported"), "source": "agent",
                    "extraction_ids": r["extraction_ids"], "layer": industry(r["ticker"]), "proven": r["ticker"] in PROVEN,
                    "status": _resolutions.status_of(idx, "values", r["ticker"], r["field"], "", r["period"]), "as_of": day})
    return out


def query(con, name: str, q: dict) -> list[dict]:
    if q.get("release") and q.get("as_of"):
        raise ValueError("as_of reads the live cells; a release is a fixed snapshot: ask for one or the other")
    if q.get("release"):
        return apply(in_scope(release_rows(q["release"], name), q), q)
    if q.get("as_of"):
        return apply(in_scope(as_of_rows(con, name, q["as_of"], q), q), q)
    return apply(in_scope(fetch(con, name), q), q)


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
