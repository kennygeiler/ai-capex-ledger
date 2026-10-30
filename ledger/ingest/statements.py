"""Find the income statement and the cash-flow statement among a filing's tables.

Scored on row labels, not captions (captions are often outside the table or missing). The primary statements are
the tables that carry the whole statement: revenue down to earnings per share, or all three cash-flow sections.
Segment and note tables also mention revenue and operating income, so the full-statement markers decide.
"""
import re

INCOME_MARKERS = {
    "revenue": re.compile(r"^(total )?(net )?(revenues?|sales)( net)?\b|^net sales|^total net sales|^total revenues?", re.I),
    "operating": re.compile(r"operating (income|loss|\(loss\) income|income \(loss\))|(income|loss) from operations|operating profit", re.I),
    "net_income": re.compile(r"^net (income|loss|\(loss\) income|income \(loss\))\b", re.I),
    "per_share": re.compile(r"per share|basic|diluted", re.I),
    "tax": re.compile(r"(provision for|benefit from|\(benefit\)|income tax)", re.I),
}
CASH_MARKERS = {
    "operating": re.compile(r"operating activities|^operations$|cash (from|provided by|used in|\(used in\) provided by) operations", re.I),
    "investing": re.compile(r"investing", re.I),
    "financing": re.compile(r"financing activities|^financing$|cash (from|provided by|used in|used for) financing", re.I),
    "ppe": re.compile(r"(purchase|acquisition|addition|payment|expenditure|investment)s?\b.*(property|equipment|plant|fixed assets|ppe)|capital expenditures", re.I),
}


CAPTIONS = {
    "income": re.compile(r"statements? of (consolidated )?(operations|income|earnings)|income statements?", re.I),
    "cash_flow": re.compile(r"statements? of (consolidated )?cash flows", re.I),
}


def _score(tables: list[dict], markers: dict) -> int:
    labels = [r["label"] for t in tables for r in t["rows"]]
    return sum(any(p.search(l) for l in labels) for p in markers.values())


def _caption(tables: list[dict], kind: str) -> int:
    """1 when the text just above the first table names the statement. Breaks ties with MD&A tables
    (quarterly results, non-GAAP reconciliations) that carry the same row labels."""
    return 1 if CAPTIONS[kind].search(tables[0]["before"][-200:]) else 0


MDNA = re.compile(r"non-gaap|reconcil|free cash flow|adjusted", re.I)


def _mdna(tables: list[dict]) -> bool:
    """Introduced as a non-GAAP measure or a reconciliation: an MD&A table, never the primary statement (Intel's
    adjusted free cash flow table scores like the cash-flow statement)."""
    return bool(MDNA.search(tables[0]["before"][-300:]))


SUMMARY = re.compile(r"snapshot|highlights|selected? (financial|items)|summary", re.I)
PERCENT = re.compile(r"%|percent", re.I)
BALANCE = re.compile(r"^(total )?(assets|liabilities|(stockholders'|shareholders'|total )?equity)\b", re.I)


def _summary(tables: list[dict]) -> bool:
    """A highlights table: introduced as a snapshot or summary, or income lines next to balance-sheet totals (IBM's
    "Management Discussion Snapshot" has revenue, net income and EPS, then assets, liabilities, equity). Never the
    primary statement, even when it scores like one and comes first."""
    labels = [r["label"] for t in tables for r in t["rows"]]
    percent = any(PERCENT.search(c) for t in tables for c in t["columns"])  # "% of Revenues" columns: an MD&A analysis table (Coherent)
    return percent or bool(SUMMARY.search(tables[0]["before"][-300:])) or (any(BALANCE.search(l) for l in labels) and any(INCOME_MARKERS["revenue"].search(l) for l in labels))


def _quarterly(tables: list[dict]) -> bool:
    """Columns of three-month periods: an MD&A quarterly summary, never a 10-K's primary statement."""
    return any(re.search(r"three months|quarter|\bq[1-4]\b", c, re.I) for t in tables for c in t["columns"])


def locate(tables: list[dict]) -> dict:
    """{'income': [table_id, ...] | None, 'cash_flow': [...] | None, '<kind>_score': n}.

    A statement can break across a page into two adjacent tables, so pairs are scored too; a pair wins only if it
    scores higher than either table alone. Among tables with enough markers, fiscal-year statement tables beat quarterly
    summaries, MD&A reconciliations and highlights tables (IREN's quarterly summary, Intel's adjusted free cash flow
    table and IBM's snapshot all score like a statement); then the higher score, a caption, and the earliest table (primary statements come before the notes).
    """
    out = {}
    for kind, markers, need in (("income", INCOME_MARKERS, 4), ("cash_flow", CASH_MARKERS, 4)):
        cands = [(_score([t], markers), _caption([t], kind), -i, [t["id"]], _quarterly([t]) or _mdna([t]) or _summary([t])) for i, t in enumerate(tables)]
        cands += [(_score(tables[i:i + 2], markers), _caption(tables[i:i + 2], kind) - 1, -i, [tables[i]["id"], tables[i + 1]["id"]], _quarterly(tables[i:i + 2]) or _mdna(tables[i:i + 2]) or _summary(tables[i:i + 2]))
                  for i in range(len(tables) - 1)
                  if _score(tables[i:i + 2], markers) > max(_score([tables[i]], markers), _score([tables[i + 1]], markers))]
        if kind == "income" and not any(c[0] >= need and not c[4] for c in cands):  # some issuers (miners, early-stage) have no EPS-style markers: accept 3; a quarterly or summary table never raises the bar (JCI, type 54)
            need = 3
        ok = [c for c in cands if c[0] >= need]
        best = max(ok, key=lambda c: (not c[4], c[0], c[1], c[2]), default=None)
        out[kind] = best[3] if best else None
        out[f"{kind}_score"] = max((c[0] for c in cands), default=0)
    return out


def assemble(tables: list[dict], ids: list[str], doc_units: list[dict] | None = None) -> list[dict]:
    """The tables that make up one statement. A continuation table (page 2 of a split statement) has no header rows
    of its own; it inherits the first part's column labels and unit when the column count matches.

    Unit source, per table: "table" when stated in or just above it; "statement" when inherited from the first part;
    "document" when only stated elsewhere in the filing (the scale used most often there). "document" is allowed
    but raises a warning downstream (decision 2026-10-27)."""
    by = {t["id"]: t for t in tables}
    parts = [dict(by[i]) for i in ids]
    for p in parts:
        p["unit_source"] = "table" if p["unit_text"] else None
    first = parts[0]
    for p in parts[1:]:
        if all(c.startswith("column ") for c in p["columns"]) and len(p["columns"]) == len(first["columns"]):
            p["columns"] = list(first["columns"])
            p["inherited_from"] = first["id"]
        if not p["unit_text"] and first["unit_text"]:
            p["unit_text"], p["scale"], p["unit_source"] = first["unit_text"], first["scale"], "statement"
    if not doc_units and any(not p["unit_text"] for p in parts):  # the filing states no unit anywhere: the SEC requires one when figures are scaled, so these are whole dollars (CleanSpark FY2022, type 62)
        for p in parts:
            if not p["unit_text"]:
                p.update(unit_text="(no unit stated anywhere in the filing: whole dollars)", scale=1, unit_source="document", unit_context="")
    if doc_units and any(not p["unit_text"] for p in parts):
        from collections import Counter
        scale = Counter(u["scale"] for u in doc_units).most_common(1)[0][0]
        u = next(u for u in doc_units if u["scale"] == scale)
        for p in parts:
            if not p["unit_text"]:
                p.update(unit_text=u["text"], scale=scale, unit_source="document", unit_context=u["context"])
    return parts
