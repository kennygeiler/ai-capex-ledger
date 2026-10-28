"""Compare an agent run with the reference run: schema and citation validity, and identical values and citations.
Used for repeatability (T48) and the no-locator test. Run: uv run python scripts/compare_outputs.py data/extract/find"""
import json
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ledger.extract import Invalid, resolve, validate_output  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
run, base = Path(sys.argv[1]), ROOT / "data" / "extract" / "outputs"
paths = dict(duckdb.connect(str(ROOT / "data" / "ledger.duckdb"), read_only=True).execute("select accession, tables_path from documents").fetchall())
key = lambda v: (v["field"], v["period_end"], v["months"])
fields = ("table_id", "row_label", "column_label", "cell_text", "value")
same = diff = bad = 0
for f in sorted(run.glob("*.json")):
    acc, obj = f.stem, json.loads(f.read_text())
    doc = json.loads((ROOT / paths[acc]).read_text())
    try:
        validate_output(obj, acc)
    except Invalid as e:
        print(f"{acc}: invalid output: {e.reason}"); bad += 1; continue
    for v in obj["values"]:
        try:
            resolve(v, doc)
        except Invalid as e:
            print(f"{acc}: citation fails: {e.reason}"); bad += 1
    a = {key(v): v for v in json.loads((base / f.name).read_text())["values"]}
    for k, v in {key(v): v for v in obj["values"]}.items():
        if k in a and all(a[k][x] == v[x] for x in fields):
            same += 1
        else:
            diff += 1; print(f"{acc}: differs {k}: {[(x, a.get(k, {}).get(x), v[x]) for x in fields if a.get(k, {}).get(x) != v[x]]}")
    print(f"{acc}: statements cited {sorted({v['table_id'] for v in obj['values']})} vs located {doc['located']['income'] + doc['located']['cash_flow']}")
print(f"identical {same}, different {diff}, invalid {bad}")
