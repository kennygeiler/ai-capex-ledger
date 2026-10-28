"""Cut the located statement tables (plus 1,500 characters of the text above each) out of real filings into
tests/fixtures/filings/, so parser tests run without the git-ignored raw cache. Run once; the output is committed."""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from ledger.ingest.filings import list_filings  # noqa: E402
from ledger.ingest.statements import locate  # noqa: E402
from ledger.ingest.tables import parse_tables  # noqa: E402

PICKS = [("NVDA", "2026-07-26"), ("ORCL", "2026-05-31"), ("IREN", "2026-06-30")]
OUT = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "filings"


def top_level_tables(html: str) -> list[tuple[int, int]]:
    """(start, end) of each top-level <table>…</table>, in document order (the parser's table index order)."""
    spans, depth, start = [], 0, 0
    for m in re.finditer(r"<(/?)table\b[^>]*>", html, re.I):
        if not m.group(1):
            if depth == 0:
                start = m.start()
            depth += 1
        elif depth:
            depth -= 1
            if depth == 0:
                spans.append((start, m.end()))
    return spans


for tk, period in PICKS:
    f = next(f for f in list_filings([tk]) if f.period == period)
    html = f.path.read_text(errors="replace")
    tables, spans = parse_tables(html), top_level_tables(html)
    loc = locate(tables)
    parts = []
    for kind in ("income", "cash_flow"):
        for tid in loc[kind]:
            # Parser IDs count every top-level table (empty ones too), so the number in the ID is the index into spans.
            s, e = spans[int(tid[1:])]
            parts.append(f"<!-- {kind} {tid} -->\n<div>{re.sub(r'<[^>]+>', ' ', html[max(0, s - 1500):s])}</div>\n{html[s:e]}")
    out = OUT / f"{tk}_{f.form}_{period}.html"
    out.write_text(f"<!-- {f.url} -->\n" + "\n".join(parts))
    print(out.name, round(out.stat().st_size / 1024), "KB", loc["income"], loc["cash_flow"])
