"""Evidence for the note figures beyond the tag (T92, docs/PROOF.md "The ladder"): readings across filings, and ties to
the filing's tagged total.

The SEC tags almost none of the untagged note figures (PP&E by category, segments a filer does not tag), so a fact
labelled `no_reference` had only its citation. Two more checks are on file for it:

  readings   every 10-K that printed the figure. A later fiscal year's 10-K repeats the year as its comparative column:
             two or more such filings (lineages: a 10-K/A folds into the 10-K it amends) that agree are a second reading
             (`reading:<accession>`, key second_reading); readings that differ by more than config.RESTATEMENT_TOLERANCE
             are the `fact_readings_differ` finding, open until a person's resolution explains it. A label never
             explains a disagreement.
  ties       the parts one filing prints for a field and a date sum to the total the same filing tags in its XBRL
             instance (PropertyPlantAndEquipmentGross, total revenue, total capex): the `*_tie` rules in rules/. A tie
             that holds checks each untagged part (`rule:<id>_tie`, key tie); one that fails is the rule's finding.
             A tie bounds the sum, not each part: two misreads that offset inside the tolerance still tie
             (taxonomy/limitations.yaml, tie_offsetting_errors).

One ladder (`fact_state`) gives a fact its state for Proof, Reconcile, the taxonomy rows and the gold check alike. Pure
functions over rows, plus loaders that read the database and the distilled instances on disk
(data/raw/<cik>/filings/<accession>.facts.json). Nothing is fetched."""
from __future__ import annotations

import json
import re

from . import config

TIE_CHECK = "parts_tie"  # the check behind every *_tie rule on the facts (rules/ppe_categories_tie.yaml and its two siblings)
DIFFER = "fact_readings_differ"  # the rule whose finding opens an untagged fact read two ways (status.DIFFER is the same id)
TOTAL_LIKE = re.compile(r"^\s*(total|subtotal|sub-total|gross|net)\s*[:.]?\s*$", re.I)  # a dimension that is itself a total, as the whole label


# ── readings ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def readings_of(fact: dict, by_id: dict) -> list[dict]:
    """The readings behind a fact: [{accession, filed, form, period, value, scale}], oldest filing first, one per
    extraction id the fact lists (one per filing: an extraction id is accession|field|dimension|period_end). `period`
    is the filing's own report period (documents.period), its lineage: a 10-K/A carries its original's."""
    out = [by_id[i] for i in (fact.get("extraction_ids") or "").split(",") if i in by_id]
    keys = ("accession", "filed", "form", "period", "value", "scale")
    return sorted(({k: r.get(k) for k in keys} for r in out), key=lambda r: (str(r["filed"] or ""), r["accession"]))


def lineages(rs: list[dict]) -> set:
    """The distinct filings that read a figure, an amendment folded into the 10-K it amends (same report period). A
    reading without its report period counts by its accession."""
    return {str(r.get("period") or "")[:10] or r.get("accession") for r in rs if r.get("accession")}


def differ(rs: list[dict]) -> bool:
    """Readings that moved by more than config.RESTATEMENT_TOLERANCE of the coarsest rounding among them."""
    vals = [r["value"] for r in rs if r.get("value") is not None]
    return len(vals) >= 2 and config.restated(min(vals), max(vals), max(max(int(r.get("scale") or 1), 1) for r in rs))


def corroborated(rs: list[dict]) -> bool:
    """A second reading: two or more lineages read the figure (a later fiscal year's 10-K, its comparative column; a
    10-K/A re-printing the same year's 10-K is the same lineage), and every reading agrees (not `differ`)."""
    return len(lineages(rs)) >= 2 and not differ(rs)


def second_accession(rs: list[dict], shipped: str | None) -> str | None:
    """The accession a second reading names: a reading from another lineage than the shipped one."""
    own = next((str(r.get("period") or "")[:10] or r["accession"] for r in rs if r["accession"] == shipped), None)
    return next((r["accession"] for r in rs if (str(r.get("period") or "")[:10] or r["accession"]) != own), None)


def differ_message(rs: list[dict]) -> str:
    from .cards import money
    return "readings differ across filings: " + " vs ".join(f"{money(r['value'])} in {r['accession']} (filed {str(r['filed'] or '')[:10]})" for r in rs)


# ── ties ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def tolerance(parts: list[dict]) -> int:
    """The bound on the sum: (n + 1) × half the coarsest table's rounding unit (config.RESTATEMENT_TOLERANCE), n parts
    each rounded to that unit and the total once more. It bounds the sum of the group, never a single part."""
    unit = max((max(int(p.get("scale") or 1), 1) for p in parts), default=1)
    return int(unit * config.RESTATEMENT_TOLERANCE * (len(parts) + 1))


def total_of(totals: dict, accession: str, end: str, concepts: list[str], pick: str) -> tuple[str, int] | None:
    """The filing's own tagged total for `end` among `concepts`: the first on the list (`pick: first`), or the largest
    (`pick: largest`, revenue: a total tag beats a component tag in the same filing, as reference.normalize does)."""
    found = [(c, totals[(accession, c, end)]) for c in concepts if (accession, c, end) in totals]
    if not found:
        return None
    return max(found, key=lambda x: x[1]) if pick == "largest" else found[0]


def degenerate(parts: list[dict], total: int) -> str | None:
    """Why a group cannot be judged, or None: fewer than two parts (one part equal to the total proves only that the
    reader copied the total), a part labelled as a total or subtotal (it would count the whole twice), or nothing but
    zeros."""
    if len(parts) < 2:
        return "fewer than two parts"
    if any(TOTAL_LIKE.match(p.get("dimension") or "") for p in parts):
        return "a part is labelled as a total"
    if not any(int(p["value"]) for p in parts) and not total:
        return "every part and the total are zero"
    return None


def groups(rule_id: str, params: dict, facts: list[dict], extractions: list[dict], totals: dict) -> list[dict]:
    """Every group a tie rule judges: per ticker, a filing (accession) and a date, the parts that filing printed for
    `params.field`, against the total it tagged. Only groups that ship a fact (a fact of the field whose newest reading
    is that filing's) are judged: a comparative column a later 10-K replaced ships nothing. A group with no tagged
    total, or a degenerate one (`degenerate`), is not judged (no tie, nothing open). Returns [{rule, ticker, field,
    period, period_end, accession, parts: [{dimension, value, scale}], dimensions, sum, total, concept, concepts_found,
    pick, tolerance, holds, key}]."""
    field_ = params["field"]
    shipped = {}
    for f in facts:
        if f["field"] == field_:
            shipped.setdefault((f["ticker"], f["accession"], str(f["period_end"])), f["period"])
    parts = {}
    for e in extractions:
        k = (e["ticker"], e["accession"], str(e["period_end"]))
        if e["field"] == field_ and k in shipped:
            parts.setdefault(k, []).append(e)
    out = []
    concepts = params["concepts"]
    for (t, acc, end), period in sorted(shipped.items()):
        ps = parts.get((t, acc, end)) or []
        tot = total_of(totals, acc, end, concepts, params.get("pick", "first"))
        if not ps or tot is None or degenerate(ps, int(tot[1])):
            continue
        s, tol = sum(int(p["value"]) for p in ps), tolerance(ps)
        out.append({"rule": rule_id, "ticker": t, "field": field_, "period": period, "period_end": end, "accession": acc,
                    "parts": sorted(({"dimension": p.get("dimension") or "", "value": int(p["value"]), "scale": int(p.get("scale") or 1)} for p in ps), key=lambda p: p["dimension"]),
                    "dimensions": sorted(p.get("dimension") or "" for p in ps), "sum": s, "total": int(tot[1]), "concept": tot[0], "pick": params.get("pick", "first"),
                    "concepts_found": sum((acc, c, end) in totals for c in concepts), "tolerance": tol,
                    "holds": abs(s - int(tot[1])) <= tol, "key": key(t, field_, period, acc)})
    return out


def key(ticker: str, field_: str, period: str, accession: str) -> str:
    return f"{ticker}|{field_}|{period}|{accession}"


def fail_message(g: dict) -> str:
    from .cards import money
    n = len(g["parts"])
    which = f"{g['concept']}, the largest of {g['concepts_found']} revenue tags it carries" if g.get("pick") == "largest" and g.get("concepts_found", 1) > 1 else g["concept"]
    return (f"{n} part{'s' * (n != 1)} in {g['accession']} sum to {money(g['sum'])}; the filing tags {which} {money(g['total'])} for {g['period_end']} "
            f"(gap {money(g['sum'] - g['total'])}, tolerance on the sum ±{money(g['tolerance'])})")


# ── the one ladder: a fact's state, for Proof, Reconcile, the taxonomy rows and gold ─────────────────────────────────
def fact_state(f: dict, idx: dict, lad: dict, restated: str | None = None) -> tuple[dict, dict]:
    """(status state, the record it rests on) for a `facts` row `f` ({ticker, field, dimension, period, label,
    accession}). `lad` is by_fact(...) (proof.ladder); `idx` the resolutions index (resolutions.by_row). A fact whose
    readings differ takes the resolution on its finding (keyed by rule and dimension, resolutions._parse), never the
    fact's; every other fact the resolution on the fact."""
    from . import resolutions, status
    t, dim = f["ticker"], f.get("dimension") or ""
    k = lad.get((t, f["field"], dim, f["period"])) or {"readings": [], "tie": None}
    rs, g = k["readings"], k["tie"]
    restated = restated if restated is not None else k.get("restated")
    untagged = f.get("label") == "no_reference"
    differs = untagged and differ(rs)
    holds = g if untagged and g and g["holds"] else None
    second = second_accession(rs, f.get("accession")) if untagged and corroborated(rs) else None
    filer = k.get("filer_tag") if untagged and not differs and f["field"] == "ppe_category" else None
    ref = {}
    if filer:
        ref["filer_tag"] = filer
    if len(lineages(rs)) >= 2 or differs:
        ref["readings"] = rs
    if holds:
        ref["tie"] = {k_: holds[k_] for k_ in ("rule", "key", "accession", "concept", "total", "sum", "tolerance", "dimensions", "parts")}
    res = (resolutions.resolution_of(idx, "findings", t, f["field"], dim, f["period"], DIFFER) if differs
           else resolutions.resolution_of(idx, "facts", t, f["field"], dim, f["period"]))
    st = status.of_fact(f, res, restated, differ=differ_message(rs) if differs else None, tie=holds["rule"] if holds else None, reading=second, filer=bool(filer))
    return st, ref


def check_columns(st: dict) -> tuple[str, str]:
    """A fact's state as the taxonomy row's (check, check_method), from the one ladder: agree / xbrl; corroborated by a
    tie or a second reading; no_reference / label:no_reference (citation only); explained by what explains it; differs
    when open (rule:fact_readings_differ for readings that differ, xbrl for a cell against its tag)."""
    by = st.get("by") or ""
    if st["state"] == "checked":
        return ("agree", by) if by in ("xbrl", "mapping:filer_tag") else ("corroborated", by)  # the company's own tag is a twin: the value is in its instance
    if st["state"] == "explained":
        return ("no_reference", by) if by == "label:no_reference" else ("explained", by)
    return "differs", by if by.startswith("rule:") else "xbrl"


# ── loaders (the database, and the distilled instances on disk; never fetched) ───────────────────────────────────────
def instance_totals(cik, accession: str, concepts: set[str]) -> dict:
    """{(accession, concept, end): value} for the company totals (no dimension member) of `concepts` the filing tagged,
    from the distilled instance on disk (data/raw/<cik>/filings/<accession>.facts.json, keys "concept\\tmember\\tend").
    Empty when it is not there: no total read, no tie."""
    from .ingest.edgar import RAW
    if cik is None or not accession:
        return {}
    p = RAW / f"{int(cik):010d}" / "filings" / f"{accession}.facts.json"
    if not p.exists():
        return {}
    out = {}
    for k, v in json.loads(p.read_text()).items():
        concept, member, end = k.split("\t")
        if not member and concept in concepts:
            out[(accession, concept, end)] = v
    return out


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def load(con, tickers: list[str], rules: list[dict]) -> dict:
    """What the readings and the ties read, for `tickers`: {facts, extractions (note_extractions with the filing's
    date, form and report period), totals}. `rules` names the tie rules (check parts_tie) and so the concepts to read."""
    tickers = list(tickers)
    has = lambda n: bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [n]).fetchone()[0])
    cols = lambda n: {r[0] for r in con.execute("select column_name from information_schema.columns where table_name = ?", [n]).fetchall()}
    need = {"facts": {"accession", "extraction_ids", "period_end"}, "note_extractions": {"extraction_id", "accession", "scale"}, "documents": {"accession", "filed", "form", "period", "cik"}}
    if not all(has(n) and need[n] <= cols(n) for n in need):
        return {"facts": [], "extractions": [], "totals": {}}  # a database without the note tables (or a hand-built one): no readings, no ties
    facts = _rows(con, "select ticker, field, dimension, period, period_end, value, label, accession, extraction_ids from facts where ticker in (select unnest(?))", tickers)
    ext = _rows(con, "select n.extraction_id, n.accession, n.ticker, n.field, n.dimension, n.period_end, n.value, n.scale, d.filed, d.form, d.period from note_extractions n "
                     "left join documents d using (accession) where n.ticker in (select unnest(?))", tickers)
    ties = [r for r in rules if r.get("check") == TIE_CHECK]
    concepts = {c for r in ties for c in r["params"]["concepts"]}
    fields = {r["params"]["field"] for r in ties}
    ciks = {d["accession"]: d["cik"] for d in _rows(con, "select accession, cik from documents where ticker in (select unnest(?))", tickers)}
    totals = {}
    for acc in sorted({f["accession"] for f in facts if f["field"] in fields}):
        totals |= instance_totals(ciks.get(acc), acc, concepts)
    return {"facts": facts, "extractions": ext, "totals": totals}


def by_fact(data: dict, rules: list[dict]) -> dict:
    """{(ticker, field, dimension, period): {"readings": [...], "tie": the group of its newest reading under the field's
    tie rule, or None}} over `data` (load()), and the groups themselves under the key "groups" ({group key: group})."""
    by_id = {e["extraction_id"]: e for e in data["extractions"]}
    gs = {}
    for r in rules:
        if r.get("check") == TIE_CHECK:
            for g in groups(r["id"], r["params"], data["facts"], data["extractions"], data["totals"]):
                gs[g["key"]] = g
    out = {"groups": gs}
    for f in data["facts"]:
        out[(f["ticker"], f["field"], f["dimension"] or "", f["period"])] = {"readings": readings_of(f, by_id), "tie": gs.get(key(f["ticker"], f["field"], f["period"], f["accession"]))}
    return out


def ladder(con, tickers: list[str], rules: list[dict] | None = None) -> dict:
    """by_fact over load(): what every caller of fact_state reads. `rules` defaults to the rules on file."""
    if rules is None:
        from .rules import load as load_rules
        try:
            rules = load_rules()
        except (ValueError, OSError):
            rules = []
    out = by_fact(load(con, tickers, rules), rules)
    # the restatement guard of a fact whose cell differs from its tag (proof._restated), read once here, so a caller
    # with no database at hand (gold.compare) climbs the same ladder
    from .proof import _restated
    for k, v in out.items():
        if k != "groups":
            v["restated"] = None
            v["filer_tag"] = None
    # the company's own tag (ledger/filertag.py): a PP&E fact whose category it checks carries the record, read once here
    from .filertag import record, verdicts, verified
    from .taxonomy import asset_types
    types = asset_types()
    tags = verdicts(con, list(tickers))
    for (t, name), tag in tags.items():  # every fact of a category the tag checks, whatever load() could read
        if verified((types.get(t) or {}).get(name), tag):
            rec = record(tag)
            for r in tag["readings"]:
                out.setdefault((t, "ppe_category", name, r["period"]), {"readings": [], "tie": None, "restated": None})["filer_tag"] = rec
    for f in _rows(con, "select ticker, field, dimension, period, accession, reference from facts where ticker in (select unnest(?)) and label = 'unresolved'", list(tickers)) if len(out) > 1 else []:  # facts on file
        k = (f["ticker"], f["field"], f["dimension"] or "", f["period"])
        if k in out:
            out[k]["restated"] = _restated(con, f["ticker"], f)
    return out
