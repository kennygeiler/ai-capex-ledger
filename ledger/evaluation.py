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


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% Wilson score interval on a proportion; None when n = 0."""
    if not n:
        return None
    p, z2 = k / n, z * z
    centre = (p + z2 / (2 * n)) / (1 + z2 / n)
    half = z * ((p * (1 - p) / n + z2 / (4 * n * n)) ** 0.5) / (1 + z2 / n)
    return (round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3))


def _band(rows: list[dict]) -> dict:
    """n, agree, the Wilson interval on the agreement rate, and the error distribution on eq entries."""
    errs = sorted(abs(r["error"]) for r in rows if r["relation"] == "eq" and r["error"] is not None)
    q = statistics.quantiles(errs, n=4) if len(errs) >= 2 else None
    return {"n": len(rows), "agree": sum(r["outcome"] == "agree" for r in rows), "agree_ci": wilson(sum(r["outcome"] == "agree" for r in rows), len(rows)),
            "median_abs_error": statistics.median(errs) if errs else None, "iqr_abs_error": (round(q[0], 3), round(q[2], 3)) if q else None, "n_eq": len(errs)}


def load(path: Path = GOLD) -> list[dict]:
    entries = yaml.safe_load(path.read_text()) if path.exists() else []
    for e in entries or []:
        for k in ("ticker", "period", "field", "measure", "relation", "value", "basis", "source", "by"):
            if k not in e:
                raise ValueError(f"gold entry {e.get('ticker')} {e.get('period')} lacks {k}")
        if e.get("scope", "same") not in SCOPES:
            raise ValueError(f"gold entry {e['ticker']} {e['period']}: scope must be one of {SCOPES}")
        if e["measure"] not in ("share", "amount") or e["relation"] not in ("eq", "ge", "le") or not e["source"].get("url"):
            raise ValueError(f"gold entry {e['ticker']} {e['period']}: measure, relation or source url out of range")
    return entries or []


SCOPES = ("same", "narrower", "wider", "not_comparable")
WINDOW = {"share": 0.15, "amount": 0.5}  # how far a wider measure may sit above a narrower one and still be consistent


def comparable(e: dict, mine: float) -> tuple[str, str]:
    """The comparability rule (docs/PROOF.md). A gold entry says how its scope relates to ours: `narrower` (the stated
    figure measures a subset of what our method measures, e.g. servers against all technical infrastructure), `wider`,
    `same`, or `not_comparable` (a planning floor, a different basis). A disagreement in the expected direction and
    inside the window is `consistent`; a not-comparable entry is `not_comparable`. Both are explained, not open."""
    scope, ref, w = e.get("scope", "same"), e["value"], WINDOW[e["measure"]]
    if scope == "not_comparable":
        return "not_comparable", e.get("scope_note") or "the reference measures something else"
    above = (mine - ref) if e["measure"] == "share" else (mine - ref) / ref
    if scope == "narrower" and 0 <= above <= w:
        return "consistent", f"ours is the wider measure, {above:.0%} above the narrower stated figure, inside the {w:.0%} window" if e["measure"] == "share" else f"ours is the wider measure, {above:.0%} above the narrower stated figure"
    if scope == "wider" and -w <= above <= 0:
        return "consistent", f"ours is the narrower measure, {-above:.0%} below the wider stated figure, inside the window"
    return "disagree", (f"scope {scope}: outside the window" if scope != "same" else "")


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
        if outcome == "disagree":
            outcome, note = comparable(e, mine)
            row["note"] = note
        rows.append({**row, "scope": e.get("scope", "same"), "ours": mine, "outcome": outcome, "error": err})
    from .config import industry
    for r in rows:
        r["layer"] = industry(r["ticker"])
    with_est = [r for r in rows if r["outcome"] != "no_estimate"]
    explained = sum(r["outcome"] in ("consistent", "not_comparable") for r in with_est)
    group = lambda key: {k: _band([r for r in with_est if r[key] == k]) for k in sorted({r[key] for r in with_est})}
    n = len(rows)
    return {"n": n, "with_estimate": len(with_est), "agree": sum(r["outcome"] == "agree" for r in with_est),
            "disagree": sum(r["outcome"] == "disagree" for r in with_est), "no_estimate": n - len(with_est), "explained": explained,
            "agree_ci": wilson(sum(r["outcome"] == "agree" for r in with_est), len(with_est)), "overall": _band(with_est),
            "eq_entries": sum(r["relation"] == "eq" for r in rows), "bands": group("method"), "layers": group("layer"), "fields": group("field"), "rows": rows}


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
    ci = lambda b: "—" if not b.get("agree_ci") else f"{b['agree_ci'][0]:.0%}–{b['agree_ci'][1]:.0%}"
    err = lambda b: "—" if b["median_abs_error"] is None else f"{b['median_abs_error']:.0%}" + (f" (IQR {b['iqr_abs_error'][0]:.0%}–{b['iqr_abs_error'][1]:.0%})" if b.get("iqr_abs_error") else "") + f" n={b['n_eq']}"
    o = ev.get("overall") or {}
    lines += ["", f"Agreement rate {ev['agree']}/{ev['with_estimate']}, 95% Wilson interval {ci(o)}. The interval is the honest width at this sample size; "
              f"it narrows as the reference set grows. Error on entries that state a figure: median {err(o)}.", ""]
    for title, key, name in (("Error band by method", "bands", "Method"), ("By layer", "layers", "Layer"), ("By field", "fields", "Field")):
        lines += [f"## {title}", "", f"| {name} | n | agree | 95% interval | abs error on eq entries (median, IQR) |", "|---|---|---|---|---|"]
        for m, b in sorted((ev.get(key) or {}).items()):
            lines.append(f"| {m} | {b['n']} | {b['agree']} | {ci(b)} | {err(b)} |")
        lines.append("")
    lines += ["", "Sources, one per entry:", ""] + [f"- {r['ticker']} {r['period']}: {r['source']['quote']} ({r['source']['url']}, {r['source'].get('date', '')})" for r in ev["rows"]] + [""]
    return "\n".join(lines)
