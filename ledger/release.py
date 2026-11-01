"""A release is a folder of plain files whose content hash a person signs. It is built only when every gate passes."""
import csv
import hashlib
import io
import json
import random
import re
from pathlib import Path

from .config import GOLDEN_SEED, SCOPE
from .store import ROOT, TAXONOMY

RELEASES = ROOT / "releases"

SPOT_CHECKS = 10  # random XBRL-agreeing values a person also checks, to test that the agreement itself works

GATES = {
    "G1": "Every filing ended in a valid output or a logged failure, and no failure is open",
    "G4": "No block exception without a current decision",
    "G5": "Every value XBRL can't vouch for, plus a random sample of those it can, confirmed on the filing at the value being released: by the re-read of the rendered 10-K, or by a person where it can't",
    "G6": "No decision left by a run for a person to confirm (decisions/resolutions.jsonl, 'to confirm')",
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


ID_START = re.compile(r"^\d{10}-\d{2}-\d{6}\|")


def split_ids(joined: str) -> list[str]:
    """extraction_ids are comma-joined, and a cost-line label may itself hold a comma ("Fuel, purchased power costs, and
    delivery fees"); a piece that does not start with an accession belongs to the id before it (type 66)."""
    out = []
    for piece in joined.split(","):
        if out and ID_START.match(out[-1]) and not ID_START.match(piece):
            out[-1] += "," + piece
        else:
            out.append(piece)
    return out


def gates(values, open_items, handcheck, confirmed=frozenset(), unconfirmed=(), tickers=None) -> dict:
    """{gate: {ticker: [failing items]}}, one column per company in scope (config.SCOPE, or `tickers`): every company
    appears under every gate, an empty list where it passes (T4). confirmed: extraction ids the rendered-10-K re-read
    found at their current cell text. unconfirmed: the resolutions a run left for a person to confirm (T3); one on a
    company outside the scope still fails G6 under that company's ticker, so nothing is dropped. One whose cause kind
    the pipeline no longer produces (resolutions.LIVE_KINDS) is stale and never a G6 failure."""
    from .resolutions import is_live
    unconfirmed = [r for r in unconfirmed if is_live(r["key"])]
    cos = list(SCOPE if tickers is None else tickers)
    cos += sorted({r["key"].split("|")[1] for r in unconfirmed if "|" in r["key"]} - set(cos))
    checked = {(h["ticker"], h["field"], h["period"]): h for h in (handcheck or {}).get("values", [])}
    machine = lambda v: bool(v["extraction_ids"]) and set(split_ids(v["extraction_ids"])) <= set(confirmed)
    tc = to_check([v for v in values if v["ticker"] in cos])
    need = [v for v in values if (v["ticker"], v["field"], v["period"]) in tc and not machine(v)]
    out = {g: {t: [] for t in cos} for g in GATES}
    for e in open_items:
        if e["ticker"] in cos and e["rule_id"] == "extraction_failed":
            out["G1"][e["ticker"]].append(e["exception_id"])
        if e["ticker"] in cos and e["severity"] == "block":
            out["G4"][e["ticker"]].append(e["exception_id"])
    for v in need:
        if handcheck is None:
            out["G5"][v["ticker"]] = ["no hand-check file"]
        elif not (h := checked.get((v["ticker"], v["field"], v["period"]), {})).get("verified") or h.get("value") != v["value"]:
            out["G5"][v["ticker"]].append(f"{v['ticker']} {v['field']} {v['period']}")
    for r in unconfirmed:
        out["G6"][r["key"].split("|")[1] if "|" in r["key"] else cos[0]].append(r["key"])
    return out


def failing(g: dict) -> dict:
    """{ticker: {gate: [items]}} for the rows that fail; empty when every company passes every gate."""
    out = {}
    for gate, by_t in g.items():
        for t, items in by_t.items():
            if items:
                out.setdefault(t, {})[gate] = items
    return out


def table(g: dict) -> str:
    """The per-company table `ledger release` prints: one row per company, one column per gate, the count of failing
    items (· when it passes)."""
    cos = list(next(iter(g.values()), {}))
    w = max([6] + [len(t) for t in cos])
    lines = ["company".ljust(w) + "".join(f"  {gate:>4}" for gate in g) + "  result"]
    for t in cos:
        cells = [len(g[gate][t]) for gate in g]
        lines.append(t.ljust(w) + "".join(f"  {n if n else '·':>4}" for n in cells) + ("  FAILS" if any(cells) else "  passes"))
    return "\n".join(lines)


def ai_spend_csv(rows: list[dict]) -> str:
    """What each 10-K says about AI's part of capex and opex: one row per company, field, fiscal year and kind."""
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["ticker", "field", "period", "kind", "scope", "class", "amount_low", "amount_high", "share", "source", "accession", "quote"])
    for a in sorted(rows, key=lambda a: (a["ticker"], a["field"], a["period"], a["kind"])):
        w.writerow([a["ticker"], a["field"], a["period"], a["kind"], a["scope"], a["class"], a["amount_low"] or "", a["amount_high"] or "",
                    "" if a["share"] is None else a["share"], a["source"], a["accession"] or "", a["quote"]])
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
    files = {"values.csv": buf.getvalue(), "facts.csv": facts_csv(list(facts)), "ai_spend.csv": ai_spend_csv(list(ai_spend)), "QUALITY.md": quality, "DIFF.md": diff,
             "README.md": readme(version, rows, list(ai_spend))}
    return files



def facts_line(rows: list[dict]) -> str:
    return (f"Facts from the notes (facts.csv): {len(rows)} values for {len({f['ticker'] for f in rows})} companies: "
            + ", ".join(f"{sum(f['field'] == k for f in rows)} {k}" for k in ("segment_capex", "segment_revenue", "ppe_category", "finance_lease_liability", "purchase_commitments"))
            + f". {sum(f['label'] == 'agree' for f in rows)} agree with the filing's own XBRL, {sum(f['label'] == 'unresolved' for f in rows)} differ, "
            f"{sum(f['label'] == 'no_reference' for f in rows)} have no tagged counterpart. Every value cites its cell.")


def ai_line(rows: list[dict]) -> str:
    cos = {a["ticker"] for a in rows}
    return (f"AI spend (ai_spend.csv): {len(rows)} statements for {len(cos)} companies on what the 10-K's MD&A says about AI's part of capex and opex; "
            f"{sum(a['scope'] == 'ai' and a['class'] != 'qualitative' for a in rows)} give a stated AI amount or share, {sum(a['class'] == 'explicit_amount' and a['scope'] == 'total' for a in rows)} give the company's total with AI as a driver, "
            f"{sum(a['class'] == 'qualitative' for a in rows)} are words only. Every row quotes its sentence.")


def readme(version, rows, ai_spend=()) -> str:
    """What a buyer gets: the files, what each column means, how every value was checked, and how to verify the packet."""
    companies, years = sorted({v["ticker"] for v in rows}), sorted({v["period"] for v in rows})
    return "\n".join([
        f"# Capex Ledger {version}", "",
        f"Revenue, capex and opex for {len(companies)} companies, fiscal years {years[0]}–{years[-1]}, read from their 10-K filings. "
        "Every value points at the exact cell of the filing it came from, was re-read on the filing as rendered, and was compared with the company's own XBRL data. "
        "A person reviewed what code could not settle and signed this release.", "",
        "Nothing here is estimated. `taxonomy.csv` is the dataset in one shape: each row an instance of a published standard concept (us-gaap for spent, committed and derived; "
        "Regulation S-K for planned), the company's own label beside it, and for AI only what the company itself stated, quoted. See docs/TAXONOMY.md in the repository.", "",
        "## Files", "",
        "- `taxonomy.csv`: one row per company, fiscal year, measure (spent, committed, derived, planned, company_stated_ai) and category; `standard_concept` names the standard, `reported_name` the company's label, `check` and `check_method` how the number was verified, `source_url` the filing at the cited row's words, `source_table` the parsed table, `proven` whether the company is in the proven set. Columns below.",
        "- `companies.csv`: the tracked companies with layer, role and the SEC's SIC code.",
        "- `statements.csv`: guidance and AI statements, quoted, with the source document and date.",
        "- `projects.csv`: named projects the filings and releases mention, verbatim.",
        "- `values.csv`: one row per company, field and fiscal year.",
        "- `facts.csv`: facts from the notes: capex and revenue per segment, property and equipment by category, finance lease liabilities, purchase commitments; `xbrl` says whether the filing's own tagged fact agrees.",
        "- `ai_spend.csv`: what each 10-K's MD&A says about AI's part of capex and opex, one row per company, field, fiscal year and kind, with the sentence quoted.",
        "- `QUALITY.md`: how many values agree with XBRL, what a person checked, and every note on definitions and restatements.",
        "- `DIFF.md`: what changed since the previous release.",
        "- `manifest.json`: the content hash, the prompt, parser and rule versions, and the number of decisions applied.",
        "- `SIGNOFF.json`: who signed, when, and the hash they signed.", "",
        "## Columns of taxonomy.csv", "",
        "One meaning per column (schema v11). Every amount is in whole units (`scale` 1) of US dollars (`currency` USD); `value_high` is only a range high, "
        "`change_from_prior` only the derived year-over-year change; a reported row carries its `period_end`, a verbatim row its `quote`; `source` is the internal id and "
        "`accession`, `filed`, `source_table`, `source_url`, `source_kind` follow it to the filing. `layer` is the supply-chain layer the company was picked under, a reading aid, not a standard.", "",
        "| Column | Allowed values | Meaning |", "|---|---|---|",
        *[f"| `{c.name}` | {', '.join(f'`{e}`' for e in c.enum) if c.enum else ''} | {c.doc} |" for c in TAXONOMY.cols], "",
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
        "| `source` | `mdna` (10-K Item 7), `earnings_release` (8-K Exhibit 99.1), `transcript` or `cfo_commentary` (the company's investor page). |",
        "| `quote` | The sentence, verbatim from the source. |", "",
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
