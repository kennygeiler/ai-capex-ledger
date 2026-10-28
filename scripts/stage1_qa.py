"""Stage 1 QA, following the Data plugin's validate-data checklist (Anthropic knowledge-work-plugins), applied to
NVDA's released-candidate values. Each check prefers evidence independent of the path that produced the value."""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
con = duckdb.connect(str(ROOT / "data" / "ledger.duckdb"), read_only=True)
q = lambda sql, *p: [dict(zip([c[0] for c in con.execute(sql, list(p)).description], r)) for r in con.execute(sql, list(p)).fetchall()]
vals = q('select * from "values" where ticker=\'NVDA\'')
ext = q("select e.*, d.form, d.period as doc_period from extractions e join documents d using(accession) where e.ticker='NVDA'")
docs = {d["accession"]: d for d in q("select * from documents where ticker='NVDA'")}
out = {}

def wilson(k, n, z=1.96):
    if n == 0:
        return (0, 1)
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(c - h, 3), round(c + h, 3))

# 1. Completeness / nulls / duplicates
out["completeness"] = {"values": len(vals), "expected": 32, "null_values": sum(v["value"] is None for v in vals),
                       "duplicate_extraction_ids": len(ext) - len({e["extraction_id"] for e in ext})}

# 2. Independent sum check: Q1+Q2+Q3 three-month columns == nine-month YTD column, both read from filings
# (income-statement fields; the Q4 = FY - 9M step makes a full-year tiling check circular, so this is the real test).
by = defaultdict(dict)
for e in ext:
    by[(e["field"], e["period_start"])][(e["period_end"], (e["period_end"] > e["period_start"]))] = e
ninem = [e for e in ext if e["field"] != "capex" and 260 <= (__import__("datetime").date.fromisoformat(e["period_end"]) - __import__("datetime").date.fromisoformat(e["period_start"])).days <= 280]
from datetime import date, timedelta
three = defaultdict(dict)
for e in ext:
    d = (date.fromisoformat(e["period_end"]) - date.fromisoformat(e["period_start"])).days
    if 80 <= d <= 100:
        three[e["field"]][e["period_start"]] = e
sums = []
for n9 in ninem:
    s, parts = date.fromisoformat(n9["period_start"]), []
    for _ in range(3):
        p = three[n9["field"]].get(s.isoformat())
        if not p:
            break
        parts.append(p)
        s = date.fromisoformat(p["period_end"]) + timedelta(days=1)
    if len(parts) == 3:
        tot = sum(p["value"] for p in parts)
        sums.append({"field": n9["field"], "nine_months_to": n9["period_end"], "q_sum": tot, "nine_month_cell": n9["value"],
                     "diff": tot - n9["value"], "ok": abs(tot - n9["value"]) <= 3 * n9["scale"] // 2})
out["q1_q3_vs_9m"] = {"checked": len(sums), "ok": sum(s["ok"] for s in sums), "fails": [s for s in sums if not s["ok"]]}

# 3. Statement tie, read independently from the parsed table: revenue - cost of revenue - total operating expenses = operating income
ties = []
for acc, d in docs.items():
    p = json.loads((ROOT / d["tables_path"]).read_text())
    for t in p["statements"]["income"]:
        rows = {r["label"]: {c["col"]: c["value"] for c in r["cells"]} for r in t["rows"]}
        need = ["Revenue", "Cost of revenue", "Total operating expenses", "Operating income"]
        if all(k in rows for k in need):
            for col in rows["Revenue"]:
                r, c, o, oi = (rows[k].get(col) for k in need)
                if None not in (r, c, o, oi):
                    ties.append({"accession": acc, "column": t["columns"][col], "diff_millions": round(r - c - o - oi, 3)})
out["statement_tie"] = {"checked": len(ties), "ok": sum(abs(x["diff_millions"]) <= 1 for x in ties), "fails": [x for x in ties if abs(x["diff_millions"]) > 1]}

# 4. Magnitude / sign
V = {(v["field"], v["cal_q"]): v["value"] for v in vals}
qs = sorted({v["cal_q"] for v in vals})
mag = []
for cq in qs:
    r, c, oi, cx = (V.get((f, cq)) for f in ("revenue", "cost_of_revenue", "operating_income", "capex"))
    if not (r > 0 and c > 0 and cx > 0 and c < r and oi <= r - c):
        mag.append(cq)
out["magnitude"] = {"quarters": len(qs), "implausible": mag,
                    "op_margin_range": [round(min(V[("operating_income", q)] / V[("revenue", q)] for q in qs), 3), round(max(V[("operating_income", q)] / V[("revenue", q)] for q in qs), 3)],
                    "capex_to_revenue_range": [round(min(V[("capex", q)] / V[("revenue", q)] for q in qs), 4), round(max(V[("capex", q)] / V[("revenue", q)] for q in qs), 4)]}

# 5. Trend continuity: quarter-on-quarter moves beyond 2x either way
jumps = []
for f in ("revenue", "cost_of_revenue", "operating_income", "capex"):
    for a, b in zip(qs, qs[1:]):
        x, y = V[(f, a)], V[(f, b)]
        if x and (y / x > 2 or y / x < 0.5):
            jumps.append({"field": f, "from": a, "to": b, "ratio": round(y / x, 2)})
out["trend_jumps_over_2x"] = jumps

# 6. Cross-reference + statistics
agree = sum(v["label"] == "agree" for v in vals)
out["xbrl_agreement"] = {"agree": agree, "n": len(vals), "wilson_95": wilson(agree, len(vals)),
                         "hand_check_zero_error_upper_bound_rule_of_three": round(3 / len(vals), 3)}

# 7. Metric definition: capex row labels used
out["capex_rows"] = sorted({e["row_label"] for e in ext if e["field"] == "capex"})
out["methods"] = dict(sorted({m: sum(v["method"] == m for v in vals) for m in {v["method"] for v in vals}}.items()))
print(json.dumps(out, indent=1, default=str))
