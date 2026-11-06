"""The reconcile workbench (Kenny's Data Emporium, Reconcile tab): every open item of the queue as one row a person can judge
without opening anything: ours, the reference, the delta, where each number came from, the evidence (the cited
cell and its screenshot), and the resolution. Built from `app.flow()`; nothing is read from filings and nothing in
it is an estimate. `/api/v1/reconcile?scope=` serves it; `/api/resolve` records one resolution, `/api/resolve/bulk` many."""
from __future__ import annotations

from . import resolutions
from ..core import status, store
from ..core.config import industry
from ..checks.rules import explain_key, explained
from ..core.states import SEGMENT_BASIS_MIXED

EVIDENCE = store.ROOT / "reports" / "evidence"
CAUSES = {"fact_differs": "Differs from SEC XBRL", "fact_changed": "Changed since last release", "blocked": "Blocks release",
          "finding_unconfirmed": "Rule findings", "new_filing": "New SEC filing", "value_missing": "Not extracted",
          "reading_unfingerprinted": "Reading not fingerprinted"}
REF_LABEL = {"fact_differs": "SEC XBRL", "fact_changed": "Last release", "blocked": None, "finding_unconfirmed": "SEC XBRL", "new_filing": None, "value_missing": "SEC XBRL", "reading_unfingerprinted": None}
# a rule's finding by the rule that fired (the queue carries kind "other" and the rule id for the note rules), one short label each
FINDING_LABEL = {"restated": "Restated", "jump": "Large year-over-year change", "row_switch": "Line renamed", "capex_intensity": "Capex high vs revenue", "opex_over_revenue": "Opex above revenue",
                 "segment_capex_tie": "Does not tie to reported total", "segment_revenue_tie": "Does not tie to reported total", "ppe_categories_tie": "Does not tie to reported total",
                 "fact_readings_differ": "Readings differ across filings"}
FINDING_LABEL["segment_basis_mixed"] = SEGMENT_BASIS_MIXED  # a display word declared in states.py (states.DISPLAY)


def xbrl_name(con, accession: str, period_end: str | None, value) -> dict | None:
    """Which us-gaap concept and member the filing's reference value came from: the instance is read (cached) and the
    one fact with that value on that date is named. The reference may come from any of the company's filings (the
    year's own 10-K tags it; a later one restates), newest first. None when no filing has such a fact."""
    if value is None or not accession:
        return None
    try:
        doc = con.execute("select cik, ticker from documents where accession = ?", [accession]).fetchone()
        if not doc:
            return None
        want = round(float(value))
        for cik, acc in con.execute("select cik, accession from documents where ticker = ? order by filed desc", [doc[1]]).fetchall():
            hits = [(c, m, e) for (c, m, e), v in _instance(int(cik), acc).items() if v == want and (not period_end or e == period_end)]
            if hits:
                c, m, e = hits[0]
                return {"concept": f"us-gaap:{c}", "member": m or None, "date": e, "accession": acc, "others": len(hits) - 1}
        return None
    except Exception:
        return None


_INSTANCES: dict = {}


def _instance(cik: int, accession: str) -> dict:
    if (cik, accession) not in _INSTANCES:
        from ..ingest.reference.dimensions import instance_facts
        if len(_INSTANCES) > 40:
            _INSTANCES.clear()
        _INSTANCES[(cik, accession)] = instance_facts(cik, accession)
    return _INSTANCES[(cik, accession)]


def _fact_series(con, ticker: str, field: str, dimension: str) -> list[dict]:
    """The same fact across years: our cited value and the filing's tag."""
    cur = con.execute("select period, value, reference, label from facts where ticker = ? and field = ? and coalesce(dimension, '') = ? order by period", [ticker, field, dimension])
    return [{"period": r[0], "value": r[1], "reference": _num(r[2]), "label": r[3]} for r in cur.fetchall()]


def _value_series(con, ticker: str, field: str) -> list[dict]:
    cur = con.execute('select period, value, label from "values" where ticker = ? and field = ? order by period', [ticker, field])
    return [{"period": r[0], "value": r[1], "reference": None, "label": r[2]} for r in cur.fetchall()]


def _num(x):
    try:
        return None if x in (None, "") else float(x)
    except (TypeError, ValueError):
        return None


def _value_states(con, ticker: str, field: str | None, period: str | None, idx: dict) -> list[dict]:
    """The states (status.of_value) of the value rows a finding fired on: the field (cost_of_revenue and operating_income
    are read to make opex, so a finding on them is about opex) and the period, or every period when it names none."""
    if not field:
        return []
    f = "opex" if field in ("cost_of_revenue", "operating_income") else field
    cur = con.execute('select field, period, label from "values" where ticker = ? and field = ?' + (" and period = ?" if period else ""), [ticker, f] + ([period] if period else []))
    rows = cur.fetchall()
    xref = dict(((r[0], r[1]), r[2]) for r in con.execute("select field, period, value from reference_values where ticker = ?", [ticker]).fetchall()) if _has_reference(con) else {}
    looked = bool(xref)  # as Proof reads it (proof.company): the lookup ran when reference_values holds the ticker's rows
    return [status.of_value({"field": r[0], "period": r[1], "label": r[2]}, resolutions.resolution_of(idx, "values", ticker, r[0], "", r[1]),
                            {"reference": xref.get((r[0], r[1])), "looked_up": looked}) for r in rows]


def _explained(con, tickers: list[str]) -> dict:
    """rules.explained over the info findings of `tickers` (T36), {} when the table or the findings are absent."""
    if not tickers or not con.execute("select count(*) from information_schema.tables where table_name = 'exceptions'").fetchone()[0]:
        return {}
    cur = con.execute("select * from exceptions where severity = 'info' and ticker in (select unnest(?))", [tickers])
    rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    if not rows:
        return {}
    try:
        return explained(rows)
    except (ValueError, OSError):
        return {}  # a rule file that does not load explains nothing; Proof shows the error as an open item


def _offers(con, key: str, enc: dict) -> dict | None:
    """judgement.offers for one queue key (T36), or None where the database has no extractions table to name lines from."""
    from . import judgement
    from .definitions import load as load_defs
    from ..checks.rules import load as load_rules
    if not con.execute("select count(*) from information_schema.tables where table_name = 'extractions'").fetchone()[0]:
        return None
    k = resolutions.parse_key(key)
    if not k:
        return None
    if not enc:
        try:
            enc |= {"defs": load_defs(judgement.DEF_FILE), "rules": load_rules(judgement.RULES_DIR)}
        except (ValueError, OSError):
            enc |= {"defs": None, "rules": None, "error": True}
    if enc.get("error"):
        return None  # nothing is offered while a definition or rule file does not load
    return judgement.offers(con, k, enc["defs"], enc["rules"])


def _has_reference(con) -> bool:
    return bool(con.execute("select count(*) from information_schema.tables where table_name = 'reference_values'").fetchone()[0])


def _fact_row(con, ticker: str, field: str | None, dimension: str | None, period: str | None) -> dict | None:
    cols = [c[0] for c in con.execute("select * from facts limit 0").description]
    r = con.execute("select * from facts where ticker = ? and field = ? and coalesce(dimension, '') = ? and period = ?", [ticker, field or "", dimension or "", period or ""]).fetchone()
    return dict(zip(cols, r)) if r else None


def _state(con, q: dict, idx: dict, xp: dict | None = None, lad: dict | None = None) -> dict:
    """The queue item's state from the one definition (status.py): the same row gets the same answer on Proof. `xp` is
    rules.explained over the scope's exceptions (T36): an explains rule on file closes the finding it names."""
    d, res, t = q.get("detail") or {}, q.get("resolution"), q["ticker"]
    if q["kind"] in ("fact_differs", "fact_changed"):
        f = _fact_row(con, t, d.get("field"), d.get("dimension"), d.get("period"))
        from ..checks.proof import _restated
        if f is None:
            return status.of_fact({"label": d.get("label")}, res)
        # T92 review: the one ladder (ties.fact_state), as Proof reads the fact; the queue item's own resolution when it has one
        from ..checks.ties import fact_state, ladder
        lad = lad if lad is not None else ladder(con, [t])
        index = {**idx, ("facts", t, f["field"], f["dimension"] or "", f["period"], ""): res} if res else idx
        return fact_state(f, index, lad, _restated(con, t, f) if f.get("label") == "unresolved" and f.get("accession") else None)[0]
    if q["kind"] == "finding_unconfirmed":
        by_rule = (xp or {}).get(explain_key(d.get("rule"), t, d.get("field"), d.get("period"), d.get("subject")))
        return status.of_exception({"rule_id": d.get("kind"), "severity": "warn", "message": d.get("message")}, res, _value_states(con, t, d.get("field"), d.get("period"), idx), by_rule)
    if q["kind"] == "blocked":
        p = q.get("proposed")  # F14: a run's or an agent's decision on the block: Proposed, as on Proof, unless a person's resolution blocks it
        if p and (res or {}).get("state") != "blocks":
            return status.state({"label": "to_confirm", "reason": f"{p.get('kind')} by {p.get('reviewer')}; no person has decided it"})
        return status.of_exception({"rule_id": d.get("rule"), "severity": "block", "message": d.get("message")}, res)
    if q["kind"] == "value_missing":  # T65: the value row itself, open by label:not_extracted; a resolution is not live for this kind
        return status.of_value({"field": d.get("field"), "period": d.get("period"), "label": d.get("label", "not_extracted")}, res)
    if q["kind"] == "reading_unfingerprinted":  # F25: open by label:unfingerprinted, as Proof's ingest item; closed by re-reading
        from ..checks.proof import UNFINGERPRINTED_WHY
        return status.state({"label": "unfingerprinted", "reason": UNFINGERPRINTED_WHY})
    return status.state({"reason": "a filing at the SEC the ledger has not read", "resolution": res})


TO_CONFIRM = "to_confirm"


def to_confirm(tickers: list[str] | None, names: dict) -> list[dict]:
    """The decisions a run made for a person to confirm (resolutions.unconfirmed), as workbench rows: their own group,
    first. None of them is a dataset row; each is a resolution a person has not yet made their own."""
    out = []  # open: the release refuses each (G6); the page word is Proposed (states.row), the same as an unconfirmed mapping
    for r in resolutions.unconfirmed():
        k = resolutions.parse_key(r["key"])  # unconfirmed() gives live keys only, so this is never None (T62)
        kind, ticker = k["kind"], k["ticker"]
        where = " ".join(x for x in (k["field"], k["dimension"], k["period"], f"({k['rule_id']})" if k["rule_id"] else "") if x)
        if tickers is not None and ticker not in tickers:
            continue
        out.append({"key": r["key"], "hash": r["hash"], "cause": TO_CONFIRM, "cause_label": "To confirm", "state": "to confirm",
                    "by": f"resolution:{r.get('id', '')}", "reason": r["reason"], "open": True, "ticker": ticker, "name": names.get(ticker, ticker), "layer": industry(ticker),
                    "field": None, "period": None, "where": f"{kind.replace('_', ' ')}: {where}", "measure": None, "ours": None, "ours_label": None, "reference": None, "ref_label": None,
                    "relation": "eq", "delta": None, "delta_pct": None, "dollars": 0, "new": False, "action": "confirm", "impact": "the release refuses while it is unconfirmed",
                    "resolution": {k: r.get(k) for k in ("id", "state", "by", "at", "reason")}, "evidence": {"message": r["reason"], "proposed": r["state"]}})
    return out


ASSET_TYPES = "asset_types"
UNMAPPED_REASON = status.UNMAPPED


def asset_types(con, tickers: list[str] | None, names: dict) -> list[dict]:
    """The mapping stage's open items as workbench rows (T33, T63): every reported PP&E category in the scope with no
    entry in taxonomy/asset_types.yaml, with the mapper's proposal when one stands (standard_type, evidence, confidence,
    reason, prompt version, model), and every one whose entry has no confirmed_by, with that entry as the proposal. Each
    carries the members a person already rejected for it, the note's words around it, the member the filer tagged
    (`filer`) and whether the proposal differs from it (`mismatch`). The state is status.of_mapping's, so Proof counts
    the row the same way. Approve or Edit writes the mapping, confirmed (POST /api/mapping, by the person); Reject logs
    the member and removes an unconfirmed entry."""
    from . import mapper
    from .mapcard import decisions
    out = []
    pend = mapper.pending(con, tickers, with_verified=True)  # with the ones the company's own tag matches: listed after the open ones, a person may override
    dec: dict = {}
    for t in sorted({p["ticker"] for p in pend}):  # the decision card: the one function the trail reads too
        dec[t] = decisions(con, t, [p["reported_name"] for p in pend if p["ticker"] == t])
    for p in pend:
        P = p["proposal"]
        D = dec.get(p["ticker"], {}).get(p["reported_name"])
        st = (D or {}).get("state") or status.of_mapping(None)  # the card's state: status.of_mapping with the company's tag, as Proof reads it
        st = {"state": st["state"], "by": st["by"], "reason": st.get("reason") or ""}
        from ..core.states import mapping as mapping_state, word
        label = word("mapping", mapping_state(st))  # the state's word (states.MAPPING), from the state Proof counts
        from ..core.config import SCOPE
        if p["ticker"] not in SCOPE:
            impact = "blocks nothing until the company is in scope (config.SCOPE)"
        elif p["kind"] == "verified":
            impact = "none: the company's own tag matches; a person may still confirm, choose another or reject"
        elif p["kind"] == "to_confirm":
            impact = "the release refuses (G6) until a person confirms, edits or rejects it"
        else:
            impact = "the derived PP&E rows stay unmapped; the Release checklist requires 0"
        out.append({"key": f"{ASSET_TYPES}|{p['ticker']}|{p['reported_name']}", "hash": "", "cause": ASSET_TYPES, "cause_label": "Category mapping", "state": st["state"],
                    "by": st["by"], "reason": st["reason"], "open": status.is_open(st), "ticker": p["ticker"], "name": names.get(p["ticker"], p["ticker"]), "layer": industry(p["ticker"]),
                    "field": None, "period": None, "where": p["reported_name"], "measure": None, "ours": None, "ours_label": None, "reference": None, "ref_label": None,
                    "relation": "eq", "delta": None, "delta_pct": None, "dollars": 0, "new": False, "action": "mapping", "impact": impact, "resolution": None,
                    "evidence": {"reported_name": p["reported_name"], "mapping": p["kind"], "label": label, "proposal": P, "rejected": p["rejected"], "reproposed": p.get("reproposed") or [], "note": p["note"],
                                 "filer": p["filer"], "mismatch": ((D or {}).get("tag") or {}).get("status") == "differs",  # the card's word: one count with the card
                                 "decision": D}})
    return out


def _finding_numbers(d: dict, ticker: str, lad: dict, restated: dict) -> dict:
    """A rule finding's key numbers for Reconcile's columns (STORY-027: every rule-finding row read "—" and the gap sat in
    the Details prose). A tie that fails: the sum of the parts against the total the filing tags (ties.groups, the same
    group Proof's trail reads). Readings that differ: the figure the dataset uses against the other reading
    (ties.restatement), oldest when there are more. {} when the finding has no such numbers; nothing is estimated."""
    rule, field_, period, subject = d.get("rule"), d.get("field"), d.get("period"), d.get("subject")
    if rule and rule.endswith("_tie"):
        from ..checks.ties import key as tie_key
        g = ((lad or {}).get("groups") or {}).get(tie_key(ticker, field_ or "", period or "", subject or ""))
        if g and g.get("sum") is not None and g.get("total") is not None:
            return {"measure": "usd", "ours": g["sum"], "ours_label": "Sum of parts", "reference": g["total"], "ref_label": "Reported total"}
    if rule == "fact_readings_differ":
        rec = (restated or {}).get((ticker, field_, subject or "", period))
        used = (rec or {}).get("used") or {}
        others = [f for st in (rec or {}).get("steps") or [] for f in st["filings"] if f.get("extraction_id") != used.get("extraction_id")]
        if used.get("value") is not None and others:
            o = others[0]
            return {"measure": "usd", "ours": used["value"], "ours_label": f"Used · {used.get('form') or '10-K'} {str(used.get('filed') or '')[:10]}",
                    "reference": o["value"], "ref_label": f"Other · {o.get('form') or '10-K'} {str(o.get('filed') or '')[:10]}"}
    return {}


def company_counts(board: dict, unconfirmed=(), unmapped=()) -> dict:
    """{ticker: {bad, wait, blocked}} (states.buckets): the Proof board's items by their row word (states.row), plus a
    run's decisions to confirm under Proposed (Reconcile's "To confirm" rows; no Proof item carries them) and, under Needs
    review, every unmapped asset type (taxonomy.unmapped) the board has no mapping row for. The Proof board, the trail
    and the Release lines read this; Reconcile counts its own rows with states.buckets, and tests.test_flow.OneNumber
    holds the two equal for every company in scope."""
    from ..core.states import BUCKETS, buckets, row
    on_board = {(c["ticker"], i.get("name")) for c in board["proven"] for i in (c["stages"].get("mapping") or {}).get("all", [])}
    pairs = [(c["ticker"], row(i["state"], i.get("by"))) for c in board["proven"] for s in c["stages"].values() for i in s["all"]]
    for r in unconfirmed:  # unconfirmed() gives live keys only; one that does not parse is a bug to see, never a count to drop
        k = resolutions.parse_key(r["key"])
        if not k:
            raise ValueError(f"a decision to confirm with a key that does not parse: {r['key']!r}")
        pairs.append((k["ticker"], "wait"))
    pairs += [(m["ticker"], "bad") for m in unmapped if (m["ticker"], m["reported_name"]) not in on_board]
    out = buckets(pairs)
    for c in board["proven"]:
        out.setdefault(c["ticker"], dict.fromkeys(BUCKETS, 0))
    return out


def _basis(con, tickers: list[str]) -> dict:
    """{(ticker, field, period): the year's segments as ties.segment_basis gives them, each with its filing, readings and
    restatement, plus the cutover}: what a segment_basis_mixed row's drawer shows."""
    from ..checks.ties import load, segment_basis
    data = load(con, tickers, [])
    out = {}
    for s in segment_basis(data["facts"], data["extractions"]):
        for r in s["years"]:
            out.setdefault((s["ticker"], s["field"], r["period"]), {"cutover": s["cutover"], "rows": []})["rows"].append(
                {k: r[k] for k in ("dimension", "period", "cell_text", "form", "filed", "accession", "mixed")} | {"restated": (r["restatement"] or {}).get("line")})
    return out


def items(con, flow: dict) -> dict:
    """One uniform row per queue item. `measure` is usd; `ours` and `reference` are in that measure; `delta` = ours - reference.
    Every row carries `state`, `by` and `reason` from status.state and `open` (open or blocked); `open` counts those.
    The decisions a run left for a person to confirm come first as their own group (`to_confirm`, T3), counted apart; the
    unmapped asset types (`asset_types`, T33) are their own group too, with `members` the list a mapping may use."""
    names, rel = flow["names"], flow["release"]["last"]
    idx = resolutions.by_row(items=flow.get("items") or flow["queue"], tickers=flow["tickers"] if "items" in flow else ())  # T62: a row with an unresolved sibling finding stays open; F15: every item, as resolutions.index reads it
    xp = _explained(con, sorted({q["ticker"] for q in flow["queue"]}))
    from ..checks.ties import ladder
    lad = ladder(con, sorted({q["ticker"] for q in flow["queue"]}))  # T92: the facts' ladder, read once
    from ..checks.ties import restatements
    tick = sorted({q["ticker"] for q in flow["queue"]})
    restated = restatements(con, tick)  # ties.restatement per fact: the drawer says it whatever the row's state
    basis = _basis(con, tick) if any((q.get("detail") or {}).get("rule") == "segment_basis_mixed" for q in flow["queue"]) else {}
    enc = {}  # the definitions and rules on file, read once for every item's offers
    rows = []
    from ..checks.crops import brief, cells
    crop_of = cells(con, [((q.get("detail") or {}).get("cite") or {}).get("extraction_id") for q in flow["queue"] if q["kind"] == "fact_differs"])  # one read for every row
    for q in flow["queue"]:
        d = q.get("detail") or {}
        st = _state(con, q, idx, xp, lad)
        row = {"key": q["key"], "hash": q["hash"], "cause": q["kind"], "cause_label": CAUSES.get(q["kind"], q["kind"]), "state": st["state"], "by": st["by"], "reason": st["reason"], "open": status.is_open(st),
               "ticker": q["ticker"], "name": names.get(q["ticker"], q["ticker"]), "layer": industry(q["ticker"]), "field": None, "period": None, "where": q["where"], "measure": None,
               "ours": None, "ours_label": None, "reference": None, "ref_label": REF_LABEL.get(q["kind"]), "relation": "eq", "delta": None, "delta_pct": None,
               "dollars": q.get("dollars") or 0, "new": bool(q.get("new")), "action": q["action"], "impact": q["impact"], "resolution": q.get("resolution"),
               "evidence": {}}
        if q["kind"] == "fact_differs":
            c = d.get("cite") or {}
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd", "ours": d.get("value"), "reference": _num(d.get("reference")), "ours_label": "Cited"}
            row["series"] = _fact_series(con, q["ticker"], d.get("field"), d.get("dimension") or "")
            pe = con.execute("select period_end from facts where ticker = ? and field = ? and coalesce(dimension, '') = ? and period = ?", [q["ticker"], d.get("field"), d.get("dimension") or "", d.get("period")]).fetchone()
            row["evidence"] = {"cell": {k: c.get(k) for k in ("table_id", "row_label", "column_label", "cell_text", "accession")} if c else None,
                               "crop": brief(crop_of.get(c["extraction_id"])) if c.get("extraction_id") else None,
                               "xbrl": xbrl_name(con, c.get("accession") or "", pe[0] if pe else None, d.get("reference")),
                               "url": d.get("url"), "release_value": d.get("release_value"), "dimension": d.get("dimension")}
        elif q["kind"] == "fact_changed":
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd", "ours": d.get("value"), "reference": d.get("release_value"), "ours_label": "Now"}
            row["evidence"] = {"dimension": d.get("dimension"), "release": rel}
        elif q["kind"] == "finding_unconfirmed":  # a rule's finding (restated, jump, row_switch, ...) the SEC's data can't confirm
            k = d.get("kind")
            lk = d.get("rule") if k == "other" and d.get("rule") else k  # the label names the rule that fired; the state still reads kind, as Proof does
            numeric = k in ("restated", "jump", "opex_over_revenue") and d.get("before") is not None and d.get("after") is not None
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd" if numeric else None, "ours": d.get("after") if numeric else None,
                    "reference": d.get("before") if numeric else None, "ours_label": {"restated": "Latest 10-K", "jump": "This year", "opex_over_revenue": "Opex"}.get(k),
                    "ref_label": {"restated": "Earlier 10-K", "jump": "Prior year", "opex_over_revenue": "Revenue"}.get(k),
                    "cause_label": FINDING_LABEL.get(lk, row["cause_label"])}
            if d.get("field"):
                row["series"] = _value_series(con, q["ticker"], d["field"])
            row["evidence"] = {"message": d.get("message"), "kind": k, "size": d.get("size"), **({"dimension": d.get("subject")} if d.get("rule") == "fact_readings_differ" and d.get("subject") else {})}  # two categories, one year: named apart
            row |= _finding_numbers(d, q["ticker"], lad, restated)  # STORY-027: the gap in the columns, not only in the Details prose
        elif q["kind"] == "blocked":
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd" if d.get("value") is not None else None, "ours": d.get("value")}
            row["evidence"] = {"message": d.get("message"), "rule": d.get("rule")}
        elif q["kind"] == "value_missing":
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd", "ours": None, "reference": _num(d.get("reference")), "ours_label": "Not extracted"}
            if d.get("field"):
                row["series"] = _value_series(con, q["ticker"], d["field"])
            row["evidence"] = {"label": d.get("label"), "reference": d.get("reference"), "period_end": d.get("period_end")}
        elif q["kind"] == "reading_unfingerprinted":
            row["evidence"] = {"step": d.get("step"), "subject": d.get("subject"), "label": d.get("label"), "rerun": f"ledger {d.get('step')} --run --ticker {q['ticker']}"}
        elif q["kind"] == "new_filing":
            row |= {"period": d.get("period")}
            row["evidence"] = {"url": d.get("url"), "filed": d.get("filed"), "form": d.get("form")}
        if q["kind"] in ("fact_differs", "fact_changed") or (q["kind"] == "finding_unconfirmed" and d.get("rule") == "fact_readings_differ"):
            dim = d.get("dimension") if q["kind"] != "finding_unconfirmed" else d.get("subject")
            row["evidence"]["restatement"] = restated.get((q["ticker"], d.get("field"), dim or "", d.get("period")))
        if q["kind"] == "finding_unconfirmed" and d.get("rule") == "segment_basis_mixed":
            row["evidence"]["basis"] = basis.get((q["ticker"], d.get("field"), d.get("period")))
        if q["kind"] in ("blocked", "finding_unconfirmed"):
            row["encode"] = _offers(con, q["key"], enc)  # T36: what this item may be written as, once, for every company it applies to
        if row["ours"] is not None and row["reference"] is not None:
            try:
                row["delta"] = row["ours"] - row["reference"]
                row["delta_pct"] = (row["delta"] / abs(row["reference"])) if row["reference"] else None
            except TypeError:
                pass
        rows.append(row)
    confirm = to_confirm(None if flow["scope"] in ("", "all") else flow["tickers"], names)
    rows += asset_types(con, flow.get("tickers") or sorted(names), names)  # the scope's tickers: SCOPE for "all", a layer's, or the one ticker asked for
    from ..core.states import row as row_state
    from .resolutions import is_live
    for r in confirm + rows:  # the row's word on the page: states.row, the one the trail and Proof read
        r["verification"] = row_state(r["state"], r["by"])
        r["bulk"] = r["cause"] != ASSET_TYPES and is_live(r["key"])  # F-BF4: only what /api/resolve/bulk accepts is selectable; a category mapping never
    from ..core.states import tally  # the header's counts, by the same word every row shows: Proposed is every `wait` row (a run's
    by_state = tally(r["verification"] for r in confirm + rows)  # decision to confirm, an asset type no person confirmed), the set G6 refuses on
    from ..core.states import buckets
    by_company = buckets((r["ticker"], r["verification"]) for r in confirm + rows)  # the one per-company count (states.buckets), as Proof and Release read it
    open_ = [r for r in rows if r["open"]]
    by_cause = {}
    for r in confirm + rows:
        by_cause.setdefault(r["cause"], {"cause": r["cause"], "label": CAUSES.get(r["cause"]) or r["cause_label"], "rows": 0, "open": 0, "dollars": 0})  # the group's own name, never its first row's
        by_cause[r["cause"]]["rows"] += 1
        by_cause[r["cause"]]["open"] += r["open"]
        by_cause[r["cause"]]["dollars"] += r["dollars"]
    causes = sorted(by_cause.values(), key=lambda c: (c["cause"] != TO_CONFIRM, -c["dollars"]))
    from .mapper import members
    from ..core.config import PEOPLE
    return {"scope": flow["scope"], "release": rel, "last_run": flow["changed"]["last_run"], "rows": confirm + rows, "open": len(open_), "to_confirm": len(confirm), "by_state": by_state, "by_company": by_company, "dollars": sum(r["dollars"] for r in open_),
            "causes": causes, "names": names, "members": members(), "people": list(PEOPLE)}  # who may write: the page disables every write for another name (F-BF13)
