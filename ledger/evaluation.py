"""How wrong is the attribution? Scored against gold/ai_capex.yaml, a reference set of sourced figures: what the
company itself, or an independent source, said AI's part of capex was.

For each reference entry: our attribution row for that company, field and year, or "no estimate"; then the
comparison the entry allows (equal within tolerance, at least, at most). The report gives coverage (how many
reference points we have a number for), agreement, and the error on the entries that state a figure, by method, so
every method carries an error band with the sample size it rests on. A small set is said to be small."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

import yaml

from .store import ROOT

GOLD = ROOT / "gold" / "ai_capex.yaml"
OUT = ROOT / "reports" / "evaluation.json"
TOL = 0.10  # an "eq" entry agrees when ours is within 10% of it, relative


def load(path: Path = GOLD) -> list[dict]:
    entries = yaml.safe_load(path.read_text()) if path.exists() else []
    for e in entries or []:
        for k in ("ticker", "period", "field", "measure", "relation", "value", "basis", "source", "by"):
            if k not in e:
                raise ValueError(f"gold entry {e.get('ticker')} {e.get('period')} lacks {k}")
        if e["measure"] not in ("share", "amount") or e["relation"] not in ("eq", "ge", "le") or not e["source"].get("url"):
            raise ValueError(f"gold entry {e['ticker']} {e['period']}: measure, relation or source url out of range")
    return entries or []


def score(entries: list[dict], attribution: list[dict], capex: dict) -> dict:
    """attribution: rows (ticker, field, period, kind, method, ai_amount, ai_share, confidence). capex: (ticker, period) -> value."""
    ours = {(a["ticker"], a["field"], a["period"]): a for a in attribution if a["kind"] == "actual"}
    rows = []
    for e in entries:
        a = ours.get((e["ticker"], e["field"], e["period"]))
        row = {"ticker": e["ticker"], "period": e["period"], "field": e["field"], "measure": e["measure"], "relation": e["relation"], "reference": e["value"],
               "basis": e["basis"], "source": e["source"], "method": a["method"] if a else None, "confidence": a["confidence"] if a else None}
        if not a or a["ai_amount"] is None:
            rows.append({**row, "ours": None, "outcome": "no_estimate", "error": None})
            continue
        mine = a["ai_share"] if e["measure"] == "share" else a["ai_amount"]
        if mine is None:
            rows.append({**row, "ours": None, "outcome": "no_estimate", "error": None})
            continue
        err = (mine - e["value"]) / e["value"] if e["value"] else None
        if e["relation"] == "eq":
            outcome = "agree" if abs(err) <= TOL else "disagree"
        elif e["relation"] == "ge":
            outcome = "agree" if mine >= e["value"] * (1 - TOL) else "disagree"
        else:
            outcome = "agree" if mine <= e["value"] * (1 + TOL) else "disagree"
        rows.append({**row, "ours": mine, "outcome": outcome, "error": err})
    by_method = {}
    for r in rows:
        if r["outcome"] == "no_estimate":
            continue
        m = by_method.setdefault(r["method"], {"n": 0, "agree": 0, "errors": []})
        m["n"] += 1
        m["agree"] += r["outcome"] == "agree"
        if r["relation"] == "eq" and r["error"] is not None:
            m["errors"].append(abs(r["error"]))
    bands = {m: {"n": v["n"], "agree": v["agree"], "median_abs_error": statistics.median(v["errors"]) if v["errors"] else None, "n_eq": len(v["errors"])}
             for m, v in by_method.items()}
    n = len(rows)
    with_est = [r for r in rows if r["outcome"] != "no_estimate"]
    return {"n": n, "with_estimate": len(with_est), "agree": sum(r["outcome"] == "agree" for r in with_est),
            "disagree": sum(r["outcome"] == "disagree" for r in with_est), "no_estimate": n - len(with_est),
            "eq_entries": sum(r["relation"] == "eq" for r in rows), "bands": bands, "rows": rows}


def render(ev: dict) -> str:
    lines = ["# Evaluation: the attribution against the reference set", "",
             f"{ev['n']} reference entries (gold/ai_capex.yaml), each a sourced figure or bound for AI's part of capex. "
             f"We have a number for {ev['with_estimate']}: {ev['agree']} agree, {ev['disagree']} disagree; {ev['no_estimate']} have no estimate from us. "
             f"Only {ev['eq_entries']} entries state a figure rather than a bound, so the error band is a first measurement, not a statistic.", "",
             "| Company | Year | Reference | Ours | Method | Outcome | What the reference measures |", "|---|---|---|---|---|---|---|"]
    fmt = lambda r, v: ("—" if v is None else f"{v:.0%}" if r["measure"] == "share" else f"${v / 1e9:,.1f}B")
    rel = {"eq": "", "ge": "≥ ", "le": "≤ "}
    for r in ev["rows"]:
        lines.append(f"| {r['ticker']} | {r['period']} | {rel[r['relation']]}{fmt(r, r['reference'])} | {fmt(r, r['ours'])} | {r['method'] or '—'} | {r['outcome'].replace('_', ' ')} | {r['basis']} |")
    lines += ["", "## Error band by method", "", "| Method | n | agree | median abs error (eq entries) |", "|---|---|---|---|"]
    for m, b in sorted(ev["bands"].items()):
        band = "—" if b["median_abs_error"] is None else f"{b['median_abs_error']:.0%} (n={b['n_eq']})"
        lines.append(f"| {m} | {b['n']} | {b['agree']} | {band} |")
    lines += ["", "Sources, one per entry:", ""] + [f"- {r['ticker']} {r['period']}: {r['source']['quote']} ({r['source']['url']}, {r['source'].get('date', '')})" for r in ev["rows"]] + [""]
    return "\n".join(lines)
