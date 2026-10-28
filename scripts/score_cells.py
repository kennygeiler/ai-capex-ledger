"""Cell-level reading accuracy: each agent value against the XBRL fact for the same filing, concept and period.
This scores reading alone, before any derivation. Run: uv run python scripts/score_cells.py ORCL APLD"""
import json
import sys
from collections import Counter
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ledger.config import CONCEPTS  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
con = duckdb.connect(str(ROOT / "data" / "ledger.duckdb"), read_only=True)
out, misses = Counter(), []
for t in sys.argv[1:]:
    cik = con.execute("select cik from documents where ticker=? limit 1", [t]).fetchone()[0]
    gaap = json.loads((ROOT / "data" / "raw" / f"{cik:010d}" / "companyfacts.json").read_text())["facts"]["us-gaap"]
    cur = con.execute("select * from extractions where ticker=?", [t])
    for e in [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]:
        facts = [abs(u["val"]) if e["field"] in ("capex", "cost_of_revenue") else u["val"]
                 for c in CONCEPTS.get(e["field"], ()) for u in gaap.get(c, {}).get("units", {}).get("USD", [])
                 if u.get("accn") == e["accession"] and u.get("end") == e["period_end"] and abs(
                     (__import__("datetime").date.fromisoformat(u["end"]) - __import__("datetime").date.fromisoformat(u.get("start", u["end"]))).days
                     - (__import__("datetime").date.fromisoformat(e["period_end"]) - __import__("datetime").date.fromisoformat(e["period_start"])).days) <= 7]
        if not facts:
            out["no XBRL fact for this cell"] += 1
        elif any(abs(f - e["value"]) <= e["scale"] // 2 for f in facts):
            out["matches"] += 1
        else:
            out["differs"] += 1
            misses.append((t, e["field"], e["period_start"], e["period_end"], e["row_label"], e["value"], sorted(set(facts))))
print(dict(out))
for m in misses:
    print("  ", m)
