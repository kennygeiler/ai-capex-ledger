"""Fault injection: corrupt real extractions the way agents misread statements, and see what catches it.

Six kinds change one cell of one extraction (wrong column, stale column, wrong row, wrong scale, sign flip, misread
digits). Three more (T67) plant the mistakes a one-cell change never showed: `omission` removes the cell, `wrong_table`
cites the other statement, `systematic` makes the same mistake in every year of a company at once.

Each trial yields one outcome: no_effect (the extraction doesn't reach a released value), rule (a block or warn rule
other than xbrl_reconcile fires), xbrl_only (only the XBRL comparison disagrees), or escaped (a released value changed
and nothing fired). `rule_set(rules, xbrl=False)` is the XBRL-off pass: the same trials with xbrl_reconcile removed,
so xbrl_only cannot occur and whatever XBRL alone caught reads escaped. `tally(rows)` counts a report's rows per kind.
"""
import copy
import re

from .reconcile import values_for
from .rules import Context, run

XBRL_RULE = "xbrl_reconcile"
OMIT = object()  # what a fault returns to drop the extraction instead of changing it
INCOME_FIELDS = {"revenue", "cost_of_revenue", "cost_of_revenue_part", "operating_income"}  # the rest (capex) are cash-flow lines
SYSTEMATIC_OF = ("wrong_row", "wrong_column", "wrong_scale")  # the one-cell kinds `systematic` applies to every year
SYSTEMATIC_MIN = 2  # a systematic trial needs at least this many years moved; one year is a one-cell fault


def _cells(doc, e):
    t = next(t for k in ("income", "cash_flow") for t in doc["statements"][k] or [] if t["id"] == e["table_id"])
    return t, [r for r in t["rows"] if r["label"] == e["row_label"]][0]


def _span(label):
    m = re.search(r"(three|six|nine|twelve) months|year", label, re.I)
    return m.group(0).lower() if m else ""


def _move(e, t, row, col):
    cell = next((c for c in row["cells"] if c["col"] == col), None)
    if not cell or not cell["value"]:
        return None
    v = round(cell["value"] * t["scale"])
    v = -v if e["field"] == "capex" else abs(v) if e["field"] == "cost_of_revenue" else v
    return {**e, "column_label": t["columns"][col], "cell_text": cell["text"], "value": v}


def wrong_column(e, doc):
    """A column covering a different length of period (six months read as three)."""
    t, row = _cells(doc, e)
    cols = [i for i, c in enumerate(t["columns"]) if _span(c) != _span(e["column_label"])]
    return next((m for i in cols if (m := _move(e, t, row, i))), None)


def stale_column(e, doc):
    """The same length of period, a year earlier (the comparative column)."""
    t, row = _cells(doc, e)
    cols = [i for i, c in enumerate(t["columns"]) if c != e["column_label"] and _span(c) == _span(e["column_label"])]
    return next((m for i in cols if (m := _move(e, t, row, i))), None)


def wrong_row(e, doc):
    """A neighbouring line in the same column (e.g. a financing line read as capex)."""
    t, row = _cells(doc, e)
    col = t["columns"].index(e["column_label"])
    i = t["rows"].index(row)
    for r in t["rows"][i + 1:] + t["rows"][:i][::-1]:
        if (m := _move({**e, "row_label": r["label"]}, t, r, col)):
            return m
    return None


def wrong_scale(e, doc):
    return {**e, "value": e["value"] * 1000}


def sign_flip(e, doc):
    return {**e, "value": -e["value"]}


def misread_digits(e, doc):
    """Two adjacent digits swapped in both the value and the cited text."""
    s = e["cell_text"]
    for i in range(len(s) - 1):
        if s[i].isdigit() and s[i + 1].isdigit() and s[i] != s[i + 1]:
            text = s[:i] + s[i + 1] + s[i] + s[i + 2:]
            return {**e, "cell_text": text, "value": int(round(float(re.sub(r"[^\d.]", "", text)) * e["scale"]))}
    return None


def omission(e, doc):
    """The reader returned nothing for this field in this filing: the cited cell is removed from the extraction set, so
    the company-year is built without it (a blank labelled not_reported, or an older filing's value where one exists).
    Simulates a reader that skipped a line, or a locator whose table had no such row (the AMZN revenue and opex blanks,
    T65). No cell changes, so citation, sign, period and tie rules see nothing wrong; the XBRL comparison reads values
    that exist and cannot see one that is missing. Since T65 the blank is labelled `not_extracted` (open) wherever XBRL
    tags the value, but that is a label, not a rule finding, so this report counts it as escaped; year-comparing rules
    (row_label_switch, jump, outlier) catch some omissions incidentally when an older filing's value fills the year. The
    intended catcher is the completeness check against the answer key (T81), not built yet."""
    return OMIT


def wrong_table(e, doc):
    """The locator picked the other statement: an income-statement citation is pointed at the cash-flow table's row in
    the same position (or a cash-flow citation at the income statement's), in the column with the same label where
    the other table has it, else the same position, so the cited cell exists and the citation resolves. Simulates
    `documents.income_tables == cash_flow_tables` (T65: AMZN), a locator that returned one table for both statements.
    In practice `row_label_switch` catches most of these (the swapped row's label differs from other years'), then the
    statement tie, sign and the XBRL comparison where the swapped cell breaks them. The T65 locator rule
    (`statement_tables_distinct`) guards the cause at ingest, on `documents`, which these trials do not change.""" 
    other = "cash_flow" if e["field"] in INCOME_FIELDS else "income"
    tables = doc["statements"].get(other) or []
    if not tables:
        return None
    t_from, row = _cells(doc, e)
    t = tables[0]
    col = t["columns"].index(e["column_label"]) if e["column_label"] in t["columns"] else t_from["columns"].index(e["column_label"])
    if col >= len(t["columns"]):
        return None
    i = min(t_from["rows"].index(row), len(t["rows"]) - 1)
    for r in t["rows"][i:] + t["rows"][:i]:
        if (m := _move({**e, "table_id": t["id"], "row_label": r["label"]}, t, r, col)):
            return m
    return None


def systematic(extractions, parsed):
    """The same mistake in every year of a company: one of wrong_row, wrong_column or wrong_scale applied to every
    extraction of one field at once, across all its filings, so a rule that compares years (jump, row_label_switch,
    outlier_vs_own_history, restated) sees a step only where a filing could not take the same mistake (a fallback, counted
    in the trial's detail as `fallbacks`); otherwise only a check that looks at each cell alone (citation, column, period,
    sign, tie) or an outside answer key (XBRL) can catch it. Simulates a reader that misreads a statement the
    same way every time, the error DISCIPLINES.md's model-risk audit named as the one a bank fears most. One trial per
    (field, variant), needing at least SYSTEMATIC_MIN years moved; for wrong_row the first filing's neighbouring line names
    the line read in every other filing (where that filing has it; else its own neighbour). Yields (extractions, detail)."""
    by_field = {}
    for i, e in enumerate(extractions):
        by_field.setdefault(e["field"], []).append(i)
    for f, idx in sorted(by_field.items()):
        for name in SYSTEMATIC_OF:
            xs, moved, label, fallbacks = list(extractions), [], None, 0
            for i in idx:
                e, doc = extractions[i], parsed[extractions[i]["accession"]]
                bad = (_same_row(e, doc, label) if label else None) if name == "wrong_row" else None
                if name == "wrong_row" and label and bad is None:
                    fallbacks += 1  # this filing has no line called `label`: it takes its own neighbour, not the same line
                bad = bad if bad is not None else FAULTS[name](e, doc)
                if bad is not None and bad is not OMIT:
                    xs[i] = bad
                    moved.append(e["extraction_id"])
                    label = label or bad["row_label"]  # the first filing's wrong line names the line for every other filing
            if len(moved) >= SYSTEMATIC_MIN:
                yield xs, {"extraction_id": moved[0], "variant": name, "field": f, "n": len(moved), "fallbacks": fallbacks}


def _same_row(e, doc, label):
    """The row called `label` in the extraction's own table and column, so every year reads the same wrong line."""
    t, _ = _cells(doc, e)
    col = t["columns"].index(e["column_label"])
    r = next((r for r in t["rows"] if r["label"] == label), None)
    return _move({**e, "row_label": label}, t, r, col) if r else None


systematic.company_wide = True

FAULTS = {f.__name__: f for f in (wrong_column, stale_column, wrong_row, wrong_scale, sign_flip, misread_digits, omission, wrong_table, systematic)}
OUTCOMES = ("rule", "xbrl_only", "no_effect", "escaped")
CAUGHT = ("rule", "xbrl_only")


def rule_set(rules: list[dict], xbrl: bool = True) -> list[dict]:
    """The rules a pass runs: every rule, or every rule but xbrl_reconcile (the XBRL-off pass)."""
    return list(rules) if xbrl else [r for r in rules if r["id"] != XBRL_RULE]


def trials(extractions, parsed):
    """Every trial of every kind: (kind, the corrupted extraction list, detail). A one-cell kind gives one trial per
    extraction it applies to; a company-wide kind decides its own trials. `detail` always names an `extraction_id`."""
    for name, fault in FAULTS.items():
        if getattr(fault, "company_wide", False):
            for xs, detail in fault(extractions, parsed):
                yield name, xs, detail
            continue
        for i, e in enumerate(extractions):
            bad = fault(e, parsed[e["accession"]])
            if bad is None:
                continue
            xs = copy.copy(extractions)
            if bad is OMIT:
                del xs[i]
            else:
                xs[i] = bad
            yield name, xs, {"extraction_id": e["extraction_id"]}


def inject(ticker, extractions, reference, fye, docs, ctx: Context, rules) -> list[dict]:
    """Every trial on one company. Returns rows: fault, extraction_id (systematic: variant, field, n too), outcome, caught_by."""
    base_vals = {(v["field"], v["period"]): v["value"] for v in values_for(ticker, extractions, reference, fye, docs, ctx.definitions)}
    # An exception counts as new if its id or its content changed: a fault can change an exception that was already open.
    base_exc = {(x["exception_id"], x["input_hash"]) for x in run(ctx, rules)}
    out = []
    for name, xs, detail in trials(extractions, ctx.parsed):
        vals = values_for(ticker, xs, reference, fye, docs, ctx.definitions)
        changed = {(v["field"], v["period"]): v["value"] for v in vals} != base_vals  # a value that moved or went missing
        new = [x for x in run(Context(vals, xs, ctx.reference, ctx.parsed, ctx.years, definitions=ctx.definitions), rules)
               if (x["exception_id"], x["input_hash"]) not in base_exc and x["severity"] != "info"]
        rules_hit = sorted({x["rule_id"] for x in new if x["rule_id"] != XBRL_RULE})
        outcome = "rule" if rules_hit else "xbrl_only" if new else "escaped" if changed else "no_effect"
        out.append({"fault": name, **detail, "outcome": outcome, "caught_by": rules_hit})
    return out


def rows_of(report) -> list[dict]:
    """The trial rows of a report file's content: the T67 shape is a dict with `rows`; older reports are the bare list."""
    return report["rows"] if isinstance(report, dict) else (report or [])


def tally(rows: list[dict]) -> dict:
    """Counts with denominators: {planted, caught, rule, xbrl_only, no_effect, escaped, by_kind: {kind: the same}}.
    caught = rule + xbrl_only; planted = caught + no_effect + escaped, overall and per kind."""
    def count(rs):
        t = {o: sum(r["outcome"] == o for r in rs) for o in OUTCOMES}
        return {"planted": len(rs), "caught": t["rule"] + t["xbrl_only"], **t}
    kinds = list(dict.fromkeys(r["fault"] for r in rows))
    return {**count(rows), "by_kind": {k: count([r for r in rows if r["fault"] == k]) for k in kinds}}
