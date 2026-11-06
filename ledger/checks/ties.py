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

from ..core import config
from ..core.ids import split_ids

TIE_CHECK = "parts_tie"  # the check behind every *_tie rule on the facts (rules/ppe_categories_tie.yaml and its two siblings)
DIFFER = "fact_readings_differ"  # the rule whose finding opens an untagged fact read two ways (status.DIFFER is the same id)
TOTAL_LIKE = re.compile(r"^\s*(total|subtotal|sub-total|gross|net)\s*[:.]?\s*$", re.I)  # a dimension that is itself a total, as the whole label


# ── readings ─────────────────────────────────────────────────────────────────────────────────────────────────────────
def readings_of(fact: dict, by_id: dict) -> list[dict]:
    """The readings behind a fact: [{accession, filed, form, period, value, scale}], oldest filing first, one per
    extraction id the fact lists (one per filing: an extraction id is accession|field|dimension|period_end). `period`
    is the filing's own report period (documents.period), its lineage: a 10-K/A carries its original's."""
    out = [by_id[i] for i in split_ids(fact.get("extraction_ids")) if i in by_id]
    keys = ("accession", "filed", "form", "period", "value", "scale", "extraction_id", "cell_text")
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
    from ..web.cards import money
    return "readings differ across filings: " + " vs ".join(f"{money(r['value'])} in {r['accession']} (filed {str(r['filed'] or '')[:10]})" for r in rs)


def differ_findings(facts: list[dict], extractions: list[dict]) -> list[dict]:
    """[{ticker, field, period, subject, message}]: one per untagged fact (label no_reference) whose readings differ.
    The rule (rules.readings_differ) writes these to `exceptions`; Reconcile's queue (app._flow) reads them live from
    the same function, as Proof's ladder does, so a database whose rules ran before a change to the readings never shows
    Proof one count and Reconcile another (F-FL1)."""
    by_id = {e["extraction_id"]: e for e in extractions}
    out = []
    for f in facts:
        if f.get("label") != "no_reference":
            continue
        rs = readings_of(f, by_id)
        if differ(rs):
            out.append({"ticker": f["ticker"], "field": f["field"], "period": f["period"], "subject": f.get("dimension") or "",
                        "message": f"{f['field']} {f.get('dimension') or ''} {f['period']}: {differ_message(rs)}".replace("  ", " ")})
    return out


# ── restatement: one fact's readings that disagree, and which one the dataset uses ──────────────────────────────────
def _same(a, b, scale: int) -> bool:
    return a is not None and b is not None and not config.restated(min(a, b), max(a, b), scale)


def _filing(r: dict) -> str:
    return f"{r.get('form') or '10-K'} {str(r.get('filed') or '')[:10]}".strip()


def restatement(rs: list[dict], used: str | None, value=None) -> dict | None:
    """The one answer to "do the readings of this fact disagree, and which is used" (T-RS, every view reads it): None
    when they agree (`differ`, config.RESTATEMENT_TOLERANCE); else the readings grouped in filing order by figure, as
    filed (`cell_text`), the reading the dataset uses, the extraction ids of the superseded readings (a figure other than
    the one used) and the pair to compare, oldest superseded against the one used. Display only: the row's state stays
    what status decides (a tagged fact checked by its XBRL twin stays checked; an untagged one stays open by
    fact_readings_differ until a person explains it).

    The reading used is the one from the fact's own accession (`used`), and only when its figure is the fact's `value`
    (within the rounding of its table; `value` None skips that test). When neither holds the line ends "Source reading
    not found" (`source` "not_found", never a good word): nothing is guessed, no reading is called superseded and there
    is no pair to compare.

        {"line": "Restated: 105,362 (10-K 2024-07-30) → 87,464 (10-K 2025-07-30, 10-K 2026-07-29) · dataset uses 87,464 (10-K 2026-07-29)",
         "steps": [{"cell_text", "value", "filings": [{accession, form, filed, extraction_id}]}], "used": {...} | None,
         "source": "found" | "not_found", "superseded": [ids], "compare": {"a", "b"} | None}"""
    from ..core.states import RESTATED, SOURCE_NOT_FOUND
    rs = [r for r in rs if r.get("value") is not None]
    if not differ(rs):
        return None
    scale = max(max(int(r.get("scale") or 1), 1) for r in rs)
    u = next((r for r in rs if r.get("accession") == used), None) if used else None
    if u is not None and value is not None and not _same(u["value"], value, max(int(u.get("scale") or 1), 1)):
        u = None  # the reading from that filing does not carry the dataset's figure: not the source
    steps: list[dict] = []
    for r in rs:  # oldest filing first (readings_of): a run of filings printing the same figure is one step
        if steps and _same(steps[-1]["value"], r["value"], scale):
            steps[-1]["filings"].append(r)
        else:
            steps.append({"value": r["value"], "cell_text": r.get("cell_text") or f"{r['value']:,}", "filings": [r]})
    sup = [r for r in rs if u is not None and not _same(r["value"], u["value"], scale)]
    shape = lambda r: {k: r.get(k) for k in ("accession", "form", "filed", "extraction_id", "cell_text", "value")} | {"filed": str(r.get("filed") or "")[:10] or None}
    figure = lambda r: r.get("cell_text") or f"{r['value']:,}"
    line = (f"{RESTATED}: " + " → ".join(f"{s['cell_text']} ({', '.join(_filing(f) for f in s['filings'])})" for s in steps)
            + (f" · dataset uses {figure(u)} ({_filing(u)})" if u is not None else f" · {SOURCE_NOT_FOUND}"))
    return {"line": line, "steps": [{"value": s["value"], "cell_text": s["cell_text"], "filings": [shape(f) for f in s["filings"]]} for s in steps],
            "used": shape(u) if u is not None else None, "source": "found" if u is not None else "not_found",
            "superseded": [r.get("extraction_id") for r in sup if r.get("extraction_id")],
            "compare": {"a": sup[0].get("extraction_id"), "b": u.get("extraction_id")} if u is not None and sup and sup[0].get("extraction_id") and u.get("extraction_id") else None}


def restatements(con, tickers: list[str], extraction_id: str | None = None) -> dict:
    """{(ticker, field, dimension, period): restatement(...)} for every fact of `tickers` whose readings disagree, read
    from facts and note_extractions (no instance, no fetch): what the gold set, the evidence page and Reconcile read
    when they hold no ladder. With `extraction_id`, only the fact that cites it, and only its readings are read."""
    has = lambda n: bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [n]).fetchone()[0])
    if not tickers or not all(has(n) for n in ("facts", "note_extractions", "documents")):
        return {}
    sql = "select ticker, field, dimension, period, value, accession, extraction_ids from facts where ticker in (select unnest(?))"
    facts = _rows(con, sql + (" and position(? in ',' || extraction_ids || ',') > 0" if extraction_id else ""), list(tickers), *([f",{extraction_id},"] if extraction_id else []))
    ids = sorted({i for f in facts for i in split_ids(f["extraction_ids"])})
    if not ids:
        return {}
    ext = _rows(con, "select n.extraction_id, n.accession, n.value, n.scale, n.cell_text, d.filed, d.form, d.period from note_extractions n "
                     "left join documents d using (accession) where n.extraction_id in (select unnest(?))", ids)
    by_id = {e["extraction_id"]: e for e in ext}
    out = {}
    for f in facts:
        rec = restatement(readings_of(f, by_id), f["accession"], f["value"])
        if rec:
            out[(f["ticker"], f["field"], f["dimension"] or "", f["period"])] = rec
    return out


def of_reading(con, ticker: str, extraction_id: str) -> dict:
    """{"restatement", "mark"} for one cited reading (/api/v1/evidence): the restatement of the one fact that cites it
    (looked up by the id, not the whole company), or None, and states.SUPERSEDED when this reading is one the dataset
    does not use, else None."""
    from ..core.states import SUPERSEDED
    rec = next(iter(restatements(con, [ticker], extraction_id).values()), None)
    return {"restatement": rec, "mark": SUPERSEDED if rec and extraction_id in rec["superseded"] else None}


def mark(cites: list[dict], rec: dict | None, key: str = "extraction_id") -> list[dict]:
    """The cited cells with `mark` (states.SUPERSEDED) on each superseded reading of `rec`, for the pages' crops."""
    from ..core.states import SUPERSEDED
    sup = set((rec or {}).get("superseded") or [])
    return [{**c, "mark": SUPERSEDED} if c.get(key) in sup else c for c in cites]


# ── segment basis: does a segment series mix filing vintages across a re-segmentation ─────────────────────────────────
SEGMENT_FIELDS = ("segment_revenue", "segment_capex")


def segment_basis(facts: list[dict], extractions: list[dict], fields=SEGMENT_FIELDS) -> list[dict]:
    """Per company and segment field, where each fiscal year's value comes from and whether the series mixes bases.

    A filing that prints a segment figure differently from an earlier filing (`restatement`) is one of two things, told
    apart by what the readings show and nothing else:
      re-segmentation  the segment set changed (`kind` "segments": the names that filing prints for the field differ
                       from the filing before it), or amounts moved between segments (`kind` "moved": for a year it
                       restated, two or more segments changed while the same names' total held within rounding);
      correction       any other changed figure (`kind` "correction"): "Figure printed differently in a later filing",
                       never called a change of segments.
    The newest re-segmentation is the series' `cutover`; every fact the dataset ships from a filing filed before it is on
    the earlier segments (`mixed`), because the newest filing printing that year did not restate it. A correction moves
    no basis. A segment dropped or added with no figure printed two ways leaves no trace here (reports/segment-basis.md).

    Returns [{ticker, field, cutover: {accession, form, filed, kind, why, changes: [{dimension, period, before, after}]} or
              None, cutovers: every re-segmentation, oldest first, corrections: the same shape, kind "correction",
              years: [{dimension, period, value, cell_text, accession, form, filed, readings, restatement, mixed}],
              mixed: [periods on earlier segments]}], sorted by ticker and field. Pure: nothing is read or decided here."""
    by_id = {e["extraction_id"]: e for e in extractions}
    series: dict = {}
    for f in facts:
        if f["field"] in fields:
            series.setdefault((f["ticker"], f["field"]), []).append(f)
    out = []
    for (t, fld), fs in sorted(series.items()):
        rows, cuts, printed, filed = [], {}, {}, {}
        for f in sorted(fs, key=lambda f: (f["period"], f.get("dimension") or "")):
            rs = readings_of(f, by_id)
            for r in rs:  # what each filing printed for each year, by segment name
                printed.setdefault(r["accession"], {}).setdefault(f["period"], {})[f.get("dimension") or ""] = (r["value"], max(int(r.get("scale") or 1), 1))
                filed[r["accession"]] = (str(r.get("filed") or "")[:10], r["accession"])
            rec = restatement(rs, f["accession"], f["value"])
            u = next((r for r in rs if r["accession"] == f["accession"]), None) or {}
            rows.append({"dimension": f.get("dimension") or "", "period": f["period"], "value": f["value"], "cell_text": u.get("cell_text"),
                         "accession": f["accession"], "form": u.get("form") or "10-K", "filed": str(u.get("filed") or "")[:10] or None,
                         "readings": [{k: (str(r.get(k) or "")[:10] or None) if k == "filed" else r.get(k) for k in ("accession", "form", "filed", "cell_text", "value")} for r in rs],
                         "restatement": rec})
            for a, b in zip((rec or {}).get("steps", []), (rec or {}).get("steps", [])[1:]):
                first, before = b["filings"][0], a["filings"][-1]  # the filing that first printed the year differently, and the one before it
                c = cuts.setdefault(first["accession"], {"accession": first["accession"], "form": first.get("form") or "10-K", "filed": first.get("filed"), "changes": []})
                c["changes"].append({"dimension": f.get("dimension") or "", "period": f["period"], "before": a["cell_text"], "after": b["cell_text"], "from": before["accession"]})
        order = sorted(filed, key=lambda acc: filed[acc])
        names = lambda acc: {d for yr in printed.get(acc, {}).values() for d in yr}
        for c in cuts.values():
            prev = next((x for x in reversed(order[:order.index(c["accession"])]) if names(x)), None) if c["accession"] in order else None
            gone, new_ = (sorted(names(prev) - names(c["accession"])), sorted(names(c["accession"]) - names(prev))) if prev else ([], [])
            moved = []
            for q in sorted({x["period"] for x in c["changes"]}):
                frm = {x["from"] for x in c["changes"] if x["period"] == q}
                old, now = (printed.get(next(iter(frm)), {}).get(q) or {}) if len(frm) == 1 else {}, printed.get(c["accession"], {}).get(q) or {}
                if len([x for x in c["changes"] if x["period"] == q]) >= 2 and old and set(old) == set(now):
                    unit = max(sc for _, sc in [*old.values(), *now.values()])
                    if abs(sum(v for v, _ in old.values()) - sum(v for v, _ in now.values())) <= unit * config.RESTATEMENT_TOLERANCE * (len(now) + 1):
                        moved.append(q)
            if gone or new_:
                c |= {"kind": "segments", "why": "segment names differ: " + "; ".join(x for x in (f"no longer printed {', '.join(gone)}" if gone else "", f"new {', '.join(new_)}" if new_ else "") if x)}
            elif moved:
                c |= {"kind": "moved", "why": f"amounts moved between segments, the total unchanged ({', '.join(moved)})"}
            else:
                c |= {"kind": "correction", "why": "Figure printed differently in a later filing"}
        key = lambda c: (str(c["filed"] or ""), c["accession"])
        reseg = sorted((c for c in cuts.values() if c["kind"] != "correction"), key=key)
        cut = reseg[-1] if reseg else None
        for r in rows:
            r["mixed"] = bool(cut) and str(r["filed"] or "") < str(cut["filed"] or "")
        out.append({"ticker": t, "field": fld, "cutover": cut, "cutovers": reseg, "corrections": sorted((c for c in cuts.values() if c["kind"] == "correction"), key=key),
                    "years": rows, "mixed": sorted({r["period"] for r in rows if r["mixed"]})})
    return out


def basis_message(s: dict, period: str) -> str:
    """One finding's words: the year, the filing it ships from, the re-segmenting filing, why it is one, what it restated."""
    c = s["cutover"]
    src = sorted({(r["filed"] or "", r["form"], r["accession"]) for r in s["years"] if r["period"] == period and r["mixed"]})
    ch = "; ".join(f"{x['dimension']} {x['period']} {x['before']} → {x['after']}" for x in c["changes"][:6]) + (f"; {len(c['changes']) - 6} more" if len(c["changes"]) > 6 else "")
    return (f"{s['field']} {period} ships from " + ", ".join(f"{fm} {fd} ({a})" for fd, fm, a in src)
            + f"; {c['form']} {str(c['filed'] or '')[:10]} ({c['accession']}) re-segmented ({c['why']}) and has no {period} reading, so {period} stays on the earlier segments. Restated: {ch}")


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
    from ..web.cards import money
    n = len(g["parts"])
    which = f"{g['concept']}, the largest of {g['concepts_found']} revenue tags it carries" if g.get("pick") == "largest" and g.get("concepts_found", 1) > 1 else g["concept"]
    return (f"{n} part{'s' * (n != 1)} in {g['accession']} sum to {money(g['sum'])}; the filing tags {which} {money(g['total'])} for {g['period_end']} "
            f"(gap {money(g['sum'] - g['total'])}, tolerance on the sum ±{money(g['tolerance'])})")


# ── the one ladder: a fact's state, for Proof, Reconcile, the taxonomy rows and gold ─────────────────────────────────
def fact_state(f: dict, idx: dict, lad: dict, restated: str | None = None) -> tuple[dict, dict]:
    """(status state, the record it rests on) for a `facts` row `f` ({ticker, field, dimension, period, label,
    accession}). `lad` is by_fact(...) (proof.ladder); `idx` the resolutions index (resolutions.index). A fact whose
    readings differ takes the resolution on its finding (keyed by rule and dimension, resolutions._parse), never the
    fact's; every other fact the resolution on the fact."""
    from ..review import resolutions
    from ..core import status
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
    rec = restatement(rs, f.get("accession"), f.get("value"))
    if rec:  # shown on every view, tagged or not; never a state (status.of_fact decides that below)
        ref["restatement"] = rec
    if holds:
        ref["tie"] = {k_: holds[k_] for k_ in ("rule", "key", "accession", "concept", "total", "sum", "tolerance", "dimensions", "parts")}
    res = (resolutions.resolution_of(idx, "findings", t, f["field"], dim, f["period"], DIFFER) if differs
           else resolutions.resolution_of(idx, "facts", t, f["field"], dim, f["period"]))
    st = status.of_fact(f, res, restated, differ=differ_message(rs) if differs else None, tie=holds["rule"] if holds else None, reading=second, filer=bool(filer),
                        looked_up=k.get("instance", ABSENT))  # F17 review: a fact the ladder did not see is not looked up, never loaded by default
    return st, ref


def check_columns(st: dict) -> tuple[str, str]:
    """A fact's state as the taxonomy row's (check, check_method), from the one ladder: agree / xbrl; corroborated by a
    tie or a second reading; no_reference / label:no_reference (citation only); explained by what explains it; differs
    when open (rule:fact_readings_differ for readings that differ, xbrl for a cell against its tag)."""
    from ..core.states import LADDER_CHECK, ladder
    by = st.get("by") or ""
    check = LADDER_CHECK[ladder(st)]  # the company's own tag is a twin: the value is in its instance, so it reads agree
    if check == "not_checked":  # no state, or the instance never loaded (F17): nothing vouches, never a default pass
        return check, by if by == "label:not_looked_up" else "none"
    return check, (by if check != "differs" or by.startswith("rule:") else "xbrl")


# ── loaders (the database, and the distilled instances on disk; never fetched) ───────────────────────────────────────
_INSTANCES: dict = {}  # path -> ((mtime_ns, size), (state, facts)): one read per instance file version, across requests
_INSTANCE_LOCK = __import__("threading").Lock()  # the app serves requests on threads: one parse per file, never one per request
LOADED, ABSENT, UNREADABLE = "loaded", "absent", "unreadable"


def instance(cik, accession: str | None) -> tuple[str, dict]:
    """The one reading of a filing's XBRL instance on disk, for the ties, the ladder, Proof's lookup marker and the
    company's own tag (filertag.instance): (state, {(concept, member, end): value}). The distilled facts
    (data/raw/<cik>/filings/<accession>.facts.json) or else the stored XML (dimensions.parse_instance; nothing is
    written). state: loaded; absent (neither file: the lookup never ran); unreadable (a file that does not parse: no
    answer either, never "tags nothing"). Memoised per (path, mtime, size). Never fetched."""
    from ..ingest.edgar import RAW
    try:
        d = RAW / f"{int(cik):010d}" / "filings"
    except (TypeError, ValueError):
        return ABSENT, {}
    if not accession:
        return ABSENT, {}
    p = next((x for x in (d / f"{accession}.facts.json", d / f"{accession}.xml") if x.exists()), None)
    if p is None:
        return ABSENT, {}
    try:
        st = p.stat()
        stamp = (st.st_mtime_ns, st.st_size)
    except OSError:
        return ABSENT, {}
    hit = _INSTANCES.get(str(p))
    if hit and hit[0] == stamp:
        return hit[1]
    with _INSTANCE_LOCK:
        hit = _INSTANCES.get(str(p))
        if hit and hit[0] == stamp:
            return hit[1]
        try:
            if p.suffix == ".json":
                raw = json.loads(p.read_text())
                facts = {tuple(k.split("\t")): v for k, v in raw.items()}
                if any(len(k) != 3 for k in facts):
                    raise ValueError("a key is not concept, member, end")
            else:
                from ..ingest.reference.dimensions import parse_instance
                facts = parse_instance(p.read_bytes())
            hit = (stamp, (LOADED, facts))
        except Exception:  # does not parse: unreadable, said so (F17 review)
            hit = (stamp, (UNREADABLE, {}))
        _INSTANCES[str(p)] = hit
    return hit[1]


def instance_totals(cik, accession: str, concepts: set[str]) -> dict:
    """{(accession, concept, end): value} for the company totals (no dimension member) of `concepts` the filing tagged,
    from instance(): empty when it is absent or unreadable (no total read, no tie)."""
    state, facts = instance(cik, accession)
    return {(accession, concept, end): v for (concept, member, end), v in facts.items() if not member and concept in concepts}


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
    ext = _rows(con, "select n.extraction_id, n.accession, n.ticker, n.field, n.dimension, n.period_end, n.value, n.scale, n.cell_text, d.filed, d.form, d.period from note_extractions n "
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
        out[(f["ticker"], f["field"], f["dimension"] or "", f["period"])] = {"readings": readings_of(f, by_id), "tie": gs.get(key(f["ticker"], f["field"], f["period"], f["accession"])),
                                                                            "accession": f["accession"]}
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
    # the company's own tag (ledger/checks/filertag.py): a PP&E fact whose category it checks carries the record, read once here
    from .filertag import record, verdicts, verified
    from ..release.taxonomy import asset_types
    types = asset_types()
    tags = verdicts(con, list(tickers))
    for (t, name), tag in tags.items():  # every fact of a category the tag checks, whatever load() could read
        if verified((types.get(t) or {}).get(name), tag):
            rec = record(tag)
            for r in tag["readings"]:
                out.setdefault((t, "ppe_category", name, r["period"]), {"readings": [], "tie": None, "restated": None})["filer_tag"] = rec
    # F17: whether each fact's filing instance is on disk; without it an untagged fact's label is no answer (the lookup never ran)
    ciks = {r[0]: r[1] for r in con.execute("select accession, cik from documents where ticker in (select unnest(?))", [list(tickers)]).fetchall()} if len(out) > 1 else {}
    for k, v in out.items():
        if k != "groups" and v.get("readings") is not None and v.get("accession"):
            v["instance"] = instance(ciks.get(v["accession"]), v["accession"])[0]
    for f in _rows(con, "select ticker, field, dimension, period, accession, reference from facts where ticker in (select unnest(?)) and label = 'unresolved'", list(tickers)) if len(out) > 1 else []:  # facts on file
        k = (f["ticker"], f["field"], f["dimension"] or "", f["period"])
        if k in out:
            out[k]["restated"] = _restated(con, f["ticker"], f)
    return out
