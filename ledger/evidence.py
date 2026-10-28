"""A second, independent read of each cited cell. The 10-K is rendered in Chrome as a person sees it; the cell is found
by its row label and by the column header above it, by position on the rendered page, not by our table parser. If the
page shows the cited text there, the citation is machine-confirmed; either way the cell is boxed in a screenshot, so a
person who must look sees exactly where."""
import hashlib
import json
import re
from pathlib import Path

DIR = Path(__file__).resolve().parents[1] / "reports" / "evidence"


def load_all() -> dict:
    """Every re-read on record, from every run (a stage or single tickers), newest file winning. Keyed by extraction id;
    a caller trusts an entry only while its cited cell equals the extraction's current cell text."""
    out = {}
    for f in sorted(DIR.glob("*.json"), key=lambda f: f.stat().st_mtime):
        out |= json.loads(f.read_text())
    return out

# Runs in the page. Returns what the rendered page shows at (row, column) and where, or null if the row or column isn't found.
_LOCATE = """([idx, row, col, cited]) => {
  const norm = (s) => (s || "").replace(/\\s+/g, "").toLowerCase();
  const tables = [...document.querySelectorAll("table")];
  const parts = col.split("|").map(norm), want = norm(row), head = parts[parts.length - 1];
  for (const t of [tables[idx], ...tables].filter(Boolean)) {
    const trs = [...t.querySelectorAll("tr")];
    const named = trs.filter((r) => { const c = [...r.cells].find((c) => c.textContent.trim()); return c && norm(c.textContent) === want; });
    if (!named.length) continue;
    // A label can repeat (Oracle lists "Services" under revenues and again under expenses): use the row that shows the cited text, else the first.
    const read = (tr) => {
      const above = trs.slice(0, trs.indexOf(tr)).flatMap((r) => [...r.cells]);
      const heads = above.filter((c) => norm(c.textContent).endsWith(head));
      if (!heads.length) return null;
      let h = null;
      if (heads.length > 1 && parts.length > 1) {  // the same sub-header under every year (Intel: "Amount"): take the one under the cited year
        const cx = (r) => r.left + r.width / 2;
        const tops = above.filter((c) => norm(c.textContent).endsWith(parts[parts.length - 2])).map((c) => cx(c.getBoundingClientRect()));
        if (tops.length) h = heads.map((c) => c.getBoundingClientRect()).sort((a, b) => Math.min(...tops.map((x) => Math.abs(cx(a) - x))) - Math.min(...tops.map((x) => Math.abs(cx(b) - x))))[0];
      }
      h = h || heads[heads.length - 1].getBoundingClientRect();
      const cells = [...tr.cells].slice(1).filter((c) => { const r = c.getBoundingClientRect(); return c.textContent.trim() && r.right > h.left + 1 && r.left < h.right - 1; });
      const near = (c, step) => { for (let n = c && c[step]; n; n = n[step]) if (n.textContent.trim()) return n; };
      const nx = near(cells[cells.length - 1], "nextElementSibling"), pv = near(cells[0], "previousElementSibling");
      if (nx && /^[)]/.test(nx.textContent.trim())) cells.push(nx);  // a closing parenthesis in its own cell, past the header
      if (pv && /^[(]$/.test(pv.textContent.trim())) cells.unshift(pv);
      const abs = (r) => ({ x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height });
      const rows = cells.map((c) => c.getBoundingClientRect()), tr_ = tr.getBoundingClientRect(), tb = t.getBoundingClientRect();
      const cell = cells.length ? { x: Math.min(...rows.map((r) => r.left)) + scrollX, y: tr_.top + scrollY, w: Math.max(...rows.map((r) => r.right)) - Math.min(...rows.map((r) => r.left)), h: tr_.height } : null;
      return { seen: cells.map((c) => c.textContent.trim()).join(""), cell, row: abs(tr_), head: abs(h), table: abs(tb) };
    };
    const found = named.map(read).filter(Boolean);
    if (found.length) return found.find((f) => norm(f.seen).replace(/[$,]/g, "") === norm(cited).replace(/[$,]/g, "")) || found[0];
  }
  return null;
}"""

_BOX = """([boxes]) => boxes.map(([b, css]) => { const d = document.createElement("div");
  Object.assign(d.style, { position: "absolute", left: b.x - 3 + "px", top: b.y - 2 + "px", width: b.w + 6 + "px", height: b.h + 4 + "px",
    pointerEvents: "none", zIndex: 99999, boxSizing: "border-box" }, css); d.className = "ledger-box"; document.body.appendChild(d); })"""


def same(a: str, b: str) -> bool:
    """Same number as printed: ignores $, spaces and thousands separators; keeps digits, parentheses and dashes."""
    n = lambda s: re.sub(r"[\s$,\u200b\ufeff]", "", s).replace("–", "—").replace("-", "—")  # \u200b: a zero-width space some filers put in cells
    return n(a) == n(b)


def read(doc: Path, cites: list[dict], shots: set[str], out_dir: Path) -> dict:
    """cites: extractions of one filing. Returns {extraction_id: {cell, seen, match, img}}; screenshots only for ids in shots."""
    from playwright.sync_api import sync_playwright  # only re-reading needs a browser

    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        page = b.new_page(viewport={"width": 1000, "height": 900}, device_scale_factor=1.5)
        page.goto(doc.resolve().as_uri(), wait_until="load")
        for e in cites:
            r = page.evaluate(_LOCATE, [int(e["table_id"][1:]), e["row_label"], e["column_label"], e["cell_text"]])
            hit = bool(r and r["cell"] and same(r["seen"], e["cell_text"]))
            img = None
            if r and e["extraction_id"] in shots:
                img = f"{hashlib.sha1(e['extraction_id'].encode()).hexdigest()[:12]}.png"
                page.evaluate(_BOX, [[[r["row"], {"background": "rgba(250,204,21,.18)"}], [r["head"], {"border": "2px solid #2563eb"}]]
                                     + ([[r["cell"], {"border": f"3px solid {'#16a34a' if hit else '#dc2626'}"}]] if r["cell"] else [])])
                t = r["table"]  # the table from its top (headers) to the cited row; a long table starts a little above the row
                top = max(0, t["y"] - 6 if r["row"]["y"] - t["y"] < 650 else r["row"]["y"] - 320)
                right = max(t["x"] + t["w"], r["cell"]["x"] + r["cell"]["w"] if r["cell"] else 0) + 10
                page.screenshot(path=out_dir / img, full_page=True,
                                clip={"x": max(0, t["x"] - 8), "y": top, "width": right - max(0, t["x"] - 8), "height": r["row"]["y"] + r["row"]["h"] + 10 - top})
                page.evaluate("document.querySelectorAll('.ledger-box').forEach((d) => d.remove())")
            res[e["extraction_id"]] = {"cell": e["cell_text"], "seen": r and r["seen"], "match": hit, "img": img}
        b.close()
    return res
