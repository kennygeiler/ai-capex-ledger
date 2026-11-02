"""Evidence cards for a company's trail: for every item, in plain words, what we found, where it is in the filing (a
link that opens the filing at that row, and the screenshot of the rendered re-read when there is one), and how we know.

The card is presentation only. It never changes an item's state: `status.state` decides checked / explained / open,
and the card says the same thing in a sentence a person can check by clicking. The internal words (`by`, `located`,
`twin`, `reason`) stay in the API for the tests; the page shows the card.

    card = {"found": str | None, "where": [{"label", "link", "shot"}], "how": {"tone": ok|info|wait|bad, "text": str}}
"""
from __future__ import annotations

from pathlib import Path

from . import evidence, status
from .definitions import load as load_definitions
from .taxonomy import deep_link, quote_link

FIELD = {"revenue": "Revenue", "capex": "Capital spending (capex)", "opex": "Operating costs (opex)",
         "cost_of_revenue": "Cost of revenue", "operating_income": "Operating income",
         "segment_capex": "Capex by segment", "segment_revenue": "Revenue by segment", "ppe_category": "Property by category",
         "finance_lease_liability": "Finance lease liabilities", "purchase_commitments": "Purchase commitments"}
OPEX_PARTS = ("revenue", "cost_of_revenue", "operating_income")


def money(v) -> str:
    """Whole dollars as people read them: $131,819M for millions, the exact figure below a million."""
    if v is None:
        return "—"
    v = int(v)
    sign = "−" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000 and a % 1_000_000 == 0:
        return f"{sign}${a // 1_000_000:,}M"
    if a >= 1_000_000:
        return f"{sign}${a / 1_000_000:,.1f}M"
    return f"{sign}${a:,}"


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _shot(ev: dict, extraction_id: str, cell_text: str | None) -> str | None:
    """The screenshot of the rendered re-read, served at /evidence/<file>, only while it shows the current cell."""
    e = ev.get(extraction_id) or {}
    if not e.get("img") or e.get("cell") not in (None, cell_text):
        return None
    return "/evidence/" + Path(e["img"]).name


def _cell(c: dict, docs: dict, ev: dict) -> dict:
    d = docs.get(c["accession"]) or {}
    filed = str(d.get("filed") or "")[:10]
    col = " ".join((c.get("column_label") or "").replace("|", " ").split())
    label = f"10-K filed {filed}: row “{c['row_label']}”, column “{col}” shows {c['cell_text']}"
    return {"label": label, "link": deep_link(d.get("url"), c.get("row_label"), c.get("cell_text")),
            "shot": _shot(ev, c["extraction_id"], c.get("cell_text"))}


def _how(it: dict, name: str, defs: dict, found_value=None) -> dict:
    """One plain sentence for the item's state and the evidence behind it."""
    by, state = it.get("by") or "", it.get("state")
    ref = it.get("ref") or {}
    if state in ("open", "blocked"):
        text = it.get("needs") or it.get("reason") or "Needs a person."
        if by == "label:to_confirm":
            text = "The robot proposed this category; approve or change it in Reconcile → Asset types."
        elif by == "label:not_extracted":
            text = "The SEC's copy has this number but the robot didn't read it from the filing. Needs a re-read."
        return {"tone": "wait" if by == "label:to_confirm" else "bad", "text": text}
    if by == "xbrl":
        same = found_value is None or ref.get("reference") == found_value
        return {"tone": "ok", "text": f"Matches the SEC's own tagged copy: {money(ref.get('reference'))}." if same
                else f"Within rounding of the SEC's own tagged copy: {money(ref.get('reference'))}."}
    if by == "quote":
        return {"tone": "ok", "text": "Found word for word in the source document."}
    if by == "located":
        return {"tone": "ok", "text": "The income statement and the cash-flow statement were both found in this report."}
    if by == "gate":
        return {"tone": "ok", "text": "Nothing blocks this company's release."}
    if by.startswith("mapping:"):
        return {"tone": "ok", "text": f"A person confirmed the category {by.split(':', 1)[1]}."}
    if by == "label:no_reference":
        return {"tone": "info", "text": f"{name} publishes no machine-readable copy of this number, so nothing outside the filing confirms it. "
                                        "Only the reading is checked: open the filing and look at the cell."}
    if by == "label:not_reported":
        return {"tone": "info", "text": f"{name}'s report has no such line, and the SEC's copy has none either."}
    if by.startswith("definition:"):
        why = ((defs or {}).get(by.split(":", 1)[1]) or {}).get("why") if isinstance(defs, dict) else None
        return {"tone": "info", "text": "Differs from the SEC's copy on purpose, by a written definition" + (f": {why}" if why else ".")}
    if by.startswith("resolution:"):
        return {"tone": "info", "text": f"Decided by a person: {it.get('reason') or ''}".strip()}
    if by.startswith("rule:"):
        return {"tone": "info", "text": f"Explained by a written rule ({by.split(':', 1)[1].replace('_', ' ')}): {it.get('reason') or ''}".strip()}
    return {"tone": "info", "text": it.get("reason") or ""}


def add(con, trail: dict) -> dict:
    """Give every item of `trail` (proof.company's result) a `card`, in place, and return the trail."""
    t, name = trail["ticker"], trail.get("name") or trail["ticker"]
    docs = {d["accession"]: d for d in _rows(con, "select accession, form, period, filed, url from documents where ticker = ?", t)}
    ev = evidence.load_all()
    defs = (load_definitions() or {}).get(t, {})
    stages = trail["stages"]

    # reports found: the filing itself
    for it in stages.get("ingest", {}).get("all", []):
        acc = (it.get("ref") or {}).get("accession")
        d = docs.get(acc) or {}
        it["card"] = {"found": f"Annual report ({d.get('form', '10-K')}) for the year ending {d.get('period')}, filed {str(d.get('filed') or '')[:10]}" if d else None,
                      "where": [{"label": "The report on sec.gov", "link": d.get("url"), "shot": None}] if d.get("url") else [],
                      "how": _how(it, name, defs)}

    # main numbers: the value, the cells it was read from, the SEC's copy
    vals = {(v["field"], v["period"]): v for v in _rows(con, 'select field, period, value, extraction_ids from "values" where ticker = ?', t)}
    ext = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, accession, field, row_label, column_label, cell_text from extractions where ticker = ?", t)}
    for it in stages.get("values", {}).get("all", []):
        ref = it.get("ref") or {}
        v = vals.get((ref.get("field"), ref.get("period")))
        if not v:
            it["card"] = {"found": None, "where": [], "how": _how(it, name, defs)}
            continue
        ids = [i for i in (v.get("extraction_ids") or "").split(",") if i in ext]
        cells = [_cell(ext[i], docs, ev) for i in ids]
        found = money(v["value"]) if v["value"] is not None else "nothing (blank)"
        if ref.get("field") == "opex" and len(ids) > 1:
            found += " = revenue − cost of revenue − operating income, from the cells below"
        it["card"] = {"found": found, "where": cells, "how": _how(it, name, defs, v["value"])}

    # footnote numbers: the fact, its cells in the notes
    facts = {(f["field"], f["dimension"] or "", f["period"]): f for f in _rows(con, "select field, dimension, period, value, extraction_ids from facts where ticker = ?", t)}
    notes = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, accession, row_label, column_label, cell_text from note_extractions where ticker = ?", t)}
    for it in stages.get("facts", {}).get("all", []):
        ref = it.get("ref") or {}
        f = facts.get((ref.get("field"), ref.get("dimension") or "", ref.get("period")))
        if not f:
            it["card"] = {"found": None, "where": [], "how": _how(it, name, defs)}
            continue
        ids = [i for i in (f.get("extraction_ids") or "").split(",") if i in notes]
        it["card"] = {"found": money(f["value"]), "where": [_cell(notes[i], docs, ev) for i in ids], "how": _how(it, name, defs, f["value"])}

    # AI quotes: the sentence, opened at its words
    stm = {s["statement_id"]: s for s in _rows(con, "select s.statement_id, s.quote, t.url, t.kind, t.date from ai_statements s join texts t on t.text_id = s.text_id where s.ticker = ?", t)}
    for it in stages.get("statements", {}).get("all", []):
        s = stm.get((it.get("ref") or {}).get("statement_id"))
        it["card"] = {"found": f"“{s['quote']}”" if s else None,
                      "where": [{"label": f"{(s['kind'] or 'source').replace('_', ' ')} dated {str(s['date'] or '')[:10]}", "link": quote_link(s["url"], s["quote"]), "shot": None}] if s and s.get("url") else [],
                      "how": _how(it, name, defs)}

    # category labels: the company's label and the proposed standard category
    from .taxonomy import asset_types
    entries = asset_types().get(t) or {}
    for it in stages.get("mapping", {}).get("all", []):
        e = entries.get(it.get("name")) or {}
        member = e.get("standard_type")
        found = f"{name} calls it “{it.get('name')}”" + (f" → standard category {member}" if member else " → no standard category yet")
        where = [{"label": f"Evidence for the category: {e['evidence']}", "link": None, "shot": None}] if e.get("evidence") else []
        it["card"] = {"found": found, "where": where, "how": _how(it, name, defs)}

    # plans and projects: the quote, opened at its words
    from .taxonomy import rows as taxonomy_rows
    planned = {(r["category"], r["fiscal_year"], r["reported_name"]): r for r in taxonomy_rows(con, [t]) if r["measure"] == "planned"}
    for it in stages.get("planned", {}).get("all", []):
        ref = it.get("ref") or {}
        r = planned.get((ref.get("category"), ref.get("fiscal_year"), ref.get("reported_name")))
        it["card"] = {"found": f"“{r['quote']}”" if r and r.get("quote") else None,
                      "where": [{"label": "The source document", "link": r.get("source_url"), "shot": None}] if r and r.get("source_url") else [],
                      "how": _how(it, name, defs)}

    for st in stages.values():  # anything not covered above (a finding, a release block) still says how in words
        for it in st.get("all", []):
            it.setdefault("card", {"found": None, "where": [], "how": _how(it, name, defs)})
    return trail
