"""What a person decided about a queue item: accept (the number is right as is), explain (right, and here is why),
fix (will be fixed; stays open), blocks (must not ship). Append-only log in decisions/resolutions.jsonl, beside
decisions.jsonl (tracked: it is judgement, like definitions/), keyed by the item and a hash of its content, so a
changed item comes back. The release gate counts `blocks`; `accept` and `explain` hide the item until its content
changes. `by_row()` maps the latest state onto dataset rows so exports and the grid can carry it."""
import json
import uuid
from datetime import datetime, timezone

from .store import ROOT

LOG = ROOT / "decisions" / "resolutions.jsonl"  # beside decisions.jsonl: the two append-only logs of judgement the app writes; definitions/ is the one a person edits
STATES = ("accept", "explain", "fix", "blocks")
STATUS = {"accept": "accepted", "explain": "explained", "fix": "fix_pending", "blocks": "blocks"}  # the word a row carries


def load() -> list[dict]:
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()] if LOG.exists() else []


def latest(rs: list[dict] | None = None) -> dict:
    out = {}
    for r in rs if rs is not None else load():
        out[r["key"]] = r
    return out


def resolve(key: str, content_hash: str, state: str, reason: str, by: str) -> dict:
    if state not in STATES or not reason.strip() or not by.strip():
        raise ValueError("a resolution needs a state (accept, explain, fix, blocks), a reason and a name")
    r = {"id": uuid.uuid4().hex[:12], "key": key, "hash": content_hash, "state": state, "reason": reason, "by": by,
         "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(r) + "\n")
    return r


def _parse(key: str):
    """A queue key -> (table, ticker, field, dimension, period, kind) with '' for what the key does not say."""
    kind, _, rest = key.partition("|")
    ticker, _, where = rest.partition("|")
    words = where.split()
    if kind == "reference_disagrees" and len(words) >= 3 and words[0] == "AI":
        return ("attribution", ticker, words[1], "", words[2], "actual")
    if kind == "attribution_moved" and len(words) == 3:
        return ("attribution", ticker, words[0], "", words[1], words[2])
    if kind in ("fact_differs", "fact_changed") and len(words) >= 2:
        return ("facts", ticker, words[0], " ".join(words[1:-1]), words[-1], "")
    if kind in ("finding_unconfirmed", "blocked") and words:
        return ("values", ticker, words[0], "", words[1] if len(words) > 1 and words[1].startswith("FY") else "", "")
    return None


def by_row(rs: list[dict] | None = None) -> dict:
    """The latest decision per dataset row: {(table, ticker, field, dimension, period, kind): {state, status, by, at, reason}}.
    A values key with no period applies to every period of that field."""
    out = {}
    for key, r in latest(rs).items():
        k = _parse(key)
        if k:
            out[k] = {"id": r.get("id"), "state": r["state"], "status": STATUS[r["state"]], "by": r["by"], "at": r["at"], "reason": r["reason"]}
    return out


def resolution_of(index: dict, table: str, ticker: str, field: str, dimension: str = "", period: str = "", kind: str = "") -> dict | None:
    """The latest resolution on a dataset row (the record `status.state` reads), or None."""
    return index.get((table, ticker, field, dimension or "", period, kind)) or (index.get((table, ticker, field, "", "", "")) if table == "values" else None)


def status_of(index: dict, table: str, ticker: str, field: str, dimension: str = "", period: str = "", kind: str = "") -> str:
    r = resolution_of(index, table, ticker, field, dimension, period, kind)
    return r["status"] if r else ""
