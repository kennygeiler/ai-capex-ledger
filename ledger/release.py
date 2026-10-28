"""T90–T94: a release is a folder of plain files whose content hash a person signs. It is built only when every gate passes."""
import csv
import hashlib
import io
import json

GATES = {
    "G1": "Every filing ended in a valid output or a logged failure, and no failure is open",
    "G4": "No block exception without a current decision",
    "G5": "Every released value hand-checked against its filing, none marked wrong",
}


def gates(values, open_items, handcheck) -> dict:
    """{gate: [failing items]}; empty lists mean the gate passes."""
    checked = {(h["ticker"], h["field"], h["cal_q"]): h for h in (handcheck or {}).get("values", [])}
    return {
        "G1": [e["exception_id"] for e in open_items if e["rule_id"] == "extraction_failed"],
        "G4": [e["exception_id"] for e in open_items if e["severity"] == "block"],
        "G5": ["no hand-check file"] if handcheck is None else
              [f"{v['ticker']} {v['field']} {v['cal_q']}" for v in values
               if not checked.get((v["ticker"], v["field"], v["cal_q"]), {}).get("verified")],
    }


def build(version, values, extractions, exceptions, previous) -> dict:
    """Release files as {name: text}. No timestamps inside, so the same inputs give the same hash (G7)."""
    ext = {e["extraction_id"]: e for e in extractions}
    rows = sorted(values, key=lambda v: (v["ticker"], v["field"], v["cal_q"]))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["ticker", "field", "cal_q", "fiscal_period", "value", "source", "xbrl", "citations"])
    for v in rows:
        cites = " ; ".join(f"{e['accession']} {e['table_id']} '{e['row_label']}' / '{e['column_label']}' = {e['cell_text']}"
                           for i in (v["extraction_ids"] or "").split(",") if (e := ext.get(i)))
        w.writerow([v["ticker"], v["field"], v["cal_q"], v["fiscal_period"], "" if v["value"] is None else v["value"], v["source"], v["label"], cites])
    notes = [e for e in exceptions if e["severity"] == "info"]
    quality = "\n".join([f"# {version}", "",
                         f"{len(rows)} values · {sum(v['source'] == 'agent' for v in rows)} from agents · "
                         f"{sum(v['source'] == 'override' for v in rows)} overridden · {sum(v['source'] == 'missing' for v in rows)} missing · "
                         f"{sum(v['label'] == 'agree' for v in rows)} agree with XBRL", "",
                         "All gates passed: " + "; ".join(f"{g} {d}" for g, d in GATES.items()) + ".", "",
                         "## Notes", ""] + [f"- {e['ticker']} {e['field'] or ''}: {e['message']}" for e in notes] + [""])
    prev = {(r["ticker"], r["field"], r["cal_q"]): r["value"] for r in previous or []}
    changes = [f"- {v['ticker']} {v['field']} {v['cal_q']}: {prev[(v['ticker'], v['field'], v['cal_q'])] or 'missing'} → {v['value'] or 'missing'} ({v['source']})"
               for v in rows if (v["ticker"], v["field"], v["cal_q"]) in prev and str(prev[(v["ticker"], v["field"], v["cal_q"])]) != str(v["value"] or "")]
    diff = "\n".join([f"# Changes in {version}", ""] + (["First release."] if previous is None else changes or ["No values changed."]) + [""])
    return {"values.csv": buf.getvalue(), "QUALITY.md": quality, "DIFF.md": diff}


def content_hash(files: dict) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
