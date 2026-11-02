"""Evidence for the note figures beyond the tag (T92, docs/PROOF.md "The ladder"): readings across filings, and ties to
the filing's tagged total.

The SEC tags almost none of the untagged note figures (PP&E by category, segments a filer does not tag), so a fact
labelled `no_reference` had only its citation. Two more checks are on file for it:

  readings   every 10-K that printed the figure (the next 10-K repeats the year as its comparative column). Two or more
             filings that agree are a second reading (`reading:<accession>`, key second_reading); readings that differ
             by more than config.RESTATEMENT_TOLERANCE are the `fact_readings_differ` finding, open until a person's
             resolution explains it. A label never explains a disagreement.
  ties       the parts one filing prints for a field and a date sum to the total the same filing tags in its XBRL
             instance (PropertyPlantAndEquipmentGross, total revenue, total capex): the `*_tie` rules in rules/. A tie
             that holds checks each untagged part (`rule:<id>_tie`, key tie); one that fails is the rule's finding.

Pure functions over rows (the rules engine and Proof call the same ones), plus loaders that read the database and the
distilled instances on disk (data/raw/<cik>/filings/<accession>.facts.json). Nothing is fetched."""
from __future__ import annotations

import json

from . import config

TIE_CHECK = "parts_tie"  # the check behind every *_tie rule on the facts (rules/ppe_categories_tie.yaml and its two siblings)


# ── readings ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def readings_of(fact: dict, by_id: dict) -> list[dict]:
    """The readings behind a fact: [{accession, filed, value, scale}], oldest filing first, one per extraction id the
    fact lists (one per filing: an extraction id is accession|field|dimension|period_end)."""
    out = [by_id[i] for i in (fact.get("extraction_ids") or "").split(",") if i in by_id]
    return sorted(({k: r.get(k) for k in ("accession", "filed", "value", "scale")} for r in out), key=lambda r: (str(r["filed"] or ""), r["accession"]))


def differ(rs: list[dict]) -> bool:
    """Readings that moved by more than config.RESTATEMENT_TOLERANCE of the coarsest rounding among them."""
    vals = [r["value"] for r in rs if r.get("value") is not None]
    return len(vals) >= 2 and config.restated(min(vals), max(vals), max(max(int(r.get("scale") or 1), 1) for r in rs))


def corroborated(rs: list[dict]) -> bool:
    """A second reading: two or more distinct filings read the figure, and they agree (not `differ`)."""
    return len({r.get("accession") for r in rs if r.get("accession")}) >= 2 and not differ(rs)


def differ_message(rs: list[dict]) -> str:
    from .cards import money
    return "readings differ across filings: " + " vs ".join(f"{money(r['value'])} in {r['accession']} (filed {str(r['filed'] or '')[:10]})" for r in rs)


# ── ties ─────────────────────────────────────────────────────────────────────────────────────────────────────────────
def tolerance(parts: list[dict]) -> int:
    """Half a rounding unit (config.RESTATEMENT_TOLERANCE) of the coarsest table among the parts, for each part and for
    the total: a sum of n figures rounded to a unit can sit n halves away from the exact total, and the total one more."""
    unit = max((max(int(p.get("scale") or 1), 1) for p in parts), default=1)
    return int(unit * config.RESTATEMENT_TOLERANCE * (len(parts) + 1))


def total_of(totals: dict, accession: str, end: str, concepts: list[str], pick: str) -> tuple[str, int] | None:
    """The filing's own tagged total for `end` among `concepts`: the first on the list (`pick: first`), or the largest
    (`pick: largest`, revenue: a total tag beats a component tag in the same filing, as reference.normalize does)."""
    found = [(c, totals[(accession, c, end)]) for c in concepts if (accession, c, end) in totals]
    if not found:
        return None
    return max(found, key=lambda x: x[1]) if pick == "largest" else found[0]


def groups(rule_id: str, params: dict, facts: list[dict], extractions: list[dict], totals: dict) -> list[dict]:
    """Every group a tie rule judges: per ticker, a filing (accession) and a date, the parts that filing printed for
    `params.field`, against the total it tagged. Only groups that ship a fact (a fact of the field whose newest reading
    is that filing's) are judged: a comparative column a later 10-K replaced ships nothing. A group with no tagged
    total is not judged (no tie, nothing open). Returns [{rule, ticker, field, period, period_end, accession, parts:
    [{dimension, value, scale}], dimensions, sum, total, concept, tolerance, holds, key}]."""
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
    for (t, acc, end), period in sorted(shipped.items()):
        ps = parts.get((t, acc, end)) or []
        tot = total_of(totals, acc, end, params["concepts"], params.get("pick", "first"))
        if not ps or tot is None:
            continue
        s, tol = sum(int(p["value"]) for p in ps), tolerance(ps)
        out.append({"rule": rule_id, "ticker": t, "field": field_, "period": period, "period_end": end, "accession": acc,
                    "parts": sorted(({"dimension": p.get("dimension") or "", "value": int(p["value"]), "scale": int(p.get("scale") or 1)} for p in ps), key=lambda p: p["dimension"]),
                    "dimensions": sorted(p.get("dimension") or "" for p in ps), "sum": s, "total": int(tot[1]), "concept": tot[0], "tolerance": tol,
                    "holds": abs(s - int(tot[1])) <= tol, "key": key(t, field_, period, acc)})
    return out


def key(ticker: str, field_: str, period: str, accession: str) -> str:
    return f"{ticker}|{field_}|{period}|{accession}"


def fail_message(g: dict) -> str:
    from .cards import money
    n = len(g["parts"])
    return (f"{n} part{'s' * (n != 1)} in {g['accession']} sum to {money(g['sum'])}; the filing tags {g['concept']} {money(g['total'])} for {g['period_end']} "
            f"(gap {money(g['sum'] - g['total'])}, tolerance {money(g['tolerance'])})")


# ── loaders (the database, and the distilled instances on disk; never fetched) ───────────────────────────────────────
def instance_totals(cik, accession: str, concepts: set[str]) -> dict:
    """{(accession, concept, end): value} for the company totals (no dimension member) of `concepts` the filing tagged,
    from the distilled instance on disk (data/raw/<cik>/filings/<accession>.facts.json). Empty when it is not there:
    no total read, no tie."""
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
    """What the readings and the ties read, for `tickers`: {facts, extractions (note_extractions with the filing date),
    totals}. `rules` names the tie rules (check parts_tie) and so the concepts to read."""
    tickers = list(tickers)
    has = lambda n: bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [n]).fetchone()[0])
    if not (has("facts") and has("note_extractions")):
        return {"facts": [], "extractions": [], "totals": {}}
    facts = _rows(con, "select ticker, field, dimension, period, period_end, value, label, accession, extraction_ids from facts where ticker in (select unnest(?))", tickers)
    ext = _rows(con, "select n.extraction_id, n.accession, n.ticker, n.field, n.dimension, n.period_end, n.value, n.scale, d.filed from note_extractions n "
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
        g = gs.get(key(f["ticker"], f["field"], f["period"], f["accession"]))
        out[(f["ticker"], f["field"], f["dimension"] or "", f["period"])] = {"readings": readings_of(f, by_id), "tie": g}
    return out
