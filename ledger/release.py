"""T90–T94: a release is a folder of plain files whose content hash a person signs. It is built only when every gate passes."""
import csv
import hashlib
import io
import json
import random

from .config import GOLDEN_SEED

SPOT_CHECKS = 10  # random XBRL-agreeing values a person also checks, to test that the agreement itself works

GATES = {
    "G1": "Every filing ended in a valid output or a logged failure, and no failure is open",
    "G4": "No block exception without a current decision",
    "G5": "Every value XBRL can't vouch for, plus a random sample of those it can, hand-checked at the value being released",
}


def to_check(values) -> dict:
    """{(ticker, field, period): why} for the values a person checks. A value that agrees with XBRL is verified by two
    independent sources; the rest, and a fixed random sample of the agreeing ones, go to a person."""
    k = lambda v: (v["ticker"], v["field"], v["period"])
    have = sorted((v for v in values if v["value"] is not None), key=k)
    agree = [v for v in have if v["label"] == "agree"]
    return {**{k(v): "xbrl_differs" for v in have if v["label"] != "agree"},
            **{k(v): "spot_check" for v in random.Random(GOLDEN_SEED).sample(agree, min(SPOT_CHECKS, len(agree)))}}


def gates(values, open_items, handcheck) -> dict:
    """{gate: [failing items]}; empty lists mean the gate passes."""
    checked = {(h["ticker"], h["field"], h["period"]): h for h in (handcheck or {}).get("values", [])}
    return {
        "G1": [e["exception_id"] for e in open_items if e["rule_id"] == "extraction_failed"],
        "G4": [e["exception_id"] for e in open_items if e["severity"] == "block"],
        "G5": ["no hand-check file"] if handcheck is None else
              [f"{v['ticker']} {v['field']} {v['period']}" for v in values if (v["ticker"], v["field"], v["period"]) in to_check(values)
               and (not (h := checked.get((v["ticker"], v["field"], v["period"]), {})).get("verified") or h.get("value") != v["value"])],
    }


def build(version, values, extractions, exceptions, previous) -> dict:
    """Release files as {name: text}. No timestamps inside, so the same inputs give the same hash (G7)."""
    ext = {e["extraction_id"]: e for e in extractions}
    rows = sorted(values, key=lambda v: (v["ticker"], v["field"], v["period"]))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["ticker", "field", "period", "period_end", "value", "basis", "first_reported", "source", "xbrl", "citations"])
    for v in rows:
        cites = " ; ".join(f"{e['accession']} {e['table_id']} '{e['row_label']}' / '{e['column_label']}' = {e['cell_text']}"
                           for i in (v["extraction_ids"] or "").split(",") if (e := ext.get(i)))
        w.writerow([v["ticker"], v["field"], v["period"], v["period_end"], "" if v["value"] is None else v["value"], v["basis"],
                    "" if v["first_reported"] is None else v["first_reported"], v["source"], v["label"], cites])
    notes = [e for e in exceptions if e["severity"] == "info"]
    quality = "\n".join([f"# {version}", "",
                         f"{len(rows)} values · {sum(v['source'] == 'agent' for v in rows)} from agents · "
                         f"{sum(v['source'] == 'override' for v in rows)} overridden · {sum(v['source'] == 'missing' for v in rows)} missing · "
                         f"{sum(v['label'] == 'agree' for v in rows)} agree with XBRL · {sum(v['basis'] == 'restated' for v in rows)} on a restated basis · "
                         f"{sum(v['label'] == 'not_reported' for v in rows)} blank because the company reports no such line", "",
                         check_line(rows), "",
                         "All gates passed: " + "; ".join(f"{g} {d}" for g, d in GATES.items()) + ".", "",
                         "## Notes", ""] + [f"- {e['ticker']} {e['field'] or ''}: {e['message']}" for e in notes] + [""])
    prev = {(r["ticker"], r["field"], r["period"]): r["value"] for r in previous or []}
    changes = [f"- {v['ticker']} {v['field']} {v['period']}: {prev[(v['ticker'], v['field'], v['period'])] or 'missing'} → {v['value'] or 'missing'} ({v['source']})"
               for v in rows if (v["ticker"], v["field"], v["period"]) in prev and str(prev[(v["ticker"], v["field"], v["period"])]) != str(v["value"] or "")]
    diff = "\n".join([f"# Changes in {version}", ""] + (["First release."] if previous is None else changes or ["No values changed."]) + [""])
    return {"values.csv": buf.getvalue(), "QUALITY.md": quality, "DIFF.md": diff}


def check_line(values) -> str:
    c = to_check(values)
    spot = sum(w == "spot_check" for w in c.values())
    agree = sum(v["label"] == "agree" and v["value"] is not None for v in values)
    return (f"Verified: {agree - spot} values by two independent sources (the 10-K cell and XBRL agree); {len(c)} hand-checked by a person "
            f"against the filing: {len(c) - spot} that XBRL can't vouch for and {spot} random spot-checks of the XBRL-agreeing values.")


def content_hash(files: dict) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
