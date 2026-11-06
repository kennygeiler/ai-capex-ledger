"""Decisions on exceptions. Append-only log in decisions/decisions.jsonl; the latest decision per exception
counts, and only while the exception's input hash is unchanged (a changed input reopens it).

F14: every decision records its author (`reviewer`) and who that is (`author_kind`: person or run, as resolutions do,
T69). A decision closes a block finding only when a person made it (`by_person`); one a run or an agent made, or one
whose words say "to confirm", is a proposal: the block stays open (gate G4) and counts as Proposed on Proof, Reconcile
and the Release checklist (gate G6) until a person decides it. A line written before the field existed is read by the
old rule (resolutions.by_person on `reviewer` and `reason`); no line is rewritten."""
import json
import uuid
from datetime import datetime, timezone

from ..core.store import KINDS, ROOT

LOG = ROOT / "decisions" / "decisions.jsonl"
AUTHOR_KINDS = ("person", "run")


def decisions() -> list[dict]:
    return [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()] if LOG.exists() else []


def by_person(d: dict) -> bool:
    """A decision a person made, failing closed: resolutions.by_person on its reviewer and reason (author_kind when the
    line carries it; before it, a name on config.PEOPLE with no "to confirm")."""
    from .resolutions import by_person as _person
    return _person({"by": d.get("reviewer"), "reason": d.get("reason"), **({"author_kind": d["author_kind"]} if "author_kind" in d else {})})


def latest(ds: list[dict], blocks=frozenset()) -> dict:
    """The decision that stands per exception: the newest. For a block finding (its id in `blocks`) a run's decision
    never supersedes a person's on the same input hash (as resolutions.latest): a proposal written after a person decided
    changes nothing (F14). Warn and info findings keep the newest line, as before F14."""
    out, person = {}, {}
    for d in ds:
        out[d["exception_id"]] = d
        if d["exception_id"] in blocks and by_person(d):
            person[(d["exception_id"], d.get("input_hash"))] = d
    for k, d in out.items():
        p = person.get((k, d.get("input_hash")))
        if p is not None and not by_person(d):
            out[k] = p
    return out


def _blocks(exceptions: list[dict]) -> set:
    return {e["exception_id"] for e in exceptions if e.get("severity") == "block"}


def current(e: dict, cur: dict) -> dict | None:
    """The standing decision on exception `e` while its input hash is unchanged, else None."""
    d = cur.get(e["exception_id"])
    return d if d and d.get("input_hash") == e["input_hash"] else None


def closes(e: dict, d: dict | None) -> bool:
    """A decision closes its finding: any current decision closes a warn; only a person's closes a block (F14)."""
    return d is not None and (e["severity"] != "block" or by_person(d))


def open_items(exceptions: list[dict], ds: list[dict]) -> list[dict]:
    """Block and warn exceptions no decision closes (`closes`), blocking first, latest fiscal year first. A block with
    only a run's decision stays here: G4 fails on it and `proposed` names it."""
    cur = latest(ds, _blocks(exceptions))
    todo = [e for e in exceptions if e["severity"] != "info" and not closes(e, current(e, cur))]
    return sorted(todo, key=lambda e: (e["severity"] != "block", -int((e["period"] or "FY0000")[2:]), e["ticker"], e["exception_id"]))


def proposed(exceptions: list[dict], ds: list[dict]) -> list[dict]:
    """The block exceptions whose current decision a run or an agent made: [{**exception, "decision": d}]. Each is
    Proposed (left to confirm) on Proof, Reconcile and gate G6, and still open under G4, until a person decides it."""
    cur = latest(ds, _blocks(exceptions))
    return [{**e, "decision": d} for e in exceptions if e["severity"] == "block" and (d := current(e, cur)) and not by_person(d)]


def decide(exc: dict, kind: str, reason: str, by: str, value: int | None = None, *, author_kind: str) -> dict:
    """Append one decision under its author. `author_kind` has no default, so every caller says who it is: person (`ledger
    review … decide … --as person`): `by` must be on config.PEOPLE (status.is_person) or nothing is written; run (`--as
    run`): an agent's or a run's decision, recorded, closing no block."""
    if kind not in KINDS or not reason.strip() or (kind == "override") != (value is not None):
        raise ValueError("kind must be accept, override (with --value) or reject, with a reason")
    if not str(by or "").strip():
        raise ValueError("a decision needs its author's name")
    if author_kind not in AUTHOR_KINDS:
        raise ValueError(f"author_kind must be one of {AUTHOR_KINDS}, not {author_kind!r}")
    from ..core.status import is_person
    if author_kind == "person" and not is_person(by):
        raise ValueError(f"{by.strip()!r} is not on config.PEOPLE, the people whose decisions count; an agent records author_kind run")
    prev = latest(decisions(), _blocks([exc])).get(exc["exception_id"])
    d = {"decision_id": uuid.uuid4().hex[:12], "exception_id": exc["exception_id"], "kind": kind, "value": value, "reason": reason,
         "reviewer": by.strip(), "author_kind": author_kind, "decided_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "input_hash": exc["input_hash"],
         "supersedes": prev["decision_id"] if prev else None}
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps(d) + "\n")
    return d


def apply(values: list[dict], exceptions: list[dict], ds: list[dict]) -> list[dict]:
    """Released values: an override or reject decision that closes a value's exception (`closes`) replaces the agent
    value; a run's decision on a block changes nothing until a person makes it theirs."""
    cur, by_key = latest(ds, _blocks(exceptions)), {}
    for e in exceptions:
        d = current(e, cur)
        if closes(e, d) and d["kind"] != "accept" and e["period"]:
            by_key[(e["ticker"], e["field"], e["period"])] = d
    out = []
    for v in values:
        d = by_key.get((v["ticker"], v["field"], v["period"]))
        out.append(v if not d else {**v, "value": d["value"], "source": "override"} if d["kind"] == "override" else {**v, "value": None, "source": "missing"})
    return out


ACTIONS = ("confirm", "overturn")  # F-TR1: what a person does with a block a run or an agent decided


class Stale(ValueError):
    """The finding or its proposed decision changed since the page showed it (the route answers 409; the page reloads)."""


def person_decides(exc: dict, action: str, reason: str, by: str, *, decision_id: str, kind: str | None = None, value: int | None = None,
                   ds: list[dict] | None = None) -> dict:
    """F-TR1: a person makes a proposed block decision theirs from the page (POST /api/decision). `exc` is the exception
    as the database holds it now; `decision_id` the proposal the page showed. Confirm writes the proposal's own kind and
    value; Overturn writes another kind (`kind`, with `value` for an override). Either goes through `decide` with
    author_kind person, so `by` must be on config.PEOPLE. Refused (ValueError, nothing written): not a block, no
    proposal standing, an unknown action. Stale: the proposal standing is not the one the page showed."""
    if action not in ACTIONS:
        raise ValueError(f"action must be one of {ACTIONS}, not {action!r}")
    if exc.get("severity") != "block":
        raise ValueError("only a block finding takes a person's decision here")
    p = next((x["decision"] for x in proposed([exc], decisions() if ds is None else ds)), None)
    if p is None:
        raise ValueError("no proposed decision stands on this finding: nothing to confirm or overturn")
    if p.get("decision_id") != decision_id:
        raise Stale("the proposed decision changed since the page showed it; reload")
    if action == "confirm":
        return decide(exc, p["kind"], reason, by, p.get("value"), author_kind="person")
    if kind == p["kind"] and (kind != "override" or value == p.get("value")):
        raise ValueError("an overturn names another decision than the one proposed; to keep it, confirm")
    return decide(exc, kind or "", reason, by, value, author_kind="person")
