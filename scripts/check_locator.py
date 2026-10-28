"""T13 acceptance check: does each located income statement contain the reference revenue for its period?

Match tolerance is the coarser rounding of the two sources (a later 10-Q may restate a comparative in millions),
and a restated reference also matches on its original value. Run: uv run python scripts/check_locator.py
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ledger.ingest.filings import list_filings  # noqa: E402
from ledger.ingest.statements import assemble, locate  # noqa: E402
from ledger.ingest.tables import document_units, parse_tables  # noqa: E402


def rounding(v: float) -> float:
    return 1e6 if v % 1e6 == 0 else 1e3 if v % 1e3 == 0 else 1


def main() -> int:
    ref = defaultdict(list)
    for r in csv.DictReader(open("data/clean/facts.csv")):
        if r["metric"] == "revenue":
            ref[(r["ticker"], r["period_end"])] += [float(r["value"])] + ([float(r["original_value"])] if r["original_value"] else [])
    fs, misses, sources = list_filings(), [], defaultdict(int)
    for f in fs:
        doc = f.path.read_bytes()
        ts = parse_tables(doc)
        tabs = assemble(ts, locate(ts)["income"], document_units(doc))
        for t in tabs:
            sources[t["unit_source"]] += 1
        scale = tabs[0]["scale"]
        cells = [c["value"] for t in tabs for r in t["rows"] for c in r["cells"]]
        if not any(abs(c * scale - v) <= max(scale, rounding(v)) / 2 for v in ref[(f.ticker, f.period)] for c in cells):
            misses.append((f.ticker, f.form, f.period, tabs[0]["id"], scale))
    ok = len(fs) - len(misses)
    print(f"income statement correctly located: {ok}/{len(fs)} = {100 * ok / len(fs):.1f}%   unit source: {dict(sources)}")
    for m in misses:
        print("  MISS", m)
    return 0 if ok / len(fs) >= 0.95 else 1


if __name__ == "__main__":
    sys.exit(main())
