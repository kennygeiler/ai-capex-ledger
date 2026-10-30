"""What the agents cost (docs/TICKETS.md C8): tokens, seconds, attempts and an estimated price per step, per company and
per release, from the `runs` table every agent step writes. The agents run on a Claude subscription, so the dollar
figure is what the same work would cost at list price (`config.PRICES`), not what was paid."""
from __future__ import annotations

import json

from .config import PRICES, industry

AGENT_STEPS = ("extract", "aispend", "notes", "projects", "attribution")


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def usd(model: str | None, inp: float, out: float) -> float | None:
    pr = PRICES.get(model or "")
    return None if not pr else round(inp / 1e6 * pr["input"] + out / 1e6 * pr["output"], 4)


def report(con, tickers: list[str] | None = None) -> dict:
    """Per agent step and per company: calls, tokens, seconds, attempts, failures, estimated USD."""
    runs = _rows(con, "select run_id, step, subject, started_at, seconds, outcome, versions, detail from runs where step in (select unnest(?))", list(AGENT_STEPS))
    acc_t = {r["accession"]: r["ticker"] for r in _rows(con, "select accession, ticker from documents")}
    txt_t = {r["text_id"]: r["ticker"] for r in _rows(con, "select text_id, ticker from texts")}
    want = set(t.upper() for t in tickers) if tickers else None
    by_step, by_co, models = {}, {}, set()
    for r in runs:
        d = json.loads(r["detail"] or "{}")
        if "input_tokens" not in d and r["outcome"] != "failed":
            continue  # a load step, not an agent call
        t = r["subject"] if r["step"] == "attribution" else (acc_t.get(r["subject"]) or txt_t.get(r["subject"]) or (r["subject"] or "").split("|")[0])
        if want and t not in want:
            continue
        model = (json.loads(r["versions"] or "{}").get("llm") or d.get("model") or json.loads(r["versions"] or "{}").get("model"))
        if model:
            models.add(model)
        inp, out = float(d.get("input_tokens") or 0), float(d.get("output_tokens") or 0)
        for key, bucket in ((r["step"], by_step), (t, by_co)):
            o = bucket.setdefault(key, {"calls": 0, "input_tokens": 0.0, "output_tokens": 0.0, "seconds": 0.0, "attempts": 0, "failed": 0, "usd": 0.0})
            o["calls"] += 1
            o["input_tokens"] += inp
            o["output_tokens"] += out
            o["seconds"] += float(d.get("seconds") or r["seconds"] or 0)  # the agent call's own seconds, not the loader's
            o["attempts"] += int(d.get("attempts") or (1 if r["outcome"] == "ok" else 0))
            o["failed"] += r["outcome"] == "failed"
            o["usd"] += usd(model, inp, out) or 0.0
    for b in (by_step, by_co):
        for o in b.values():
            o["usd"] = round(o["usd"], 2)
            o["seconds"] = round(o["seconds"], 1)
    total = {k: round(sum(o[k] for o in by_step.values()), 2) for k in ("calls", "input_tokens", "output_tokens", "seconds", "attempts", "failed", "usd")}
    companies = [{"ticker": t, "layer": industry(t), **o} for t, o in sorted(by_co.items(), key=lambda kv: -kv[1]["usd"])]
    per_co = round(total["usd"] / len(by_co), 2) if by_co else None
    return {"steps": {k: by_step[k] for k in AGENT_STEPS if k in by_step}, "companies": companies, "total": total, "per_company_usd": per_co,
            "models": sorted(models), "prices": {m: PRICES[m] for m in models if m in PRICES}, "unpriced_models": sorted(m for m in models if m not in PRICES),
            "note": "Estimated at list price; the agents ran on a Claude subscription. Tokens include cache reads at the input price."}


def render(rep: dict) -> str:
    t = rep["total"]
    lines = [f"Agent cost: {int(t['calls'])} calls, {t['input_tokens'] / 1e6:.1f}M in / {t['output_tokens'] / 1e6:.2f}M out tokens, {t['seconds'] / 60:.0f} min, "
             f"{int(t['failed'])} failed, about ${t['usd']:,.2f} at list price" + (f" (${rep['per_company_usd']:,.2f} per company)" if rep["per_company_usd"] else "") + ".",
             "", "| Step | calls | in tokens | out tokens | min | attempts | failed | USD |", "|---|---|---|---|---|---|---|---|"]
    for k, o in rep["steps"].items():
        lines.append(f"| {k} | {int(o['calls'])} | {o['input_tokens'] / 1e6:.2f}M | {o['output_tokens'] / 1e6:.3f}M | {o['seconds'] / 60:.1f} | {int(o['attempts'])} | {int(o['failed'])} | ${o['usd']:,.2f} |")
    lines += ["", "| Company | layer | calls | USD |", "|---|---|---|---|"] + [f"| {c['ticker']} | {c['layer']} | {int(c['calls'])} | ${c['usd']:,.2f} |" for c in rep["companies"][:15]]
    if rep["unpriced_models"]:
        lines.append(f"\nNo price on file for: {', '.join(rep['unpriced_models'])} (add to ledger/config.py PRICES).")
    return "\n".join(lines)
