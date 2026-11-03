"""Write reports/segment-basis.md: per company with segment facts, each segment and fiscal year, the filing its value
comes from, the newest filing that prints that year for the field, and every other reading. Read-only (the database
and nothing else); the analysis is ledger.checks.ties.segment_basis, the function the segment_basis_mixed rule runs.

    uv run python scripts/segment_basis.py [TICKER ...]     (default: config.PROVEN)
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import duckdb  # noqa: E402

from ledger.checks.ties import load, segment_basis  # noqa: E402
from ledger.core import store  # noqa: E402
from ledger.core.config import MVP_YEARS, PROVEN  # noqa: E402

OUT = ROOT / "reports" / "segment-basis.md"


def newest_by_year(s: dict) -> dict:
    """{period: (filed, form, accession)} of the newest filing with any reading of that year for the field."""
    out = {}
    for r in s["years"]:
        for x in r["readings"]:
            k = (x["filed"] or "", x["form"] or "10-K", x["accession"])
            if k > out.get(r["period"], ("",)):
                out[r["period"]] = k
    return out


def table(s: dict) -> list[str]:
    newest = newest_by_year(s)
    lines = ["| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |", "|---|---|---|---|---|---|---|"]
    for r in s["years"]:
        nf, nform, nacc = newest.get(r["period"], ("", "", ""))
        own = f"{r['form']} {r['filed']}"
        others = "; ".join(f"{x['cell_text']} ({x['form']} {x['filed']})" for x in r["readings"] if x["accession"] != r["accession"]) or "—"
        on_newest = r["accession"] == nacc
        basis = "earlier basis (before cutover)" if r["mixed"] else "newest" if on_newest else f"not in the newest ({nform} {nf})"
        lines.append(f"| {r['dimension']} | {r['period']} | {r['cell_text']} | {own} | {nform} {nf} | {others} | {basis} |")
    return lines


def conclusion(t: str, mine: list[dict]) -> str:
    """One plain line per company: which series mix definitions or vintages, and how each was seen."""
    if not mine:
        return f"- **{t}**: no segment facts."
    parts = []
    for s in mine:
        newest = newest_by_year(s)
        rel = [q for q in s["mixed"] if q in MVP_YEARS]
        if s["cutover"]:
            c = s["cutover"]
            after = sorted({r["period"] for r in s["years"] if not r["mixed"] and r["period"] in MVP_YEARS})
            parts.append(f"{s['field']} mixes definitions: {', '.join(rel) or 'no release year'} on segments from before {c['form']} {c['filed']}, "
                         f"{', '.join(after)} on the restated ones ({c['why']}; seen by `segment_basis_mixed`)" if rel else
                         f"{s['field']}: a cutover at {c['form']} {c['filed']}, every release year on its basis")
        stray = [r for r in s["years"] if not r["mixed"] and r["accession"] != newest.get(r["period"], ("", "", ""))[2] and r["period"] in MVP_YEARS]
        if stray:
            dims = sorted({r["dimension"] for r in stray})
            twins = sorted({f"{a['dimension']} / {b['dimension']} {a['period']} {a['cell_text']}" for a in s["years"] for b in s["years"]
                            if a["period"] == b["period"] and a["dimension"] < b["dimension"] and a["value"] == b["value"]})
            parts.append(f"{s['field']} mixes vintages: {', '.join(dims)} in {', '.join(sorted({r['period'] for r in stray}))} come from a filing older than the newest one "
                         f"printing that year, which does not print them (a segment dropped or renamed; no figure printed two ways, so the rule does not see it)"
                         + (f"; the same figure under two names: {'; '.join(twins)}" if twins else ""))
    return f"- **{t}**: " + ("; ".join(parts) if parts else "every release year of every segment series comes from the newest filing printing it, and no re-segmentation shows in the readings: one basis.")


def main(argv: list[str]) -> int:
    tickers = [t.upper() for t in argv] or list(PROVEN)
    con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    try:
        data = load(con, tickers, [])
    finally:
        con.close()
    series = segment_basis(data["facts"], data["extractions"])
    out = ["# Segment basis by company", "",
           "Written by `scripts/segment_basis.py` from the database (ledger/checks/ties.py `segment_basis`, the analysis the "
           "`segment_basis_mixed` rule runs). For each segment and fiscal year: the value the dataset ships as the filing printed it, the "
           "filing it comes from, the newest filing that prints that year for the field, and every other reading. A re-segmentation is "
           "seen only where a later 10-K prints a segment figure differently (the cutover); a segment dropped or added with no figure "
           "printed two ways is not seen by the rule and is called out in the conclusion. No value is changed.", "",
           f"Release years: {', '.join(MVP_YEARS)}.", "", "## Conclusion", "",
           *[conclusion(t, [s for s in series if s["ticker"] == t]) for t in tickers], ""]
    for t in tickers:
        mine = [s for s in series if s["ticker"] == t]
        out += [f"## {t}", ""]
        if not mine:
            out += ["No segment facts.", ""]
            continue
        for s in mine:
            c = s["cutover"]
            head = f"### {s['field']}"
            cut = (f"Cutover (re-segmentation): {c['form']} {c['filed']} ({c['accession']}) printed {len(c['changes'])} segment figures differently; {c['why']}. "
                   f"Years on an earlier basis: {', '.join(s['mixed']) or 'none'}" + (f" (in release years: {', '.join(q for q in s['mixed'] if q in MVP_YEARS) or 'none'})." if s["mixed"] else ".")) \
                if c else "No re-segmentation seen in the readings."
            if len(s["cutovers"]) > 1:
                cut += " Earlier re-segmentations: " + "; ".join(f"{x['form']} {x['filed']} ({x['why']}) restated " + ", ".join(f"{y['dimension']} {y['period']} {y['before']} → {y['after']}" for y in x["changes"])
                                                         for x in s["cutovers"][:-1]) + "."
            if s["corrections"]:
                cut += " Corrections (figure printed differently in a later filing, same segments, no basis change): " + "; ".join(
                    f"{x['form']} {x['filed']}: " + ", ".join(f"{y['dimension']} {y['period']} {y['before']} → {y['after']}" for y in x["changes"]) for x in s["corrections"]) + "."
            out += [head, "", cut, "", *table(s), ""]
    OUT.write_text("\n".join(out).rstrip() + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
