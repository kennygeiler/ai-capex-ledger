"""T10/T11: the MVP filing list and the primary documents behind it.

For each MVP company, every 10-Q and 10-K whose report period ends between FIRST_PERIOD and LAST_PERIOD.
The range starts a year before the window so year-to-date cash-flow lines can be turned into single quarters
(the Q3 2024 quarter of a December-year company needs its Q2 2024 10-Q) and Q4 can be derived from the 10-K.
"""
import json
from dataclasses import asdict, dataclass

from ..config import MVP_TICKERS
from .edgar import RAW, _cached, fetch_json, fetch_tickers

FIRST_PERIOD = "2024-01-01"
LAST_PERIOD = "2026-08-31"  # late fiscal calendars (Nvidia ends Q2 in late July) still map into 2026Q2
FORMS = ("10-Q", "10-K")


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
    for t in tickers or MVP_TICKERS:
        cik = tmap[t]["cik"]
        sub, _ = fetch_json("submissions", cik, refresh=refresh, max_age_h=24 * 7)
        seen = set()
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


def report_period_ends(ticker: str) -> list[str]:
    """Every 10-Q/10-K report-period end the company has filed (submissions API, all pages). The company's fiscal
    calendar, used to date the start of a period without touching XBRL values."""
    tmap, _ = fetch_tickers()
    cik = tmap[ticker]["cik"]
    sub, _ = fetch_json("submissions", cik, max_age_h=24 * 7)
    rows = list(_rows(sub["filings"]["recent"]))
    for f in sub["filings"].get("files", []):
        body, _ = _cached(f"https://data.sec.gov/submissions/{f['name']}", RAW / f"{cik:010d}" / f["name"], False, 24 * 30)
        rows += list(_rows(json.loads(body)))
    return sorted({r["reportDate"] for r in rows if r["form"] in FORMS + ("10-K/A", "10-Q/A", "10-KT") and r["reportDate"]})
