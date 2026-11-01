"""The reconcile workbench (DATAHQ, Reconcile tab): every open item of the queue as one row a person can judge
without opening anything: ours, the reference, the delta, where each number came from, the evidence (the cited
cell and its screenshot), and the resolution. Built from `app.flow()`; nothing is read from filings and nothing in
it is an estimate. `/api/v1/reconcile?scope=` serves it; `/api/resolve` records one resolution, `/api/resolve/bulk` many."""
from __future__ import annotations

from . import resolutions, status, store
from .config import industry

EVIDENCE = store.ROOT / "reports" / "evidence"
CAUSES = {"fact_differs": "Fact differs from the filing's XBRL tag", "fact_changed": "Fact changed since the signed release", "blocked": "Blocked: a definition is missing",
          "finding_unconfirmed": "SEC data can't confirm a value", "new_filing": "New filing at the SEC"}
REF_LABEL = {"fact_differs": "XBRL tag", "fact_changed": "signed release", "blocked": None, "finding_unconfirmed": "XBRL tag", "new_filing": None}


def _png(extraction_id: str | None) -> str | None:
    return f"/evidence/{extraction_id}.png" if extraction_id and (EVIDENCE / f"{extraction_id}.png").exists() else None


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
        from .reference.dimensions import instance_facts
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
    return [status.of_value({"field": r[0], "period": r[1], "label": r[2]}, resolutions.resolution_of(idx, "values", ticker, r[0], "", r[1])) for r in cur.fetchall()]


def _fact_row(con, ticker: str, field: str | None, dimension: str | None, period: str | None) -> dict | None:
    cols = [c[0] for c in con.execute("select * from facts limit 0").description]
    r = con.execute("select * from facts where ticker = ? and field = ? and coalesce(dimension, '') = ? and period = ?", [ticker, field or "", dimension or "", period or ""]).fetchone()
    return dict(zip(cols, r)) if r else None


def _state(con, q: dict, idx: dict) -> dict:
    """The queue item's state from the one definition (status.py): the same row gets the same answer on Proof."""
    d, res, t = q.get("detail") or {}, q.get("resolution"), q["ticker"]
    if q["kind"] in ("fact_differs", "fact_changed"):
        f = _fact_row(con, t, d.get("field"), d.get("dimension"), d.get("period")) or {"label": d.get("label")}
        from .proof import _restated
        return status.of_fact(f, res, _restated(con, t, f) if f.get("label") == "unresolved" and f.get("accession") else None)
    if q["kind"] == "finding_unconfirmed":
        return status.of_exception({"rule_id": d.get("kind"), "severity": "warn", "message": d.get("message")}, res, _value_states(con, t, d.get("field"), d.get("period"), idx))
    if q["kind"] == "blocked":
        return status.of_exception({"rule_id": d.get("rule"), "severity": "block", "message": d.get("message")}, res)
    return status.state({"reason": "a filing at the SEC the ledger has not read", "resolution": res})


TO_CONFIRM = "to_confirm"


def to_confirm(tickers: list[str] | None, names: dict) -> list[dict]:
    """The decisions a run made for a person to confirm (resolutions.unconfirmed), as workbench rows: their own group,
    first. None of them is a dataset row; each is a resolution a person has not yet made their own."""
    out = []
    for r in resolutions.unconfirmed():
        kind, _, rest = r["key"].partition("|")
        ticker, _, where = rest.partition("|")
        if tickers is not None and ticker not in tickers:
            continue
        out.append({"key": r["key"], "hash": r["hash"], "cause": TO_CONFIRM, "cause_label": "To confirm: a decision a run made, for Kenny Geiler to confirm or overturn", "state": "to confirm",
                    "by": f"resolution:{r.get('id', '')}", "reason": r["reason"], "open": False, "ticker": ticker, "name": names.get(ticker, ticker), "layer": industry(ticker),
                    "field": None, "period": None, "where": f"{kind.replace('_', ' ')}: {where}", "measure": None, "ours": None, "ours_label": None, "reference": None, "ref_label": None,
                    "relation": "eq", "delta": None, "delta_pct": None, "dollars": 0, "new": False, "action": "confirm", "impact": "the release refuses while it is unconfirmed",
                    "resolution": {k: r.get(k) for k in ("id", "state", "by", "at", "reason")}, "evidence": {"message": r["reason"], "proposed": r["state"]}})
    return out


def items(con, flow: dict) -> dict:
    """One uniform row per queue item. `measure` is usd; `ours` and `reference` are in that measure; `delta` = ours - reference.
    Every row carries `state`, `by` and `reason` from status.state and `open` (open or blocked); `open` counts those.
    The decisions a run left for a person to confirm come first as their own group (`to_confirm`, T3), counted apart."""
    names, rel = flow["names"], flow["release"]["last"]
    idx = resolutions.by_row()
    rows = []
    for q in flow["queue"]:
        d = q.get("detail") or {}
        st = _state(con, q, idx)
        row = {"key": q["key"], "hash": q["hash"], "cause": q["kind"], "cause_label": CAUSES.get(q["kind"], q["kind"]), "state": st["state"], "by": st["by"], "reason": st["reason"], "open": status.is_open(st),
               "ticker": q["ticker"], "name": names.get(q["ticker"], q["ticker"]), "layer": industry(q["ticker"]), "field": None, "period": None, "where": q["where"], "measure": None,
               "ours": None, "ours_label": None, "reference": None, "ref_label": REF_LABEL.get(q["kind"]), "relation": "eq", "delta": None, "delta_pct": None,
               "dollars": q.get("dollars") or 0, "new": bool(q.get("new")), "action": q["action"], "impact": q["impact"], "resolution": q.get("resolution"),
               "evidence": {}}
        if q["kind"] == "fact_differs":
            c = d.get("cite") or {}
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd", "ours": d.get("value"), "reference": _num(d.get("reference")), "ours_label": "cited cell"}
            row["series"] = _fact_series(con, q["ticker"], d.get("field"), d.get("dimension") or "")
            pe = con.execute("select period_end from facts where ticker = ? and field = ? and coalesce(dimension, '') = ? and period = ?", [q["ticker"], d.get("field"), d.get("dimension") or "", d.get("period")]).fetchone()
            row["evidence"] = {"cell": {k: c.get(k) for k in ("table_id", "row_label", "column_label", "cell_text", "accession")} if c else None, "png": _png(c.get("extraction_id")),
                               "xbrl": xbrl_name(con, c.get("accession") or "", pe[0] if pe else None, d.get("reference")),
                               "url": d.get("url"), "release_value": d.get("release_value"), "dimension": d.get("dimension")}
        elif q["kind"] == "fact_changed":
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd", "ours": d.get("value"), "reference": d.get("release_value"), "ours_label": "now"}
            row["evidence"] = {"dimension": d.get("dimension"), "release": rel}
        elif q["kind"] == "finding_unconfirmed":  # a rule's finding (restated, jump, row_switch, ...) the SEC's data can't confirm
            k = d.get("kind")
            numeric = k in ("restated", "jump", "opex_over_revenue") and d.get("before") is not None and d.get("after") is not None
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd" if numeric else None, "ours": d.get("after") if numeric else None,
                    "reference": d.get("before") if numeric else None, "ours_label": {"restated": "newest filing", "jump": "this year", "opex_over_revenue": "opex"}.get(k),
                    "ref_label": {"restated": "earlier filing", "jump": "year before", "opex_over_revenue": "revenue"}.get(k),
                    "cause_label": {"restated": "Restated: the SEC's data can't confirm", "jump": "Big move: the SEC's data can't confirm", "row_switch": "Line renamed across filings",
                                    "capex_intensity": "Capex high against revenue", "opex_over_revenue": "Opex above revenue"}.get(k, row["cause_label"])}
            if d.get("field"):
                row["series"] = _value_series(con, q["ticker"], d["field"])
            row["evidence"] = {"message": d.get("message"), "kind": k, "size": d.get("size")}
        elif q["kind"] == "blocked":
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd" if d.get("value") is not None else None, "ours": d.get("value")}
            row["evidence"] = {"message": d.get("message"), "rule": d.get("rule")}
        elif q["kind"] == "new_filing":
            row |= {"period": d.get("period")}
            row["evidence"] = {"url": d.get("url"), "filed": d.get("filed"), "form": d.get("form")}
        if row["ours"] is not None and row["reference"] is not None:
            try:
                row["delta"] = row["ours"] - row["reference"]
                row["delta_pct"] = (row["delta"] / abs(row["reference"])) if row["reference"] else None
            except TypeError:
                pass
        rows.append(row)
    open_ = [r for r in rows if r["open"]]
    confirm = to_confirm(None if flow["scope"] in ("", "all") else flow["tickers"], names)
    by_cause = {}
    for r in confirm + rows:
        by_cause.setdefault(r["cause"], {"cause": r["cause"], "label": r["cause_label"], "rows": 0, "open": 0, "dollars": 0})
        by_cause[r["cause"]]["rows"] += 1
        by_cause[r["cause"]]["open"] += r["open"]
        by_cause[r["cause"]]["dollars"] += r["dollars"]
    causes = sorted(by_cause.values(), key=lambda c: (c["cause"] != TO_CONFIRM, -c["dollars"]))
    return {"scope": flow["scope"], "release": rel, "last_run": flow["changed"]["last_run"], "rows": confirm + rows, "open": len(open_), "to_confirm": len(confirm), "dollars": sum(r["dollars"] for r in open_),
            "causes": causes, "names": names}
