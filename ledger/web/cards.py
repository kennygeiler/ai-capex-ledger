"""Evidence cards for a company's trail: for every item, in plain words, what we found, where it is in the filing (a
link that opens the stored filing at that cell, and the crop of the cell with its state, crops.cells), and how we know.

The card is presentation only. It never changes an item's state: `status.state` decides checked / explained / open,
and the card says the same thing in a sentence a person can check by clicking. The internal words (`by`, `located`,
`twin`, `reason`) stay in the API for the tests; the page shows the card.

    card = {"found": str | None, "where": [{"label", "link", ...the cited cell (crops.cells): viewer, crop state, form, filed}],
            "how": {"tone": ok|corroborated|info|wait|bad, "text": one short line, "detail": the long form or None},
            "compare": {"a", "b"} extraction ids when two readings differ}

The tones are the ladder (T92): ok (Verified) only for an SEC XBRL match or a quote that matches its source; corroborated,
a tie to the filing's tagged total or the same figure in two or more filings; company, a category the company's own XBRL
tag matches; done, found or confirmed but not checked (statements located, no blocking items, a reviewer's confirmation);
info, citation only (or an explanation on file); wait and bad, needs review. `VERIFIED_BY` lists what may read Verified.
"""
from __future__ import annotations

import json
import re

from ..core import status, store
from ..review.definitions import load as load_definitions
from ..release.taxonomy import deep_link, quote_link

FIELD = {"revenue": "Revenue", "capex": "Capital spending (capex)", "opex": "Operating costs (opex)",
         "cost_of_revenue": "Cost of revenue", "operating_income": "Operating income",
         "segment_capex": "Capex by segment", "segment_revenue": "Revenue by segment", "ppe_category": "Property by category",
         "finance_lease_liability": "Finance lease liabilities", "purchase_commitments": "Purchase commitments"}
OPEX_PARTS = ("revenue", "cost_of_revenue", "operating_income")


def money(v) -> str:
    """Whole dollars as people read them, the one money format of the app: $131,819M for whole millions, $1.8M (tenths,
    half up) otherwise, the exact figure below a million, $0 for zero, — for a blank. The pages' copy is `usd` in
    _shared.js (tests.test_cards.Money.test_the_pages_format_is_pythons runs both on the same cases)."""
    if v is None:
        return "—"
    v = int(round(v))
    sign = "−" if v < 0 else ""
    a = abs(v)
    if a >= 1_000_000 and a % 1_000_000 == 0:
        return f"{sign}${a // 1_000_000:,}M"
    if a >= 1_000_000:
        tenths = (a + 50_000) // 100_000  # integer arithmetic: the same rounding as the page's copy, never banker's
        return f"{sign}${tenths // 10:,}.{tenths % 10}M"
    return f"{sign}${a:,}"


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def member_label(member: str | None) -> str:
    """A us-gaap member as words: us-gaap:BuildingAndBuildingImprovementsMember -> Building and building improvements."""
    if not member:
        return ""
    m = re.sub(r"Member$", "", member.split(":")[-1])
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", m).split()
    return " ".join([words[0]] + [w if w.isupper() and len(w) > 1 else w.lower() for w in words[1:]]) if words else member


def _cell(c: dict, docs: dict, ev: dict) -> dict:
    """One cited cell as the trail shows it: the filing (form, filed), the cell, the in-app viewer, the crop's state
    from crops.cells (the one reading the gold set, Reconcile and /api/v1/evidence share) and the sec.gov address."""
    d = docs.get(c["accession"]) or {}
    filed = str(d.get("filed") or "")[:10]
    col = " ".join((c.get("column_label") or "").replace("|", " ").split())
    from ..checks.crops import brief
    b = brief(ev.get(c["extraction_id"]))
    return {"label": f"{d.get('form') or '10-K'} {filed}", "form": d.get("form") or "10-K", "filed": filed or None, "extraction_id": c["extraction_id"],
            "row": c["row_label"], "column": col, "cell": c["cell_text"], "link": deep_link(d.get("url"), c.get("row_label"), c.get("cell_text")),
            "viewer": b["viewer"], "crop": {k: b[k] for k in ("state", "reason", "url")}}


from ..core.states import VERIFIED_BY  # the only checks a page may call Verified (tests.test_cards.How.test_only_sec_xbrl_and_quotes_read_verified)
RULE_TEXT = {"part_year": "Part-year amount", "restated_between_filings": "Restated in a later 10-K", "amendment_without_statements": "Amendment without statements",
             "program_words": "Program, not annual guidance"}


def _how(it: dict, name: str, defs: dict, found_value=None) -> dict:
    """The item's state and its evidence: one short line (`text`) and, when there is more, the long form (`detail`). The
    tone is the row state, decided by states.row from the item's status state and `by`, never here."""
    from ..core import states
    return {**_words(it, name, defs, found_value), "tone": states.row(it.get("state"), it.get("by"))}


def _words(it: dict, name: str, defs: dict, found_value=None) -> dict:
    by, state = it.get("by") or "", it.get("state")
    ref = it.get("ref") or {}
    if state in ("open", "blocked"):
        more = it.get("detail") or it.get("reason") or None
        if by == "label:to_confirm":
            return {"tone": "wait", "text": "Proposed category. Review in Reconcile.", "detail": None}
        if by == "label:not_extracted":
            return {"tone": "bad", "text": "In SEC XBRL, not extracted. Re-read required.", "detail": None}
        rs = ref.get("readings") or []
        if by == "rule:fact_readings_differ" and len(rs) >= 2:
            text = "Readings differ: " + " → ".join(money(r.get("value")) for r in (rs[0], rs[-1]))
            return {"tone": "bad", "text": text, "detail": " · ".join(f"{r.get('form') or '10-K'} filed {str(r.get('filed') or '')[:10]}: {money(r.get('value'))}" for r in rs)}
        if by.startswith("rule:") and by.endswith("_tie"):
            g = ref.get("tie_gap")
            if not g:
                return {"tone": "bad", "text": "Does not tie to reported total", "detail": more}
            text = f"Does not tie · gap {money(abs(g['gap']))}"
            return {"tone": "bad", "text": text, "detail": f"Parts {money(g['sum'])} · total {money(g['total'])} (SEC XBRL) · {g['parts']} parts · tolerance ±{money(g['tolerance'])}"}
        text = "Decide in Reconcile"
        return {"tone": "bad", "text": text, "detail": more}
    if by == "xbrl":
        same = found_value is None or ref.get("reference") == found_value
        text = f"Matches SEC XBRL: {money(ref.get('reference'))}" if same else f"Matches SEC XBRL within rounding: {money(ref.get('reference'))}"
        return {"tone": "ok", "text": text, "detail": None}
    if by.startswith("rule:") and by.endswith("_tie") and isinstance(ref.get("tie"), dict):
        t = ref["tie"]
        parts = t.get("parts") or [{"dimension": d} for d in t.get("dimensions") or []]
        members = "; ".join(f"{p.get('dimension') or 'total'} {money(p['value'])}" if p.get("value") is not None else (p.get("dimension") or "") for p in parts)
        text = f"Ties to reported total: {money(t.get('total'))} (SEC XBRL)"
        return {"tone": "corroborated", "text": text, "detail": f"{len(parts)} parts · tolerance ±{money(t.get('tolerance'))}" + (f" · {members}" if members else "")}
    if by.startswith("reading:"):
        n = len({r.get("accession") for r in ref.get("readings") or []})
        return {"tone": "corroborated", "text": f"Confirmed in {n} filings", "detail": None}
    if by == "quote":
        return {"tone": "ok", "text": "Quote matches source", "detail": None}
    if by == "located":  # found, not verified: nothing independent checks a located table
        return {"tone": "done", "text": "Statements located", "detail": None}
    if by == "gate":
        return {"tone": "done", "text": "No blocking items", "detail": None}
    if by == "mapping:filer_tag":  # the company's own XBRL tag: a second reading by the same company, not SEC agreement on a value
        tag = ref.get("filer_tag") or {}
        return {"tone": "company", "text": member_label(tag.get("member")) or "Same member", "detail": None}
    if by.startswith("mapping:"):  # a person confirmed the proposal: a decision, not a check
        return {"tone": "done", "text": f"Confirmed: {member_label(by.split(':', 1)[1])}", "detail": None}
    if by == "label:no_reference":
        return {"tone": "info", "text": "Citation only", "detail": None}
    if by == "label:not_reported":
        return {"tone": "info", "text": "Not reported · none in SEC XBRL", "detail": None}
    if by.startswith("definition:"):
        why = ((defs or {}).get(by.split(":", 1)[1]) or {}).get("why") if isinstance(defs, dict) else None
        return {"tone": "info", "text": "Definition differs from SEC XBRL", "detail": why or None}
    if by.startswith("resolution:"):
        return {"tone": "info", "text": "Decision on file", "detail": it.get("reason") or None}
    if by.startswith("rule:"):
        rid = by.split(":", 1)[1]
        text = RULE_TEXT.get(rid) or rid.replace("_", " ").capitalize()
        return {"tone": "info", "text": text, "detail": None}
    return {"tone": "info", "text": it.get("reason") or "", "detail": None}


def add(con, trail: dict) -> dict:
    """Give every item of `trail` (proof.company's result) a `card`, in place, and return the trail."""
    t, name = trail["ticker"], trail.get("name") or trail["ticker"]
    docs = {d["accession"]: d for d in _rows(con, "select accession, form, period, filed, url from documents where ticker = ?", t)}
    from ..checks import crops
    ev = crops.cells(con, [r[0] for r in con.execute("select extraction_id from extractions where ticker = ? union all select extraction_id from note_extractions where ticker = ?", [t, t]).fetchall()])
    defs = (load_definitions() or {}).get(t, {})
    stages = trail["stages"]

    # reports found: the filing itself
    for it in stages.get("ingest", {}).get("all", []):
        acc = (it.get("ref") or {}).get("accession")
        d = docs.get(acc) or {}
        it["card"] = {"found": None,
                      "where": [{"label": f"{d.get('form') or '10-K'} filed {str(d.get('filed') or '')[:10]}", "link": d.get("url"), "viewer": f"/filing/{acc}"}] if d else [],
                      "how": _how(it, name, defs)}

    # main numbers: the value, the cells it was read from, the SEC's copy
    vals = {(v["field"], v["period"]): v for v in _rows(con, 'select field, period, value, extraction_ids from "values" where ticker = ?', t)}
    from ..checks import calc
    calcs = calc.for_ticker(con, t)  # a figure calculated from several cells says so (the gold set reads the same function)
    ext = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, accession, field, table_id, row_label, column_label, cell_text from extractions where ticker = ?", t)}
    for it in stages.get("values", {}).get("all", []):
        ref = it.get("ref") or {}
        v = vals.get((ref.get("field"), ref.get("period")))
        if not v:
            it["card"] = {"found": None, "where": [], "how": _how(it, name, defs)}
            continue
        ids = [i for i in (v.get("extraction_ids") or "").split(",") if i in ext]
        c = calcs.get((ref.get("field"), ref.get("period")))
        role = {i["extraction_id"]: i["role"] for i in (c or {}).get("inputs", [])}
        order = {i["extraction_id"]: k for k, i in enumerate((c or {}).get("inputs", []))}
        cells = sorted((_cell(ext[i], docs, ev) | ({"role": role[i]} if i in role else {}) for i in ids), key=lambda w: order.get(w["extraction_id"], len(order)))
        found = money(v["value"]) if v["value"] is not None else "Not reported"
        it["card"] = {"found": found, "where": cells, "how": _how(it, name, defs, v["value"]), "calc": c}

    # footnote numbers: the fact, its cells in the notes
    facts = {(f["field"], f["dimension"] or "", f["period"]): f for f in _rows(con, "select field, dimension, period, value, extraction_ids from facts where ticker = ?", t)}
    notes = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, accession, table_id, row_label, column_label, cell_text from note_extractions where ticker = ?", t)}
    for it in stages.get("facts", {}).get("all", []):
        ref = it.get("ref") or {}
        f = facts.get((ref.get("field"), ref.get("dimension") or "", ref.get("period")))
        if not f:
            d = docs.get(ref.get("accession")) or {}  # a finding on a group of parts (a tie): the filing it judged, opened whole
            where = [{"label": f"{d.get('form') or '10-K'} {str(d.get('filed') or '')[:10]}", "form": d.get("form"), "filed": str(d.get("filed") or "")[:10] or None,
                      "link": d.get("url"), "viewer": f"/filing/{ref['accession']}"}] if d else []
            it["card"] = {"found": None, "where": where, "how": _how(it, name, defs)}
            continue
        ids = [i for i in (f.get("extraction_ids") or "").split(",") if i in notes]
        where = sorted((_cell(notes[i], docs, ev) for i in ids), key=lambda w: (w["filed"] or "", w["extraction_id"]))
        it["card"] = {"found": money(f["value"]), "where": where, "how": _how(it, name, defs, f["value"])}
        if it.get("by") == "rule:fact_readings_differ" and len(where) >= 2:  # the oldest and the newest reading, side by side on #evidence/compare
            it["card"]["compare"] = {"a": where[0]["extraction_id"], "b": where[-1]["extraction_id"]}

    # AI quotes: the sentence, opened at its words
    stm = {s["statement_id"]: s for s in _rows(con, "select s.statement_id, s.quote, t.url, t.kind, t.date from ai_statements s join texts t on t.text_id = s.text_id where s.ticker = ?", t)}
    for it in stages.get("statements", {}).get("all", []):
        s = stm.get((it.get("ref") or {}).get("statement_id"))
        it["card"] = {"found": f"“{s['quote']}”" if s else None,
                      "where": [{"label": f"{(s['kind'] or 'source').replace('_', ' ').capitalize()} · {str(s['date'] or '')[:10]}", "link": quote_link(s["url"], s["quote"])}] if s and s.get("url") else [],
                      "how": _how(it, name, defs)}

    # category labels: the company's label and the proposed standard category, and the decision card (ledger/review/mapcard.py,
    # the same function Reconcile's asset types group reads)
    from ..review.mapcard import decisions
    from ..release.taxonomy import asset_types
    entries = asset_types().get(t) or {}
    mapping_items = stages.get("mapping", {}).get("all", [])
    dec = decisions(con, t, [it.get("name") for it in mapping_items]) if mapping_items else {}
    for it in mapping_items:
        e = entries.get(it.get("name")) or {}
        member = e.get("standard_type")
        found = f"“{it.get('name')}” → {member_label(member)}" if member else f"“{it.get('name')}” → Unmapped"
        where = [{"label": f"Basis: {e['evidence']}", "link": None}] if e.get("evidence") else []
        it["card"] = {"found": found, "where": where, "how": _how(it, name, defs)}
        it["decision"] = dec.get(it.get("name"))

    # plans and projects: the quote, opened at its words
    from ..release.taxonomy import rows as taxonomy_rows
    planned = {(r["category"], r["fiscal_year"], r["reported_name"]): r for r in taxonomy_rows(con, [t]) if r["measure"] == "planned"}
    for it in stages.get("planned", {}).get("all", []):
        ref = it.get("ref") or {}
        r = planned.get((ref.get("category"), ref.get("fiscal_year"), ref.get("reported_name")))
        it["card"] = {"found": f"“{r['quote']}”" if r and r.get("quote") else None,
                      "where": [{"label": "Source", "link": r.get("source_url")}] if r and r.get("source_url") else [],
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


def status_line(con, trail: dict, newest: dict | None, watch: dict, at=None) -> dict:
    """The company's state as of now: current through (newest report, next expected), SEC last checked, trust split,
    shipped (last signed release) and what changed since. The SEC check's age comes from clock.age_hours: a missing,
    unreadable, zone-less or future time is `sec_check_problem` with no age, and the page reads it stale."""
    from datetime import date, datetime, timedelta, timezone
    nxt = None
    if newest and newest.get("period") and newest.get("filed"):
        try:
            p, f = date.fromisoformat(str(newest["period"])[:10]), date.fromisoformat(str(newest["filed"])[:10])
            nxt = (p + timedelta(days=365) + (f - p)).isoformat()
        except ValueError:
            nxt = None
    stages = trail["stages"]
    figures = [i for s in ("values", "facts") for i in stages.get(s, {}).get("all", []) if (i.get("ref") or {}).get("field") and not (i.get("ref") or {}).get("finding")]
    waiting = sum(len(st.get("open", [])) for st in stages.values())
    matched = sum(i.get("key") == "twin" for i in figures)
    tied = sum(i.get("key") == "tie" for i in figures)
    second = sum(i.get("key") == "second_reading" for i in figures)
    reading = sum(i.get("state") == "explained" for i in figures)
    quotes = sum(1 for s in ("statements", "planned") for i in stages.get(s, {}).get("all", []) if i.get("state") == "checked")
    rel = last_release(trail["ticker"])
    from ..core.states import edgar
    sec, age, problem = edgar(watch.get("checked_at"), at)  # fresh | stale | never | unreadable, the one reading (states.EDGAR)
    problem = None if problem == "never" else problem  # never checked has its own words on the page
    return {"as_of": (at or datetime.now(timezone.utc)).strftime("%-d %b %Y, %H:%M UTC"),
            "current_through": {"form": newest.get("form"), "period": str(newest.get("period") or "")[:10], "filed": str(newest.get("filed") or "")[:10]} if newest else None,
            "sec_check_problem": problem, "sec_check": sec,
            "next_expected": nxt, "sec_checked_hours_ago": None if age is None else round(age),
            "figures": len(figures), "matched": matched, "tied": tied, "second_reading": second, "reading_only": reading, "waiting": waiting, "quotes": quotes,
            "shipped": {k: rel[k] for k in ("version", "signed_by", "signed_at")} if rel else None,
            "since": since_release(con, trail["ticker"], rel)}
