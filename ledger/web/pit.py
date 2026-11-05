"""Point in time (T55): the figure the newest filing filed on or before a date gave.

`values` ships one figure per (ticker, field, fiscal year): the newest 10-K's, with the first 10-K's beside it as
`first_reported`. A backtest must not see that: on day D only the filings filed by D existed, and a figure a later 10-K
restated is lookahead. `as_of(con, D)` answers from the cells themselves (`extractions` keeps every filing's cells) joined
to `documents.filed`, with the same arithmetic as the values builder (`reconcile.values_for`): one cell per field, opex
from three cells of the same 10-K column, cost-of-revenue lines summed when the statement has no total line, the newest
filing by `filed` and on the same day the more complete one. Nothing is inferred: a (ticker, field, year) no filing by D
reports is absent, not null-filled. Overrides (a person's replacement value in `decisions`) are not applied: the as-of
figure is what the filing said.

Covered: the fields `values` holds (config.RELEASE_FIELDS) for the fiscal years `values` knows (its `period_end` per
company and year is the calendar; a year no 10-K read reports has no row at any date)."""
from __future__ import annotations

from datetime import date

from ..core.config import RELEASE_FIELDS
from ..core.ids import split_ids
from ..checks.reconcile import _restated

PARTS = {"opex": ("revenue", "cost_of_revenue", "operating_income")}


def parse_day(s: str) -> str:
    """An ISO date, or ValueError (the API answers 400)."""
    try:
        return date.fromisoformat(str(s)).isoformat()
    except (TypeError, ValueError):
        raise ValueError(f"as_of must be an ISO date (YYYY-MM-DD), got {s!r}") from None


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _filings(extractions: list[dict]) -> dict:
    """(ticker, period_end) -> [(filed, accession, {field: cell})], oldest first; the same grouping as reconcile.values_for."""
    cells: dict = {}
    for e in extractions:
        if not 350 <= (date.fromisoformat(e["period_end"]) - date.fromisoformat(e["period_start"])).days <= 380:
            continue  # a 12-month column only
        fs = cells.setdefault((e["ticker"], e["period_end"], e["accession"], e["filed"]), {})
        if e["field"] == "cost_of_revenue_part":
            fs.setdefault("parts", []).append(e)
        else:
            fs[e["field"]] = e
    out: dict = {}
    for (ticker, end, accession, filed), fs in cells.items():
        if "cost_of_revenue" not in fs and fs.get("parts"):
            ps = fs["parts"]
            fs["cost_of_revenue"] = {**ps[0], "value": sum(x["value"] for x in ps), "parts": ps}
        out.setdefault((ticker, end), []).append((filed, accession, fs))
    for fl in out.values():
        fl.sort(key=lambda x: (x[0], len(x[2])))  # newest filing last; on the same day, the more complete one
    return out


def _value(fs: dict, field: str) -> int | None:
    parts = PARTS.get(field, (field,))
    if not all(p in fs for p in parts):
        return None
    if field == "opex":
        v = fs["revenue"]["value"] - fs["cost_of_revenue"]["value"] - fs["operating_income"]["value"]
        return None if v < 0 else v  # operating income holding fair-value gains is not opex (reconcile, type 65)
    return fs[field]["value"]


def _used(fs: dict, field: str) -> list[dict]:
    return [x for p in PARTS.get(field, (field,)) for x in fs[p].get("parts", [fs[p]])]


def as_of(con, day: str, tickers: list[str] | None = None) -> list[dict]:
    """One row per (ticker, field, period) the newest filing filed on or before `day` reports: ticker, field, period,
    period_end, value, accession, filed, extraction_ids, restated_later (a filing after the one answering changed the figure
    beyond its rounding; the later filing may be after `day`), as_of. As in values_for, every field of a year comes from
    that one newest filing: when it lacks the line the field is absent at that date, even if an older filing had it.
    `vintage_check`: only the newest vintage is reconciled against XBRL (reconcile.values_for); a row from the accession
    `values` checked carries that label (agree, unresolved, …), every older vintage carries "unchecked": its figure is the
    filing's cell as read, never compared with its own filing's tags (AT&T FY2022 revenue: the first 10-K's cell was read at
    the wrong scale, $120,741,000 for $120.7bn, and `values` calls it restated; T55b in docs/TICKETS.md). Columns used: extractions.ticker, field, period_start,
    period_end, value, scale, accession, extraction_id joined to documents.accession for documents.filed; "values".ticker,
    period, period_end for the fiscal calendar."""
    day = parse_day(day)
    where = "where e.ticker in (select unnest(?))" if tickers else ""
    p = [tickers] if tickers else []
    exts = _rows(con, f"""select e.extraction_id, e.ticker, e.field, e.period_start, e.period_end, e.value, e.scale, e.accession, d.filed
                          from extractions e join documents d on d.accession = e.accession {where}""", *p)
    vals = _rows(con, f'select ticker, field, period, period_end, label, extraction_ids from "values" {where.replace("e.", "")}', *p)
    years = {(v["ticker"], v["period_end"]): v["period"] for v in vals}
    checked = {(v["ticker"], v["field"], v["period"]): ((v["extraction_ids"] or "").split("|")[0], v["label"]) for v in vals}  # the accession values reconciled, and how it came out
    out = []
    for (ticker, end), fl in sorted(_filings(exts).items()):
        period = years.get((ticker, end))
        if period is None:
            continue  # a year values does not know: nothing to answer for it
        by_day = [x for x in fl if x[0] <= day]
        if not by_day:
            continue
        filed, acc, fs = by_day[-1]  # every field from the newest filing by `day`, as values_for: a year never mixes filings
        for field in RELEASE_FIELDS:
            v = _value(fs, field)
            if v is None:
                continue  # that filing has no such line: values says not_reported, the as-of row is absent (an older filing's line is not reached for)
            later = [lv for lv in (_value(f2, field) for _, _, f2 in fl[len(by_day):]) if lv is not None]
            scale = max(e["scale"] for e in _used(fs, field))
            chk_acc, label = checked.get((ticker, field, period), (None, None))
            out.append({"ticker": ticker, "field": field, "period": period, "period_end": end, "value": v, "accession": acc, "filed": filed,
                        "extraction_ids": ",".join(sorted(e["extraction_id"] for e in _used(fs, field))),
                        "restated_later": any(_restated(v, lv, scale) for lv in later),
                        "vintage_check": label if acc == chk_acc and label else "unchecked", "as_of": day})
    return out


def taxonomy_as_of(con, rows: list[dict], day: str, tickers: list[str] | None = None) -> list[dict]:
    """The taxonomy list on `day`: a `spent` / `capex` row (built from `values`) is re-pointed at the newest filing filed
    by `day` through `as_of` (value, source, accession, filed, source_table, source_url; `check` becomes `not_checked`
    with method `none` when that filing is not the one the live row was checked against, because the XBRL comparison was
    made on the newest figure); it is absent when no filing by `day` reports the year. Every other row is kept only when
    its own `filed` is on or before `day`: a 10-K note, MD&A or 8-K figure filed after `day` is dropped, not replaced by
    an earlier filing's (facts holds the newest filing's note figures only, so there is nothing to re-point to), and a
    row with no filing date (transcript, CFO commentary, gathered) is dropped because its date is not on the row."""
    from ..release.taxonomy import deep_link
    day = parse_day(day)
    pit = {(r["ticker"], r["period"]): r for r in as_of(con, day, tickers) if r["field"] == "capex"}
    ids = {i for r in pit.values() for i in split_ids(r["extraction_ids"])}
    cells = {e["extraction_id"]: e for e in _rows(con, "select e.extraction_id, e.table_id, e.row_label, e.cell_text, d.url from extractions e join documents d on d.accession = e.accession where e.extraction_id in (select unnest(?))", list(ids))} if ids else {}
    out = []
    for r in rows:
        if r.get("measure") == "spent" and r.get("category") == "capex":
            p = pit.get((r["ticker"], r["fiscal_year"]))
            if p is None:
                continue
            cell = cells.get((split_ids(p["extraction_ids"]) or [""])[0]) or {}
            same = p["accession"] == r.get("accession")
            out.append({**r, "value": p["value"], "source": p["extraction_ids"], "accession": p["accession"], "filed": p["filed"], "source_table": cell.get("table_id"),
                        "source_url": deep_link(cell.get("url"), cell.get("row_label"), cell.get("cell_text")), "has_value": True,
                        "check": r["check"] if same else "not_checked", "check_method": r["check_method"] if same else "none", "as_of": day})
        elif r.get("filed") and str(r["filed"]) <= day:
            out.append({**r, "as_of": day})
    return out
