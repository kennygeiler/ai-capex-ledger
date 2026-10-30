"""Plans versus reality: what a company said it would spend, against what it spent (docs/THESIS.md).

Code only, nothing new is read. For every company, field and fiscal year that has an actual value, the plan is the
newest guidance for that year made before the year ended: an `ai_statements` row with kind outlook, class
explicit_amount, from a text dated on or before the fiscal year end. Total guidance (scope total) is compared with the
company's own value; AI guidance (scope ai) with the attributed AI amount. The gap is actual minus the midpoint of the
guided range, and `inside_range` says whether the actual landed inside the range the company gave."""
from __future__ import annotations


def plans(con, tickers: list[str] | None = None) -> list[dict]:
    where = "where v.ticker in (select unnest(?))" if tickers else ""
    params = [tickers] if tickers else []
    rows = lambda sql, p=(): [dict(zip([c[0] for c in con.execute(sql, list(p)).description], r)) for r in con.execute(sql, list(p)).fetchall()]
    actual = {(r["ticker"], r["field"], r["period"]): r for r in rows(f'select v.ticker, v.field, v.period, v.period_end, v.value from "values" v {where} and v.value is not null' if where else 'select v.ticker, v.field, v.period, v.period_end, v.value from "values" v where v.value is not null', params)}
    ai = {(r["ticker"], r["field"], r["period"]): r for r in rows("select ticker, field, period, ai_amount, method from attribution where kind = 'actual' and ai_amount is not null")}
    guidance = rows("""select s.ticker, s.field, s.period, s.scope, s.amount_low, s.amount_high, s.quote, s.source, s.text_id, t.date, t.url
                       from ai_statements s join texts t on t.text_id = s.text_id
                       where s.kind = 'outlook' and s.class = 'explicit_amount' order by t.date desc""")
    out = []
    for (ticker, field, period), v in sorted(actual.items()):
        for scope in ("total", "ai"):
            g = next((g for g in guidance if (g["ticker"], g["field"], g["period"], g["scope"]) == (ticker, field, period, scope) and g["date"] <= v["period_end"]), None)
            if g is None:
                continue
            real = v["value"] if scope == "total" else (ai.get((ticker, field, period)) or {}).get("ai_amount")
            mid = (g["amount_low"] + g["amount_high"]) // 2
            out.append({"ticker": ticker, "field": field, "period": period, "scope": scope, "plan_low": g["amount_low"], "plan_high": g["amount_high"], "plan_mid": mid,
                        "plan_date": g["date"], "plan_source": g["source"], "plan_quote": g["quote"], "plan_url": g["url"], "plan_text": g["text_id"],
                        "actual": real, "actual_method": None if scope == "total" else (ai.get((ticker, field, period)) or {}).get("method"),
                        "gap": None if real is None else real - mid, "gap_share": None if real is None or mid == 0 else round((real - mid) / mid, 3),
                        "inside_range": None if real is None else g["amount_low"] <= real <= g["amount_high"]})
    return out
