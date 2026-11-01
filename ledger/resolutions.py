"""What a person decided about a queue item: accept (the number is right as is), explain (right, and here is why),
fix (will be fixed; stays open), blocks (must not ship). Append-only log in decisions/resolutions.jsonl, beside
decisions.jsonl (tracked: it is judgement, like definitions/), keyed by the item and a hash of its content, so a
changed item comes back. The release gate counts `blocks`; `accept` and `explain` hide the item until its content
changes. `by_row()` maps the latest state onto dataset rows so exports and the grid can carry it."""
import json
import re
import uuid
from datetime import datetime, timezone

from .store import ROOT

LOG = ROOT / "decisions" / "resolutions.jsonl"  # beside decisions.jsonl: the two append-only logs of judgement the app writes; definitions/ is the one a person edits
STATES = ("accept", "explain", "fix", "blocks")
# The cause kinds the pipeline produces today, each named by its producer (app.flow() builds the queue; the key is
# kind|ticker|where). A resolution on any other kind is stale: its cause can no longer come back (reference_disagrees
# and attribution_moved went with the inferred layer, 2ee2e6f), so it is not shown, not counted and not a gate failure.
# Stale lines are moved to decisions/archive/, never rewritten in the live log.
LIVE_KINDS = ("fact_differs",        # app.flow(): a fact whose label is unresolved against the filing's XBRL tag
              "fact_changed",        # app.flow(): a fact that differs from the signed release
              "finding_unconfirmed", # app.flow(): a rule's finding (hq findings) the SEC's data can't confirm
              "blocked",             # app.flow(): a block-severity exception (hq questions)
              "new_filing")          # app.flow(): a filing the watch found and the ledger has not read


def kind_of(key: str) -> str:
    return key.partition("|")[0]


def is_live(key: str) -> bool:
    return kind_of(key) in LIVE_KINDS
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
    """A queue key -> (table, ticker, field, dimension, period, kind) with '' for what the key does not say. None for a
    kind the pipeline no longer produces (LIVE_KINDS) and for kinds that name no dataset row (new_filing)."""
    kind, _, rest = key.partition("|")
    ticker, _, where = rest.partition("|")
    words = where.split()
    if kind not in LIVE_KINDS:
        return None
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


TO_CONFIRM = re.compile(r"\bto confirm\b", re.I)


def unconfirmed(rs: list[dict] | None = None) -> list[dict]:
    """The latest resolutions a run made for a person to confirm (`by` or `reason` says "to confirm"), oldest first. They
    stay here until that person records a resolution of their own on the same key; the release refuses while any remain.
    A key whose cause kind the pipeline no longer produces (LIVE_KINDS) is stale and left out, even if still on file."""
    return sorted((r for r in latest(rs).values() if is_live(r["key"]) and TO_CONFIRM.search(f"{r.get('by', '')} {r.get('reason', '')}")), key=lambda r: r["at"])
