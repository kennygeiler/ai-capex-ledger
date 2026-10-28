"""Data-quality checks. Each issue: {severity: error|warn|info, check, ticker, metric, cal_q, message}."""
from .normalize import days

CHECKED = ("revenue", "capex", "opex", "total_costs")


def check_company(ticker: str, metrics: dict, vint_by_metric: dict, window: list[str], first_filed: str | None, last_period_end: str | None) -> tuple[list[dict], dict]:
    issues, stats = [], {"tiling_checks": 0, "tiling_failures": 0}
    add = lambda sev, check, metric, cq, msg: issues.append({"severity": sev, "check": check, "ticker": ticker, "metric": metric, "cal_q": cq, "message": msg})

    for metric in CHECKED:
        rows = metrics.get(metric, {})
        # 1. Sign: revenue and capex are never negative; opex below zero means a mapping problem.
        for cq, r in rows.items():
            if cq not in window:
                continue
            if r["value"] < 0:
                add("error" if metric in ("revenue", "capex") else "warn", "sign", metric, cq, f"Negative value {r['value']:,}.")
        # 2. Period length: a fiscal quarter is 12-17 weeks (52/53-week calendars and Costco's 16-week Q4 included).
        for cq, r in rows.items():
            if cq in window and not 82 <= r["days"] <= 119:
                add("warn", "period_length", metric, cq, f"Quarter spans {r['days']} days ({r['period_start']} to {r['period_end']}).")
        # 3. Jumps: a >3x move between quarters usually means a derivation or tag error.
        ordered = sorted((r for r in rows.values() if r["cal_q"] >= window[0]), key=lambda r: r["period_end"])
        for a, b in zip(ordered, ordered[1:]):
            if a["value"] > 0 and b["value"] > 0 and max(a["value"], b["value"]) / min(a["value"], b["value"]) > 3:
                add("warn", "jump", metric, b["cal_q"], f"{a['value'] / 1e6:,.0f}M to {b['value'] / 1e6:,.0f}M between {a['cal_q']} and {b['cal_q']}.")
        # 4. Coverage inside the window, with a reason for every gap.
        for cq in window:
            if cq in rows:
                continue
            if metric == "opex" and cq in metrics.get("total_costs", {}):
                reason = "No separate cost-of-revenue line (costs reported by type), so opex excluding cost of revenue can't be split out. Use total_costs."
            elif metric in ("opex", "total_costs") and cq in metrics.get("revenue", {}):
                reason = "Operating income not tagged for this quarter."
            elif first_filed and _q_end(cq) < first_filed and (not rows or cq < min(rows)):
                reason = "Before the company's first periodic filing (pre-IPO or pre-registration)."
            elif last_period_end and _q_end(cq) > last_period_end:
                reason = "Not filed yet."
            elif metric == "capex" and not rows:
                reason = "No capex line in the standard us-gaap tags: banks and insurers don't report it separately, and some companies use their own extension tag, which the companyfacts API leaves out."
            elif metric == "opex" and not rows:
                reason = "None of the opex routes has data (operating income, total costs, OperatingExpenses, SG&A, non-interest expense)."
            else:
                reason = "No fact found for any candidate tag."
            add("info", "coverage", metric, cq, reason)
        # 5. Restatements and fallback forms.
        for cq, r in rows.items():
            if cq in window and r.get("restated"):
                if r.get("original_value") is not None:
                    add("info", "restated", metric, cq, f"Restated: first filed {r['original_value']:,}, now {r['value']:,}.")
                else:
                    add("info", "restated", metric, cq, "A source filing behind this derived quarter was later restated; the latest value is used.")
            if cq in window and r.get("basis_conflict"):
                add("info", "basis_conflict", metric, cq, "Full year minus nine months mixed an old and a restated basis; used full year minus the three restated quarters instead.")
            if cq in window and r.get("fallback_form"):
                add("info", "fallback_form", metric, cq, f"Taken from {r['form']} (registration statement), not a 10-Q/10-K.")
        # 6. Tag switches inside the window.
        tags = {rows[cq]["concept"] for cq in window if cq in rows}
        if len(tags) > 1 and metric in ("revenue", "capex"):
            add("info", "tag_switch", metric, None, f"Uses {len(tags)} tags across the window: {', '.join(sorted(tags))}.")

    # 7. Tiling: quarters must add up to each year-to-date / full-year fact they fall inside.
    for metric in ("revenue", "capex"):
        series = metrics.get(metric, {})
        by_end = {r["period_end"]: r for r in series.values()}
        for (s, e), f in vint_by_metric.get(metric, {}).items():
            if days(s, e) <= 100 or not any(cq in window for cq in [r["cal_q"] for r in series.values() if s <= r["period_start"] and r["period_end"] <= e]):
                continue
            inside = sorted((r for r in by_end.values() if r["period_start"] >= s and r["period_end"] <= e), key=lambda r: r["period_end"])
            if not inside or inside[0]["period_start"] != s or inside[-1]["period_end"] != e:
                continue
            if any(r["concept"] != f["concept"] for r in inside):
                continue
            stats["tiling_checks"] += 1
            total = sum(r["value"] for r in inside)
            if abs(total - f["val"]) > max(1e6, abs(f["val"]) * 0.005):
                stats["tiling_failures"] += 1
                add("warn", "tiling", metric, inside[-1]["cal_q"], f"Quarters {s} to {e} sum to {total:,} but the filed total is {f['val']:,}.")
    return issues, stats


def _q_end(cq: str) -> str:
    y, q = int(cq[:4]), int(cq[5])
    return {1: f"{y}-03-31", 2: f"{y}-06-30", 3: f"{y}-09-30", 4: f"{y}-12-31"}[q]
