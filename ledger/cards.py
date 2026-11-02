"""Evidence cards for a company's trail: for every item, in plain words, what we found, where it is in the filing (a
link that opens the filing at that row, and the screenshot of the rendered re-read when there is one), and how we know.

The card is presentation only. It never changes an item's state: `status.state` decides checked / explained / open,
and the card says the same thing in a sentence a person can check by clicking. The internal words (`by`, `located`,
`twin`, `reason`) stay in the API for the tests; the page shows the card.

    card = {"found": str | None, "where": [{"label", "link", "shot"}], "how": {"tone": ok|info|wait|bad, "text": str}}
"""
from __future__ import annotations

import json
from pathlib import Path

from . import evidence, status, store
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
    label = f"10-K {filed} · “{c['row_label']}” · {col} · {c['cell_text']}"
    return {"label": label, "link": deep_link(d.get("url"), c.get("row_label"), c.get("cell_text")),
            "shot": _shot(ev, c["extraction_id"], c.get("cell_text"))}


def _how(it: dict, name: str, defs: dict, found_value=None) -> dict:
    """One plain sentence for the item's state and the evidence behind it."""
    by, state = it.get("by") or "", it.get("state")
    ref = it.get("ref") or {}
    if state in ("open", "blocked"):
        text = it.get("needs") or it.get("reason") or "Needs a person."
        if by == "label:to_confirm":
            text = "Proposed category. Review in Reconcile."
        elif by == "label:not_extracted":
            text = "In SEC XBRL, not extracted. Re-read required."
        return {"tone": "wait" if by == "label:to_confirm" else "bad", "text": text}
    if by == "xbrl":
        same = found_value is None or ref.get("reference") == found_value
        return {"tone": "ok", "text": f"Matches SEC XBRL: {money(ref.get('reference'))}" if same
                else f"Matches SEC XBRL within rounding: {money(ref.get('reference'))}"}
    if by == "quote":
        return {"tone": "ok", "text": "Quote matches source"}
    if by == "located":
        return {"tone": "ok", "text": "Income statement and cash-flow statement located"}
    if by == "gate":
        return {"tone": "ok", "text": "No blocking items"}
    if by.startswith("mapping:"):
        return {"tone": "ok", "text": f"Confirmed: {by.split(':', 1)[1]}"}
    if by == "label:no_reference":
        return {"tone": "info", "text": "No external source. Citation verified only."}
    if by == "label:not_reported":
        return {"tone": "info", "text": "Not reported (none in SEC XBRL)"}
    if by.startswith("definition:"):
        why = ((defs or {}).get(by.split(":", 1)[1]) or {}).get("why") if isinstance(defs, dict) else None
        return {"tone": "info", "text": "Definition differs from SEC XBRL" + (f": {why}" if why else "")}
    if by.startswith("resolution:"):
        return {"tone": "info", "text": f"Reviewer decision: {it.get('reason') or ''}".strip(": ")}
    if by.startswith("rule:"):
        return {"tone": "info", "text": f"Rule: {by.split(':', 1)[1].replace('_', ' ')}"}
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
        it["card"] = {"found": f"{d.get('form', '10-K')} · FY ending {d.get('period')} · filed {str(d.get('filed') or '')[:10]}" if d else None,
                      "where": [{"label": "sec.gov", "link": d.get("url"), "shot": None}] if d.get("url") else [],
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
            found += " (revenue − cost of revenue − operating income)"
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
        found = f"“{it.get('name')}” → {member}" if member else f"“{it.get('name')}” → unmapped"
        where = [{"label": f"Basis: {e['evidence']}", "link": None, "shot": None}] if e.get("evidence") else []
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

    # why you are here: the newest report read, and any report the SEC has that the ledger has not read yet
    newest = max(docs.values(), key=lambda d: str(d.get("filed") or ""), default=None)
    watch_file = store.ROOT / "data" / "watch.json"
    try:
        w = json.loads(watch_file.read_text()) if watch_file.exists() else {}
    except (OSError, ValueError):
        w = {}
    unread = [f for f in (w.get("new") or []) if f.get("ticker") == t]
    trail["status"] = status_line(con, trail, newest, w)
    trail["summary"] = {"newest": {"form": newest.get("form"), "period": str(newest.get("period") or "")[:10], "filed": str(newest.get("filed") or "")[:10], "url": newest.get("url")} if newest else None,
                        "unread": [{"form": f.get("form"), "period": f.get("period"), "filed": f.get("filed")} for f in unread],
                        "watched_at": str(w.get("checked_at") or "")[:10] or None}

    for st in stages.values():  # anything not covered above (a finding, a release block) still says how in words
        for it in st.get("all", []):
            it.setdefault("card", {"found": None, "where": [], "how": _how(it, name, defs)})
    return trail


def _version_key(v: str):
    return tuple(int(x) for x in v.lstrip("v").split(".") if x.isdigit())


def last_release(ticker: str) -> dict | None:
    """The newest signed release whose scope holds `ticker`: version, signer, date, and its values and facts for it."""
    import csv
    rel = store.ROOT / "releases"
    for d in sorted((p for p in rel.iterdir() if p.is_dir() and p.name.startswith("v")), key=lambda p: _version_key(p.name), reverse=True) if rel.exists() else []:
        sig = d / "SIGNOFF.json"
        if not sig.exists():
            continue
        so = json.loads(sig.read_text())
        if ticker not in ((so.get("checklist") or {}).get("scope") or []):
            continue
        read = lambda name: [r for r in csv.DictReader(open(d / name)) if r.get("ticker") == ticker] if (d / name).exists() else []
        return {"version": so.get("version") or d.name, "signed_by": so.get("signed_by"), "signed_at": str(so.get("signed_at") or "")[:10],
                "values": read("values.csv"), "facts": read("facts.csv")}
    return None


def _num(x):
    try:
        return int(float(x)) if x not in (None, "") else None
    except ValueError:
        return None


def since_release(con, ticker: str, rel: dict | None) -> dict | None:
    """What changed for `ticker` since its last signed release: figures added, changed, removed (values and facts)."""
    if not rel:
        return None
    now_v = {(r["field"], r["period"]): r["value"] for r in _rows(con, 'select field, period, value from "values" where ticker = ? and value is not null', ticker)}
    now_f = {(r["field"], r["dimension"] or "", r["period"]): r["value"] for r in _rows(con, "select field, dimension, period, value from facts where ticker = ?", ticker)}
    was_v = {(r["field"], r["period"]): _num(r["value"]) for r in rel["values"] if _num(r.get("value")) is not None}
    was_f = {(r["field"], r.get("dimension") or "", r["period"]): _num(r["value"]) for r in rel["facts"]}
    out = {"added": [], "changed": [], "removed": []}
    for now, was in ((now_v, was_v), (now_f, was_f)):
        for k, v in now.items():
            if k not in was:
                out["added"].append(" · ".join(x for x in k if x) + f": {money(v)}")
            elif was[k] != v:
                out["changed"].append(" · ".join(x for x in k if x) + f": {money(was[k])} → {money(v)}")
        out["removed"] += [" · ".join(x for x in k if x) for k in was if k not in now]
    return out


def status_line(con, trail: dict, newest: dict | None, watch: dict) -> dict:
    """The company's state as of now: current through (newest report, next expected), SEC last checked, trust split,
    shipped (last signed release) and what changed since."""
    from datetime import date, datetime, timedelta, timezone
    nxt = None
    if newest and newest.get("period") and newest.get("filed"):
        try:
            p, f = date.fromisoformat(str(newest["period"])[:10]), date.fromisoformat(str(newest["filed"])[:10])
            nxt = (p + timedelta(days=365) + (f - p)).isoformat()
        except ValueError:
            nxt = None
    stages = trail["stages"]
    figures = [i for s in ("values", "facts") for i in stages.get(s, {}).get("all", []) if (i.get("ref") or {}).get("field")]
    waiting = sum(len(st.get("open", [])) for st in stages.values())
    matched = sum(i.get("by") == "xbrl" and i.get("state") == "checked" for i in figures)
    reading = sum(i.get("state") == "explained" for i in figures)
    quotes = sum(1 for s in ("statements", "planned") for i in stages.get(s, {}).get("all", []) if i.get("state") == "checked")
    rel = last_release(trail["ticker"])
    checked_at = watch.get("checked_at")
    age = None
    if checked_at:
        try:
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(checked_at)).total_seconds() / 3600
        except ValueError:
            age = None
    return {"as_of": datetime.now().strftime("%-d %b %Y, %H:%M"),
            "current_through": {"form": newest.get("form"), "period": str(newest.get("period") or "")[:10], "filed": str(newest.get("filed") or "")[:10]} if newest else None,
            "next_expected": nxt, "sec_checked_hours_ago": None if age is None else round(age),
            "figures": len(figures), "matched": matched, "reading_only": reading, "waiting": waiting, "quotes": quotes,
            "shipped": {k: rel[k] for k in ("version", "signed_by", "signed_at")} if rel else None,
            "since": since_release(con, trail["ticker"], rel)}
