"""The 10-K list for each company and the primary documents behind it.

For each company, every 10-K whose fiscal year ends between FIRST_PERIOD and today. A 10-K shows two or three fiscal
years (smaller filers show two), so reaching back to the FY2022 10-K covers every year in the window; later 10-Ks
restate earlier years where the company did, and the newest wins.
"""
import hashlib
import json
import re
from datetime import date
from dataclasses import asdict, dataclass

from ..config import PREDECESSORS, stage_tickers
from .edgar import RAW, _cached, fetch_json, fetch_tickers

FIRST_PERIOD = "2022-01-01"
LAST_PERIOD = date.today().isoformat()
FORMS = ("10-K", "10-K/A")  # annual filings only; an amendment counts when it carries the financial statements


@dataclass(frozen=True)
class Filing:
    ticker: str
    cik: int
    accession: str
    form: str
    period: str
    filed: str
    primary_document: str

    @property
    def url(self) -> str:
        return f"https://www.sec.gov/Archives/edgar/data/{self.cik}/{self.accession.replace('-', '')}/{self.primary_document}"

    @property
    def path(self):
        return RAW / f"{self.cik:010d}" / "docs" / f"{self.accession}.htm"


def _rows(block: dict):
    n = len(block["accessionNumber"])
    for i in range(n):
        yield {k: block[k][i] for k in ("accessionNumber", "form", "reportDate", "filingDate", "primaryDocument")}


def _all_rows(sub: dict, cik: int, refresh: bool):
    """Recent filings, plus the older pages SEC splits out when a company files a lot (Form 4s push 10-Qs out)."""
    yield from _rows(sub["filings"]["recent"])
    for f in sub["filings"].get("files", []):
        if f.get("filingTo", "9999") < FIRST_PERIOD:
            continue
        body, _ = _cached(f"https://data.sec.gov/submissions/{f['name']}", RAW / f"{cik:010d}" / f["name"], refresh, 24 * 30)
        yield from _rows(json.loads(body))


def list_filings(tickers: list[str] | None = None, refresh: bool = False) -> list[Filing]:
    tmap, _ = fetch_tickers()
    out = []
    for t in tickers or stage_tickers(3):
        seen = set()
        # A company that reorganized under a new CIK (ExxonMobil, 2026) keeps its history under the old one.
        for cik in [tmap[t]["cik"]] + [p["cik"] for p in PREDECESSORS.get(t, [])]:
            sub, _ = fetch_json("submissions", cik, refresh=refresh, max_age_h=24 * 7)
            for r in _all_rows(sub, cik, refresh):
                if r["form"] in FORMS and FIRST_PERIOD <= r["reportDate"] <= LAST_PERIOD and r["accessionNumber"] not in seen:
                    seen.add(r["accessionNumber"])
                    out.append(Filing(t, cik, r["accessionNumber"], r["form"], r["reportDate"], r["filingDate"], r["primaryDocument"]))
    return sorted(out, key=lambda f: (f.ticker, f.period, f.accession))


def fetch_documents(filings: list[Filing], refresh: bool = False) -> list[dict]:
    """Download each primary document once (cached for a year: a filed document never changes)."""
    manifest = []
    for f in filings:
        _, meta = _cached(f.url, f.path, refresh, 24 * 365)
        manifest.append(asdict(f) | {"url": f.url, "bytes": meta["bytes"], "sha256": meta.get("sha256"), "cache": meta["cache"]})
    return manifest


def with_statements(f: Filing, located: dict, locate) -> Filing | None:
    """Some filers (IBM) keep the financial statements in an exhibit, the annual report to stockholders, so the primary
    document has no statements. Try the filing's other HTML documents, largest first; the first that locates what the
    primary lacks replaces it (same cached path, so every later step reads the right document)."""
    if located["income"] and located["cash_flow"]:
        return None
    base = f"https://www.sec.gov/Archives/edgar/data/{f.cik}/{f.accession.replace('-', '')}"
    body, _ = _cached(f"{base}/index.json", RAW / f"{f.cik:010d}" / f"{f.accession}.index.json", False, 24 * 365)
    items = [i for i in json.loads(body)["directory"]["item"]
             if i["name"].endswith((".htm", ".html")) and i["name"] != f.primary_document and not re.fullmatch(r"R\d+\.htm", i["name"])]
    for i in sorted(items, key=lambda i: -int(i.get("size") or 0))[:3]:
        alt = Filing(f.ticker, f.cik, f.accession, f.form, f.period, f.filed, i["name"])
        tmp = RAW / f"{f.cik:010d}" / "docs" / f"{f.accession}.{i['name']}"
        doc, _ = _cached(alt.url, tmp, False, 24 * 365)
        from .tables import parse_tables  # here, not at module top: tables imports nothing from this module, but keep the dependency one-way
        loc = locate(parse_tables(doc))
        if (loc["income"] or located["income"]) and (loc["cash_flow"] or located["cash_flow"]):
            f.path.write_bytes(doc)
            f.path.with_suffix(".meta.json").write_text(json.dumps({"url": alt.url, "fetched_at": "", "bytes": len(doc), "sha256": hashlib.sha256(doc).hexdigest(),
                                                                     "note": f"statements are in this exhibit, not in {f.primary_document}"}, indent=1))
            return alt
    return None


def report_period_ends(ticker: str) -> list[str]:
    """Every 10-K report-period end the company has filed (submissions API, all pages). The company's fiscal
    calendar, used to date the start of a period without touching XBRL values."""
    tmap, _ = fetch_tickers()
    cik = tmap[ticker]["cik"]
    sub, _ = fetch_json("submissions", cik, max_age_h=24 * 7)
    rows = list(_rows(sub["filings"]["recent"]))
    for f in sub["filings"].get("files", []):
        body, _ = _cached(f"https://data.sec.gov/submissions/{f['name']}", RAW / f"{cik:010d}" / f["name"], False, 24 * 30)
        rows += list(_rows(json.loads(body)))
    return sorted({r["reportDate"] for r in rows if r["form"] in FORMS + ("10-KT",) and r["reportDate"]})
