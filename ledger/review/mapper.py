"""The mapping assistant (docs/TICKETS.md T33): for a company's reported PP&E categories with no entry in
taxonomy/asset_types.yaml, an agent proposes the nearest us-gaap PropertyPlantAndEquipmentByTypeAxis member with the
note's own words as evidence and a confidence. A proposal is a proposal: it lands in decisions/mapping_proposals.jsonl
(append-only) and on Reconcile's "asset types" group, where a person approves, edits or rejects it. Only the approval
(`approve`, behind POST /api/mapping) writes taxonomy/asset_types.yaml, with `by` = the person. A rejection is a line
in the same log, so the next run does not propose the same member again. Charter: agents/charters/mapper.md.

T63: an entry is a person's only when it carries `confirmed_by` (status.confirmed). `approve` writes `confirmed_by` and
`confirmed_at` beside `by` and `at`, since a person clicked it; on an entry already in the file without them (the 47
entries Claude Fable 5.1 wrote on 1 Nov 2026) Approve adds them to that line, Edit replaces the line with the person's
member, also confirmed, and Reject removes the line and logs the member, so the category is unmapped again and the next
mapper run proposes another. `filer_members` names the member the filer itself tagged for the category in its XBRL
instance, so Reconcile can flag a proposal that differs from it."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from ..extract import agents
from ..core import store
from ..extract.extract import render_statement
from ..core.status import confirmed
from ..release.taxonomy import ASSET_TYPES, asset_types, to_confirm, unmapped

ROOT = store.ROOT
TASKS = ROOT / "data" / "mapper" / "tasks"
PROPOSALS = ROOT / "decisions" / "mapping_proposals.jsonl"
CONFIDENCES = ("high", "medium", "low")
NONE = "none"


@dataclass
class Invalid(Exception):
    reason: str


def prompt_version() -> str:
    return agents.load()["mapper"]["prompt"]


def prompt_versions() -> tuple[str, ...]:
    return tuple(agents.versions("mapper"))


def members(path: Path = ASSET_TYPES) -> list[str]:
    """The allowed us-gaap members: the list in the comment header of taxonomy/asset_types.yaml ("us-gaap members used: ...")."""
    text = path.read_text() if path.exists() else ""
    head = "\n".join(l[1:].strip() for l in text.splitlines() if l.startswith("#"))
    m = re.search(r"us-gaap members used:(.*?)(?:\.\s*$|\n\s*\n|\Z)", head, re.S)
    return re.findall(r"[A-Z][A-Za-z]+Member", m.group(1)) if m else []


# ── the log ───────────────────────────────────────────────────────────────────

def load_proposals(path: Path | None = None) -> list[dict]:
    p = path or PROPOSALS
    return [json.loads(l) for l in p.read_text().splitlines() if l.strip()] if p.exists() else []


def _append(line: dict, path: Path | None = None) -> dict:
    p = path or PROPOSALS
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(line) + "\n")
    return line


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def by_name(ticker: str, lines: list[dict] | None = None, unconfirmed: set[str] | frozenset = frozenset()) -> dict[str, dict]:
    """Per reported_name of `ticker`: {"proposal": the current proposal or None; "rejected": the members a person rejected
    for it; "reproposed": proposals of a member that arrived after a person rejected it (T100), never current; "late":
    proposals that arrived after a person's approval, which hold no proposal current while the approval stands;
    "approved": the latest approval line, if any}.

    T100, a late writer never overwrites a newer state: a proposal of a member a person rejected for this name, whether
    the rejection came before or after it in the log, is never current; it shows under `reproposed` ("re-proposed after
    rejection") and needs a fresh decision from a person (Approve or Edit), with the rejected list beside it. A proposal
    that arrives after a person's approval changes nothing. `unconfirmed`: the names whose entry in
    taxonomy/asset_types.yaml is no longer a person's (unmapped or unconfirmed: the approval was undone by hand); for
    them the approval no longer stands (`approved` None) and the proposals after it count again."""
    out: dict[str, dict] = {}
    since: dict[str, list[dict]] = {}  # per name, the proposals since the last approval, in log order
    for l in lines if lines is not None else load_proposals():
        if l.get("ticker") != ticker:
            continue
        e = out.setdefault(l["reported_name"], {"proposal": None, "rejected": [], "reproposed": [], "late": [], "approved": None})
        props = since.setdefault(l["reported_name"], [])
        if l.get("kind") == "proposed":
            props.append(l)
            if l.get("standard_type") in e["rejected"]:
                e["reproposed"].append(l)  # a member a person already rejected: re-proposed after rejection
        elif l.get("kind") == "rejected":
            if l.get("standard_type") and l["standard_type"] not in e["rejected"]:
                e["rejected"].append(l["standard_type"])
        elif l.get("kind") in ("approved", "confirmed"):
            e["approved"] = l
            props.clear()
    for name, e in out.items():
        props = since.get(name) or []
        if e["approved"] and name in unconfirmed:
            e["approved"] = None  # the approval was undone: what came after it counts
        if e["approved"]:
            e["late"] = list(props)
            continue
        e["proposal"] = next((p for p in reversed(props) if p.get("standard_type") not in e["rejected"]), None)
    return out


def reject(ticker: str, reported_name: str, standard_type: str, by: str, reason: str = "", path: Path | None = None, yaml_path: Path | None = None) -> dict:
    """Log `standard_type` as rejected for the category. When taxonomy/asset_types.yaml holds an entry for it with that
    member and no `confirmed_by` (a proposal, T63), the line is removed too, so it stops counting: the category is
    unmapped again. The check and the removal happen on one snapshot under the file's lock (`_edit`), so a confirmation
    written meanwhile is seen and the confirmed line is never removed."""
    if not ticker.strip() or not reported_name.strip() or not standard_type.strip() or not by.strip():
        raise ValueError("a rejection needs the ticker, the reported name, the member rejected and a name")
    if not is_person(by):  # F-BF5: the same name check as Approve and every other write (T80)
        raise ValueError(f"{by.strip()!r} is not on config.PEOPLE, the people who may reject a mapping")
    ticker, reported_name, standard_type, by = ticker.strip().upper(), reported_name.strip(), standard_type.strip(), by.strip()
    y = yaml_path or ASSET_TYPES
    removed = {}

    def change(lines: list[str], data: dict):
        entry = (data.get(ticker) or {}).get(reported_name)
        if not entry or entry.get("standard_type") != standard_type:
            return None  # nothing in the file carries this member: the rejection is a log line only
        if confirmed(entry):
            raise ValueError(f"{ticker} {reported_name!r} is mapped to {standard_type} and confirmed by {entry['confirmed_by']}; a confirmed mapping is not rejected here")
        del lines[_entry_index(lines, ticker, reported_name)]
        removed.update({k: (str(v) if v is not None else v) for k, v in entry.items()})
        return lines, None

    if y.exists():
        _edit(y, ticker, reported_name, change)
    return _append({"kind": "rejected", "ticker": ticker, "reported_name": reported_name, "standard_type": standard_type, "by": by, "reason": reason, "at": _now(),
                    **({"removed_entry": removed} if removed else {})}, path)


# ── the task ──────────────────────────────────────────────────────────────────

def note_words(con, ticker: str, names: list[str]) -> list[dict]:
    """The note's words the categories were cited from: per (newest filing, table) one block with the text that introduces
    the table and the table as the notes reader saw it (the parsed filing at documents.tables_path). Empty when the
    parsed filing is not on disk (a clone without data/docs): the task then carries the category names alone."""
    if not names or not con.execute("select count(*) from information_schema.tables where table_name = 'note_extractions'").fetchone()[0]:
        return []
    cur = con.execute("""select n.accession, n.table_id, n.row_label, d.tables_path, d.filed from note_extractions n join documents d on d.accession = n.accession
                         where n.ticker = ? and n.field = 'ppe_category' and n.dimension in (select unnest(?)) order by d.filed desc""", [ticker, names])
    rows = [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]
    out, seen = [], set()
    for r in rows:
        key = (r["accession"], r["table_id"])
        if key in seen or r["table_id"] is None:
            continue
        p = ROOT / (r["tables_path"] or "")
        if not r["tables_path"] or not p.exists():
            continue
        parsed = json.loads(p.read_text())
        t = next((t for t in parsed["tables"] if t["id"] == r["table_id"]), None)
        if not t:
            continue
        seen.add(key)
        out.append({"accession": r["accession"], "table_id": r["table_id"], "filed": r["filed"], "before": re.sub(r"\s+", " ", (t.get("before") or "")[-1500:]).strip(),
                    "table": render_statement(f"PP&E table {r['table_id']} of filing {r['accession']} (filed {r['filed']})", [{**t, "unit_text": t.get("unit_text"), "unit_source": t.get("unit_source", "table")}])})
        if len(out) >= 3:  # the newest filings say what the categories hold today; older ones repeat them
            break
    return out


def make_task(ticker: str, names: list[str], blocks: list[dict], rejected: dict[str, list[str]] | None = None, allowed: list[str] | None = None) -> str:
    allowed = allowed or members()
    rejected = rejected or {}
    head = f"# Task: {ticker}, reported PP&E categories with no us-gaap member\n\nTicker: {ticker}\nPrompt version: {prompt_version()}\n"
    lst = "\n".join(f"- {m}" for m in allowed)
    cats = "\n".join(f"- \"{n}\"" + (f"  (a person rejected: {', '.join(rejected[n])}; propose another member or none)" if rejected.get(n) else "") for n in names)
    body = [f"## Allowed members (PropertyPlantAndEquipmentByTypeAxis)\n\n{lst}", f"## Categories to map\n\n{cats}"]
    if blocks:
        body.append("## The note's words\n\n" + "\n\n".join(f"Text before the table: \"{b['before']}\"\n\n{b['table']}" for b in blocks))
    else:
        body.append("## The note's words\n\n(the parsed note is not on disk; the category names above are all the note's words you have)")
    return head + "\n" + "\n\n".join(body) + "\n"


def write_task(ticker: str, text: str) -> Path:
    TASKS.mkdir(parents=True, exist_ok=True)
    p = TASKS / f"{ticker}.md"
    p.write_text(text)
    return p


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def validate_output(obj: dict, ticker: str, names: list[str], task: str, allowed: list[str] | None = None) -> None:
    allowed = allowed or members()
    if not isinstance(obj, dict):
        raise Invalid("output is not a JSON object")
    for k in ("ticker", "prompt_version", "proposals"):
        if k not in obj:
            raise Invalid(f"missing '{k}'")
    if obj["ticker"] != ticker:
        raise Invalid(f"ticker {obj['ticker']!r} is not the task's {ticker!r}")
    if obj["prompt_version"] not in (known := prompt_versions()):
        raise Invalid(f"prompt_version {obj['prompt_version']!r}, expected one of {known}")
    if not isinstance(obj["proposals"], list):
        raise Invalid("'proposals' must be a list")
    notes = _norm(task.partition("## The note's words")[2]) + " " + " ".join(_norm(n) for n in names)  # the note's words and the category names: never the headings or the member list
    seen = set()
    for i, p in enumerate(obj["proposals"]):
        missing = [k for k in ("reported_name", "standard_type", "evidence", "confidence", "reason") if k not in p]
        if missing:
            raise Invalid(f"proposals[{i}] missing {missing}")
        if p["reported_name"] not in names:
            raise Invalid(f"proposals[{i}].reported_name {p['reported_name']!r} is not one of the categories to map")
        if p["reported_name"] in seen:
            raise Invalid(f"proposals[{i}]: a second proposal for {p['reported_name']!r}")
        seen.add(p["reported_name"])
        if p["standard_type"] != NONE and p["standard_type"] not in allowed:
            raise Invalid(f"proposals[{i}].standard_type {p['standard_type']!r} is not on the allowed list (or none)")
        if not isinstance(p["evidence"], str) or not p["evidence"].strip() or not re.search(r"(?<!\S)" + re.escape(_norm(p["evidence"])) + r"(?!\S)", notes):
            raise Invalid(f"proposals[{i}].evidence is not whole words of the note: {str(p['evidence'])[:80]!r}")
        if p["confidence"] not in CONFIDENCES:
            raise Invalid(f"proposals[{i}].confidence must be one of {CONFIDENCES}")
    left = [n for n in names if n not in seen]
    if left:
        raise Invalid(f"no proposal for {left}")


def propose(ticker: str, obj: dict, run: dict, path: Path | None = None) -> list[dict]:
    """Append one `proposed` line per proposal, with the prompt version, the model and when."""
    at = _now()
    return [_append({"kind": "proposed", "ticker": ticker, **{k: p[k] for k in ("reported_name", "standard_type", "evidence", "confidence", "reason")},
                     "prompt_version": obj["prompt_version"], "model": run.get("model"), "at": at}, path) for p in obj["proposals"]]


# ── the approval: the one writer of taxonomy/asset_types.yaml ─────────────────

def _scalar(s: str) -> str:
    """A value as the file writes it: bare when YAML reads it back as the same string, quoted otherwise (No, On, 2026)."""
    import yaml
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9 .\-']*", s):
        try:
            if yaml.safe_load(f"k: {s}") == {"k": s}:
                return s
        except yaml.YAMLError:
            pass
    return json.dumps(s)


from ..core.status import NOT_A_PERSON, is_person  # T80: one name check, in status, for confirmed_by and resolutions


def person(by: str) -> str:
    """T63: the name written into confirmed_by. A name that names a model, an agent or a run is refused; it is not a
    person standing behind the mapping. T80: so is any name not on config.PEOPLE (status.is_person, fail closed), since
    status.confirmed would not count it. (Who may press the button is T6, auth.)"""
    by = by.strip()
    if not by or NOT_A_PERSON.search(by):
        raise ValueError(f"{by!r} is not a person's name: a model, an agent or a run never confirms a mapping")
    if not is_person(by):
        raise ValueError(f"{by!r} is not on config.PEOPLE, the people who may confirm a mapping")
    return by


class Stale(ValueError):
    """The entry changed since the page showed it (the route answers 409 and the page reloads)."""


_UNSET = object()


def approve(ticker: str, reported_name: str, standard_type: str, evidence: str, by: str, path: Path | None = None, log: Path | None = None, at: str | None = None, con=None,
            expected=_UNSET) -> dict:
    """Write one entry to taxonomy/asset_types.yaml, in the file's own format (one flow-mapping line under the ticker's
    block; the comment header untouched), with `confirmed_by` and `confirmed_at` = the person and today (T63: a person
    clicked it). Refuse a member off the header's list, a confirmer name that names a model or agent (`person`), a
    category already mapped and confirmed, and a name that is not one of the company's reported categories with no
    mapping (taxonomy.unmapped) or with an unconfirmed one (taxonomy.to_confirm), on `con` or on the database read-only
    when none is given. On an unconfirmed entry, the same member adds `confirmed_by` and `confirmed_at` to its line (the
    proposer's `by`, `at` and evidence kept); a different member replaces the line with the person's entry, confirmed.
    The read, the checks and the write are one step under the file's lock (`_edit`). Logged as `approved` or `confirmed`.
    `expected` (the route always passes it): what the page showed for the entry, {standard_type, at} or None for no
    entry; when the file holds something else on the snapshot, nothing is written and Stale is raised (a stale Approve)."""
    p = path or ASSET_TYPES
    ticker, reported_name, standard_type, evidence, by = ticker.strip().upper(), reported_name.strip(), standard_type.strip(), " ".join(evidence.split()), by.strip()
    if not ticker or not reported_name or not evidence or not by:
        raise ValueError("a mapping needs the ticker, the reported name, the evidence and the name of the person approving it")
    person(by)
    allowed = members(p)
    if standard_type not in allowed:
        raise ValueError(f"{standard_type!r} is not a member on the list in taxonomy/asset_types.yaml")
    day = at or date.today().isoformat()
    out: dict = {}

    def change(lines: list[str], data: dict):
        old = (data.get(ticker) or {}).get(reported_name)
        if expected is not _UNSET:
            _check_expected(old, expected, ticker, reported_name)
        _check_unconfirmed(old, ticker, reported_name)
        if old and old.get("standard_type"):  # a proposal in the file (T63): confirm it, or replace it with the person's member
            if reported_name not in {u["reported_name"] for u in _to_confirm(con, ticker)}:
                raise ValueError(f"{ticker} {reported_name!r} is not one of the company's reported PP&E categories with an unconfirmed mapping; nothing written")
            i = _entry_index(lines, ticker, reported_name)
            if old.get("standard_type") == standard_type:
                new = _confirm_line(lines, i, old, by, day)
                out.update({"kind": "confirmed", "ticker": ticker, "reported_name": reported_name, **{k: (str(v) if v is not None else v) for k, v in new.items()}})
            else:
                lines[i] = _line(reported_name, standard_type, evidence, by, day)
                new = {"standard_type": standard_type, "evidence": evidence, "by": by, "at": day, "confirmed_by": by, "confirmed_at": day}
                out.update({"kind": "approved", "ticker": ticker, "reported_name": reported_name, **new, "replaced": {k: (str(v) if v is not None else v) for k, v in old.items()}})
            return lines, new
        if reported_name not in {u["reported_name"] for u in _unmapped(con, ticker)}:
            raise ValueError(f"{ticker} {reported_name!r} is not one of the company's reported PP&E categories with no mapping; nothing written")
        line = _line(reported_name, standard_type, evidence, by, day)
        if old is not None:  # an entry with no member (an unmapped category): replaced
            lines[_entry_index(lines, ticker, reported_name)] = line
        else:
            head = _ticker_line(lines, ticker)
            if head is None:
                lines += [f"{ticker}:", line]
            else:
                i = head + 1
                while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
                    i += 1
                while i > head + 1 and not lines[i - 1].strip():  # insert before any blank line that ends the block
                    i -= 1
                lines.insert(i, line)
        new = {"standard_type": standard_type, "evidence": evidence, "by": by, "at": day, "confirmed_by": by, "confirmed_at": day}
        out.update({"kind": "approved", "ticker": ticker, "reported_name": reported_name, **new})
        return lines, new

    _edit(p, ticker, reported_name, change)
    _append(out, log)
    return {k: v for k, v in out.items() if k != "kind"}


def _check_expected(old: dict | None, expected, ticker: str, reported_name: str) -> None:
    """Stale unless the file's entry is what the page showed ({standard_type, at}, or None for no entry)."""
    now = {"standard_type": old.get("standard_type"), "at": str(old["at"]) if old.get("at") is not None else None} if old and old.get("standard_type") else None
    want = {"standard_type": (expected or {}).get("standard_type"), "at": str((expected or {}).get("at")) if (expected or {}).get("at") is not None else None} if expected else None
    if now != want:
        raise Stale(f"{ticker} {reported_name!r} changed since the page was loaded: on file {now or 'no entry'}, the page showed {want or 'no entry'}; reload")


def _check_unconfirmed(old: dict | None, ticker: str, reported_name: str) -> None:
    if old and confirmed(old):
        raise ValueError(f"{ticker} {reported_name!r} is already mapped to {old.get('standard_type')} and confirmed by {old['confirmed_by']}")


def _confirm_line(lines: list[str], i: int, old: dict, by: str, day: str) -> dict:
    """Add confirmed_by and confirmed_at to the entry's own line (the proposer's by, at and evidence kept)."""
    if not lines[i].rstrip().endswith("}"):
        raise ValueError("the entry is not one flow-mapping line; confirm it by hand")
    lines[i] = lines[i].rstrip()[:-1] + f", confirmed_by: {_scalar(by)}, confirmed_at: {day}}}"
    return {**old, "confirmed_by": by, "confirmed_at": day}


BULK_MAX = 100  # one "Approve all" at most; the page sends the categories one card shows


def matched(con, tickers: list[str]) -> set:
    """{(ticker, reported_name)} of the entries no person confirmed whose member the company's own XBRL tag matches
    (status.of_mapping's filer_tag state): taxonomy.to_confirm with the verified ones, less those still to confirm. The
    server's own verdict, read once per batch; never the page's word."""
    def read(c):
        every = {(e["ticker"], e["reported_name"]) for e in to_confirm(c, tickers, with_verified=True)}
        return every - {(e["ticker"], e["reported_name"]) for e in to_confirm(c, tickers)}
    if con is not None:
        return read(con)
    import duckdb
    c = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    try:
        return read(c)
    finally:
        c.close()


def approve_many(items: list, by: str, path: Path | None = None, log: Path | None = None, at: str | None = None, con=None) -> dict:
    """Reconcile's "Approve all N" on Matches company tag (docs/ux-flow/report.md #5). Everything is checked in one pass
    before anything is written, on one read of the file and one query: the person (config.PEOPLE), 1 to BULK_MAX items
    with no repeat, each confirming the member the page showed (standard_type equal to expected.standard_type: a bulk
    never changes a member), each member on the file's list, and each item one the server itself finds the company's own
    tag matches (`matched`): a Proposed or unmapped category in the batch refuses the whole batch (400), whatever the page
    sent. Then one write under the file's lock confirms every entry on its own line, with the same checks a single
    Approve makes (`_check_expected`: a stale entry is 409; `_check_unconfirmed`; `_confirm_line`) on that snapshot, and
    the parsed file must equal the snapshot except those entries, or nothing is written: k of N is N or 0. Each is
    logged `confirmed`, as approve logs one."""
    import yaml
    from ..core.safewrite import safe_write
    p = path or ASSET_TYPES
    if not isinstance(items, list) or not items:
        raise ValueError("send `items`: the categories to approve, each {ticker, reported_name, standard_type, evidence, expected}")
    if len(items) > BULK_MAX:
        raise ValueError(f"{len(items)} items: approve at most {BULK_MAX} at once")
    by = person(str(by or ""))
    norm_items, seen = [], set()
    for it in items:
        if not isinstance(it, dict):
            raise ValueError("each item is {ticker, reported_name, standard_type, evidence, expected}")
        t, n, m = str(it.get("ticker", "")).strip().upper(), str(it.get("reported_name", "")).strip(), str(it.get("standard_type", "")).strip()
        exp = it.get("expected")
        if not t or not n or not m:
            raise ValueError("each item needs the ticker, the reported name and the member")
        if not isinstance(exp, dict) or exp.get("standard_type") != m:
            raise ValueError(f"{t} {n!r}: a bulk confirms the member the page showed; standard_type must equal expected.standard_type")
        if (t, n) in seen:
            raise ValueError(f"{t} {n!r} is in the batch twice")
        seen.add((t, n))
        norm_items.append((t, n, m, exp))
    allowed = set(members(p))
    off = [f"{t} {n!r} ({m})" for t, n, m, _ in norm_items if m not in allowed]
    if off:
        raise ValueError(f"not members on the list in taxonomy/asset_types.yaml: {', '.join(off)}; nothing written")
    ok = matched(con, sorted({t for t, *_ in norm_items}))
    not_matched = [f"{t} {n!r}" for t, n, *_ in norm_items if (t, n) not in ok]
    if not_matched:
        raise ValueError(f"not a category the company's own tag matches: {', '.join(not_matched)}; approve it on its own row. Nothing written")
    day = at or date.today().isoformat()
    written: list[dict] = []

    def mutate(text):
        text = text or ""
        lines = text.splitlines()
        before = yaml.safe_load(text) or {}
        expect = json.loads(json.dumps({k: (v or {}) for k, v in before.items()}, default=str, sort_keys=True))
        for t, n, m, exp in norm_items:
            _ticker_line(lines, t)
            old = (before.get(t) or {}).get(n)
            _check_expected(old, exp, t, n)
            _check_unconfirmed(old, t, n)
            new = _confirm_line(lines, _entry_index(lines, t, n), old, by, day)
            expect[t][n] = json.loads(json.dumps(new, default=str, sort_keys=True))
            written.append({"kind": "confirmed", "ticker": t, "reported_name": n, **{k: (str(v) if v is not None else v) for k, v in new.items()}})
        new_text = "\n".join(lines) + "\n"
        after = json.loads(json.dumps({k: (v or {}) for k, v in (yaml.safe_load(new_text) or {}).items()}, default=str, sort_keys=True))
        if after != expect:
            raise ValueError("the file would change more than the entries approved; nothing written")
        return new_text
    try:
        safe_write(p, p.with_name(f".{p.name}.lock"), mutate)
    except ValueError as e:
        raise type(e)(f"Approved 0 of {len(norm_items)}; nothing written: {e}") from e
    for line in written:
        _append(line, log)
    return {"approved": len(written), "items": [{"ticker": w["ticker"], "reported_name": w["reported_name"]} for w in written]}


def _line(reported_name: str, standard_type: str, evidence: str, by: str, day: str) -> str:
    """One entry as the file writes it: a person's approval is also their confirmation (T63). The name is always quoted."""
    return f"  {json.dumps(reported_name)}: {{standard_type: {standard_type}, evidence: {json.dumps(evidence)}, by: {_scalar(by)}, at: {day}, confirmed_by: {_scalar(by)}, confirmed_at: {day}}}"


def _top_key(line: str):
    """The key of a top-level mapping line (`MU:`, `"MU":`, `MU: # note`), or None."""
    import yaml
    if not line.strip() or line[0] in " #\t":
        return None
    try:
        d = yaml.safe_load(line)
    except yaml.YAMLError:
        return None
    return next(iter(d)) if isinstance(d, dict) and len(d) == 1 else None


def _ticker_line(lines: list[str], ticker: str, what: str = "taxonomy/asset_types.yaml") -> int | None:
    """The index of the ticker's block header, None when the file has none; ValueError when it has more than one (PyYAML
    keeps the last duplicate and silently drops the other block's entries) or a header that is not a plain block.
    `what` names the file in the error (T36 writes definitions/companies.yaml through the same `_edit`)."""
    hits = [i for i, l in enumerate(lines) if _top_key(l) == ticker]
    if len(hits) > 1:
        raise ValueError(f"{what} has {len(hits)} blocks for {ticker}; merge them by hand, nothing written")
    if hits:
        import yaml
        d = yaml.safe_load(lines[hits[0]])
        if d.get(ticker) is not None:
            raise ValueError(f"{ticker}'s block is not a plain block of one-line entries; edit it by hand, nothing written")
    return hits[0] if hits else None


def _entry_index(lines: list[str], ticker: str, reported_name: str) -> int:
    """The line of the entry for `reported_name` inside the ticker's block; ValueError when it is not one line there."""
    import yaml
    head = _ticker_line(lines, ticker)
    if head is not None:
        i = head + 1
        while i < len(lines) and (lines[i].startswith(" ") or not lines[i].strip()):
            if lines[i].strip() and not lines[i].lstrip().startswith("#"):
                try:
                    if reported_name in (yaml.safe_load(lines[i].strip()) or {}):
                        return i
                except yaml.YAMLError:
                    pass
            i += 1
    raise ValueError(f"{ticker} {reported_name!r}: no one-line entry in the ticker's block; nothing written")


_MISSING = object()


def _edit(p: Path, ticker: str, reported_name: str, change, what: str = "taxonomy/asset_types.yaml") -> bool:
    """The one way the file is written (safewrite.safe_write: an exclusive lock on a lock file beside it, a temporary file
    moved into place). Under the lock read the file once, hand its lines and parsed content to `change(lines, data)`,
    which checks what it needs on that snapshot and returns None (nothing to write) or (new lines, the entry as it must
    now read, None for gone). The new text must parse, the ticker's block must occur once, and the parsed file must
    equal the snapshot except that one entry, or nothing is written."""
    import yaml
    from ..core.safewrite import safe_write

    def mutate(text):
        text = text or ""
        lines = text.splitlines()
        _ticker_line(lines, ticker, what)  # a duplicated or odd header is refused before anything is changed
        before = yaml.safe_load(text) or {}
        got = change(lines, before)
        if got is None:
            return None
        lines, want = got
        new_text = "\n".join(lines) + "\n"
        after = yaml.safe_load(new_text) or {}
        _ticker_line(lines, ticker, what)
        norm = lambda d: json.loads(json.dumps({t: (v or {}) for t, v in d.items()}, default=str, sort_keys=True))  # an emptied block reads None
        expect = norm(before)
        block = expect.setdefault(ticker, {})
        if want is None:
            block.pop(reported_name, None)
        else:
            block[reported_name] = norm({"_": want})["_"]
        if norm(after) != expect:
            raise ValueError("the file would change more than the one entry; nothing written")
        return new_text
    return safe_write(p, p.with_name(f".{p.name}.lock"), mutate)


def _to_confirm(con, ticker: str) -> list[dict]:
    """The company's reported categories whose entry has no confirmed_by (taxonomy.to_confirm), on `con` or read-only;
    with the ones the company's own tag checks, which a person may still confirm."""
    if con is not None:
        return to_confirm(con, [ticker], with_verified=True)
    import duckdb
    c = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    try:
        return to_confirm(c, [ticker], with_verified=True)
    finally:
        c.close()


def _unmapped(con, ticker: str) -> list[dict]:
    """The company's reported categories with no mapping (taxonomy.unmapped), on `con` or on the database read-only."""
    if con is not None:
        return unmapped(con, [ticker])
    import duckdb
    c = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
    try:
        return unmapped(c, [ticker])
    finally:
        c.close()


def yaml_load(p: Path) -> dict:
    import yaml
    return yaml.safe_load(p.read_text()) or {}


# ── what Reconcile shows ──────────────────────────────────────────────────────

def pending(con, tickers: list[str] | None, lines: list[dict] | None = None, with_verified: bool = False) -> list[dict]:
    """Every reported asset type in `tickers` (None: every company) a person has yet to stand behind: the unmapped ones
    with the mapper's latest proposal, if one stands, and (T63) the ones whose entry in taxonomy/asset_types.yaml has no
    confirmed_by, with that entry as the proposal (`source` "taxonomy/asset_types.yaml"). Each carries the members a
    person rejected for it, the note's words around it, and the member the filer tagged for it (`filer`). `with_verified`:
    also the entries the company's own tag matches (kind "verified"), which Reconcile lists after the open ones so a
    person can still confirm, choose another or reject."""
    out = []
    by_t: dict[str, list[tuple[str, dict | None]]] = {}
    for u in unmapped(con, tickers):
        by_t.setdefault(u["ticker"], []).append((u["reported_name"], None))
    waiting = {(e["ticker"], e["reported_name"]) for e in to_confirm(con, tickers)}
    for e in to_confirm(con, tickers, with_verified=with_verified):  # with_verified: also the ones the company's own tag matches, which a person may override
        by_t.setdefault(e["ticker"], []).append((e["reported_name"], {**e, "_verified": (e["ticker"], e["reported_name"]) not in waiting}))
    for t, pairs in sorted(by_t.items()):
        names = [n for n, _ in pairs]
        idx = by_name(t, lines, set(names))  # every name here is unmapped or unconfirmed: an approval on file for it was undone
        blocks = note_words(con, t, names)
        filed = filer_members(con, t, names)
        for n, entry in sorted(pairs, key=lambda x: (x[1] is not None, x[0])):
            e = idx.get(n) or {"proposal": None, "rejected": [], "reproposed": [], "late": [], "approved": None}
            note = next((b for b in blocks if _norm(n) in _norm(b["table"])), blocks[0] if blocks else None)
            proposal = e["proposal"] if entry is None else {"standard_type": entry["standard_type"], "evidence": entry.get("evidence"), "by": entry.get("by"), "at": entry.get("at"),
                                                            "source": "taxonomy/asset_types.yaml", "confidence": None, "reason": None}
            out.append({"ticker": t, "reported_name": n, "kind": "unmapped" if entry is None else "verified" if entry.get("_verified") else "to_confirm", "proposal": proposal, "rejected": e["rejected"],
                        "reproposed": [r["standard_type"] for r in e["reproposed"]] if entry is None else [], "filer": filed.get(n),
                        "note": {"accession": note["accession"], "table_id": note["table_id"], "before": note["before"][-400:]} if note else None})
    return out


def filer_members(con, ticker: str, names: list[str]) -> dict[str, dict | None]:
    """Per reported name, what the filer itself tagged for that category: {"members": [...], "ambiguous": bool}, the
    PropertyPlantAndEquipmentByTypeAxis members whose PropertyPlantAndEquipmentGross fact in the filing's own instance
    has the category's value on its balance date, over every extracted year. A view over filertag.verdicts (one reader of the
    instance, read from disk only: a page read never reaches the SEC). None for a name when nothing could be checked
    (no instance on disk for any one of its filings, or the query failed), which the page shows as "not checked", never as
    "the filer tags nothing". A zero is never matched, and a value two members share, or members that differ across
    years, make the answer ambiguous: shown, never a mismatch. Members may be the filer's extension (amzn:, goog:)."""
    if not names:
        return {}
    from ..checks.filertag import verdicts
    vs = verdicts(con, [ticker])
    out: dict[str, dict | None] = {}
    for n in names:
        v = vs.get((ticker, n))
        read = (v or {}).get("readings") or []
        if not read or any(r.get("members") is None for r in read):  # one year not read is not checked, as filertag.judge says
            out[n] = None
            continue
        ms = sorted({m for r in read for m in r["members"]})
        out[n] = {"members": ms, "ambiguous": any(len(r["members"]) > 1 for r in read) or len(ms) > 1}
    return out


def mismatch(member: str | None, filer: dict | None) -> bool:
    """A proposal differs from the filer when the filer tagged the category with exactly one member, a us-gaap one, and
    it is not the proposal's. Not checked (None), ambiguous, nothing tagged, or the filer's extension member (amzn:,
    goog:, nvda:, apld:, no us-gaap member to compare): no flag."""
    if not member or not filer or filer.get("ambiguous") or len(filer.get("members") or []) != 1:
        return False
    m = filer["members"][0]
    return m.startswith("us-gaap:") and m.split(":", 1)[1] != member
