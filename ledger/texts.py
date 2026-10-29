"""Every text the AI spend reader reads, in one registry (`texts`): where it came from, which fiscal period it speaks
to, and the cached plain text on disk.

  mdna              Item 7 of each 10-K (edgartools), speaks to the fiscal year the 10-K reports
  earnings_release  Exhibit 99.1 of each 8-K with Item 2.02 (EDGAR, edgartools), speaks to the quarter just ended
  transcript        earnings-call transcript PDF from the company's own investor page (sources/ir.yaml)
  cfo_commentary    CFO commentary PDF from the investor page (Nvidia)

Investor pages sit behind a bot check, which code must not get around: a person lists the PDF links in
sources/ir.yaml from their own browser, and the PDFs download directly (pypdf reads them). No paid transcript source."""
from __future__ import annotations

import hashlib
import json
import re
import urllib.request
from datetime import date
from pathlib import Path

import yaml

from . import store
from .ingest.edgar import RAW, _cached, fetch_json, fetch_tickers, user_agent
from .ingest.filings import FIRST_PERIOD, _rows
from .reference.normalize import fiscal_label

TEXT = store.ROOT / "data" / "text"
IR = store.ROOT / "sources" / "ir.yaml"
KINDS = ("mdna", "earnings_release", "transcript", "cfo_commentary")


def _identity():
    from edgar import set_identity
    set_identity(user_agent())


def quarter_ends(ticker: str) -> list[str]:
    """Every 10-Q and 10-K report-period end the company has filed: its quarterly calendar."""
    tmap, _ = fetch_tickers()
    cik = tmap[ticker]["cik"]
    sub, _ = fetch_json("submissions", cik, max_age_h=24 * 7)
    rows = list(_rows(sub["filings"]["recent"]))
    for f in sub["filings"].get("files", []):
        body, _ = _cached(f"https://data.sec.gov/submissions/{f['name']}", RAW / f"{cik:010d}" / f["name"], False, 24 * 30)
        rows += list(_rows(json.loads(body)))
    return sorted({r["reportDate"] for r in rows if r["form"] in ("10-Q", "10-K", "10-KT", "10-Q/A", "10-K/A") and r["reportDate"]})


def _row(ticker, kind, path: Path, text: str, period_end: str, fye: str | None, date_: str, url: str, accession: str | None) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return {"text_id": f"{ticker}|{kind}|{period_end}|{hashlib.sha256(url.encode()).hexdigest()[:8]}", "ticker": ticker, "kind": kind,
            "accession": accession, "url": url, "date": date_, "period_end": period_end, "fiscal_year": fiscal_label(period_end, fye)[0],
            "path": str(path.relative_to(store.ROOT)), "sha256": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text)}


# ── 10-K MD&A ──────────────────────────────────────────────────────────────────────────────────────────────────────
def mdna(docs: list[dict], fye: str | None) -> list[dict]:
    """One text per 10-K document row (accession, ticker, cik, form, period, filed, url)."""
    out = []
    for d in docs:
        p = TEXT / f"{d['cik']:010d}" / f"{d['accession']}.mdna.txt"
        if p.exists():
            text = p.read_text()
        else:
            _identity()
            from edgar import Filing
            k = Filing(cik=d["cik"], company=d["ticker"], form=d["form"], filing_date=d["filed"], accession_no=d["accession"]).obj()
            try:
                text = (k["Item 7"] if k is not None else "") or ""
            except (KeyError, TypeError):
                text = ""
        out.append(_row(d["ticker"], "mdna", p, text, d["period"], fye, d["filed"], d["url"], d["accession"]))
    return out


# ── 8-K earnings releases ──────────────────────────────────────────────────────────────────────────────────────────
def earnings_releases(ticker: str, cik: int, fye: str | None, ends: list[str]) -> list[dict]:
    """Exhibit 99.1 of every 8-K with Item 2.02 since the window began; the period is the latest quarter end before
    the filing date (a release comes three to six weeks after the quarter)."""
    _identity()
    from edgar import Company
    out = []
    for f in Company(cik).get_filings(form="8-K").filter(date=f"{FIRST_PERIOD}:{date.today().isoformat()}"):
        if "2.02" not in (f.items or []):
            continue
        filed = str(f.filing_date)
        period = max((e for e in ends if e < filed), default=None)
        if not period:
            continue
        p = TEXT / f"{cik:010d}" / f"{f.accession_no}.ex99.txt"
        if p.exists():
            text = p.read_text()
        else:
            ex = [a for a in f.attachments if str(a.document_type).upper().startswith("EX-99")]
            text = "\n\n".join(a.text() or "" for a in ex[:2])
        out.append(_row(ticker, "earnings_release", p, text, period, fye, filed, f"https://www.sec.gov/Archives/edgar/data/{cik}/{f.accession_no.replace('-', '')}/", f.accession_no))
    return out


# ── investor-page PDFs ─────────────────────────────────────────────────────────────────────────────────────────────
def ir_config() -> dict:
    return yaml.safe_load(IR.read_text()) if IR.exists() else {}


QUARTER = re.compile(r"\b(?:Q([1-4])[\s\-_]*(?:FY)?\s*(\d{2,4})|(first|second|third|fourth) quarter[\s\-_]*(?:fiscal )?(?:year )?(\d{4})|(\d{4})[\s\-_]*Q([1-4]))", re.I)
WORDS = {"first": 1, "second": 2, "third": 3, "fourth": 4}


def _quarter(label: str) -> tuple[int, int] | None:
    """(fiscal year, quarter) from a link text or file name: 'Q3-2026', 'Second Quarter 2027', '2026-Q1', 'Q2FY27'."""
    m = QUARTER.search(label)
    if not m:
        return None
    if m.group(1):
        q, y = int(m.group(1)), int(m.group(2))
    elif m.group(3):
        q, y = WORDS[m.group(3).lower()], int(m.group(4))
    else:
        q, y = int(m.group(6)), int(m.group(5))
    return (2000 + y if y < 100 else y), q


def _pdf_text(url: str, path: Path) -> str:
    if path.exists():
        return path.read_text()
    from io import BytesIO
    from pypdf import PdfReader
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (capex-ledger; " + user_agent() + ")"})
    with urllib.request.urlopen(req, timeout=120) as r:
        body = r.read()
    text = "\n\n".join((pg.extract_text() or "") for pg in PdfReader(BytesIO(body)).pages)
    return text


def ir_texts(ticker: str, fye: str | None, ends: list[str]) -> list[dict]:
    """Transcripts and CFO commentary from the links a person listed for the company in sources/ir.yaml. The period is
    the quarter the file name or link names, mapped onto the company's own quarter calendar."""
    cfg = ir_config().get(ticker)
    if not cfg:
        return []
    out, seen = [], set()
    for kind, links in cfg.items():
        for href in links:
            fq = _quarter(href.rsplit("/", 1)[-1]) or _quarter(href)
            if not fq or href in seen:
                print(f"  {ticker}: no quarter in {href}")
                continue
            seen.add(href)
            fy, q = fq
            year_ends = [e for e in ends if fiscal_label(e, fye)[0] == fy]
            if len(year_ends) < q:
                continue  # the quarter isn't on the calendar yet (or the link names a year we don't track)
            period = sorted(year_ends)[q - 1]
            if period < FIRST_PERIOD:
                continue
            name = re.sub(r"[^A-Za-z0-9._-]", "_", href.rsplit("/", 1)[-1])
            p = TEXT / "ir" / ticker / (name[:-4] + ".txt")
            try:
                text = _pdf_text(href, p)
            except Exception as e:  # one bad PDF must not stop the company
                print(f"  {ticker}: could not read {href}: {e}")
                continue
            out.append(_row(ticker, kind, p, text, period, fye, period, href, None))
    return out
