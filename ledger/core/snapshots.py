"""What the ledger looked like after each `ledger run`, so Kenny's Data Emporium can say what changed since the last one.

A snapshot holds the filings read, every value with its basis, and the open review items. Kept in data/snapshots/
next to the database (not in git): one small JSON file per run."""
import json
from datetime import datetime, timezone

from ..review.review import decisions, open_items
from .store import ROOT

DIR = ROOT / "data" / "snapshots"


def take(con, tickers: list[str]) -> dict:
    q = lambda sql: con.execute(sql, [tickers]).fetchall()
    excs = [dict(zip([c[0] for c in con.execute("select * from exceptions limit 0").description], r))
            for r in q("select * from exceptions where ticker in (select unnest(?))")]
    return {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "filings": sorted(f"{t}|{a}|{f}|{p}" for t, a, f, p in q("select ticker, accession, form, period from documents where ticker in (select unnest(?))")),
            "values": {f"{t}|{f}|{p}": [v, b] for t, f, p, v, b in q('select ticker, field, period, value, basis from "values" where ticker in (select unnest(?))')},
            "open": {e["exception_id"]: e["severity"] for e in open_items(excs, decisions())}}


def save(snap: dict) -> None:
    DIR.mkdir(parents=True, exist_ok=True)
    (DIR / f"{snap['at'].replace(':', '')}.json").write_text(json.dumps(snap, sort_keys=True))


def last_two() -> tuple[dict | None, dict | None]:
    files = sorted(DIR.glob("*.json"))
    load = lambda f: json.loads(f.read_text())
    return (load(files[-2]) if len(files) > 1 else None), (load(files[-1]) if files else None)


def diff(prev: dict | None, cur: dict | None) -> dict | None:
    """What changed between two runs. None when there is nothing to compare."""
    if not prev or not cur:
        return None
    pv, cv = prev["values"], cur["values"]
    changed = [{"key": k, "before": pv.get(k, [None])[0], "after": cv.get(k, [None])[0]}
               for k in sorted(pv.keys() | cv.keys()) if pv.get(k, [None])[0] != cv.get(k, [None])[0]]
    restated = [k for k in sorted(cv) if cv[k][1] == "restated" and pv.get(k, [None, None])[1] != "restated"]
    return {"since": prev["at"], "at": cur["at"],
            "new_filings": sorted(set(cur["filings"]) - set(prev["filings"])),
            "changed": changed, "newly_restated": restated,
            "opened": sorted(set(cur["open"]) - set(prev["open"])), "closed": sorted(set(prev["open"]) - set(cur["open"]))}
