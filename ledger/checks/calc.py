"""A figure calculated from several cells says so: opex is revenue − cost of revenue − operating income (reconcile.values_for),
read from three or more cells of one 10-K column. For every such value this gives the formula, each input with its role,
the arithmetic on the real inputs, and the cross-checks: the filing's own printed total (a "Total operating expenses" row
in the same table and column) and the SEC's XBRL value. A cross-check that differs names the line that explains the
difference when one line of the table, or one input, is exactly that amount.

One function (`for_ticker`) feeds the trail's cards and the gold set, so a calculated figure never reads two ways. The
cross-check's state is states.CROSSCHECK (`crosscheck`): matches, explained (the filing's own total differs by exactly
one formula input, sign-aware, and by no other line: Amazon's total includes cost of sales), differs (a line is named
only when exactly one line, sign-aware, is that amount; SEC XBRL is compared with the inputs only), or none (no total in
that table and column, no XBRL value). The arithmetic is recomputed from the inputs here, never copied from the stored
value: when the two disagree, `holds` is False and the page shows the stored value; when the rounded terms would not
add up, every term prints to the dollar."""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..core import store
from ..core.config import rounding_unit

# the formula per calculated field: (input field, sign, role on the page), in the order the arithmetic reads
FORMULAS = {"opex": ("revenue − cost of revenue − operating income",
                     (("revenue", 1, "Revenue"), ("cost_of_revenue", -1, "Cost of revenue"), ("cost_of_revenue_part", -1, "Cost of revenue"),
                      ("operating_income", -1, "Operating income")))}
# the filing's own printed total of the same measure: the whole label, normalised (a "Total costs and expenses" line also
# holds cost of revenue: it is another measure, never this cross-check)
OWN_TOTAL = {"opex": re.compile(r"^total operating expenses$")}
DOCS = store.ROOT / "data" / "docs"


def _norm(s: str | None) -> str:
    return " ".join((s or "").lower().split())


def _tol(scales: list[int], n: int, ref: int | None = None) -> int:
    """Half a rounding unit per input: the tolerance reconcile.values_for uses (n inputs rounded on their own)."""
    return max(list(scales) + ([rounding_unit(ref)] if ref is not None else [])) // 2 * max(1, n)


def state(ours: int, other: int | None, tol: int, explained: bool = False) -> str:
    """states.CROSSCHECK (M18): none (nothing printed or tagged to compare), matches (within rounding), explained (the other
    total differs by exactly one formula input, sign-aware, and by no other line: `explained` says so), differs."""
    if other is None:
        return "none"
    if abs(ours - other) <= tol:
        return "matches"
    return "explained" if explained else "differs"


def _lines(gap: int, inputs: list[dict], table: dict | None, col: int | None, scale: int, tol: int, skip: str | None = None) -> list[dict]:
    """Every line whose amount is the gap (the other total minus ours), sign-aware. An input explains it when the other
    total leaves out what the formula does with it: gap = −sign × value (a cost we subtract that the other total counts
    in). Another row of the same table column explains it when the other total adds it: gap = +value. One entry per line
    label; `exact` when the amounts are equal to the dollar."""
    out, seen = [], set()
    for i in inputs:
        want = -i["sign"] * i["value"]
        if abs(gap - want) <= tol and _norm(i["row"]) not in seen:
            seen.add(_norm(i["row"]))
            out.append({"row": i["row"], "value": i["value"], "input": True, "exact": gap == want})
    if table is not None and col is not None:
        for r in table.get("rows", []):
            lab = _norm(r.get("label"))
            if lab in seen or lab == _norm(skip):
                continue
            c = next((c for c in r.get("cells", []) if c.get("col") == col and c.get("value") is not None), None)
            v = int(round(c["value"] * scale)) if c and c["value"] else None
            if v is not None and abs(gap - v) <= tol:
                seen.add(lab)
                out.append({"row": r.get("label"), "value": v, "input": False, "exact": gap == v})
    return out


def _shown(v: int) -> int:
    """The amount `money` prints, in dollars: whole millions, tenths of a million half up, or the exact figure."""
    a = abs(int(v))
    if a >= 1_000_000 and a % 1_000_000:
        a = (a + 50_000) // 100_000 * 100_000
    return a if v >= 0 else -a


def exact(v: int) -> str:
    from ..web.cards import exact as ex
    return ex(v)


def _table(cik: int | None, accession: str, table_id: str, root: Path | None = None) -> dict | None:
    if cik is None:
        return None
    p = (root or DOCS) / f"{int(cik):010d}" / f"{accession}.tables.json"
    try:
        doc = json.loads(p.read_text())
    except (OSError, ValueError):
        return None
    return next((t for t in doc.get("tables", []) if t.get("id") == table_id), None)


def calculation(field: str, value: int | None, cells: list[dict], reference: int | None = None, table: dict | None = None) -> dict | None:
    """The calculation behind one value. cells: its extractions (extraction_id, field, row_label, column_label, value,
    scale, table_id); reference: the SEC XBRL value; table: the parsed statement table the cells sit in (for the
    filing's own total). None when the field is not calculated or fewer than two cells back it."""
    from ..web.cards import money
    if field not in FORMULAS or len(cells) < 2:
        return None
    words, parts = FORMULAS[field]
    order = {f: (k, sign, role) for k, (f, sign, role) in enumerate(parts)}
    use = sorted((c for c in cells if c.get("field") in order and c.get("value") is not None), key=lambda c: (order[c["field"]][0], c.get("row_label") or ""))
    inputs = [{"extraction_id": c["extraction_id"], "field": c["field"], "role": order[c["field"]][2], "sign": order[c["field"]][1], "row": c.get("row_label"),
               "value": int(c["value"]), "scale": int(c.get("scale") or 1)} for c in use]
    result = sum(i["sign"] * i["value"] for i in inputs)
    # the arithmetic as printed: "$611.3M − ($396.9M + $56.8M) − (−$236.5M) = $394.1M"; when the rounded terms would
    # not add up to the rounded result, every term to the dollar instead
    groups, k = [], 0
    while k < len(inputs):
        g = [x for x in inputs[k:] if x["field"] == inputs[k]["field"]]
        groups.append(g)
        k += len(g)
    fits = sum(x["sign"] * _shown(x["value"]) for g in groups for x in g) == _shown(result)
    fmt = money if fits else exact

    def term(n, g):
        txt = " + ".join(fmt(x["value"]) for x in g)
        txt = f"({txt})" if len(g) > 1 or g[0]["value"] < 0 else txt
        return ("" if not n else " − " if g[0]["sign"] < 0 else " + ") + txt
    arithmetic = "".join(term(n, g) for n, g in enumerate(groups)) + f" = {fmt(result)}"
    scales = [i["scale"] for i in inputs]
    tol = _tol(scales, len(inputs))
    checks = []
    col, own, own_row, own_text = None, None, None, None
    if table is not None and use:
        cols = [_norm(c) for c in table.get("columns", [])]
        want = _norm(use[0].get("column_label"))
        col = cols.index(want) if want in cols else None
        rx = OWN_TOTAL.get(field)
        row = next((r for r in table.get("rows", []) if rx and rx.match(_norm(r.get("label")))), None) if col is not None else None
        cell = next((c for c in (row or {}).get("cells", []) if c.get("col") == col and c.get("value") is not None), None)
        if cell is not None:
            own, own_row, own_text = int(round(cell["value"] * max(scales))), row.get("label"), cell.get("text")
    # the filing's own total: none when the table, its column or the row is missing; the one check that can read explained
    checks.append(_check("filing", own, result, tol, own_row, inputs, table, col, max(scales), own_text))
    # SEC XBRL: compared with the inputs only (no table row stands for an XBRL concept)
    checks.append(_check("xbrl", None if reference is None else int(reference), result, _tol(scales, len(inputs), reference), None, inputs, None, None, max(scales), None))
    return {"field": field, "formula": words, "inputs": inputs, "result": result, "value": value, "holds": value is not None and result == int(value),
            "line": f"Calculated: {words} = {money(result)}", "arithmetic": arithmetic, "exact": not fits, "checks": checks}


def _lower(s: str) -> str:
    return s[:1].lower() + s[1:] if s[1:2].islower() else s


def _check(against: str, other: int | None, ours: int, tol: int, row: str | None, inputs: list[dict], table, col, scale: int, text: str | None) -> dict:
    from ..core.states import word
    from ..web.cards import money
    label = "Filing’s own total" if against == "filing" else "SEC XBRL"
    out = {"against": against, "label": label, "row": row, "value": other, "cell_text": text, "state": "none", "diff": None, "by_line": None}
    if other is None:
        out["text"] = f"{label}: {word('crosscheck', 'none')}"
        return out
    gap = other - ours
    lines = [] if abs(gap) <= tol else _lines(gap, inputs, table, col, scale, tol, row)
    one = lines[0] if len(lines) == 1 else None  # a line is named only when it is the only one of that amount
    explained = against == "filing" and one is not None and one["input"] and one["exact"]
    st = state(ours, other, tol, explained)
    out.update(state=st, diff=ours - other, by_line=one and {"row": one["row"], "value": one["value"]})
    if st == "matches":
        out["text"] = f"{label}: {money(other)} · {word('crosscheck', 'matches')}" + (" within rounding" if gap else "")
    elif st == "explained":
        out["text"] = f"Filing’s total {word('crosscheck', 'explained')} {_lower(one['row'])} · {money(abs(one['value']))}"
    else:
        out["text"] = f"{label}: {money(other)} · {word('crosscheck', 'differs')} {money(abs(gap))}" + (f" · {one['row']} line" if one else "")
    return out


def for_ticker(con, ticker: str, root: Path | None = None) -> dict:
    """{(field, period): calculation} for every calculated value of a company, read from the database and the parsed
    tables on disk. The trail's cards and the gold set read this one function."""
    from ..core.ids import split_ids

    def rows(sql, *p):
        cur = con.execute(sql, list(p))
        return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    vals = [v for v in rows('select field, period, value, extraction_ids from "values" where ticker = ?', ticker) if v["field"] in FORMULAS]
    if not vals:
        return {}
    ext = {e["extraction_id"]: e for e in rows("select extraction_id, accession, field, table_id, row_label, column_label, cell_text, value, scale from extractions where ticker = ?", ticker)}
    ref = {(r["field"], r["period"]): r["value"] for r in rows("select field, period, value from reference_values where ticker = ?", ticker)}
    cik = {d["accession"]: d["cik"] for d in rows("select accession, cik from documents where ticker = ?", ticker)}
    out, tables = {}, {}
    for v in vals:
        cells = [ext[i] for i in split_ids(v.get("extraction_ids") or "") if i in ext]  # a cost-line label may hold a comma
        if len(cells) < 2:
            continue
        key = (cells[0]["accession"], cells[0]["table_id"])
        if key not in tables:
            tables[key] = _table(cik.get(key[0]), *key, root=root)
        c = calculation(v["field"], v["value"], cells, ref.get((v["field"], v["period"])), tables[key])
        if c:
            out[(v["field"], v["period"])] = c
    return out
