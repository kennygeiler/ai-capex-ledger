"""Open in filing (in-app): /filing/<accession>?t=<table>&row=<label>&col=<header>&cell=<text> serves the STORED 10-K
(data/raw, fingerprinted in documents.sha256) with one script added: the same locator as the crops and the re-read
(ledger/evidence.py _LOCATE) finds the cell by row label and column header, scrolls to it, outlines it in red and its
row lightly, and a fixed banner says what it found. The script reads its parameters from the page's own URL, so
nothing a visitor types is written into the HTML. Only accessions in the documents table are served; the file must
sit under data/raw and match its fingerprint."""
from __future__ import annotations

import hashlib
import re
import secrets
from pathlib import Path

from . import store
from .crops import doc_path
from .evidence import _LOCATE, _SAME

ACCESSION = re.compile(r"\d{10}-\d{2}-\d{6}")
LOCATED = "Cell located"
NOT_LOCATED = "Cell not located on this page"
# Every answer from /filing/ carries a policy, the refusals too: a sandboxed page, nothing loaded, nothing framed.
ERROR_CSP = "default-src 'none'; sandbox; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"

_SCRIPT = """
(() => {
  const LOCATE = %s;
  const SAME = %s;
  const show = () => {
    const q = new URLSearchParams(location.search), row = q.get("row") || "", col = q.get("col") || "", cell = q.get("cell") || "";
    const idx = parseInt((q.get("t") || "").slice(1), 10);
    if (!row && !cell) return;  // the whole filing, no cell asked for: nothing to locate, no banner
    const bar = document.createElement("div");
    Object.assign(bar.style, { position: "fixed", top: "0", left: "0", right: "0", zIndex: 2147483647, padding: "8px 14px",
      font: "13px/1.4 -apple-system, system-ui, sans-serif", color: "#fff", background: "#1f2937", boxShadow: "0 1px 4px rgba(0,0,0,.25)" });
    bar.id = "ledger-banner";
    let r = null;
    try { r = row && col ? LOCATE([Number.isNaN(idx) ? -1 : idx, row, col, cell]) : null; } catch (e) { r = null; }
    const hit = !!(r && r.cell && SAME(r.seen, cell));
    if (hit) {
      bar.textContent = %s + ": " + row + " · " + col.split("|").map((s) => s.trim()).join(" ") + " · " + cell;
      bar.dataset.state = "located";
      document.querySelectorAll("[data-ledger=cell]").forEach((c) => { c.style.outline = "3px solid #dc2626"; c.style.outlineOffset = "1px"; });
      const tr = document.querySelector("tr[data-ledger=row]");
      if (tr) { tr.style.outline = "1px solid rgba(220,38,38,.45)"; tr.style.background = "rgba(250,204,21,.18)"; tr.scrollIntoView({ block: "center" }); }
    } else {
      bar.textContent = %s + (r && r.ambiguous ? " · Column ambiguous" : r && r.cell ? " · Page shows " + r.seen + " · cited " + cell : "");
      bar.dataset.state = "not_located";
      bar.style.background = "#7f1d1d";
    }
    document.body.appendChild(bar);
    document.body.style.paddingTop = "40px";
  };
  if (document.readyState === "complete") show(); else window.addEventListener("load", show);
})();
"""


def script() -> str:
    import json
    # ASCII only (\u escapes): a filing declares its own charset, often none, and must not garble the script's dashes and dots
    return (_SCRIPT % (_LOCATE, _SAME, json.dumps(LOCATED), json.dumps(NOT_LOCATED))).encode("ascii", "backslashreplace").decode()


class Refused(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code = code


def filing(con, accession: str, root: Path | None = None) -> tuple[bytes, str]:
    """(html, csp) for a stored filing, or Refused(404 unknown or malformed, 409 the stored copy differs, 410 missing)."""
    if not ACCESSION.fullmatch(accession or ""):
        raise Refused(404, "not a filing")
    row = con.execute("select cik, sha256 from documents where accession = ?", [accession]).fetchone()
    if not row:
        raise Refused(404, "no stored filing with that accession")
    root = root or store.ROOT
    f = doc_path(row[0], accession, root)
    base = (root / "data" / "raw").resolve()
    if not f.resolve().is_relative_to(base) or not f.is_file():
        raise Refused(410, "the stored copy of this filing is missing")
    body = f.read_bytes()
    if hashlib.sha256(body).hexdigest() != row[1]:
        raise Refused(409, "the stored copy of this filing differs from its fingerprint")
    nonce = secrets.token_urlsafe(16)
    tag = f'<script nonce="{nonce}">{script()}</script>'.encode()
    low = body.lower()
    at = low.rfind(b"</body>")
    html = body[:at] + tag + body[at:] if at >= 0 else body + tag
    # The filing is the filer's HTML: sandboxed (an opaque origin, so it can reach none of this app's routes as itself),
    # only our nonce script runs, nothing loads or posts anywhere.
    csp = (f"sandbox allow-scripts; default-src 'none'; script-src 'nonce-{nonce}'; style-src 'unsafe-inline'; img-src 'self' data:; "
           "font-src data:; base-uri 'none'; form-action 'none'; connect-src 'none'; frame-ancestors 'self'")
    return html, csp
