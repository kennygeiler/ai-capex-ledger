"""T70–T72: decisions on exceptions. Append-only log in decisions/decisions.jsonl; the latest decision per exception
counts, and only while the exception's input hash is unchanged (a changed input reopens it)."""
import json
import uuid
from datetime import datetime, timezone

from .store import ROOT

LOG = ROOT / "decisions" / "decisions.jsonl"
KINDS = ("accept", "override", "reject")


def decisions() -> list[dict]:
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()] if LOG.exists() else []


def latest(ds: list[dict]) -> dict:
    out = {}
    for d in ds:
        out[d["exception_id"]] = d
    return out


def open_items(exceptions: list[dict], ds: list[dict]) -> list[dict]:
    """Block and warn exceptions without a current decision, blocking first, latest quarter first."""
    cur = latest(ds)
    todo = [e for e in exceptions if e["severity"] != "info" and cur.get(e["exception_id"], {}).get("input_hash") != e["input_hash"]]
    return sorted(todo, key=lambda e: (e["severity"] != "block", -int((e["period"] or "FY0000")[2:]), e["ticker"], e["exception_id"]))


def decide(exc: dict, kind: str, reason: str, by: str, value: int | None = None) -> dict:
    if kind not in KINDS or not reason.strip() or (kind == "override") != (value is not None):
        raise ValueError("kind must be accept, override (with --value) or reject, with a reason")
    prev = latest(decisions()).get(exc["exception_id"])
    d = {"decision_id": uuid.uuid4().hex[:12], "exception_id": exc["exception_id"], "kind": kind, "value": value, "reason": reason,
         "reviewer": by, "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "input_hash": exc["input_hash"],
         "supersedes": prev["decision_id"] if prev else None}
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(d) + "\n")
    return d


def apply(values: list[dict], exceptions: list[dict], ds: list[dict]) -> list[dict]:
    """Released values: an override or reject decision on a value's exception replaces the agent value."""
    cur, by_key = latest(ds), {}
    for e in exceptions:
        d = cur.get(e["exception_id"])
        if d and d["input_hash"] == e["input_hash"] and d["kind"] != "accept" and e["period"]:
            by_key[(e["ticker"], e["field"], e["period"])] = d
    out = []
    for v in values:
        d = by_key.get((v["ticker"], v["field"], v["period"]))
        out.append(v if not d else {**v, "value": d["value"], "source": "override"} if d["kind"] == "override" else {**v, "value": None, "source": "missing"})
    return out
