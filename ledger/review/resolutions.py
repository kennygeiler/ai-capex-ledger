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
legacy-shaped key is simply not live (not shown, not counted, not a gate failure), like a stale kind.

Who wrote a line (T69) is a field, `author_kind` person or run, set by the writer: the person's routes write person and
refuse a `by` not on config.PEOPLE; an agent or replication writer writes run, and its line is "to confirm" (unconfirmed,
gate G6) whatever its words say. Lines from before the field are read by the old rule (by_person, by_run), never
rewritten. A run line never supersedes a person line on the same key and hash, and lines are ordered by `at`, not by
their place in the file (T100, latest)."""
import json
import re
import uuid
from datetime import datetime, timezone

from ..core.status import is_person
from ..core.store import ROOT

LOG = ROOT / "decisions" / "resolutions.jsonl"  # beside decisions.jsonl: the two append-only logs of judgement the app writes; definitions/ is the one a person edits
STATES = ("accept", "explain", "fix", "blocks")
# The cause kinds the pipeline produces today, each named by its producer (app.flow() builds the queue with key_for()).
# A resolution on any other kind is stale: its cause can no longer come back (reference_disagrees and attribution_moved
# went with the inferred layer, 2ee2e6f), so it is not shown, not counted and not a gate failure. Stale lines are moved
# to decisions/archive/, never rewritten in the live log.
from ..core.config import NOTE_FIELDS  # T92 review: a finding on a note field is keyed by rule and subject (_parse)

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


TO_CONFIRM = re.compile(r"\bto confirm\b", re.I)
AUTHOR_KINDS = ("person", "run")  # T69: who wrote a line, set by the writer: /api/resolve and bulk write person, an agent or replication run writes run


def by_person(r: dict) -> bool:
    """A line a person wrote, failing closed (T69, T80). A line with `author_kind` says so itself. A line written before
    the field existed is read by the old rule: a `by` on config.PEOPLE that names no model, agent or run
    (status.is_person) and no "to confirm" in `by` or `reason`. No migration: history is read as it was written."""
    if "author_kind" in r:
        return r["author_kind"] == "person"
    by = str(r.get("by") or "").strip()
    return is_person(by) and not TO_CONFIRM.search(f"{by} {r.get('reason') or ''}")


def by_run(r: dict) -> bool:
    """A line a run wrote for a person to confirm. With `author_kind`, the field alone decides: a run line counts whatever
    its words say. Before the field, the old rule: "to confirm" in `by` or `reason`."""
    if "author_kind" in r:
        return r["author_kind"] == "run"
    return bool(TO_CONFIRM.search(f"{r.get('by', '')} {r.get('reason', '')}"))


def latest(rs: list[dict] | None = None) -> dict:
    """The line that stands per key (T100). Lines are ordered by `at`, then by file order for a tie, never by file order
    alone: `migrate-keys` appends its copies at the end with their original `at`, so a copy never outranks a line written
    after the one it copies. The newest line stands, except that a run line never supersedes a person line with the same
    key AND hash, whatever came between: when the newest line is not a person's and some person line carries its key and
    hash, the newest such person line stands. So P1 (h1, blocks), P2 (h2, explain), R1 (h1, run) leaves P1 standing. A
    later person line supersedes an earlier one; a run line on a hash no person decided stands (it waits, unconfirmed)."""
    rows = list(rs if rs is not None else load())
    order = sorted(range(len(rows)), key=lambda i: (str(rows[i].get("at") or ""), i))
    out, person = {}, {}
    for i in order:
        r = rows[i]
        out[r["key"]] = r
        if by_person(r):
            person[(r["key"], r.get("hash"))] = r
    for k, r in out.items():
        p = person.get((k, r.get("hash")))
        if p is not None and not by_person(r):
            out[k] = p
    return out


def _line(key: str, content_hash: str, state: str, reason: str, by: str, author_kind: str) -> dict:
    """One resolution line, checked: a state, a reason and a name; author_kind person or run; a person's `by` on
    config.PEOPLE; a live key. Raises ValueError; writes nothing."""
    if state not in STATES or not str(reason or "").strip() or not str(by or "").strip():
        raise ValueError("a resolution needs a state (accept, explain, fix, blocks), a reason and a name")
    if author_kind not in AUTHOR_KINDS:
        raise ValueError(f"author_kind must be one of {AUTHOR_KINDS}, not {author_kind!r}")
    if author_kind == "person" and not is_person(by):
        raise ValueError(f"{by.strip()!r} is not on config.PEOPLE, the people whose resolutions count as a person's; a run writes author_kind run")
    if not is_live(key):
        raise ValueError(f"not a queue item's key (kind|ticker|field|period|dimension|rule_id|subject, a live kind): {key!r}")
    return {"id": uuid.uuid4().hex[:12], "key": key, "hash": content_hash, "state": state, "reason": reason, "by": by.strip(), "author_kind": author_kind,
            "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


def _write(lines: list[dict]) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a") as f:
        f.write("".join(json.dumps(r) + "\n" for r in lines))


def resolve(key: str, content_hash: str, state: str, reason: str, by: str, *, author_kind: str) -> dict:
    """Append one resolution. `author_kind` is the writer's to set (T69): "person" from the routes a person uses
    (/api/resolve, /api/resolve/bulk), where `by` must be on config.PEOPLE (status.is_person) or the line is refused;
    "run" from any agent or replication writer, whose line waits for a person to confirm (unconfirmed, gate G6)."""
    r = _line(key, content_hash, state, reason, by, author_kind)
    _write([r])
    return r


def resolve_many(items: list[dict], state: str, reason: str, by: str, *, author_kind: str) -> list[dict]:
    """One decision on many items ([{key, hash}]), each its own line. Every item is checked first (`_line`); one bad
    item refuses them all and nothing is written, so a 400 never leaves part of a bulk decision on file."""
    if not items:
        raise ValueError("no items")
    lines = [_line(str(i.get("key", "")), str(i.get("hash", "")), state, reason, by, author_kind) for i in items]
    _write(lines)
    return lines


def _parse(key: str):
    """A queue key -> (table, ticker, field, dimension, period, kind) with '' for what the key does not say. None for a
    kind the pipeline no longer produces (LIVE_KINDS), for kinds that name no dataset row (new_filing) and for a
    legacy-shaped key (migrated, or archived, by `migrate-keys`)."""
    k = parse_key(key)
    if not k or k["kind"] not in LIVE_KINDS or not k["field"]:
        return None
    if k["kind"] in ("fact_differs", "fact_changed"):
        return ("facts", k["ticker"], k["field"], k["dimension"], k["period"], "")
    if k["kind"] == "finding_unconfirmed" and k["field"] in NOTE_FIELDS:
        # T92 review: a finding on a note figure (a tie on a filing's group, two readings of one fact) is keyed whole, by
        # its rule and subject (the filing, or the fact's dimension), so a resolution closes only the item it was written
        # for, never every finding on the field and year
        return ("findings", k["ticker"], k["field"], k["subject"] or "", k["period"], k["rule_id"] or "")
    if k["kind"] in ("finding_unconfirmed", "blocked"):
        return ("values", k["ticker"], k["field"], "", k["period"], "")
    return None


WORST = ("blocks", "fix", "explain", "accept")  # a row's state is the worst over its items' latest resolutions


def by_row(rs: list[dict] | None = None, items: list[dict] | None = None, tickers=()) -> dict:
    """The decision per dataset row: {(table, ticker, field, dimension, period, kind): {state, status, by, at, reason}}.
    A row may carry several queue items (T62: two findings on one field and year); its state is the worst of their latest
    resolutions, blocks > fix > explain > accept. With `items` (the queue, [{key, hash}]), a resolution whose item's hash
    moved on no longer counts, and a row one of whose items has no current resolution reads as unresolved: it is left
    out, so the row is open. `tickers` says for which companies `items` is every item there is (F15): a resolution of
    theirs whose key no item carries today closes nothing. A values key with no period applies to
    every period of that field. Pages read `index()`, which passes both."""
    lt = latest(rs)
    unresolved, expired = set(), set()
    for q in items or []:
        k = _parse(q["key"])
        r = lt.get(q["key"])
        if k and not (r and r["hash"] == q["hash"]):
            unresolved.add(k)
            if r:
                expired.add(q["key"])  # the item changed since: its resolution no longer counts, the item is back
    if tickers:
        live = {q["key"] for q in items or []}
        expired |= {key for key in lt if key not in live and (parse_key(key) or {}).get("ticker") in set(tickers)}  # the item is gone: nothing to close
    per_row = {}
    for key, r in lt.items():
        k = _parse(key)
        if k and key not in expired:
            per_row.setdefault(k, []).append(r)
    out = {}
    for k, rows in per_row.items():
        r = min(rows, key=lambda r: WORST.index(r["state"]))
        if r["state"] in ("explain", "accept", "fix") and k in unresolved:
            continue  # another item on the row has no current decision: the row is open, and no word of one item's decision stands for it
        out[k] = {"id": r.get("id"), "state": r["state"], "status": STATUS[r["state"]], "by": r["by"], "at": r["at"], "reason": r["reason"]}
    return out


UNMATCHED = "Resolutions not matched · queue not built"


class Unmatched(RuntimeError):
    """The queue the resolutions are matched against could not be built: no page may count a resolution."""


def index(con, tickers=None, rs: list[dict] | None = None) -> dict:
    """by_row as every page reads it (F15, F1): each resolution matched against the queue item, key and hash, it was
    written for (app.queue_items, the producer Reconcile lists), so a changed or gone item reopens on Proof, the Release
    counts, the read API and the taxonomy rows exactly as on Reconcile, and two items on one row need a decision each.
    The queue is built only for the companies that have a live resolution on file (`tickers` narrows them), once per
    stamp (queue.items_for). When it cannot be built (a file the snapshot reads is missing, a database without its
    tables) nothing is guessed: Unmatched is raised, a 503 "Resolutions not matched · queue not built" on a page and a
    stopped command, never a page that quietly disagrees with Reconcile."""
    rs = load() if rs is None else rs
    have = {k["ticker"] for key in latest(rs) if (k := parse_key(key)) and k["kind"] in LIVE_KINDS}
    want = sorted(have if tickers is None else have & {str(t).upper() for t in tickers})
    if not want:
        return {}
    import duckdb
    from .queue import items_for
    try:
        items = items_for(con, want)
    except (OSError, ValueError, duckdb.Error) as e:
        raise Unmatched(f"{UNMATCHED}: {e.__class__.__name__}: {str(e)[:200]}") from e
    return {k: v for k, v in by_row(rs, items=items, tickers=want).items() if k[1] in want}


def resolution_of(index: dict, table: str, ticker: str, field: str, dimension: str = "", period: str = "", kind: str = "") -> dict | None:
    """The latest resolution on a dataset row (the record `status.state` reads), or None."""
    return index.get((table, ticker, field, dimension or "", period, kind)) or (index.get((table, ticker, field, "", "", "")) if table == "values" else None)


def status_of(index: dict, table: str, ticker: str, field: str, dimension: str = "", period: str = "", kind: str = "") -> str:
    r = resolution_of(index, table, ticker, field, dimension, period, kind)
    return r["status"] if r else ""


def unconfirmed(rs: list[dict] | None = None) -> list[dict]:
    """The standing resolutions (latest) a run made for a person to confirm, oldest first: `author_kind` run, or, on a
    line from before the field (T69), "to confirm" in `by` or `reason` (by_run). They stay here until a person records
    a resolution of their own on the same key; the release refuses while any remain. A key whose cause kind the
    pipeline no longer produces (LIVE_KINDS) is stale and left out, even if still on file."""
    return sorted((r for r in latest(rs).values() if is_live(r["key"]) and by_run(r)), key=lambda r: r["at"])


# ── T62: the one-off from kind|ticker|where to key_for() ───────────────────────────────────────────────────────────
ARCHIVE_DIR = ROOT / "decisions" / "archive"


def archived_keys() -> list[dict]:
    """The lines of every migrate-keys archive file (decisions/archive/resolutions-keys-*.jsonl), note lines left out."""
    return [r for p in sorted(ARCHIVE_DIR.glob("resolutions-keys-*.jsonl")) for r in load(p) if "key" in r]


def legacy_key(item: dict) -> str:
    """The key app.flow() built before T62 for a queue item: kind|ticker|where."""
    return f"{item['kind']}|{item['ticker']}|{item['where']}"


def migrate_keys(lines: list[dict], queue_for, now: str | None = None, archived_before: list[dict] = ()) -> dict:
    """Plan the migration of `lines` (the log, in file order). `queue_for(ticker)` gives that company's queue items
    (app.flow). A legacy line that matches exactly one item's legacy key is migrated: the same line (id, hash, state,
    reason, by, at untouched) under the item's key, plus `migrated_from` and `migrated_at`; the hash is kept, not
    recomputed, so a resolution whose item changed since stays expired (`current` says whether it still matches).
    One that matches no item or several is archived with a note. A line already in the new shape, one migrated before
    and one archived before (`archived_before`: the archive files' lines) is untouched, so a second run is a no-op.
    Returns {migrated: [...], archived: [...], untouched: [...], current: {id: hash still the item's}}; nothing is written."""
    now = now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    out, queues = {"migrated": [], "archived": [], "untouched": [], "current": {}}, {}
    done = {(r.get("migrated_from"), r.get("id")) for r in lines if r.get("migrated_from")} | {(r.get("key"), r.get("id")) for r in archived_before if r.get("key")}
    for r in lines:
        if parse_key(r["key"]) is not None or r["key"].count("|") != LEGACY_PIPES or (r["key"], r.get("id")) in done:
            out["untouched"].append(r)
            continue
        ticker = r["key"].split("|")[1]
        if ticker not in queues:
            queues[ticker] = queue_for(ticker)
        hits = [q for q in queues[ticker] if legacy_key(q) == r["key"]]
        if len(hits) == 1:
            kind = r.get("author_kind") or ("person" if by_person(r) else "run" if by_run(r) else None)  # T100: the copy says who wrote the original
            out["migrated"].append({**r, "key": hits[0]["key"], "migrated_from": r["key"], "migrated_at": now, **({"author_kind": kind} if kind else {})})
            out["current"][r.get("id")] = hits[0]["hash"] == r["hash"]
        else:
            why = "no queue item carries this key today" if not hits else f"{len(hits)} queue items carry this key: " + "; ".join(q["key"] for q in hits)
            out["archived"].append({**r, "note": f"not migrated by migrate-keys on {now[:10]}: {why}; the live line stays and is not live (legacy shape)"})
    return out


def write_migration(plan: dict, log=None, archive=None) -> None:
    """Append the migrated lines to the log and the archived ones, behind a note line, to the archive file. Removes nothing."""
    log, archive = log or LOG, archive or ARCHIVE_DIR / f"resolutions-keys-{datetime.now(timezone.utc):%Y-%m-%d}.jsonl"
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
