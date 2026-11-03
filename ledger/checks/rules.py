"""The rule registry. Each rule lives in rules/<id>.yaml (what it checks, why, how severe, which check function and
parameters). This module holds the check functions and the engine that runs them and writes `exceptions`.

A check receives a Context (plain lists and dicts, so tests can build one by hand) and returns Findings. The engine
adds the rule's id and severity and a stable exception id, so the same finding on the same inputs is the same row.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from datetime import date, timedelta
from pathlib import Path

import yaml

from ..core import config
from ..core.store import ROOT

RULES_DIR = ROOT / "rules"
REQUIRED = ("id", "description", "rationale", "severity", "check", "owner", "title", "plain", "action")


@dataclass
class Finding:
    ticker: str
    message: str
    field: str | None = None
    period: str | None = None
    subject: str | None = None


@dataclass
class Context:
    """Everything a rule may look at, for the companies being checked."""
    values: list[dict]                       # rows of the `values` table
    extractions: list[dict]                  # rows of `extractions`
    reference: dict = field(default_factory=dict)   # (ticker, field, period) -> reference row
    parsed: dict = field(default_factory=dict)      # accession -> parsed document (statements)
    years: list[str] = field(default_factory=list)
    tickers: list[str] = field(default_factory=list)  # every company asked for, including any with no 10-K
    ai_spend: list[dict] = field(default_factory=list)  # rows of `ai_spend` (what the MD&A says about AI's part)
    definitions: dict = field(default_factory=dict)   # per-company definitions (definitions/companies.yaml)
    documents: list[dict] = field(default_factory=list)  # rows of `documents` (accession, ticker, form, period, income_tables, cash_flow_tables)
    today: date = field(default_factory=date.today)   # coverage: a year whose 10-K isn't due yet isn't missing
    rules: list = field(default_factory=list)          # the loaded rules; `explains` re-runs the rule it explains (run() fills it)
    facts: list[dict] = field(default_factory=list)          # rows of `facts` (T92: the readings and the ties judge the note figures)
    note_extractions: list[dict] = field(default_factory=list)  # rows of `note_extractions`, with the filing date (`filed`)
    totals: dict = field(default_factory=dict)               # (accession, concept, end) -> the filing's tagged company total (ties.instance_totals)


def _days(e: dict) -> int:
    return (date.fromisoformat(e["period_end"]) - date.fromisoformat(e["period_start"])).days + 1


CHECKS = {}


def check(name):
    def deco(fn):
        CHECKS[name] = fn
        return fn
    return deco


# ── checks on what the agent read ──────────────────────────────────────────────────────────────────────────────────
@check("citation_resolves")
def _citation(ctx: Context, p: dict):
    """Every extracted cell, whether or not it reaches a released value."""
    from ..extract.extract import Invalid, resolve
    out = []
    for e in ctx.extractions:
        doc = ctx.parsed.get(e["accession"])
        try:
            if doc is None:
                raise Invalid(f"filing {e['accession']} has no parsed document")
            resolve({"field": e["field"], "table_id": e["table_id"], "row_label": e["row_label"], "column_label": e["column_label"],
                     "cell_text": e["cell_text"], "value": e["value"]}, doc)
        except Invalid as x:
            out.append(Finding(e["ticker"], f"citation for {e['period_start']}..{e['period_end']} does not resolve: {x.reason}", e["field"], None, e["extraction_id"]))
    return out


@check("unit_from_document")
def _unit_doc(ctx, p):
    return [Finding(e["ticker"], f"unit '{e['unit_stated']}' is not stated with the table; taken from elsewhere in the filing", e["field"], None, e["extraction_id"])
            for e in ctx.extractions if e["unit_source"] == "document"]


@check("period_length")
def _period(ctx, p):
    out = []
    full = {(e["ticker"], e["accession"], e["field"]) for e in ctx.extractions if 350 <= _days(e) <= 380}
    for e in ctx.extractions:
        d = _days(e)
        if d < 350 and ((ctx.parsed.get(e["accession"]) or {}).get("form") == "10-KT" or (e["ticker"], e["accession"], e["field"]) in full):
            continue  # a transition period (10-KT) or a short comparative column beside a full-year one (Hut 8's July to December 2023, type 64); reconcile never ships it as a fiscal year
        if not 350 <= d <= 380:
            out.append(Finding(e["ticker"], f"period {e['period_start']}..{e['period_end']} is {d} days, not a fiscal year", e["field"], None, e["extraction_id"]))
    return out


@check("column_matches_period")
def _column_period(ctx, p):
    """The cited column's label agrees with the period the value claims: its end date (or year) and its length."""
    spans = {"three": 3, "six": 6, "nine": 9, "twelve": 12, "year": 12}
    out = []
    for e in ctx.extractions:
        label, end = e["column_label"], date.fromisoformat(e["period_end"])
        m = re.search(r"([A-Z][a-z]{2})[a-z]*\.? (\d{1,2}), (\d{4})", label)
        stated = date(int(m.group(3)), MONTHS.index(m.group(1)) + 1, int(m.group(2))) if m else None
        years = [int(y) for y in re.findall(r"\b(20\d\d)\b", label)]
        span = re.search(r"(three|six|nine|twelve) months|year", label, re.I)
        months = round(_days(e) / 30.4)
        named = {end.year} | ({end.year - 1} if end.month == 1 and end.day <= 7 else set())  # a 52/53-week year ending 2 Jan 2021 is "2020"
        if stated and stated != end or not stated and years and not (set(years) & named):
            out.append(Finding(e["ticker"], f"column '{label}' does not match the claimed period end {end}", e["field"], None, e["extraction_id"]))
        elif span and spans[span.group(1 if span.group(1) else 0).lower()] != months:
            out.append(Finding(e["ticker"], f"column '{label}' does not match the claimed length of {months} months", e["field"], None, e["extraction_id"]))
    return out


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@check("row_label_switch")
def _row_switch(ctx, p):
    """The row an agent cites for a field should be the same across a company's filings. A change may be a renamed
    line, or the agent picking a different line. Cost lines are several rows by design and may be renamed between
    filings, so for them the check is that every year in one filing uses the same set of lines, each once."""
    out, seen, lines = [], {}, {}
    for e in sorted(ctx.extractions, key=lambda e: (e["ticker"], e["field"], e["accession"])):
        if e["field"] == "cost_of_revenue_part":
            lines.setdefault((e["ticker"], e["accession"]), {}).setdefault(e["period_end"], []).append(e["row_label"])
            continue
        k = (e["ticker"], e["field"])
        label = re.sub(r"\s+", " ", e["row_label"].strip().lower())
        seen.setdefault(k, {}).setdefault(label, []).append(e["accession"])
    for (t, f), labels in seen.items():
        if len(labels) > 1:
            desc = "; ".join(f"'{l}' in {len(a)} filing(s)" for l, a in sorted(labels.items(), key=lambda kv: -len(kv[1])))
            out.append(Finding(t, f"{f} is read from different rows across filings: {desc}", f))
    for (t, accn), by_year in lines.items():
        sets = {tuple(sorted(ls)) for ls in by_year.values()}
        if len(sets) > 1 or any(len(set(ls)) < len(ls) for ls in by_year.values()):
            desc = "; ".join(f"{end}: {', '.join(sorted(ls))}" for end, ls in sorted(by_year.items()))
            out.append(Finding(t, f"cost lines differ between years of {accn}: {desc}", "cost_of_revenue_part", None, accn))
    return out


@check("cost_lines_summed")
def _cost_lines(ctx, p):
    """No total cost-of-revenue line, so cost lines the agent classified were added up: list them for review. Quiet
    for a company whose definition already names every line the agent used."""
    from ..review.definitions import cost_lines
    lines = {}
    for e in ctx.extractions:
        if e["field"] == "cost_of_revenue_part":
            lines.setdefault(e["ticker"], {}).setdefault(e["row_label"], set()).add(e["accession"])
    lines = {t: ls for t, ls in lines.items() if not ((known := cost_lines(ctx.definitions, t)) and set(ls) <= known)}
    def gaps(t):  # how far opex built this way is from the SEC figure, so the size of the judgement is visible
        out = []
        for v in sorted(ctx.values, key=lambda v: v["period"]):
            r = ctx.reference.get((t, "opex", v["period"]))
            if v["ticker"] == t and v["field"] == "opex" and v["label"] == "definition_gap" and r and r["value"]:
                out.append(f"{v['period']} {v['value'] / 1e6:,.1f}M vs {r['value'] / 1e6:,.1f}M ({(v['value'] - r['value']) / abs(r['value']):+.0%})")
        return f". Opex vs SEC data: {', '.join(out)}" if out else ""
    return [Finding(t, "cost of revenue is the sum of: " + "; ".join(f"'{l}' ({len(a)} filing{'s' * (len(a) > 1)})" for l, a in sorted(ls.items())) + gaps(t),
                    "cost_of_revenue") for t, ls in lines.items()]


@check("definition_note")
def _definition(ctx, p):
    """Lines whose wording shows they measure more or less than the field's definition (e.g. capex that includes intangibles)."""
    pats = [(f, re.compile(rx, re.I)) for f, rx in p.get("patterns", {}).items()]
    found = {}
    for e in ctx.extractions:
        for f, rx in pats:
            if e["field"] == f and rx.search(e["row_label"]):
                found.setdefault((e["ticker"], f, e["row_label"]), 0)
                found[(e["ticker"], f, e["row_label"])] += 1
    return [Finding(t, f"{f} is read from '{label}' ({n} values), which differs from the field definition; note it when comparing companies", f)
            for (t, f, label), n in found.items()]


# Any revenue line, not only the total (APLD's "Hosting revenue"), but never an expense line that mentions sales ("Cost of
# sales", "Sales and marketing", "Selling, general and administrative"). A bank's income statement has no revenue line:
# its top lines are interest and noninterest income, which count.
REVENUE_LIKE = re.compile(
    r"^(?!.*\bcost of\b)(?!.*\bsales and marketing\b)(?!.*\bselling\b)(?!.*\bmarketing and sales\b).*\b(revenues?|sales)\b"
    r"|\b(total |net )?interest income\b|\bnon-?interest income\b", re.I)


def _tables(s: str) -> set[str]:
    return {t.strip() for t in (s or "").split(",") if t.strip()}


@check("statement_tables_distinct")
def _statement_tables(ctx, p):
    """The locator named a different table for the income statement than for the cash-flow statement, and the income
    table it named has a revenue-like row. Amazon's four 10-Ks had income_tables == cash_flow_tables (type 73), so the
    reader was never shown the income statement. A 10-K/A whose only located table is not an income statement is the
    amendment guard's case (proof.amendment_without_statements), not this rule's."""
    out = []
    for d in ctx.documents:
        inc, cf = d.get("income_tables") or "", d.get("cash_flow_tables") or ""
        if not inc:
            continue
        shared = _tables(inc) & _tables(cf)
        if shared:  # the same table named for both statements, wholly or in part ("t0034,t0035" against "t0034")
            both = ", ".join(sorted(shared))
            out.append(Finding(d["ticker"], f"{d.get('form')} {d.get('period')}: income_tables and cash_flow_tables are both {both}: the income statement was not located", None, None, d["accession"]))
            continue
        if not cf and str(d.get("form", "")).endswith("/A"):
            continue
        tables = ((ctx.parsed.get(d["accession"]) or {}).get("statements") or {}).get("income") or []
        labels = [r["label"] for t in tables for r in t.get("rows", [])]
        if tables and not any(REVENUE_LIKE.search(l) for l in labels):
            out.append(Finding(d["ticker"], f"{d.get('form')} {d.get('period')}: the located income statement ({inc}) has no revenue-like row", None, None, d["accession"]))
    return out


# ── arithmetic checks, using independently read cells ──────────────────────────────────────────────────────────────


@check("statement_tie")
def _tie(ctx, p):
    """In each parsed income statement: revenue − cost of revenue − total operating expenses = operating income, for every
    column. Reads the table directly, so it also catches parser and table-choice errors. Skipped when the statement
    has no total-operating-expenses line (the rule says so)."""
    rx = {k: re.compile(v, re.I) for k, v in p["labels"].items()}
    out = []
    for acc, doc in ctx.parsed.items():
        ticker = doc["ticker"]
        for t in doc["statements"]["income"] or []:
            rows, at, body = {}, {}, t["rows"]
            for i, r in enumerate(body):
                for k, pat in rx.items():
                    # A "Total …" line replaces a component matched earlier (APLD lists "Revenue" above "Total revenue").
                    if pat.search(r["label"]) and (k not in rows or r["label"].lower().startswith("total")):
                        rows[k], at[k] = {c["col"]: c["value"] for c in r["cells"]}, i
            if len(rows) < 4:
                continue
            # Operating lines outside the operating-expenses block, as shown (impairments, gains on sales: Core Scientific):
            # between cost of revenue and the block's heading, and between its total and operating income.
            heads = [i for i in range(at["cost_of_revenue"] + 1, at["total_opex"]) if not body[i]["cells"]]
            between = [body[i] for i in [*range(at["cost_of_revenue"] + 1, heads[-1] if heads else at["cost_of_revenue"] + 1),
                                         *range(at["total_opex"] + 1, at["operating_income"])]
                       if body[i]["cells"] and not re.search(r"gross (profit|margin)", body[i]["label"], re.I)]
            for col in rows["revenue"]:
                vals = [rows[k].get(col) for k in ("revenue", "cost_of_revenue", "total_opex", "operating_income")]
                if None in vals:
                    continue
                r, c, o, oi = vals
                x = sum(v for b in between for cc in b["cells"] if cc["col"] == col and (v := cc["value"]) is not None)
                # Total operating expenses either excludes cost of revenue or includes it (CoreWeave); both layouts tie.
                gap = min(r - abs(c) - abs(o) + x - oi, r - abs(o) + x - oi, r - abs(c) - abs(o) - oi, r - abs(o) - oi, key=abs)
                if abs(gap) > p.get("tolerance_cells", 1):
                    out.append(Finding(ticker, f"{t['id']} column '{t['columns'][col]}': revenue {r:,} − cost {abs(c):,} − operating expenses {abs(o):,} ≠ operating income {oi:,} (gap {gap:+,} in table units)", None, None, acc))
    return out


# ── checks on the released values ─────────────────────────────────────────────────────────────────────────────────
@check("sign")
def _sign(ctx, p):
    nonneg = set(p["non_negative"])
    return [Finding(v["ticker"], f"{v['field']} is {v['value']:,}; it should never be negative", v["field"], v["period"])
            for v in ctx.values if v["value"] is not None and v["field"] in nonneg and v["value"] < 0]


@check("jump")
def _jump(ctx, p):
    ratio = p.get("ratio", 3)
    by = {}
    for v in ctx.values:
        if v["value"] is not None:
            by.setdefault((v["ticker"], v["field"]), {})[v["period"]] = v["value"]
    out = []
    for (t, f), s in by.items():
        qs = sorted(s)
        for a, b in zip(qs, qs[1:]):
            x, y = s[a], s[b]
            if x and y and x > 0 and y > 0 and (y / x > ratio or x / y > ratio):
                out.append(Finding(t, f"{f} moves {y / x:.2f}× from {a} ({x:,}) to {b} ({y:,})", f, b))
    return out


def first_periods(values: list[dict]) -> dict:
    """{ticker: the earliest fiscal year any `values` row of it holds}: the year its 10-Ks start. A year before it is no
    10-K's to show (`no_10k_yet` names it); `coverage` and the checklist's completeness line (proof.missing_from_dataset,
    T81) both skip it, so they never disagree about such a year."""
    first = {}
    for v in values:
        first[v["ticker"]] = min(first.get(v["ticker"], v["period"]), v["period"])
    return first


@check("coverage")
def _coverage(ctx, p):
    """A year after the company's newest 10-K is not missing while that 10-K isn't due yet: the fiscal year hasn't
    ended, or ended less than `filing_days` ago, nor a year before the company's first `values` row (first_periods). The
    fields are config.RELEASE_FIELDS (params may narrow them in a test). A row counts as present when it carries a value or a stated reason
    (`not_reported`: the company has no such line and XBRL none either); a null `not_extracted` row is a missing value
    (T65: the finding then takes that row's state, open). `not_reported` over an XBRL value is no reason (T81: the
    checklist's "Answer-key values missing from the dataset" counts the same cell), so the finding fires on it."""
    have = {(v["ticker"], v["field"], v["period"]) for v in ctx.values if v["value"] is not None or (
        v.get("label") == "not_reported" and (ctx.reference.get((v["ticker"], v["field"], v["period"])) or {}).get("value") is None)}
    tickers = sorted({v["ticker"] for v in ctx.values} | {e["ticker"] for e in ctx.extractions})
    newest = {}
    for v in ctx.values:
        if v.get("period_end") and v["period"] > newest.get(v["ticker"], ("",))[0]:
            newest[v["ticker"]] = (v["period"], date.fromisoformat(v["period_end"]))

    def not_due(t, q):
        if t not in newest or q <= newest[t][0]:
            return False
        last, end = newest[t]
        due = end.replace(year=end.year + int(q[2:]) - int(last[2:])) + timedelta(days=p.get("filing_days", 90))
        return due > ctx.today

    first = first_periods(ctx.values)
    fields = p.get("fields") or config.RELEASE_FIELDS  # one list (T81): what a release ships, as the completeness line reads it; a test may narrow it
    return [Finding(t, f"no {f} value for {q}", f, q) for t in tickers for f in fields for q in ctx.years
            if (t, f, q) not in have and not not_due(t, q) and q >= first.get(t, q)]


@check("no_10k_yet")
def _no_10k(ctx, p):
    """Years no 10-K can show, named by code: the company has filed no 10-K at all (newly public), or the year is
    before its first 10-K (it wasn't public, or filed a different annual form, such as a foreign issuer's 20-F)."""
    first = first_periods(ctx.values)
    out = [Finding(t, f"{t} has filed no 10-K for any year from {ctx.years[0]} on (it may be newly public)") for t in ctx.tickers if t not in first]
    for t, f in sorted(first.items()):
        out += [Finding(t, f"no 10-K shows {q}: the company's 10-Ks start at {f}", None, q) for q in ctx.years if q < f]
    return out


@check("restated")
def _restated(ctx, p):
    """The same field and period read from two filings with different values: a restatement (or a misread). The latest
    filing wins in derivation; this keeps the change visible. Cost lines (cost_of_revenue_part) are compared line by
    line: a company with several cost lines has several values for one period, which is not a restatement."""
    by, years = {}, {(v["ticker"], str(v.get("period_end"))): v["period"] for v in ctx.values}
    for e in ctx.extractions:
        line = e["row_label"] if e["field"] == "cost_of_revenue_part" else None
        by.setdefault((e["ticker"], e["field"], e["period_start"], e["period_end"], line), []).append(e)
    out = []
    for (t, f, s, en, line), es in by.items():
        # one filing in thousands, a later one in millions is rounding, not a restatement (config.RESTATEMENT_TOLERANCE)
        if config.restated(min(x["value"] for x in es), max(x["value"] for x in es), max(x["scale"] for x in es)):
            parts = ", ".join(f"{x['value']:,} ({x['accession']})" for x in sorted(es, key=lambda x: x["accession"]))
            what = f"{f} ({line})" if line else f
            fy = years.get((t, en))  # the fiscal year, so a person sees which year changed
            out.append(Finding(t, f"{what} {fy or ''} {s}..{en} differs between filings: {parts}".replace("  ", " "), f, fy, f"{s}..{en}"))
    return out


@check("xbrl_reconcile")
def _xbrl(ctx, p):
    out = []
    for v in ctx.values:
        if v["label"] == "unresolved":
            r = ctx.reference.get((v["ticker"], v["field"], v["period"]))
            ref = f"{r['value']:,}" if r else "no XBRL value"
            out.append(Finding(v["ticker"], f"agent {v['value']:,} vs XBRL {ref}", v["field"], v["period"]))
    return out


@check("outlier_vs_own_history")
def _outlier(ctx, p):
    """capex ÷ revenue more than `factor`× away from the company's own median for the window."""
    factor = p.get("factor", 2)
    V = {(v["ticker"], v["field"], v["period"]): v["value"] for v in ctx.values if v["value"]}
    out = []
    for t in sorted({k[0] for k in V}):
        ratios = {q: V[(t, "capex", q)] / V[(t, "revenue", q)] for (tt, f, q) in V if tt == t and f == "capex" and (t, "revenue", q) in V}
        if len(ratios) < 4:
            continue
        med = sorted(ratios.values())[len(ratios) // 2]
        for q, r in sorted(ratios.items()):
            if med and (r / med > factor or med / r > factor):
                out.append(Finding(t, f"capex ÷ revenue is {r:.1%} in {q}, vs a median of {med:.1%} for the window", "capex", q))
    return out


# ── the note figures: readings across filings and ties to the tagged total (T92, ledger/checks/ties.py) ────────────────────
@check("readings_differ")
def _readings_differ(ctx, p):
    """An untagged note figure (facts.label no_reference) printed by two or more 10-Ks with values that differ by more
    than config.RESTATEMENT_TOLERANCE. The newest filing wins in the dataset; this keeps the disagreement open, because
    nothing on file says which reading is right (a tagged fact has the restatement guard and its tag instead)."""
    from .ties import differ, differ_message, readings_of
    by_id = {e["extraction_id"]: e for e in ctx.note_extractions}
    out = []
    for f in ctx.facts:
        if f.get("label") != "no_reference":
            continue
        rs = readings_of(f, by_id)
        if differ(rs):
            out.append(Finding(f["ticker"], f"{f['field']} {f['dimension'] or ''} {f['period']}: {differ_message(rs)}".replace("  ", " "), f["field"], f["period"], f["dimension"] or ""))
    return out


@check("segment_basis_mixed")
def _segment_basis(ctx, p):
    """A segment series (segment_revenue, segment_capex) whose fiscal years come from filings on both sides of a
    re-segmentation (ties.segment_basis): a later 10-K printed a segment figure differently, and a year the dataset
    ships is from a filing before it. One finding per field and year in ctx.years, subject the cutover filing. Nothing
    is changed and no basis is picked: a person decides."""
    from .ties import basis_message, segment_basis
    years = set(ctx.years or [])
    out = []
    for s in segment_basis(ctx.facts, ctx.note_extractions, tuple(p.get("fields") or ("segment_revenue", "segment_capex"))):
        for q in s["mixed"]:
            if years and q not in years:
                continue
            out.append(Finding(s["ticker"], basis_message(s, q), s["field"], q, s["cutover"]["accession"]))
    return out


TIE_CHECK_NAME = "parts_tie"


@check(TIE_CHECK_NAME)
def _parts_tie(ctx, p):
    """The parts one filing prints for a note field and a date sum to the company total the same filing tags in its XBRL
    instance (params: field, concepts in order, pick first or largest), within ties.tolerance. Fires on a group that does
    not tie, naming the filing; a group with no tagged total is not judged. A segment set that leaves out a reconciling
    line (corporate, eliminations, hedging) does not tie, and the finding says so; nothing is added to force it."""
    from .ties import fail_message, groups
    return [Finding(g["ticker"], fail_message(g), g["field"], g["period"], g["accession"])
            for g in groups(TIE_CHECK_NAME, p, ctx.facts, ctx.note_extractions, ctx.totals) if not g["holds"]]


# ── judgement encoded as a rule (T36) ──────────────────────────────────────────────────────────────────────────────
EXPLAIN_CONDITIONS = ("row_labels",)  # the closed vocabulary of what an `explains` rule may test; each names rows exactly
EXPLAIN_PARAMS = {"rule", "field", "condition"}
# The warn rules an `explains` rule may target: only those whose finding is about which line was read (a label-driven
# finding). A value-driven rule (jump, outlier_vs_own_history, coverage) is never explainable once for every year: one
# explanation would close every future real spike. Widen this list on purpose, with a test.
EXPLAINABLE = ("row_label_switch",)


def label_key(s: str) -> str:
    """A row label as row_label_switch compares it: whitespace collapsed, lower case."""
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def lines_read(extractions: list[dict], ticker: str, field_: str) -> list[str]:
    """Every row label the company's `field_` was read from, across its filings, one per label_key, sorted."""
    out = {}
    for e in extractions:
        label = (e.get("row_label") or "").strip()
        if e["ticker"] == ticker and e["field"] == field_ and label:  # a NULL or blank label names nothing
            out.setdefault(label_key(label), label)
    return sorted(out.values(), key=label_key)


@check("explains")
def _explains(ctx, p):
    """A person's explanation, written once as a rule (T36): every finding of the warn rule `rule` on `field` whose
    company reads that field from exactly the lines named in `condition.row_labels` (the same set, compared as
    label_key; a subset or a superset is a different cause) is explained. The finding is re-emitted with the same ticker, field, period and subject, so status joins it to the
    finding it explains (`explained`). Never a pattern: a label is matched whole, so the rule names its rows exactly."""
    target = next((r for r in ctx.rules if r["id"] == p["rule"]), None)
    if target is None:
        return []  # load() refuses a rule that names no rule on file; a hand-built list without it explains nothing
    want = {label_key(l) for l in p["condition"]["row_labels"]}
    out = []
    for f in CHECKS[target["check"]](ctx, target["params"]):
        if f.field != p["field"]:
            continue
        read = {label_key(l) for l in lines_read(ctx.extractions, f.ticker, f.field)}
        if read and read == want:
            out.append(Finding(f.ticker, f"explains {p['rule']}: {f.field} is read from exactly the lines the rule names ({'; '.join(sorted(read))})", f.field, f.period, f.subject))
    return out


def _check_explains(rules: list[dict]) -> None:
    """An `explains` rule names exactly what it matches (T36): info severity; params rule, field and condition and
    nothing else; `rule` a warn rule on file in EXPLAINABLE (an info finding is explained already, a block is never
    explained by a note, a value-driven finding never once for every year); `field` one field; a condition from
    EXPLAIN_CONDITIONS with a non-empty list of whole labels; `by` a person (status.is_person) and the same as `owner`.
    A rule whose params have the explains shape (rule and condition) must have check explains, so a hand edit of
    `check` cannot keep the shape and drop these checks. Raises ValueError."""
    from ..core.status import is_person
    by_id = {r["id"]: r for r in rules}
    for r in rules:
        if r["check"] != "explains":
            if {"rule", "condition"} <= set(r["params"]):
                raise ValueError(f"{r['id']}.yaml: params name a rule and a condition, the shape of an explains rule, but check is {r['check']!r}")
            continue
        p, name = r["params"], f"{r['id']}.yaml"
        if not is_person(r.get("by")) or r.get("by") != r.get("owner"):
            raise ValueError(f"{name}: an explains rule's by must be a person on config.PEOPLE and the same as owner, not {r.get('by')!r}")
        if r["severity"] != "info":
            raise ValueError(f"{name}: an explains rule is info severity")
        if set(p) != EXPLAIN_PARAMS:
            raise ValueError(f"{name}: an explains rule's params are exactly {sorted(EXPLAIN_PARAMS)}")
        t = by_id.get(p["rule"])
        if not t or t["check"] == "explains" or t["severity"] != "warn" or p["rule"] not in EXPLAINABLE:
            raise ValueError(f"{name}: params.rule must name a label-driven warn rule on file ({', '.join(EXPLAINABLE)}), not {p['rule']!r}")
        if not isinstance(p["field"], str) or not p["field"].strip():
            raise ValueError(f"{name}: params.field must name one field")
        c = p["condition"]
        if not isinstance(c, dict) or not c or set(c) - set(EXPLAIN_CONDITIONS):
            raise ValueError(f"{name}: params.condition must be one of {EXPLAIN_CONDITIONS}")
        labels = c.get("row_labels")
        if not isinstance(labels, list) or not labels or not all(isinstance(l, str) and l.strip() for l in labels):
            raise ValueError(f"{name}: condition.row_labels must be a non-empty list of whole labels")


def explained(exceptions: list[dict], rules: list[dict] | None = None) -> dict:
    """{(rule it explains, ticker, field, period, subject): the explains rule's id} over `exceptions` (rows of the
    table), for the info findings of the explains rules on file. Proof's values stage and Reconcile's queue read it, so
    one rule closes the same finding on both pages. None and '' are one key part."""
    targets = {r["id"]: r["params"]["rule"] for r in (load() if rules is None else rules) if r["check"] == "explains"}
    out = {}
    for e in sorted(exceptions, key=lambda e: e["rule_id"]):
        if e.get("severity") == "info" and e["rule_id"] in targets:
            out.setdefault(explain_key(targets[e["rule_id"]], e["ticker"], e.get("field"), e.get("period"), e.get("subject")), e["rule_id"])
    return out


def explain_key(rule_id, ticker, field_, period, subject) -> tuple:
    return (rule_id or "", ticker or "", field_ or "", period or "", subject or "")


# ── engine ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def load(rules_dir: Path | None = None) -> list[dict]:
    rules = []
    for f in sorted(Path(rules_dir or RULES_DIR).glob("*.yaml")):
        r = yaml.safe_load(f.read_text())
        check_rule(r, f.name)
        r["file_sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        rules.append(r)
    _check_explains(rules)
    return rules


def check_rule(r: dict, name: str) -> None:
    """One rule file's own checks (load runs them on every file; the T36 writer on the file it is about to write).
    Fills params with {} when absent. Raises ValueError naming the file."""
    f = Path(name)
    if not isinstance(r, dict):
        raise ValueError(f"{f.name}: not a mapping")
    missing = [k for k in REQUIRED if not r.get(k)]
    if missing:
        raise ValueError(f"{f.name}: missing {missing}")
    if r["severity"] not in ("block", "warn", "info"):
        raise ValueError(f"{f.name}: severity must be block, warn or info")
    if r["check"] not in CHECKS:
        raise ValueError(f"{f.name}: unknown check '{r['check']}' (known: {sorted(CHECKS)})")
    if r["id"] != f.stem:
        raise ValueError(f"{f.name}: id '{r['id']}' must match the file name")
    r["params"] = r.get("params") or {}


def run(ctx: Context, rules: list[dict]) -> list[dict]:
    """Every rule over the context. Returns exception rows, sorted, with stable ids."""
    if not ctx.rules:
        ctx = replace(ctx, rules=rules)
    rows = {}
    for r in rules:
        for fnd in CHECKS[r["check"]](ctx, r["params"]):
            key = "|".join(str(x) for x in (r["id"], fnd.ticker, fnd.field, fnd.period, fnd.subject))
            rows[key] = {"exception_id": key, "rule_id": r["id"], "severity": r["severity"], "ticker": fnd.ticker,
                         "field": fnd.field, "period": fnd.period, "subject": fnd.subject, "message": fnd.message,
                         "input_hash": hashlib.sha256(json.dumps([fnd.message, r["file_sha256"]]).encode()).hexdigest()[:16]}
    return [rows[k] for k in sorted(rows)]
