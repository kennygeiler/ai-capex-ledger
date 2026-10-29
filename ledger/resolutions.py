"""What a person decided about a queue item: accept (the number is right as is), explain (right, and here is why),
fix (will be fixed; stays open), blocks (must not ship). Append-only log in data/resolutions.jsonl, keyed by the
item and a hash of its content, so a changed item comes back. The release gate counts `blocks`; `accept` and
`explain` hide the item until its content changes."""
import json
import uuid
from datetime import datetime, timezone

from .store import ROOT

LOG = ROOT / "data" / "resolutions.jsonl"
STATES = ("accept", "explain", "fix", "blocks")


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
