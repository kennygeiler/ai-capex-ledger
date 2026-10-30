"""The reconcile workbench (DATAHQ, Reconcile tab): every open item of the Flow queue as one row a person can judge
without opening anything: ours, the reference, the delta, where each number came from, the evidence (the cited
cell and its screenshot, the quote, the inputs), and the resolution. Built from `app.flow()`; nothing is read from
filings. `/api/v1/reconcile?scope=` serves it; `/api/resolve` records one resolution, `/api/resolve/bulk` many."""
from __future__ import annotations

from . import store
from .config import industry

EVIDENCE = store.ROOT / "reports" / "evidence"
CAUSES = {"reference_disagrees": "Attribution disagrees with a stated figure", "fact_differs": "Fact differs from the filing's XBRL tag",
          "fact_changed": "Fact changed since the signed release", "attribution_moved": "Attribution moved in the last load",
          "blocked": "Blocked: a definition is missing", "finding_unconfirmed": "SEC data can't confirm a value", "new_filing": "New filing at the SEC"}
REF_LABEL = {"reference_disagrees": "stated", "fact_differs": "XBRL tag", "fact_changed": "signed release", "attribution_moved": "before the load",
             "blocked": None, "finding_unconfirmed": "XBRL tag", "new_filing": None}


def _png(extraction_id: str | None) -> str | None:
    return f"/evidence/{extraction_id}.png" if extraction_id and (EVIDENCE / f"{extraction_id}.png").exists() else None


def _inputs(con, ids: str) -> list[dict]:
    """The attribution's inputs by id, with their values: fact:T|field|dim|period or value:T|field|period."""
    out = []
    for i in (ids or "").split(","):
        if not i:
            continue
        kind, _, rest = i.partition(":")
        parts = rest.split("|")
        try:
            if kind == "fact" and len(parts) == 4:
                r = con.execute("select value, label from facts where ticker=? and field=? and dimension=? and period=?", parts).fetchone()
                out.append({"id": i, "what": f"{parts[2]} {parts[3]}".strip(), "field": parts[1], "value": r[0] if r else None, "check": r[1] if r else None})
            elif kind == "stmt":  # a statement the attributor used: its quote and amount
                r = con.execute("select amount_low, amount_high, share, quote, source, period from ai_statements where statement_id = ?", [rest]).fetchone()
                amt = (r[0] + r[1]) / 2 if r and r[0] is not None and r[1] is not None else None
                out.append({"id": i, "what": f"“{r[3] or ''}” ({r[4]}, {r[5]})" if r else i, "value": amt, "check": None,  # the whole quote: a cut one hid "AI infrastructure capex" (type 68)
                            "share": r[2] if r else None})
            elif kind == "value" and len(parts) == 3:
                r = con.execute('select value, label from "values" where ticker=? and field=? and period=?', parts).fetchone()
                out.append({"id": i, "what": f"{parts[1]} {parts[2]}", "field": parts[1], "value": r[0] if r else None, "check": r[1] if r else None})
            else:
                out.append({"id": i, "what": i, "value": None, "check": None})
        except Exception:  # a malformed id never breaks the page
            out.append({"id": i, "what": i, "value": None, "check": None})
    return out


def _attribution_series(con, ticker: str, field: str, refs: list[dict]) -> list[dict]:
    """Ours by year (amount, share, the total it is a share of, method) with every stated figure for that year."""
    cur = con.execute("select period, ai_amount, ai_share, method, kind from attribution where ticker = ? and field = ? and kind = 'actual' and ai_amount is not null order by period", [ticker, field])
    ours = {r[0]: {"period": r[0], "amount": r[1], "share": r[2], "method": r[3]} for r in cur.fetchall()}
    totals = {r[0]: r[1] for r in con.execute('select period, value from "values" where ticker = ? and field = ? and value is not null', [ticker, field]).fetchall()}
    out = {}
    for p in sorted(set(ours) | {r["period"] for r in refs} | set(totals)):
        out[p] = {"period": p, "amount": ours.get(p, {}).get("amount"), "share": ours.get(p, {}).get("share"), "method": ours.get(p, {}).get("method"), "total": totals.get(p), "refs": []}
    for r in refs:
        out[r["period"]]["refs"].append({"measure": r["measure"], "relation": r["relation"], "reference": r["reference"], "outcome": r["outcome"], "source": (r.get("source") or {}).get("kind")})
    return list(out.values())


def xbrl_name(con, accession: str, period_end: str | None, value) -> dict | None:
    """Which us-gaap concept and member the filing's reference value came from: the instance is read (cached XML) and
    the one fact with that value on that date is named. None when the filing has no instance or no such fact."""
    if value is None or not accession:
        return None
    try:
        doc = con.execute("select cik, ticker from documents where accession = ?", [accession]).fetchone()
        if not doc:
            return None
        want = round(float(value))
        # the reference may come from any of the company's filings (the year's own 10-K tags it; a later one restates), newest first
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


def items(con, flow: dict) -> dict:
    """One uniform row per queue item. `measure` is usd or share; `ours` and `reference` are in that measure;
    `delta` = ours - reference; `delta_pct` relative to the reference."""
    names, rel = flow["names"], flow["release"]["last"]
    attr = {}
    tickers = sorted({q["ticker"] for q in flow["queue"]})
    if tickers:
        cur = con.execute("select ticker, field, period, kind, method, ai_amount, ai_share, basis, inputs, confidence from attribution where ticker in (select unnest(?))", [tickers])
        for r in cur.fetchall():
            attr[(r[0], r[1], r[2], r[3])] = dict(zip([c[0] for c in cur.description], r))
    evrows = {}
    for r in ((flow.get("insight") or {}).get("evaluation") or {}).get("rows", []):
        evrows.setdefault((r["ticker"], r.get("field", "capex")), []).append(r)
    rows = []
    for q in flow["queue"]:
        d = q.get("detail") or {}
        row = {"key": q["key"], "hash": q["hash"], "cause": q["kind"], "cause_label": CAUSES.get(q["kind"], q["kind"]), "state": q["state"], "ticker": q["ticker"],
               "name": names.get(q["ticker"], q["ticker"]), "layer": industry(q["ticker"]), "field": None, "period": None, "where": q["where"], "measure": None,
               "ours": None, "ours_label": None, "reference": None, "ref_label": REF_LABEL.get(q["kind"]), "relation": "eq", "delta": None, "delta_pct": None,
               "dollars": q.get("dollars") or 0, "new": bool(q.get("new")), "action": q["action"], "impact": q["impact"], "resolution": q.get("resolution"),
               "evidence": {}}
        if q["kind"] == "reference_disagrees":
            a = attr.get((q["ticker"], d.get("field", "capex"), d.get("period"), "actual"), {})
            row |= {"field": f"ai_{d.get('field', 'capex')}", "period": d.get("period"), "measure": d.get("measure"), "ours": d.get("ours"), "reference": d.get("reference"), "relation": d.get("relation", "eq"),
                    "ours_label": f"by {d.get('method')}"}
            row["series"] = _attribution_series(con, q["ticker"], d.get("field", "capex"), evrows.get((q["ticker"], d.get("field", "capex")), []))
            row["evidence"] = {"quote": (d.get("source") or {}).get("quote"), "url": (d.get("source") or {}).get("url"), "source_kind": (d.get("source") or {}).get("kind"), "source_date": (d.get("source") or {}).get("date"),
                               "reference_basis": d.get("basis"), "basis": a.get("basis"), "inputs": _inputs(con, a.get("inputs", "")), "confidence": a.get("confidence"),
                               "ours_amount": a.get("ai_amount"), "ours_share": a.get("ai_share")}
        elif q["kind"] == "fact_differs":
            c = d.get("cite") or {}
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd", "ours": d.get("value"), "reference": d.get("reference"), "ours_label": "cited cell"}
            row["series"] = _fact_series(con, q["ticker"], d.get("field"), d.get("dimension") or "")
            pe = con.execute("select period_end from facts where ticker = ? and field = ? and coalesce(dimension, '') = ? and period = ?", [q["ticker"], d.get("field"), d.get("dimension") or "", d.get("period")]).fetchone()
            row["evidence"] = {"cell": {k: c.get(k) for k in ("table_id", "row_label", "column_label", "cell_text", "accession")} if c else None, "png": _png(c.get("extraction_id")),
                               "xbrl": xbrl_name(con, c.get("accession") or "", pe[0] if pe else None, d.get("reference")),
                               "url": d.get("url"), "used_by": d.get("used_by") or [], "release_value": d.get("release_value"), "dimension": d.get("dimension")}
        elif q["kind"] == "fact_changed":
            row |= {"field": d.get("field"), "period": d.get("period"), "measure": "usd", "ours": d.get("value"), "reference": d.get("release_value"), "ours_label": "now"}
            row["evidence"] = {"dimension": d.get("dimension"), "release": rel}
        elif q["kind"] == "attribution_moved":
            parts = (q["where"] or "").split()  # "revenue FY2025 actual"
            before, after = d.get("before") or [None, None], d.get("after") or [None, None]
            row |= {"field": parts[0] if parts else None, "period": parts[1] if len(parts) > 1 else None, "measure": "usd", "ours": after[1], "reference": before[1],
                    "ours_label": f"by {after[0]}", "ref_label": f"before, by {before[0]}"}
            row["evidence"] = {"before": before, "after": after}
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
    open_ = [r for r in rows if not r["resolution"] or r["resolution"]["state"] in ("fix", "blocks")]
    by_cause = {}
    for r in rows:
        by_cause.setdefault(r["cause"], {"cause": r["cause"], "label": r["cause_label"], "rows": 0, "open": 0, "dollars": 0})
        by_cause[r["cause"]]["rows"] += 1
        by_cause[r["cause"]]["open"] += r in open_
        by_cause[r["cause"]]["dollars"] += r["dollars"]
    return {"scope": flow["scope"], "release": rel, "last_run": flow["changed"]["last_run"], "rows": rows, "open": len(open_), "dollars": sum(r["dollars"] for r in open_),
            "causes": sorted(by_cause.values(), key=lambda c: -c["dollars"]), "noise": flow["noise"], "names": names}
