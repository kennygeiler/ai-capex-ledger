"""T30: the rule registry. Each rule lives in rules/<id>.yaml (what it checks, why, how severe, which check function and
parameters). This module holds the check functions and the engine that runs them and writes `exceptions`.

A check receives a Context (plain lists and dicts, so tests can build one by hand) and returns Findings. The engine
adds the rule's id and severity and a stable exception id, so the same finding on the same inputs is the same row.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import yaml

from .store import ROOT

RULES_DIR = ROOT / "rules"
REQUIRED = ("id", "description", "rationale", "severity", "check", "owner")


@dataclass
class Finding:
    ticker: str
    message: str
    field: str | None = None
    cal_q: str | None = None
    subject: str | None = None


@dataclass
class Context:
    """Everything a rule may look at, for the companies being checked."""
    values: list[dict]                       # rows of the `values` table
    extractions: list[dict]                  # rows of `extractions`
    reference: dict = field(default_factory=dict)   # (ticker, field, cal_q) -> reference row
    parsed: dict = field(default_factory=dict)      # accession -> parsed document (statements)
    quarters: list[str] = field(default_factory=list)

    def ext_by_id(self):
        return {e["extraction_id"]: e for e in self.extractions}


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
    from .extract import Invalid, resolve
    out = []
    ids = ctx.ext_by_id()
    for v in ctx.values:
        if v["source"] != "agent":
            continue
        cited = [i for i in (v["extraction_ids"] or "").split(",") if i]
        if not cited:
            out.append(Finding(v["ticker"], "agent value has no citation", v["field"], v["cal_q"]))
        for i in cited:
            e = ids.get(i)
            if e is None:
                out.append(Finding(v["ticker"], f"value cites extraction {i!r}, which does not exist", v["field"], v["cal_q"]))
                continue
            doc = ctx.parsed.get(e["accession"])
            if doc is None:
                out.append(Finding(v["ticker"], f"cited filing {e['accession']} has no parsed document", v["field"], v["cal_q"]))
                continue
            try:
                resolve({"field": e["field"], "table_id": e["table_id"], "row_label": e["row_label"], "column_label": e["column_label"],
                         "cell_text": e["cell_text"], "value": e["value"]}, doc)
            except Invalid as x:
                out.append(Finding(v["ticker"], f"citation for {e['period_start']}..{e['period_end']} does not resolve: {x.reason}", v["field"], v["cal_q"], i))
    return out


@check("unit_from_document")
def _unit_doc(ctx, p):
    return [Finding(e["ticker"], f"unit '{e['unit_stated']}' is not stated with the table; taken from elsewhere in the filing", e["field"], None, e["extraction_id"])
            for e in ctx.extractions if e["unit_source"] == "document"]


@check("period_length")
def _period(ctx, p):
    ok = {3: (80, 100), 6: (170, 196), 9: (260, 287), 12: (350, 380)}
    out = []
    for e in ctx.extractions:
        d = _days(e)
        if not any(lo <= d <= hi for lo, hi in ok.values()):
            out.append(Finding(e["ticker"], f"period {e['period_start']}..{e['period_end']} is {d} days: not a quarter, half-year, nine months or year", e["field"], None, e["extraction_id"]))
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
        if stated and stated != end or not stated and years and end.year not in years:
            out.append(Finding(e["ticker"], f"column '{label}' does not match the claimed period end {end}", e["field"], None, e["extraction_id"]))
        elif span and spans[span.group(1 if span.group(1) else 0).lower()] != months:
            out.append(Finding(e["ticker"], f"column '{label}' does not match the claimed length of {months} months", e["field"], None, e["extraction_id"]))
    return out


MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


@check("row_label_switch")
def _row_switch(ctx, p):
    """The row an agent cites for a field should be the same across a company's filings. A change may be a renamed
    line, or the agent picking a different line."""
    out, seen = [], {}
    for e in sorted(ctx.extractions, key=lambda e: (e["ticker"], e["field"], e["accession"])):
        k = (e["ticker"], e["field"])
        label = re.sub(r"\s+", " ", e["row_label"].strip().lower())
        seen.setdefault(k, {}).setdefault(label, []).append(e["accession"])
    for (t, f), labels in seen.items():
        if len(labels) > 1:
            desc = "; ".join(f"'{l}' in {len(a)} filing(s)" for l, a in sorted(labels.items(), key=lambda kv: -len(kv[1])))
            out.append(Finding(t, f"{f} is read from different rows across filings: {desc}", f))
    return out


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


# ── arithmetic checks, using independently read cells ──────────────────────────────────────────────────────────────
@check("quarters_sum_to_ytd")
def _ytd(ctx, p):
    """Q1 + Q2 + Q3 three-month cells must equal the nine-month cell (and Q1 + Q2 the six-month cell). Both sides are
    read from filings, so this is an independent test. (A quarters-sum-to-year test would be circular here, because
    Q4 is derived as the year minus nine months.)"""
    out = []
    three = {}
    for e in ctx.extractions:
        if 80 <= _days(e) <= 100:
            three.setdefault((e["ticker"], e["field"], e["period_start"]), e)
    for e in ctx.extractions:
        d = _days(e)
        n = 3 if 260 <= d <= 287 else 2 if 170 <= d <= 196 else 0
        if not n:
            continue
        s, parts = date.fromisoformat(e["period_start"]), []
        for _ in range(n):
            q = three.get((e["ticker"], e["field"], s.isoformat()))
            if not q:
                break
            parts.append(q)
            s = date.fromisoformat(q["period_end"]) + timedelta(days=1)
        if len(parts) != n:
            continue
        total = sum(x["value"] for x in parts)
        tol = n * e["scale"] // 2 + e["scale"] // 2
        if abs(total - e["value"]) > tol:
            out.append(Finding(e["ticker"], f"{n} quarters sum to {total:,} but the {d}-day cell ({e['cell_text']}) says {e['value']:,} (diff {total - e['value']:+,})",
                               e["field"], None, e["extraction_id"]))
    return out


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
            rows = {}
            for r in t["rows"]:
                for k, pat in rx.items():
                    # A "Total …" line replaces a component matched earlier (APLD lists "Revenue" above "Total revenue").
                    if pat.search(r["label"]) and (k not in rows or r["label"].lower().startswith("total")):
                        rows[k] = {c["col"]: c["value"] for c in r["cells"]}
            if len(rows) < 4:
                continue
            for col in rows["revenue"]:
                vals = [rows[k].get(col) for k in ("revenue", "cost_of_revenue", "total_opex", "operating_income")]
                if None in vals:
                    continue
                r, c, o, oi = vals
                # Total operating expenses either excludes cost of revenue or includes it (CoreWeave); both layouts tie.
                gap = min(r - abs(c) - abs(o) - oi, r - abs(o) - oi, key=abs)
                if abs(gap) > p.get("tolerance_cells", 1):
                    out.append(Finding(ticker, f"{t['id']} column '{t['columns'][col]}': revenue {r:,} − cost {abs(c):,} − operating expenses {abs(o):,} ≠ operating income {oi:,} (gap {gap:+,} in table units)", None, None, acc))
    return out


# ── checks on the quarterly values ─────────────────────────────────────────────────────────────────────────────────
@check("sign")
def _sign(ctx, p):
    nonneg = set(p["non_negative"])
    return [Finding(v["ticker"], f"{v['field']} is {v['value']:,}; it should never be negative", v["field"], v["cal_q"])
            for v in ctx.values if v["value"] is not None and v["field"] in nonneg and v["value"] < 0]


@check("magnitude")
def _magnitude(ctx, p):
    V = {(v["ticker"], v["field"], v["cal_q"]): v["value"] for v in ctx.values if v["value"] is not None}
    out = []
    for (t, f, q), r in V.items():
        if f != "revenue":
            continue
        c, oi = V.get((t, "cost_of_revenue", q)), V.get((t, "operating_income", q))
        if c is not None and c > r:
            out.append(Finding(t, f"cost of revenue {c:,} exceeds revenue {r:,}", "cost_of_revenue", q))
        if c is not None and oi is not None and oi > r - c:
            out.append(Finding(t, f"operating income {oi:,} exceeds gross profit {r - c:,}", "operating_income", q))
    return out


@check("jump")
def _jump(ctx, p):
    ratio = p.get("ratio", 3)
    by = {}
    for v in ctx.values:
        if v["value"] is not None:
            by.setdefault((v["ticker"], v["field"]), {})[v["cal_q"]] = v["value"]
    out = []
    for (t, f), s in by.items():
        qs = sorted(s)
        for a, b in zip(qs, qs[1:]):
            x, y = s[a], s[b]
            if x and y and x > 0 and y > 0 and (y / x > ratio or x / y > ratio):
                out.append(Finding(t, f"{f} moves {y / x:.2f}× from {a} ({x:,}) to {b} ({y:,})", f, b))
    return out


@check("coverage")
def _coverage(ctx, p):
    have = {(v["ticker"], v["field"], v["cal_q"]) for v in ctx.values}
    tickers = sorted({v["ticker"] for v in ctx.values} | {e["ticker"] for e in ctx.extractions})
    return [Finding(t, f"no {f} value for {q}", f, q) for t in tickers for f in p["fields"] for q in ctx.quarters if (t, f, q) not in have]


@check("restated")
def _restated(ctx, p):
    """The same field and period read from two filings with different values: a restatement (or a misread). The latest
    filing wins in derivation; this keeps the change visible."""
    by = {}
    for e in ctx.extractions:
        by.setdefault((e["ticker"], e["field"], e["period_start"], e["period_end"]), []).append(e)
    out = []
    for (t, f, s, en), es in by.items():
        tol = max(x["scale"] for x in es) // 2  # one filing in thousands, a later one in millions is rounding, not a restatement
        if max(x["value"] for x in es) - min(x["value"] for x in es) > tol:
            parts = ", ".join(f"{x['value']:,} ({x['accession']})" for x in sorted(es, key=lambda x: x["accession"]))
            out.append(Finding(t, f"{f} {s}..{en} differs between filings: {parts}", f, None, f"{s}..{en}"))
    return out


@check("xbrl_reconcile")
def _xbrl(ctx, p):
    out = []
    for v in ctx.values:
        if v["label"] == "unresolved":
            r = ctx.reference.get((v["ticker"], v["field"], v["cal_q"]))
            ref = f"{r['value']:,}" if r else "no XBRL value"
            out.append(Finding(v["ticker"], f"agent {v['value']:,} vs XBRL {ref}", v["field"], v["cal_q"]))
    return out


@check("outlier_vs_own_history")
def _outlier(ctx, p):
    """capex ÷ revenue more than `factor`× away from the company's own median for the window."""
    factor = p.get("factor", 2)
    V = {(v["ticker"], v["field"], v["cal_q"]): v["value"] for v in ctx.values if v["value"]}
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


# ── engine ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def load(rules_dir: Path = RULES_DIR) -> list[dict]:
    rules = []
    for f in sorted(rules_dir.glob("*.yaml")):
        r = yaml.safe_load(f.read_text())
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
        r["file_sha256"] = hashlib.sha256(f.read_bytes()).hexdigest()
        rules.append(r)
    return rules


def run(ctx: Context, rules: list[dict]) -> list[dict]:
    """Every rule over the context. Returns exception rows, sorted, with stable ids."""
    rows = {}
    for r in rules:
        for fnd in CHECKS[r["check"]](ctx, r["params"]):
            key = "|".join(str(x) for x in (r["id"], fnd.ticker, fnd.field, fnd.cal_q, fnd.subject))
            rows[key] = {"exception_id": key, "rule_id": r["id"], "severity": r["severity"], "ticker": fnd.ticker,
                         "field": fnd.field, "cal_q": fnd.cal_q, "subject": fnd.subject, "message": fnd.message,
                         "input_hash": hashlib.sha256(json.dumps([fnd.message, r["file_sha256"]]).encode()).hexdigest()[:16]}
    return [rows[k] for k in sorted(rows)]
