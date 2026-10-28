"""Fault injection: corrupt one real extraction at a time, the way agents misread statements, and see what catches it.

Each fault yields one outcome: no_effect (the extraction doesn't reach a released value), rule (a block or warn rule
fires), xbrl_only (only the XBRL comparison disagrees), or escaped (a released value changed and nothing fired).
"""
import copy
import re

from .reconcile import values_for
from .rules import Context, run


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


FAULTS = {f.__name__: f for f in (wrong_column, stale_column, wrong_row, wrong_scale, sign_flip, misread_digits)}


def inject(ticker, extractions, reference, fye, docs, ctx: Context, rules) -> list[dict]:
    """One trial per (fault, extraction). Returns rows: fault, extraction_id, outcome, caught_by."""
    base_vals = {(v["field"], v["period"]): v["value"] for v in values_for(ticker, extractions, reference, fye, docs)}
    # An exception counts as new if its id or its content changed: a fault can change an exception that was already open.
    base_exc = {(x["exception_id"], x["input_hash"]) for x in run(ctx, rules)}
    out = []
    for name, fault in FAULTS.items():
        for i, e in enumerate(extractions):
            bad = fault(e, ctx.parsed[e["accession"]])
            if bad is None:
                continue
            xs = copy.copy(extractions)
            xs[i] = bad
            vals = values_for(ticker, xs, reference, fye, docs)
            changed = any(base_vals.get((v["field"], v["period"])) != v["value"] for v in vals)
            new = [x for x in run(Context(vals, xs, ctx.reference, ctx.parsed, ctx.years), rules)
                   if (x["exception_id"], x["input_hash"]) not in base_exc and x["severity"] != "info"]
            rules_hit = sorted({x["rule_id"] for x in new if x["rule_id"] != "xbrl_reconcile"})
            outcome = "rule" if rules_hit else "xbrl_only" if new else "escaped" if changed else "no_effect"
            out.append({"fault": name, "extraction_id": e["extraction_id"], "outcome": outcome, "caught_by": rules_hit})
    return out
