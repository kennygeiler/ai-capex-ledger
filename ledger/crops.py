"""A picture of every cited cell, statements and notes: the stored 10-K rendered in Chrome, the cell found by the same
in-page locator as the re-read (ledger/evidence.py _LOCATE, by row label and column header), then a crop of its table:
the column header rows, the cited row with about two rows above and below (rows in between are folded into one line
that says how many), full table width, the cited cell boxed in red.

Recorded in reports/evidence/crops.json, keyed by extraction id: {img, img_sha256, accession, document_sha256,
table_id, row_label, column_label, cell_text, seen, match, located, reason, hidden, at, code}. A crop is evidence only
while it is current (`state`): the stored filing on disk still hashes to its fingerprint, the citation (table, row,
column, cited text) and the crop code are what they were, and the picture is the one written. A cell the locator
cannot find, finds under more than one column, or finds showing other text, is recorded located false with the reason
and no picture: never a crop of the wrong place. The PNGs are not in git; `ledger evidence --crops` regenerates them."""
from __future__ import annotations

import fcntl
import hashlib
import inspect
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

from . import store
from . import evidence
from .evidence import _BOX, _LOCATE, _SAME, CROPS_FILE, offline, runs_together, same
from .safewrite import locked, replace_text

DIR = store.ROOT / "reports" / "evidence"
CROPS = DIR / "crops"
RECORD = DIR / CROPS_FILE
ABOVE = BELOW = 2  # neighbours of the cited row in the crop
VIEWPORT, SCALE = {"width": 800, "height": 900}, 2  # a narrow page: filings stretch tables to the page width, so the crop stays legible side by side

# Runs in the page after _LOCATE marked what it read (data-ledger table/row/head/cell). Folds the rows between the
# header and the neighbours into one line, and returns the crop box and the cell box measured after the fold.
_FRAME = """([above, below]) => {
  const t = document.querySelector("table[data-ledger=table]"), tr = document.querySelector("tr[data-ledger=row]"), hc = document.querySelector("[data-ledger=head]");
  if (!t || !tr || !hc) return null;
  const all = [...t.querySelectorAll("tr")];
  const rows = all.filter((r) => r.textContent.trim() && r.getBoundingClientRect().height > 0);
  const i = rows.indexOf(tr), hr = rows.indexOf(hc.closest("tr"));
  if (i < 0 || hr < 0 || hr > i) return null;
  const top = Math.max(0, hr - 1), lo = Math.max(hr + 1, i - above), hi = Math.min(rows.length - 1, i + below);
  const gap = all.slice(all.indexOf(rows[hr]) + 1, all.indexOf(rows[lo])).filter((r) => !r.hasAttribute("data-ledger-fold"));
  const shown = gap.filter((r) => rows.includes(r)).length;
  if (shown) {  // nothing is folded unless a row with text sits in the gap; then the whole gap goes, and the fold line counts the rows with text
    gap.forEach((r) => { r.dataset.ledgerHid = r.style.display || "-"; r.style.display = "none"; });
    const f = document.createElement("tr"); f.setAttribute("data-ledger-fold", "");
    const td = document.createElement("td"); td.colSpan = 99; td.textContent = "… " + shown + " row" + (shown > 1 ? "s" : "") + " not shown";
    Object.assign(td.style, { font: "11px system-ui, sans-serif", color: "#64748b", padding: "3px 4px" }); f.appendChild(td);
    rows[lo].before(f);
  }
  const abs = (r) => ({ x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height });
  const cs = [...t.querySelectorAll("[data-ledger=cell]")].map((c) => c.getBoundingClientRect());
  const tb = t.getBoundingClientRect(), r0 = rows[top].getBoundingClientRect(), r1 = rows[hi].getBoundingClientRect(), row = tr.getBoundingClientRect();
  if (!cs.length || r1.bottom <= r0.top) return null;
  const cell = { x: Math.min(...cs.map((r) => r.left)) + scrollX, y: row.top + scrollY, w: Math.max(...cs.map((r) => r.right)) - Math.min(...cs.map((r) => r.left)), h: row.height };
  const right = Math.max(tb.right, cell.x - scrollX + cell.w);
  return { cell, row: abs(row), head: abs(hc.getBoundingClientRect()), hidden: shown,
           clip: { x: Math.max(0, tb.left + scrollX - 8), y: Math.max(0, r0.top + scrollY - 6), w: right - Math.max(0, tb.left - 8) + 8, h: r1.bottom - r0.top + 8 } };
}"""

_RESTORE = """() => {
  document.querySelectorAll(".ledger-box, [data-ledger-fold]").forEach((d) => d.remove());
  document.querySelectorAll("[data-ledger-hid]").forEach((r) => { r.style.display = r.dataset.ledgerHid === "-" ? "" : r.dataset.ledgerHid; delete r.dataset.ledgerHid; });
  document.querySelectorAll("[data-ledger]").forEach((e) => e.removeAttribute("data-ledger"));
}"""

def code_inputs() -> list[str]:
    """What a crop depends on besides the filing and the citation: the locator, the framing, the boxes, the rule that
    compares cell text (the page's copy and Python's), the page size and the neighbours."""
    return [_LOCATE, _FRAME, _BOX, _SAME, inspect.getsource(evidence._n), inspect.getsource(same), json.dumps([VIEWPORT, SCALE, ABOVE, BELOW])]


CODE = "crops@2:" + hashlib.sha1("\n".join(code_inputs()).encode()).hexdigest()[:8]  # any change to those makes old crops stale

SEC = "https://www.sec.gov/"


def img_name(extraction_id: str) -> str:
    return f"{hashlib.sha256(extraction_id.encode()).hexdigest()[:16]}.png"


_HASHES: dict = {}


def sha256(path: Path) -> str | None:
    """The file's sha256, or None when it is not there; cached by (path, size, mtime) so a page read stays cheap."""
    try:
        st = path.stat()
    except OSError:
        return None
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key not in _HASHES:
        _HASHES[key] = hashlib.sha256(path.read_bytes()).hexdigest()
    return _HASHES[key]


def doc_path(cik: int, accession: str, root: Path | None = None) -> Path:
    return (root or store.ROOT) / "data" / "raw" / f"{int(cik):010d}" / "docs" / f"{accession}.htm"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _entry(e: dict, doc_sha: str, at: str, **kw) -> dict:
    base = {"img": None, "img_sha256": None, "accession": e["accession"], "document_sha256": doc_sha, "table_id": e["table_id"],
            "row_label": e["row_label"], "column_label": e["column_label"], "cell_text": e["cell_text"], "seen": None, "match": False,
            "located": False, "reason": None, "hidden": 0, "at": at, "code": CODE}
    return base | kw


def _png(page, dest: Path, clip: dict) -> str:
    """Screenshot to a temporary file beside dest, moved into place: a reader never sees half a picture. Returns its sha256."""
    fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.", suffix=".tmp")
    os.close(fd)
    try:
        page.screenshot(path=tmp, type="png", full_page=True, clip=clip)
        digest = hashlib.sha256(Path(tmp).read_bytes()).hexdigest()
        os.replace(tmp, dest)
        return digest
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def crop_doc(doc: Path, doc_sha: str, cites: list[dict], out_dir: Path, page=None, at: str | None = None) -> dict:
    """cites: extractions of one filing (extraction_id, table_id, row_label, column_label, cell_text, accession).
    doc_sha: the fingerprint on record (documents.sha256); at: the run's start, stamped on every entry. Returns
    {extraction_id: entry}; PNGs land in out_dir."""
    at = at or _now()
    if not doc.is_file():
        return {e["extraction_id"]: _entry(e, doc_sha, at, reason="Stored filing missing") for e in cites}
    if sha256(doc) != doc_sha:
        return {e["extraction_id"]: _entry(e, doc_sha, at, reason="Stored filing differs from fingerprint") for e in cites}
    if page is None:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            try:
                pg = b.new_page(viewport=VIEWPORT, device_scale_factor=SCALE)
                offline(pg)
                return crop_doc(doc, doc_sha, cites, out_dir, pg, at)
            finally:
                b.close()
    out_dir.mkdir(parents=True, exist_ok=True)
    page.goto(doc.resolve().as_uri(), wait_until="load")
    res = {}
    for e in cites:
        r = page.evaluate(_LOCATE, [int(e["table_id"][1:]) if e["table_id"][1:].isdigit() else -1, e["row_label"], e["column_label"], e["cell_text"]])
        k, cited = e["extraction_id"], e["cell_text"]
        try:
            if not r:
                res[k] = _entry(e, doc_sha, at, reason="Row or column not on page")
            elif r.get("ambiguous"):
                res[k] = _entry(e, doc_sha, at, reason="Column ambiguous")
            elif not r["cell"]:
                res[k] = _entry(e, doc_sha, at, seen="", reason="No value in column")
            elif not same(r["seen"], cited):
                lead = "Values run together · " if runs_together(r["seen"], cited) else ""
                res[k] = _entry(e, doc_sha, at, seen=r["seen"], reason=f"{lead}Page shows {r['seen']} · cited {cited}")
            elif not (f := page.evaluate(_FRAME, [ABOVE, BELOW])):
                res[k] = _entry(e, doc_sha, at, seen=r["seen"], match=True, reason="Table not framed")
            else:
                page.evaluate(_BOX, [[[f["row"], {"background": "rgba(250,204,21,.18)"}], [f["head"], {"border": "2px solid #2563eb"}],
                                      [f["cell"], {"border": "3px solid #dc2626"}]]])
                img, c = img_name(k), f["clip"]
                digest = _png(page, out_dir / img, {"x": c["x"], "y": c["y"], "width": c["w"], "height": c["h"]})
                res[k] = _entry(e, doc_sha, at, img=img, img_sha256=digest, seen=r["seen"], match=True, located=True, hidden=f["hidden"])
        finally:
            page.evaluate(_RESTORE)
    return res


# ── the record ──────────────────────────────────────────────────────────────────────────────────────────────────
def load(path: Path | None = None) -> dict:
    path = path or RECORD
    return json.loads(path.read_text()) if path.is_file() else {}


def merge(new: dict, path: Path | None = None) -> dict:
    """Write new entries into the record under its lock, re-reading what is on disk: an entry from a run that started
    earlier (its `at`) never replaces one from a run that started later. Returns the record as written."""
    path = path or RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    with locked(path.with_name(f".{path.name}.lock")):
        cur = load(path)
        for k, v in new.items():
            if k not in cur or v["at"] >= cur[k]["at"]:
                cur[k] = v
        replace_text(path, json.dumps(cur, indent=1, sort_keys=True))
    return cur


CITATION = ("table_id", "row_label", "column_label", "cell_text")


def state(entry: dict | None, cite: dict, doc_sha: str | None, doc_file: Path | None, img_dir: Path | None = None) -> dict:
    """{state, reason}, computed on every read, never stored. cite: the extraction now (table_id, row_label,
    column_label, cell_text); doc_sha: documents.sha256; doc_file: the stored filing, hashed here as the viewer does.
    none: no crop on record. stale: the stored filing no longer hashes to its fingerprint, the fingerprint, the citation
    or the crop code changed since. not_located: the locator did not find the cited text there. missing: the picture is
    gone or is not the one written. located: current."""
    if not entry:
        return {"state": "none", "reason": "No crop"}
    on_disk = sha256(doc_file) if doc_file is not None else None
    why = [w for w, bad in (("Stored filing missing", on_disk is None), ("Stored filing changed", on_disk is not None and on_disk != doc_sha),
                            ("Filing fingerprint changed", entry.get("document_sha256") != doc_sha),
                            ("Citation changed", any(entry.get(f) != cite.get(f) for f in CITATION)),
                            ("Crop code changed", entry.get("code") != CODE)) if bad]
    if why:
        return {"state": "stale", "reason": " · ".join(why)}
    if not entry.get("located"):
        return {"state": "not_located", "reason": entry.get("reason") or "Not located"}
    f = (img_dir or CROPS) / entry["img"] if entry.get("img") else None
    if f is None or not f.is_file():
        return {"state": "missing", "reason": "Crop file missing"}
    if sha256(f) != entry.get("img_sha256"):
        return {"state": "missing", "reason": "Crop file changed"}
    return {"state": "located", "reason": None}


def located_images(record: dict | None = None, img_dir: Path | None = None) -> set[str]:
    """The picture names the app may serve: those of located entries whose file is the one written."""
    out = set()
    for v in (load() if record is None else record).values():
        if v.get("located") and v.get("img"):
            f = (img_dir or CROPS) / v["img"]
            if f.is_file() and sha256(f) == v.get("img_sha256"):
                out.add(v["img"])
    return out


# ── what the pages read ─────────────────────────────────────────────────────────────────────────────────────────
_STATEMENT = """select e.extraction_id, e.accession, e.ticker, e.field, null as dimension, e.period_start, e.period_end, null as months,
  e.value, e.scale, e.table_id, e.row_label, e.column_label, e.cell_text, 'statement' as kind from extractions e"""
_NOTE = """select n.extraction_id, n.accession, n.ticker, n.field, n.dimension, null as period_start, n.period_end, n.months,
  n.value, n.scale, n.table_id, n.row_label, n.column_label, n.cell_text, 'note' as kind from note_extractions n"""


def _rows(con, sql, params):
    cur = con.execute(sql, params)
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def cites(con, tickers: list[str]) -> list[dict]:
    """Every cited cell of these companies, statements and notes, with its filing's cik and fingerprint."""
    return _rows(con, f"""select x.*, d.cik, d.sha256 as document_sha256 from ({_STATEMENT} union all {_NOTE}) x join documents d using(accession)
                          where x.ticker in (select unnest(?)) order by x.accession, x.extraction_id""", [tickers])


def viewer_url(e: dict) -> str:
    return f"/filing/{e['accession']}?" + urlencode({"t": e["table_id"], "row": e["row_label"], "col": e["column_label"], "cell": e["cell_text"]})


def _sec(url) -> str | None:
    return url if isinstance(url, str) and url.startswith(SEC) else None


def cells(con, ids: list[str], record: dict | None = None, img_dir: Path | None = None, root: Path | None = None) -> dict:
    """{extraction_id: the cited cell as every page shows it}: the reading, its filing, the crop's state and reason
    (`state`, the one function that decides it), the crop's url only while located, the in-app viewer's url, and the
    sec.gov address only when it is on www.sec.gov. The trail, the gold set, Reconcile and /api/v1/evidence all read
    this, so a cell never shows two states. An id with no extraction on file is left out."""
    ids = [i for i in dict.fromkeys(ids or []) if i]
    have = {r[0] for r in con.execute("select table_name from information_schema.tables").fetchall()}
    if not ids or not {"extractions", "note_extractions", "documents"} <= have:  # a database without the cited cells: nothing to show, never a guess
        return {}
    rows = _rows(con, f"""select x.*, d.cik, d.sha256 as document_sha256, d.filed, d.form, d.period as fiscal_period, d.url as sec_url
                          from ({_STATEMENT} union all {_NOTE}) x join documents d using(accession) where x.extraction_id in (select unnest(?))""", [ids])
    rec = load() if record is None else record
    out = {}
    for e in rows:
        entry = rec.get(e["extraction_id"])
        st = state(entry, e, e["document_sha256"], doc_path(e["cik"], e["accession"], root), img_dir)
        out[e["extraction_id"]] = {
            **{k: e[k] for k in ("extraction_id", "kind", "ticker", "field", "dimension", "period_start", "period_end", "months", "value", "scale",
                                 "table_id", "row_label", "column_label", "cell_text", "accession", "form", "fiscal_period")},
            "filed": str(e["filed"] or "")[:10] or None, "sec_url": _sec(e["sec_url"]), **st,
            "crop": entry and {"url": f"/evidence/crops/{entry['img']}" if st["state"] == "located" else None, "seen": entry.get("seen"),
                               "at": entry.get("at"), "code": entry.get("code"), "hidden": entry.get("hidden", 0)},
            "viewer": viewer_url(e)}
    return out


def brief(e: dict | None) -> dict:
    """A cited cell (`cells`) as a page row shows it: state, reason, the crop url only while located, the in-app viewer,
    sec.gov, the filing. No extraction on file is the state `none`, the same word everywhere."""
    if not e:
        return {"state": "none", "reason": "No crop", "url": None, "viewer": None, "sec_url": None, "filed": None, "form": None}
    return {"state": e["state"], "reason": e["reason"], "url": (e.get("crop") or {}).get("url"), "viewer": e["viewer"], "sec_url": e["sec_url"],
            "filed": e["filed"], "form": e["form"]}


def view(con, extraction_id: str, record: dict | None = None, img_dir: Path | None = None, root: Path | None = None) -> dict | None:
    """/api/v1/evidence/<extraction_id>: one cited cell (`cells`)."""
    return cells(con, [extraction_id], record, img_dir, root).get(extraction_id)


class Busy(RuntimeError):
    """Another crop run holds the run lock."""


def run(con, tickers: list[str], out_dir: Path | None = None, record: Path | None = None, log=print) -> dict:
    """Crop every cited cell of these companies, one browser, one filing at a time. One run at a time (a lock beside
    the record); every entry carries the run's start; the record is merged after each filing, so a run stopped
    half-way keeps what it did."""
    from playwright.sync_api import sync_playwright
    out_dir, record = out_dir or CROPS, record or RECORD
    record.parent.mkdir(parents=True, exist_ok=True)
    lock = open(record.with_name(f".{record.name}.run.lock"), "a")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        raise Busy("another crop run is in progress") from None
    try:
        at = _now()
        by_doc: dict = {}
        for e in cites(con, tickers):
            by_doc.setdefault((e["cik"], e["accession"], e["document_sha256"]), []).append(e)
        names: dict = {}
        for es in by_doc.values():
            for e in es:
                n = img_name(e["extraction_id"])
                if names.setdefault(n, e["extraction_id"]) != e["extraction_id"]:
                    raise ValueError(f"two cells would share one crop file: {names[n]} and {e['extraction_id']}")
        res = {}
        with sync_playwright() as p:
            b = p.chromium.launch(channel="chrome")
            page = b.new_page(viewport=VIEWPORT, device_scale_factor=SCALE)
            blocked = offline(page)
            try:
                for (cik, accn, sha), es in sorted(by_doc.items()):
                    r = crop_doc(doc_path(cik, accn), sha, es, out_dir, page, at)
                    merge(r, record)
                    res |= r
                    log(f"  {accn}: {sum(v['located'] for v in r.values())} of {len(r)} located")
            finally:
                b.close()
        if blocked:
            log(f"  {len(blocked)} network requests blocked while rendering")
        return res
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)
        lock.close()
