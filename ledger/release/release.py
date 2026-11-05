"""A release is a folder of plain files whose content hash a person signs. It is built only when every gate passes."""
import csv
import hashlib
import io
import json
import random
import re
from pathlib import Path

from ..core.config import GOLDEN_SEED, SCOPE
from ..core.store import ROOT, TABLES, TAXONOMY

RELEASES = ROOT / "releases"

SPOT_CHECKS = 10  # random XBRL-agreeing values a person also checks, to test that the agreement itself works

GATES = {
    "G1": "Every filing ended in a valid output or a logged failure, and no failure is open",
    "G4": "No block exception without a current decision",
    "G5": "Every value XBRL can't vouch for, plus a random sample of those it can, confirmed on the filing at the value being released: by the re-read of the rendered 10-K, or by the hand-check file (golden/stage<N>-handcheck.json) where the re-read did not confirm the cell",
    "G6": "No decision left by a run for a person to confirm (decisions/resolutions.jsonl, 'to confirm'), and no asset-type mapping without a person's confirmed_by (taxonomy/asset_types.yaml, T63)",
}


def version_key(name: str) -> list[int]:
    """v1.10.0 sorts after v1.9.0: by number, never by string."""
    return [int(x) for x in name.lstrip("v").split(".")]


def releases() -> list[Path]:
    """Every release folder, oldest version first."""
    return sorted(RELEASES.glob("v*"), key=lambda p: version_key(p.name))


def to_check(values) -> dict:
    """{(ticker, field, period): why} for the values a person checks. A value that agrees with XBRL is verified by an
    independent reading (the agent's read of the cell and the filer's XBRL, both the filer's); the rest, and a fixed random sample of the agreeing ones, go to a person."""
    k = lambda v: (v["ticker"], v["field"], v["period"])
    have = sorted((v for v in values if v["value"] is not None), key=k)
    agree = [v for v in have if v["label"] == "agree"]
    return {**{k(v): "xbrl_differs" for v in have if v["label"] != "agree"},
            **{k(v): "spot_check" for v in random.Random(GOLDEN_SEED).sample(agree, min(SPOT_CHECKS, len(agree)))}}


from ..core.ids import ID_START, split_ids  # noqa: E402,F401  the one reader of extraction_ids, kept importable from here


def gates(values, open_items, handcheck, confirmed=frozenset(), unconfirmed=(), tickers=None, mappings=(), proposed=()) -> dict:
    """{gate: {ticker: [failing items]}}, one column per company in scope (config.SCOPE, or `tickers`): every company
    appears under every gate, an empty list where it passes (T4). confirmed: extraction ids the rendered-10-K re-read
    found at their current cell text. unconfirmed: the resolutions a run left for a person to confirm (T3); one on a
    company outside the scope still fails G6 under that company's ticker, so nothing is dropped. One whose cause kind
    the pipeline no longer produces (resolutions.LIVE_KINDS) is stale and never a G6 failure. mappings: the asset-type
    entries no person confirmed (taxonomy.to_confirm, T63), each a G6 failure under its company as
    `asset_types|<ticker>|<reported name>`, exactly like a decision a run left. proposed: the block findings whose current
    decision a run or an agent made (review.proposed, F14), each a G6 failure as `decisions|<ticker>|<exception id>`; the
    block itself stays in `open_items`, so G4 fails on it too until a person decides it."""
    from ..review.resolutions import is_live
    unconfirmed = [r for r in unconfirmed if is_live(r["key"])]
    cos = list(SCOPE if tickers is None else tickers)
    cos += sorted(({r["key"].split("|")[1] for r in unconfirmed if "|" in r["key"]} | {m["ticker"] for m in mappings} | {e["ticker"] for e in proposed}) - set(cos))
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
    for m in mappings:
        out["G6"][m["ticker"]].append(f"asset_types|{m['ticker']}|{m['reported_name']}")
    for e in proposed:
        out["G6"][e["ticker"]].append(f"decisions|{e['ticker']}|{e['exception_id']}")
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



def build(version, values, extractions, exceptions, previous, confirmed=frozenset(), ai_spend=(), facts=(), handcheck=None, handcheck_file=None) -> dict:
    """Release files as {name: text}. No timestamps inside, so the same inputs give the same hash (G7). `values` is every
    row of the table in scope, null values included: values.csv ships the rows with a value (checklist.packet replaces it
    with api.fetch's, the same set with the same columns), QUALITY.md counts the rest. handcheck: the hand-check file's
    content and name when there is one, so QUALITY.md says what a person checked, or that nobody did (T64). LIMITATIONS.md
    says what the data can't support (T68)."""
    ext = {e["extraction_id"]: e for e in extractions}
    rows = sorted(values, key=lambda v: (v["ticker"], v["field"], v["period"]))
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["ticker", "field", "period", "period_end", "value", "basis", "first_reported", "source", "check_label", "citations"])  # the API's names (one name per thing); checklist.packet ships api.fetch's wider header
    for v in rows:
        cites = " ; ".join(f"{e['accession']} {e['table_id']} '{e['row_label']}' / '{e['column_label']}' = {e['cell_text']}"
                           for i in split_ids(v["extraction_ids"]) if (e := ext.get(i)))
        w.writerow([v["ticker"], v["field"], v["period"], v["period_end"], "" if v["value"] is None else v["value"], v["basis"],
                    "" if v["first_reported"] is None else v["first_reported"], v["source"], v["label"], cites])
    notes = [e for e in exceptions if e["severity"] == "info"]
    have = [v for v in rows if v["value"] is not None]
    quality = "\n".join([f"# {version}", "",
                         f"{len(have)} values in values.csv · {sum(v['source'] == 'agent' for v in have)} from agents · "
                         f"{sum(v['source'] == 'override' for v in have)} overridden · "
                         f"{sum(v['label'] == 'agree' for v in have)} agree with XBRL · {sum(v['basis'] == 'restated' for v in have)} on a restated basis · "
                         + without_value_line(rows), "",
                         ai_line(list(ai_spend)), "", facts_line(list(facts)), "",
                         check_line(rows, confirmed, handcheck, handcheck_file), "",
                         "All gates passed: " + "; ".join(f"{g} {d}" for g, d in GATES.items()) + ".", "",
                         "## Notes", ""] + [f"- {e['ticker']} {e['field'] or ''}: {e['message']}" for e in notes] + [""])
    prev = {(r["ticker"], r["field"], r["period"]): r["value"] for r in previous or []}
    changes = [f"- {v['ticker']} {v['field']} {v['period']}: {prev[(v['ticker'], v['field'], v['period'])] or 'missing'} → {v['value'] or 'missing'} ({v['source']})"
               for v in rows if (v["ticker"], v["field"], v["period"]) in prev and str(prev[(v["ticker"], v["field"], v["period"])]) != str(v["value"] or "")]
    added = {}
    for v in have:  # a row without a value is not a value added (DC6, T64): it is counted on its own line below
        if previous is not None and (v["ticker"], v["field"], v["period"]) not in prev:
            added[v["ticker"]] = added.get(v["ticker"], 0) + 1
    blank = [v for v in rows if v["value"] is None]
    body = ["First release."] if previous is None else (changes or ["No values changed."]) + (
        ["", f"Added: {sum(added.values())} values for {', '.join(sorted(added))}."] if added else [])
    body += ["", without_value_line(rows) + "."] if blank else []
    diff = "\n".join([f"# Changes in {version}", ""] + body + [""])
    files = {"values.csv": buf.getvalue(), "facts.csv": facts_csv(list(facts)), "ai_spend.csv": ai_spend_csv(list(ai_spend)), "QUALITY.md": quality, "DIFF.md": diff}
    files["LIMITATIONS.md"] = limitations_md(version, files)
    files["README.md"] = readme(version, rows, list(ai_spend), files)
    return files


def limitations_md(version: str, files: dict) -> str:
    """LIMITATIONS.md from taxonomy/limitations.yaml (T68), its computed counts read from `files` where they count rows
    of the packet; checklist.packet writes it again once every list is in, as it does README.md."""
    from .limitations import markdown
    return markdown(version, files)


def without_value_line(values) -> str:
    """"n rows without a value, not in values.csv (label: count)": the (company, field, year) rows the newest 10-K gave no
    figure for, by their label, so a headline count of values never includes a blank row (DC6, T64)."""
    blank = [v for v in values if v["value"] is None]
    by = {}
    for v in blank:
        by[v["label"]] = by.get(v["label"], 0) + 1
    return f"{len(blank)} rows without a value, not in values.csv" + (f" ({', '.join(f'{k}: {n}' for k, n in sorted(by.items()))})" if by else "")



# ── T8: the diff in rows. Each list's CSV against the previous release's, by the row's natural key ──────────────
ROW_KEYS = {"taxonomy": ("ticker", "fiscal_year", "measure", "category", "reported_name"), "values": ("ticker", "field", "period"),
            "facts": ("ticker", "field", "dimension", "period"), "statements": ("statement_id",), "projects": ("project_id",), "companies": ("ticker",),
            "ai_spend": ("ticker", "field", "period", "kind", "source", "quote")}
DIFF_EXAMPLES = 25  # per list and kind, so DIFF.md stays readable when the scope changes


def _keyed(text: str, key: tuple) -> tuple[list[str], dict]:
    """{key: [rows]} from a CSV text. A key that repeats (two statements with one category and name) keeps every row, in
    a stable order, and the rows are paired by position, so a repeat is never counted as a change of itself."""
    rows = list(csv.DictReader(io.StringIO(text))) if text else []
    header = list(rows[0].keys()) if rows else (text.splitlines()[0].split(",") if text else [])
    out = {}
    for r in rows:
        out.setdefault(tuple(r.get(k) or "" for k in key), []).append(r)
    return header, out


def _pair(a: list[dict], b: list[dict], common: list[str]) -> list[tuple]:
    """Pair old rows with new rows under one key: identical rows first, then the closest by the columns they share, so
    a repeated key (several statements with one category and name) counts a change only where a row really moved.
    Greedy by the count of equal columns, best pair first: exact where every row has one close match; where several old
    rows are equally close to one new row the first by position wins, so a removed row and a changed row under one key
    can swap places (the counts stay right, the named example may be the other row)."""
    score = lambda r, q: sum((r.get(c) or "") == (q.get(c) or "") for c in common)
    ranked = sorted(((score(r, q), i, j) for i, r in enumerate(a) for j, q in enumerate(b)), key=lambda x: (-x[0], x[1], x[2]))
    taken_a, taken_b, pairs = set(), set(), []
    for _, i, j in ranked:  # the best-matching pairs first, so a row that stayed is never paired with one that left
        if i not in taken_a and j not in taken_b:
            pairs.append((a[i], b[j]))
            taken_a.add(i)
            taken_b.add(j)
    return pairs + [(a[i], None) for i in range(len(a)) if i not in taken_a] + [(None, b[j]) for j in range(len(b)) if j not in taken_b]


def rows_diff(files: dict, previous: dict | None) -> dict:
    """{list: {added, removed, changed, examples, columns_added, columns_removed, key}} per CSV list in `files` that the
    previous release also has (`previous`: {name: text}). A row is changed when any column both releases carry differs;
    a column only one release has is reported on its own, so a new column is not 6,700 changed rows. None when there
    is no previous release."""
    if previous is None:
        return {}
    out = {}
    for name, key in ROW_KEYS.items():
        fn = f"{name}.csv"
        if fn not in files or fn not in previous:
            continue
        h_new, new = _keyed(files[fn], key)
        h_old, old = _keyed(previous[fn], key)
        common = [c for c in h_new if c in h_old]
        d = {"key": list(key), "added": 0, "removed": 0, "changed": 0, "examples": {"added": [], "removed": [], "changed": []},
             "columns_added": [c for c in h_new if c not in h_old], "columns_removed": [c for c in h_old if c not in h_new], "rows": sum(len(v) for v in new.values()),
             "without_value": {"added": 0, "removed": 0}}  # of the added / removed rows, those whose `value` is empty (DC6): a row is not a value
        for k in sorted(set(new) | set(old)):
            a, b = old.get(k, []), new.get(k, [])
            for r_old, r_new in _pair(a, b, common):
                if r_old is None:
                    d["added"] += 1
                    d["without_value"]["added"] += "value" in h_new and not r_new.get("value")
                    if len(d["examples"]["added"]) < DIFF_EXAMPLES:
                        d["examples"]["added"].append(list(k))
                elif r_new is None:
                    d["removed"] += 1
                    d["without_value"]["removed"] += "value" in h_old and not r_old.get("value")
                    if len(d["examples"]["removed"]) < DIFF_EXAMPLES:
                        d["examples"]["removed"].append(list(k))
                else:
                    diffs = {c: (r_old.get(c) or "", r_new.get(c) or "") for c in common if (r_old.get(c) or "") != (r_new.get(c) or "")}
                    if diffs:
                        d["changed"] += 1
                        if len(d["examples"]["changed"]) < DIFF_EXAMPLES:
                            d["examples"]["changed"].append({"key": list(k), "columns": diffs})
        out[name] = d
    return out


def rows_diff_md(d: dict) -> str:
    """The "## Rows" section of DIFF.md: one table line per list, then the examples by key, a changed row naming the
    columns that moved (old → new). Empty when there is no previous release."""
    if not d:
        return ""
    lines = ["", "## Rows", "", "Against the previous release, by each list's row key (a row is changed when a column both releases carry differs).", "",
             "| List | Rows | Added | Removed | Changed | Key |", "|---|---|---|---|---|---|"]
    for name, x in d.items():
        lines.append(f"| {name}.csv | {x['rows']} | {x['added']} | {x['removed']} | {x['changed']} | {' + '.join(x['key'])} |")
    for name, x in d.items():
        notes = []
        if x["columns_added"]:
            notes.append(f"columns added: {', '.join(f'`{c}`' for c in x['columns_added'])}")
        if x["columns_removed"]:
            notes.append(f"columns removed: {', '.join(f'`{c}`' for c in x['columns_removed'])}")
        wv = x.get("without_value") or {}
        if wv.get("added") or wv.get("removed"):
            notes.append("rows without a value: " + ", ".join(f"{wv[k]} of the {k}" for k in ("added", "removed") if wv.get(k)))
        ex = x["examples"]
        if not (notes or ex["added"] or ex["removed"] or ex["changed"]):
            continue
        lines += ["", f"### {name}.csv", ""]
        lines += [f"- {n}" for n in notes]
        more = lambda n, shown: f" … and {n - shown} more" if n > shown else ""
        if ex["changed"]:
            lines += [f"- changed ({x['changed']}):"]
            lines += [f"  - {' '.join(e['key'])}: " + "; ".join(f"{c}: {a or 'empty'} → {b or 'empty'}" for c, (a, b) in e["columns"].items()) for e in ex["changed"]]
            lines += [f"  -{more(x['changed'], len(ex['changed']))}"] if x["changed"] > len(ex["changed"]) else []
        if ex["added"]:
            lines += [f"- added ({x['added']}): " + ", ".join(" ".join(k) for k in ex["added"]) + more(x["added"], len(ex["added"]))]
        if ex["removed"]:
            lines += [f"- removed ({x['removed']}): " + ", ".join(" ".join(k) for k in ex["removed"]) + more(x["removed"], len(ex["removed"]))]
    return "\n".join(lines) + "\n"


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


# ── T64: the README's column tables are written from the CSV headers that ship, one meaning per column ──────────────
# A column a table defines takes its dictionary description (store.SCHEMA); the rest, which the API or a writer adds,
# are described here, as a meaning or as (allowed values, meaning) where the shipped set is narrower than the table's
# enum. A column with no description raises: nothing ships undocumented, and the test on checklist.packet compares every
# CSV header in the packet with the README's tables.
LIST_TABLES = {"values": "values", "facts": "facts", "statements": "ai_statements", "projects": "projects", "ai_spend": "ai_spend"}
COLUMN_DOCS = {
    "*": {"layer": "The supply-chain layer the company was picked under (config.INDUSTRIES): a reading aid, not a standard.",
          "proven": "True when the company is in the proven set (docs/PROOF.md): every number checked or explained.",
          "status": "A person's latest decision on the row (decisions/resolutions.jsonl): empty, confirmed, overridden or rejected.",
          "flag": "What the numbers say by themselves: `differs_from_xbrl` when the check is unresolved, else empty."},
    "values": {"ticker": "Company ticker, e.g. NVDA.",
               "period": "The company's own fiscal year, e.g. FY2026 (`period_end` is its last day; Nvidia's FY2026 ended 25 Jan 2026).",
               "field": ("`revenue`, `capex`, `opex`", "`revenue`: total revenue or net sales. `capex`: cash paid for property and equipment. `opex`: revenue − cost of revenue − operating income, all from the same 10-K column; it includes impairments and other operating items, so it can exceed revenue."),
               "value": "Whole US dollars, unscaled, never empty: a (company, field, year) the newest 10-K gives no figure for is not in this file (QUALITY.md counts them).",
               "check_label": ("`agree`, `definition_gap`, `unresolved`, `no_reference`", "`agree`: matches the company's XBRL data. `definition_gap`: differs only in which lines count as cost of revenue, confirmed by a reviewer. `unresolved`: differs; a reviewer decided. `no_reference`: XBRL has no tag to compare with."),
               "basis": "`as_reported`, or `restated` when a later 10-K moved the figure by more than half a rounding unit of the cell's scale (config.RESTATEMENT_TOLERANCE); `first_reported` keeps the first figure.",
               "first_reported": "The figure in the first 10-K that reported this fiscal year, whole US dollars.",
               "source": ("`agent`, `override`", "`agent`: read from the filing by the agent and checked. `override`: a reviewer replaced it, with a recorded reason."),
               "extraction_ids": "The cited cells' ids (accession, field, period start, period end, joined by a vertical bar), comma-separated; `citations` spells them out.",
               "accession": "SEC accession number of the 10-K the value comes from; every cell behind a value is from this one filing.",
               "filed": "The day that 10-K was filed (YYYY-MM-DD); `?as_of=` on the read API answers for any earlier day.",
               "citations": "The filing's accession number, table, row label, column label and the cell text, for every cell behind the value, separated by ` ; `."},
    "facts": {"check_label": "`agree` or `unresolved` against the filing's XBRL instance member; `no_reference` when no tagged fact matches the dimension.",
              "xbrl": "The XBRL value compared with, when any.", "xbrl_value": "The XBRL value compared with, when any."},
    "statements": {"amount_mid": "The middle of `amount_low` and `amount_high`, for sums; empty when the statement gives no amount.",
                   "date": "Filing or quarter-end date of the text (YYYY-MM-DD).", "url": "Where the text came from."},
    "companies": {"ticker": "Company ticker, e.g. NVDA.", "name": "Company name.", "group": "The set the company was picked from (config.AI_SET or added since).",
                  "role": "buyer: spends capex on the AI buildout. seller: supplies it (chips, networking, memory).", "note": "A note on the listing (IPO, form change), when any.",
                  "sic": "The SEC's SIC code from the EDGAR submissions, when cached.", "sic_description": "The SEC's description of that SIC code."},
}


def column_doc(name: str, col: str) -> tuple[str, str]:
    """(allowed values, meaning) for column `col` of list `name`: the list's own docs first, then the table's dictionary
    entry, then the columns every list shares. KeyError when none describes it: a column never ships undocumented."""
    table = TAXONOMY if name == "taxonomy" else TABLES.get(LIST_TABLES.get(name, ""))
    c = next((c for c in table.cols if c.name == col), None) if table else None
    allowed = ", ".join(f"`{e}`" for e in c.enum) if c and c.enum else ""
    if col in COLUMN_DOCS.get(name, {}):
        d = COLUMN_DOCS[name][col]
        return (d[0], d[1]) if isinstance(d, tuple) else (allowed, d)
    if c:
        return allowed, c.doc
    if col in COLUMN_DOCS["*"]:
        return allowed, COLUMN_DOCS["*"][col]
    raise KeyError(f"{name}.csv column `{col}` has no description (release.COLUMN_DOCS or store.SCHEMA)")


def csv_header(text: str) -> list[str]:
    return next(csv.reader(io.StringIO(text))) if text.strip() else []


def columns_section(name: str, text: str) -> list[str]:
    """"## Columns of <name>.csv", one line per column of the header that ships, in the file's order."""
    return [f"## Columns of {name}.csv", "", "| Column | Allowed values | Meaning |", "|---|---|---|",
            *[f"| `{col}` | {a} | {m} |" for col in csv_header(text) for a, m in [column_doc(name, col)]], ""]


FILE_ORDER = ("taxonomy", "companies", "values", "facts", "statements", "projects", "ai_spend")  # the column sections, in this order


def readme(version, rows, ai_spend=(), files=None) -> str:
    """What a buyer gets: the files, what each column means (from the CSV headers in `files`, one source of truth), how every
    value was checked, and how to verify the packet."""
    files = files or {}
    companies, years = sorted({v["ticker"] for v in rows}), sorted({v["period"] for v in rows})
    blank = [v for v in rows if v["value"] is None]
    return "\n".join([
        f"# Capex Ledger {version}", "",
        f"Revenue, capex and opex for {len(companies)} companies, fiscal years {years[0]}–{years[-1]}, read from their 10-K filings. "
        "Every value points at the exact cell of the filing it came from, was re-read on the filing as rendered, and was compared with the company's own XBRL data. "
        "The release was signed by a person after every gate passed; what code could not settle was re-read by machine on the rendered filing or decided by a person in Reconcile, and QUALITY.md says which.", "",
        "Nothing here is estimated. `taxonomy.csv` is the dataset in one shape: each row an instance of a published standard concept (us-gaap for spent, committed and derived; "
        "Regulation S-K for planned), the company's own label beside it, and for AI only what the company itself stated, quoted. See docs/TAXONOMY.md in the repository.", "",
        "## Files", "",
        "- `taxonomy.csv`: one row per company, fiscal year, measure (spent, committed, derived, planned, company_stated_ai) and category; `standard_concept` names the standard, `reported_name` the company's label, `check` and `check_method` how the number was verified, `source_url` the filing at the cited row's words, `source_table` the parsed table, `proven` whether the company is in the proven set. Columns below.",
        "- `companies.csv`: the tracked companies with layer, role and the SEC's SIC code.",
        "- `statements.csv`: guidance and AI statements, quoted, with the source document and date.",
        "- `projects.csv`: named projects the filings and releases mention, verbatim.",
        "- `values.csv`: one row per company, field and fiscal year that has a value, with the cells it cites. A (company, field, year) the newest 10-K gives no figure for is not a row here"
        + (f" ({len(blank)} in this release: {', '.join(f'{t} {n}' for t, n in sorted(_by_ticker(blank).items()))}; QUALITY.md counts them by label)" if blank else " (none in this release)") + ".",
        "- `facts.csv`: facts from the notes: capex and revenue per segment, property and equipment by category, finance lease liabilities, purchase commitments; `xbrl` is the filing's own tagged value it was compared with, when there is one, `check_label` says agree or unresolved, and `first_reported` keeps the first filing's figure beside a restated one.",
        "- `ai_spend.csv`: what each 10-K's MD&A says about AI's part of capex and opex, one row per company, field, fiscal year and kind, with the sentence quoted.",
        "- `QUALITY.md`: how many values agree with XBRL, what was checked by machine, what a person checked (or that nobody did), and every note on definitions and restatements.",
        "- `DIFF.md`: what changed since the previous release.",
        "- `LIMITATIONS.md`: what the data is for and not for, every known weakness with the rows it affects, the mitigation and the ticket that would close it, "
        "and how releases, corrections and support work.",
        "- `manifest.json`: the content hash, the rule versions, the number of decisions applied, and under `provenance` what produced the rows: "
        "the prompt versions per reader and the models over the shipped rows, the parser versions over the filings in scope, rows whose run is unrecorded, "
        "the commit built on, and the sha256 of the definitions, taxonomy and resolutions files. `provenance` is the record; the top-level `prompt`, `parser` and `model` name the versions in use when the packet was built.",
        "- `SIGNOFF.json`: who signed, when, and the hash they signed.", "",
        "## Columns", "",
        "Each table below is written from the header of the file it describes, so a column is here exactly when it ships. "
        "taxonomy.csv: one meaning per column (schema v11). Every amount is in whole units (`scale` 1) of US dollars (`currency` USD); `value_high` is only a range high, "
        "`change_from_prior` only the derived year-over-year change; a reported row carries its `period_end`, a verbatim row its `quote`; `source` is the internal id and "
        "`accession`, `filed`, `source_table`, `source_url`, `source_kind` follow it to the filing. `layer` is the supply-chain layer the company was picked under, a reading aid, not a standard.", "",
        *[line for name in FILE_ORDER if f"{name}.csv" in files for line in columns_section(name, files[f"{name}.csv"])],
        "## Point in time", "",
        "`values.csv` carries the newest filing's figure per fiscal year, with `first_reported` beside it. A backtest must not see a figure restated after the day it is "
        "testing: ask the read API with `?as_of=YYYY-MM-DD` on `/api/v1/values` or `/api/v1/taxonomy` (docs/API.md) for what the newest filing filed on or before that day "
        "gave, with its accession and filing date. No as-of file is in the packet: the packet holds the signed dataset once, and the as-of answer is derived from the same cells.", "",
        "## Verify it yourself", "",
        "The hash in `manifest.json` is SHA-256 over the files it lists, so the packet can be checked against the signature. "
        "Each citation names a public filing on sec.gov; open the accession number, find the row and column, and the cell text should match.", "",
        f"Companies: {', '.join(companies)}.", ""])


def _by_ticker(values) -> dict:
    out = {}
    for v in values:
        out[v["ticker"]] = out.get(v["ticker"], 0) + 1
    return out


def check_line(values, confirmed=frozenset(), handcheck=None, handcheck_file=None) -> str:
    """What was checked and by what (T64): code (XBRL, the rules, the rendered-10-K re-read) with its counts; a person only
    where a hand-check file exists, with its count, else "no hand-check for this release". Never a standing promise."""
    c = to_check(values)
    spot = sum(w == "spot_check" for w in c.values())
    agree = sum(v["label"] == "agree" and v["value"] is not None for v in values)
    ids = [i for v in values if v["extraction_ids"] for i in split_ids(v["extraction_ids"])]
    keys = {(v["ticker"], v["field"], v["period"]): v for v in values}
    by_person = [h for h in (handcheck or {}).get("values", []) if h.get("verified") and (v := keys.get((h["ticker"], h["field"], h["period"]))) and h.get("value") == v["value"]]
    person = (f"By a person: {len(by_person)} values verified on the filing in {handcheck_file or 'the hand-check file'}, at the value released"
              if handcheck else "By a person: no hand-check for this release (no golden/stage<N>-handcheck.json); nothing here was confirmed by hand")
    return (f"Verified: {agree - spot} values by an independent reading (the agent read the 10-K cell without seeing XBRL, and the filer's XBRL agrees; both come from the same filer). {len(c)} more to confirm on the filing "
            f"({len(c) - spot} that XBRL can't vouch for, {spot} random spot-checks of the agreeing ones). "
            f"By machine: the re-read of the rendered 10-K confirmed {sum(i in confirmed for i in ids)} of {len(ids)} cited cells at their cell text, "
            f"and the rules (rules/*.yaml) passed every gate. {person}.")


def content_hash(files: dict) -> str:
    return hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
