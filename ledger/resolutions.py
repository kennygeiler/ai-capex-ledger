"""What a person decided about a queue item: accept (the number is right as is), explain (right, and here is why),
fix (will be fixed; stays open), blocks (must not ship). Append-only log in decisions/resolutions.jsonl, beside
decisions.jsonl (tracked: it is judgement, like definitions/), keyed by the item and a hash of its content, so a
changed item comes back. The release gate counts `blocks`; `accept` and `explain` hide the item until its content
changes. `by_row()` maps the latest state onto dataset rows so exports and the grid can carry it.

The key (T62): `key_for()` builds it from the item's fields, kind|ticker|field|period|dimension|rule_id|subject, with ''
for what the item does not have and '|' inside a part escaped as %7C (a segment name, a rule's subject: the filing, the
column). It names one item: two findings on one field and year (a jump and an opex-over-revenue, or
the same rule on two filings) are two keys. Before T62 the key was kind|ticker|where, `where` being the display string
"field period", so those findings shared one key and resolving the second un-resolved the first; `ledger resolutions
migrate-keys` appends each such line again under its new key (`migrated_from` names the old one), copies the ones that
map to no item or to several into decisions/archive/ with a note, and removes nothing: the log is append-only, so a
legacy-shaped key is simply not live (not shown, not counted, not a gate failure), like a stale kind."""
import json
import re
import uuid
from datetime import datetime, timezone

from .store import ROOT

LOG = ROOT / "decisions" / "resolutions.jsonl"  # beside decisions.jsonl: the two append-only logs of judgement the app writes; definitions/ is the one a person edits
STATES = ("accept", "explain", "fix", "blocks")
# The cause kinds the pipeline produces today, each named by its producer (app.flow() builds the queue with key_for()).
# A resolution on any other kind is stale: its cause can no longer come back (reference_disagrees and attribution_moved
# went with the inferred layer, 2ee2e6f), so it is not shown, not counted and not a gate failure. Stale lines are moved
# to decisions/archive/, never rewritten in the live log.
LIVE_KINDS = ("fact_differs",        # app.flow(): a fact whose label is unresolved against the filing's XBRL tag
              "fact_changed",        # app.flow(): a fact that differs from the signed release
              "finding_unconfirmed", # app.flow(): a rule's finding (hq findings) the SEC's data can't confirm
              "blocked",             # app.flow(): a block-severity exception (hq questions)
              "new_filing")          # app.flow(): a filing the watch found and the ledger has not read
KEY_FIELDS = ("kind", "ticker", "field", "period", "dimension", "rule_id", "subject")  # the key's parts, in order
LEGACY_PIPES = 2  # kind|ticker|where: the shape before T62


def _esc(p: str | None) -> str:
    return (p or "").replace("%", "%25").replace("|", "%7C")


def _unesc(p: str) -> str:
    return p.replace("%7C", "|").replace("%25", "%")


def key_for(kind: str, ticker: str, field: str | None = None, period: str | None = None, dimension: str | None = None,
            rule_id: str | None = None, subject: str | None = None) -> str:
    """One queue item's key, from its fields and never from a display string. A '|' inside a part (a segment name, a
    rule's subject) is escaped as %7C, so the key always splits into exactly these seven parts."""
    return "|".join(_esc(p) for p in (kind, ticker, field, period, dimension, rule_id, subject))


def parse_key(key: str) -> dict | None:
    """The key's parts, {kind, ticker, field, period, dimension, rule_id, subject}, or None for a legacy-shaped key."""
    parts = key.split("|")
    if len(parts) != len(KEY_FIELDS):
        return None
    return dict(zip(KEY_FIELDS, (_unesc(p) for p in parts)))


def kind_of(key: str) -> str:
    return key.partition("|")[0]


def is_live(key: str) -> bool:
    """A key the queue can produce today: a live kind in the key_for() shape. A legacy key (kind|ticker|where) is not."""
    return kind_of(key) in LIVE_KINDS and parse_key(key) is not None
STATUS = {"accept": "accepted", "explain": "explained", "fix": "fix_pending", "blocks": "blocks"}  # the word a row carries


def load(path=None) -> list[dict]:
    p = path or LOG
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


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
    kind the pipeline no longer produces (LIVE_KINDS), for kinds that name no dataset row (new_filing) and for a
    legacy-shaped key (migrated, or archived, by `migrate-keys`)."""
    k = parse_key(key)
    if not k or k["kind"] not in LIVE_KINDS or not k["field"]:
        return None
    if k["kind"] in ("fact_differs", "fact_changed"):
        return ("facts", k["ticker"], k["field"], k["dimension"], k["period"], "")
    if k["kind"] in ("finding_unconfirmed", "blocked"):
        return ("values", k["ticker"], k["field"], "", k["period"], "")
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


# ── T62: the one-off from kind|ticker|where to key_for() ───────────────────────────────────────────────────────────
def legacy_key(item: dict) -> str:
    """The key app.flow() built before T62 for a queue item: kind|ticker|where."""
    return f"{item['kind']}|{item['ticker']}|{item['where']}"


def migrate_keys(lines: list[dict], queue_for, now: str | None = None) -> dict:
    """Plan the migration of `lines` (the log, in file order). `queue_for(ticker)` gives that company's queue items
    (app.flow). A legacy line that matches exactly one item's legacy key is migrated: the same line (id, hash, state,
    reason, by, at untouched) under the item's key, plus `migrated_from` and `migrated_at`; the hash is kept, not
    recomputed, so a resolution whose item changed since stays expired (`current` says whether it still matches).
    One that matches no item or several is archived with a note. A line already in the new shape is untouched.
    Returns {migrated: [...], archived: [...], untouched: [...]}; nothing is written."""
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    out, queues = {"migrated": [], "archived": [], "untouched": []}, {}
    done = {(r.get("migrated_from"), r.get("id")) for r in lines if r.get("migrated_from")}  # a second run changes nothing
    for r in lines:
        if parse_key(r["key"]) is not None or r["key"].count("|") != LEGACY_PIPES or (r["key"], r.get("id")) in done:
            out["untouched"].append(r)
            continue
        ticker = r["key"].split("|")[1]
        if ticker not in queues:
            queues[ticker] = queue_for(ticker)
        hits = [q for q in queues[ticker] if legacy_key(q) == r["key"]]
        if len(hits) == 1:
            out["migrated"].append({**r, "key": hits[0]["key"], "migrated_from": r["key"], "migrated_at": now, "current": hits[0]["hash"] == r["hash"]})
        else:
            why = "no queue item carries this key today" if not hits else f"{len(hits)} queue items carry this key: " + "; ".join(q["key"] for q in hits)
            out["archived"].append({**r, "note": f"not migrated by migrate-keys on {now[:10]}: {why}; the live line stays and is not live (legacy shape)"})
    return out


def write_migration(plan: dict, log=None, archive=None) -> None:
    """Append the migrated lines to the log and the archived ones, behind a note line, to the archive file. Removes nothing."""
    log, archive = log or LOG, archive or (ROOT / "decisions" / "archive" / f"resolutions-keys-{datetime.now(timezone.utc):%Y-%m-%d}.jsonl")
    if plan["migrated"]:
        with log.open("a") as f:
            for r in plan["migrated"]:
                f.write(json.dumps(r) + "\n")
    if plan["archived"]:
        archive.parent.mkdir(parents=True, exist_ok=True)
        with archive.open("a") as f:
            f.write(json.dumps({"note": "Resolutions whose legacy key (kind|ticker|where, before T62) maps to no queue item or to several, so migrate-keys could not give them one key_for() key. Copied here with the reason, not deleted; the line in decisions/resolutions.jsonl stays and is not live. To keep one, resolve the item again from Reconcile.", "count": len(plan["archived"])}) + "\n")
            for r in plan["archived"]:
                f.write(json.dumps(r) + "\n")
