"""A release is a folder of plain files whose content hash a person signs. It is built only when every gate passes."""
import csv
import hashlib
import io
import json
import random
from pathlib import Path

from .config import GOLDEN_SEED
from .store import ROOT

RELEASES = ROOT / "releases"

SPOT_CHECKS = 10  # random XBRL-agreeing values a person also checks, to test that the agreement itself works

GATES = {
    "G1": "Every filing ended in a valid output or a logged failure, and no failure is open",
    "G4": "No block exception without a current decision",
    "G5": "Every value XBRL can't vouch for, plus a random sample of those it can, confirmed on the filing at the value being released: by the re-read of the rendered 10-K, or by a person where it can't",
}


def version_key(name: str) -> list[int]:
    """v1.10.0 sorts after v1.9.0: by number, never by string."""
    return [int(x) for x in name.lstrip("v").split(".")]


def releases() -> list[Path]:
    """Every release folder, oldest version first."""
    return sorted(RELEASES.glob("v*"), key=lambda p: version_key(p.name))


def to_check(values) -> dict:
    """{(ticker, field, period): why} for the values a person checks. A value that agrees with XBRL is verified by two
    independent sources; the rest, and a fixed random sample of the agreeing ones, go to a person."""
    k = lambda v: (v["ticker"], v["field"], v["period"])
    have = sorted((v for v in values if v["value"] is not None), key=k)
    agree = [v for v in have if v["label"] == "agree"]
    return {**{k(v): "xbrl_differs" for v in have if v["label"] != "agree"},
            **{k(v): "spot_check" for v in random.Random(GOLDEN_SEED).sample(agree, min(SPOT_CHECKS, len(agree)))}}


def gates(values, open_items, handcheck, confirmed=frozenset()) -> dict:
    """{gate: [failing items]}; empty lists mean the gate passes. confirmed: extraction ids the rendered-10-K re-read
    found at their current cell text."""
    checked = {(h["ticker"], h["field"], h["period"]): h for h in (handcheck or {}).get("values", [])}
    machine = lambda v: bool(v["extraction_ids"]) and set(v["extraction_ids"].split(",")) <= set(confirmed)
    need = [v for v in values if (v["ticker"], v["field"], v["period"]) in to_check(values) and not machine(v)]
    return {
        "G1": [e["exception_id"] for e in open_items if e["rule_id"] == "extraction_failed"],
        "G4": [e["exception_id"] for e in open_items if e["severity"] == "block"],
        "G5": ["no hand-check file"] if need and handcheck is None else
              [f"{v['ticker']} {v['field']} {v['period']}" for v in need
               if not (h := checked.get((v["ticker"], v["field"], v["period"]), {})).get("verified") or h.get("value") != v["value"]],
    }


def ai_spend_csv(rows: list[dict]) -> str:
    """What each 10-K says about AI's part of capex and opex: one row per company, field, fiscal year and kind."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["ticker", "field", "period", "kind", "scope", "class", "amount_low", "amount_high", "share", "ai_amount", "accession", "quote"])
    for a in sorted(rows, key=lambda a: (a["ticker"], a["field"], a["period"], a["kind"])):
        w.writerow([a["ticker"], a["field"], a["period"], a["kind"], a["scope"], a["class"], a["amount_low"] or "", a["amount_high"] or "",
                    "" if a["share"] is None else a["share"], "" if a["ai_amount"] is None else a["ai_amount"], a["accession"], a["quote"]])
    return buf.getvalue()


def facts_csv(rows: list[dict]) -> str:
    """Facts from the notes: segment capex and revenue, PP&E by category, finance lease liabilities, purchase commitments."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["ticker", "field", "dimension", "period", "period_end", "value", "basis", "first_reported", "xbrl", "xbrl_value", "accession"])
    for f in sorted(rows, key=lambda f: (f["ticker"], f["field"], f["dimension"], f["period"])):
        w.writerow([f["ticker"], f["field"], f["dimension"], f["period"], f["period_end"], f["value"], f["basis"], f["first_reported"], f["label"],
                    "" if f["reference"] is None else f["reference"], f["accession"]])
    return buf.getvalue()


def build(version, values, extractions, exceptions, previous, confirmed=frozenset(), ai_spend=(), facts=()) -> dict:
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
                         ai_line(list(ai_spend)), "", facts_line(list(facts)), "",
                         check_line(rows, confirmed), "",
                         "All gates passed: " + "; ".join(f"{g} {d}" for g, d in GATES.items()) + ".", "",
                         "## Notes", ""] + [f"- {e['ticker']} {e['field'] or ''}: {e['message']}" for e in notes] + [""])
    prev = {(r["ticker"], r["field"], r["period"]): r["value"] for r in previous or []}
    changes = [f"- {v['ticker']} {v['field']} {v['period']}: {prev[(v['ticker'], v['field'], v['period'])] or 'missing'} → {v['value'] or 'missing'} ({v['source']})"
               for v in rows if (v["ticker"], v["field"], v["period"]) in prev and str(prev[(v["ticker"], v["field"], v["period"])]) != str(v["value"] or "")]
    added = {}
    for v in rows:
        if previous is not None and (v["ticker"], v["field"], v["period"]) not in prev:
            added[v["ticker"]] = added.get(v["ticker"], 0) + 1
    body = ["First release."] if previous is None else (changes or ["No values changed."]) + (
        ["", f"Added: {sum(added.values())} values for {', '.join(sorted(added))}."] if added else [])
    diff = "\n".join([f"# Changes in {version}", ""] + body + [""])
    return {"values.csv": buf.getvalue(), "facts.csv": facts_csv(list(facts)), "ai_spend.csv": ai_spend_csv(list(ai_spend)), "QUALITY.md": quality, "DIFF.md": diff,
            "README.md": readme(version, rows, list(ai_spend))}


def facts_line(rows: list[dict]) -> str:
    return (f"Facts from the notes (facts.csv): {len(rows)} values for {len({f['ticker'] for f in rows})} companies: "
            + ", ".join(f"{sum(f['field'] == k for f in rows)} {k}" for k in ("segment_capex", "segment_revenue", "ppe_category", "finance_lease_liability", "purchase_commitments"))
            + f". {sum(f['label'] == 'agree' for f in rows)} agree with the filing's own XBRL, {sum(f['label'] == 'unresolved' for f in rows)} differ, "
            f"{sum(f['label'] == 'no_reference' for f in rows)} have no tagged counterpart. Every value cites its cell.")


def ai_line(rows: list[dict]) -> str:
    cos = {a["ticker"] for a in rows}
    return (f"AI spend (ai_spend.csv): {len(rows)} statements for {len(cos)} companies on what the 10-K's MD&A says about AI's part of capex and opex; "
            f"{sum(a['ai_amount'] is not None for a in rows)} give an AI dollar amount, {sum(a['class'] == 'explicit_amount' and a['scope'] == 'total' for a in rows)} give the company's total with AI as a driver, "
            f"{sum(a['class'] == 'qualitative' for a in rows)} are words only. Every row quotes its sentence.")


def readme(version, rows, ai_spend=()) -> str:
    """What a buyer gets: the files, what each column means, how every value was checked, and how to verify the packet."""
    companies, years = sorted({v["ticker"] for v in rows}), sorted({v["period"] for v in rows})
    return "\n".join([
        f"# Capex Ledger {version}", "",
        f"Revenue, capex and opex for {len(companies)} companies, fiscal years {years[0]}–{years[-1]}, read from their 10-K filings. "
        "Every value points at the exact cell of the filing it came from, was re-read on the filing as rendered, and was compared with the company's own XBRL data. "
        "A person reviewed what code could not settle and signed this release.", "",
        "## Files", "",
        "- `values.csv`: one row per company, field and fiscal year.",
        "- `facts.csv`: facts from the notes: capex and revenue per segment, property and equipment by category, finance lease liabilities, purchase commitments; `xbrl` says whether the filing's own tagged fact agrees.",
        "- `ai_spend.csv`: what each 10-K's MD&A says about AI's part of capex and opex, one row per company, field, fiscal year and kind, with the sentence quoted.",
        "- `QUALITY.md`: how many values agree with XBRL, what a person checked, and every note on definitions and restatements.",
        "- `DIFF.md`: what changed since the previous release.",
        "- `manifest.json`: the content hash, the prompt, parser and rule versions, and the number of decisions applied.",
        "- `SIGNOFF.json`: who signed, when, and the hash they signed.", "",
        "## Columns of values.csv", "",
        "| Column | Meaning |", "|---|---|",
        "| `ticker`, `period` | Company and its own fiscal year (`period_end` is the year's last day; Nvidia's FY2026 ended 25 Jan 2026). |",
        "| `field` | `revenue`: total revenue or net sales. `capex`: cash paid for property and equipment. `opex`: revenue − cost of revenue − operating income, all from the same 10-K column; it includes impairments and other operating items, so it can exceed revenue. |",
        "| `value` | Whole US dollars, unscaled. Blank when the 10-K has no such line (`source` = missing) or a reviewer rejected it. |",
        "| `basis`, `first_reported` | `restated` when a later 10-K changed the figure; `first_reported` keeps the first one. |",
        "| `source` | `agent`: read from the filing by the agent and checked. `override`: a reviewer replaced it, with a recorded reason. |",
        "| `xbrl` | `agree`: matches the company's XBRL data. `definition_gap`: differs only in which lines count as cost of revenue, confirmed by a reviewer. `unresolved`: differs; a reviewer decided. `not_reported`: no line to read. |",
        "| `citations` | The filing's accession number, table, row label, column label and the cell text, for every cell behind the value. |", "",
        "## Columns of ai_spend.csv", "",
        "| Column | Meaning |", "|---|---|",
        "| `kind` | `actual`: the fiscal year the filing reports. `outlook`: a later year the filing speaks to. |",
        "| `scope` | `ai`: the figure is the AI part. `total`: the company's whole capex or opex, with AI named as a driver; **not** AI spend. |",
        "| `class` | `explicit_amount` (dollars in `amount_low`, `amount_high`), `explicit_share` (`share`, 0 to 1), or `qualitative` (words only). |",
        "| `ai_amount` | AI dollars only where the filing supports one: the midpoint of an explicit AI amount, or an explicit AI share × the released value. Blank otherwise. |",
        "| `quote` | The sentence, verbatim from the filing. |", "",
        "## Verify it yourself", "",
        "The hash in `manifest.json` is SHA-256 over the files it lists, so the packet can be checked against the signature. "
        "Each citation names a public filing on sec.gov; open the accession number, find the row and column, and the cell text should match.", "",
        f"Companies: {', '.join(companies)}.", ""])


def check_line(values, confirmed=frozenset()) -> str:
    c = to_check(values)
    spot = sum(w == "spot_check" for w in c.values())
    agree = sum(v["label"] == "agree" and v["value"] is not None for v in values)
    ids = [i for v in values if v["extraction_ids"] for i in v["extraction_ids"].split(",")]
    return (f"Verified: {agree - spot} values by two independent sources (the 10-K cell and XBRL agree). {len(c)} more confirmed on the filing "
            f"({len(c) - spot} that XBRL can't vouch for, {spot} random spot-checks of the agreeing ones): by re-reading the rendered 10-K where "
            f"it confirms the cited cell, by a person where it can't. Re-read confirmed {sum(i in confirmed for i in ids)} of {len(ids)} cited cells.")


def content_hash(files: dict) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
