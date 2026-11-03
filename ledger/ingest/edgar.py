"""Thin, polite client for the SEC EDGAR APIs, with an on-disk cache and a log of every call.

SEC rules: a User-Agent with a contact email, and at most 10 requests per second.
https://www.sec.gov/os/accessing-edgar-data
"""
import hashlib
import json
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ["LEDGER_ROOT"]).resolve() if os.environ.get("LEDGER_ROOT") else Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "raw"
CHECKOUT_RAW = Path(__file__).resolve().parents[2] / "data" / "raw"  # the checkout's own cache; under LEDGER_ROOT (golden, the tests' temp roots) offline reads fall back to it
MIN_INTERVAL = 0.15  # seconds between requests (under 10/s)
_last = 0.0
LOG: list[dict] = []  # one entry per call: network requests and cache reads


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def user_agent() -> str:
    ua = os.environ.get("SEC_USER_AGENT")
    if not ua:
        env = ROOT / ".env"
        if env.exists():
            for line in env.read_text().splitlines():
                if line.startswith("SEC_USER_AGENT="):
                    ua = line.split("=", 1)[1].strip().strip('"')
    if not ua or "@" not in ua:
        raise SystemExit("Set SEC_USER_AGENT (name and contact email) in .env; SEC rejects requests without one.")
    return ua


def offline() -> bool:
    """LEDGER_OFFLINE=1: every SEC read is served from the data/raw cache whatever its age, and anything not cached raises
    Offline. `ledger test` and `ledger golden --check` set it unless --online; tests/__init__.py sets it for a bare
    `python -m unittest`. No contact (SEC_USER_AGENT) is needed, since nothing is fetched."""
    return os.environ.get("LEDGER_OFFLINE") == "1"


def refuse_if_offline(url: str) -> None:
    """Every code path that reaches the network calls this first (the SEC client, edgartools, the investor-page PDFs)."""
    if offline():
        raise Offline(f"LEDGER_OFFLINE=1 and not cached: {url}")
    if os.environ.get("LEDGER_READONLY") == "1":  # a hosted Kenny's Data Emporium serves what it has; it never reaches the SEC
        raise Offline(f"not in the cache and this copy is read-only: {url}")


def _get(url: str, retries: int = 4) -> bytes:
    global _last
    refuse_if_offline(url)
    for attempt in range(1, retries + 1):
        wait = MIN_INTERVAL - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()
        req = urllib.request.Request(url, headers={"User-Agent": user_agent(), "Accept-Encoding": "identity"})
        t0 = time.monotonic()
        entry = {"url": url, "at": _now(), "attempt": attempt, "source": "network"}
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
            LOG.append(entry | {"status": r.status, "ms": round((time.monotonic() - t0) * 1000), "bytes": len(body)})
            return body
        except urllib.error.HTTPError as e:
            LOG.append(entry | {"status": e.code, "ms": round((time.monotonic() - t0) * 1000), "bytes": 0, "error": str(e.reason)})
            if e.code in (429, 500, 502, 503) and attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise
        except urllib.error.URLError as e:
            LOG.append(entry | {"status": None, "ms": round((time.monotonic() - t0) * 1000), "bytes": 0, "error": str(e.reason)})
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            raise
    raise RuntimeError("unreachable")


class Offline(RuntimeError):
    """A read-only or offline copy asked for a document it does not hold."""


def _offline_hit(url: str, path: Path) -> tuple[bytes, dict] | None:
    """Offline: the cached file at `path`, or at the same place under the checkout's data/raw, whatever its age."""
    cands = [path]
    try:
        cands.append(CHECKOUT_RAW / path.resolve().relative_to(RAW.resolve()))
    except ValueError:
        pass
    for p in cands:
        if p.exists():
            meta_path = p.with_suffix(".meta.json")
            meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"url": url, "fetched_at": None, "bytes": p.stat().st_size}
            LOG.append({"url": url, "at": _now(), "attempt": 1, "source": "cache", "status": 200, "ms": 0, "bytes": meta.get("bytes"), "fetched_at": meta.get("fetched_at"), "offline": True})
            return p.read_bytes(), meta | {"cache": "hit"}
    return None


def _cached(url: str, path: Path, refresh: bool, max_age_h: float) -> tuple[bytes, dict]:
    if offline():
        hit = _offline_hit(url, Path(path))
        if hit is None:
            raise Offline(f"LEDGER_OFFLINE=1 and not cached: {url}")
        return hit
    meta_path = path.with_suffix(".meta.json")
    fresh = path.exists() and meta_path.exists() and (time.time() - path.stat().st_mtime) < max_age_h * 3600
    if fresh and not refresh:
        meta = json.loads(meta_path.read_text())
        LOG.append({"url": url, "at": _now(), "attempt": 1, "source": "cache", "status": 200, "ms": 0, "bytes": meta["bytes"], "fetched_at": meta["fetched_at"]})
        return path.read_bytes(), meta | {"cache": "hit"}
    refuse_if_offline(url)
    body = _get(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    meta = {"url": url, "fetched_at": _now(), "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}
    meta_path.write_text(json.dumps(meta, indent=1))
    return body, meta | {"cache": "miss"}


def fetch_json(kind: str, cik: int, refresh: bool = False, max_age_h: float = 24) -> tuple[dict, dict]:
    """kind: 'companyfacts' | 'submissions'. Returns (data, manifest entry)."""
    url = {
        "companyfacts": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json",
        "submissions": f"https://data.sec.gov/submissions/CIK{cik:010d}.json",
    }[kind]
    body, meta = _cached(url, RAW / f"{cik:010d}" / f"{kind}.json", refresh, max_age_h)
    return json.loads(body), meta


def fetch_tickers(refresh: bool = False) -> tuple[dict[str, dict], dict]:
    """SEC's ticker -> CIK map. Returns ({TICKER: {cik, title}}, manifest entry)."""
    body, meta = _cached("https://www.sec.gov/files/company_tickers.json", RAW / "company_tickers.json", refresh, 24)
    rows = json.loads(body).values()
    return {r["ticker"].upper(): {"cik": r["cik_str"], "title": r["title"]} for r in rows}, meta
