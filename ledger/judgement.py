"""Resolve by rule (T36): a person's explanation in Reconcile, written once as a definition or a rule, so the next run
closes the same cause without asking again.

Two writers, one discipline. `write_definition` adds one entry to definitions/companies.yaml (company-level: what a
field means for that company, the kinds definitions.load accepts) through mapper._edit, the T63 writer: an exclusive
fcntl lock, the file read once, the whole file parsed before and after and compared so that only the one entry
changes, a temporary file moved into place with os.replace. `write_rule` adds one file to rules/ (cross-company: an
info-severity `explains` rule, rules._explains): under a lock on the directory the rule set is loaded before, the new
file is checked with the loader's own checks and written to a temporary name the loader never globs, moved into place,
and the set is loaded again; anything but exactly the one new rule, with every other file's hash unchanged, removes
it and refuses. Both record `by` (a person on config.PEOPLE, mapper.person, fail closed), `why` and `at`; both files
are tracked in git like every judgement file, and nothing here commits.

What may be written is decided here, from the queue item's key and the database, never from what the page sends
beyond the reason and the name (`offers`): a rule names the warn rule the finding came from, its field, and the whole
labels the company's field is read from; a definition is offered only for the causes a definition settles (an XBRL
disagreement on revenue or opex, a cost-of-revenue made of lines). A rule is never a pattern: it matches a finding
only where every line the field is read from is one it names, so it cannot explain an unrelated row."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

import yaml

from . import definitions, resolutions, rules as rules_mod
from .mapper import _edit, _scalar, _ticker_line, person

DEF_FILE = definitions.FILE
RULES_DIR = rules_mod.RULES_DIR
DEFINITION_KINDS = ("revenue", "opex", "cost_lines")  # what definitions.load accepts
TICKER = re.compile(r"[A-Z][A-Z0-9.\-]{0,9}")


def _one_line(s: str) -> str:
    return " ".join(str(s or "").split())


# ── what an item may become ─────────────────────────────────────────────────────────────────────────────────────────
def _labels(con, ticker: str, field: str) -> list[str]:
    cur = con.execute("select ticker, field, row_label from extractions where ticker = ? and field = ?", [ticker, field])
    return rules_mod.lines_read([{"ticker": t, "field": f, "row_label": l} for t, f, l in cur.fetchall()], ticker, field)


def rule_id(target: str, field: str, labels: list[str]) -> str:
    """The id (and file name) of the rule that explains `target` on `field` for exactly these labels: stable, so the same
    explanation written twice is the same file and the second write is refused."""
    h = hashlib.sha256("\n".join(sorted(rules_mod.label_key(l) for l in labels)).encode()).hexdigest()[:8]
    return f"explains_{target}_{field}_{h}"


def offers(con, key: dict, defs: dict | None = None, rules: list[dict] | None = None) -> dict:
    """What the queue item `key` (resolutions.parse_key) may be written as: {"rule": {...} | {"why_not"}, "definition":
    {...} | {"why_not"}}. A rule: a finding (finding_unconfirmed) of a warn rule on file with a field, and the company
    reads that field from at least one line; it names the rule, the field and those lines. A definition: a block of
    xbrl_reconcile on revenue or opex (the definition says the SEC's tag measures something else), or of
    cost_lines_summed (the lines are the company's cost of revenue), for a company with no such entry yet."""
    defs = definitions.load(DEF_FILE) if defs is None else defs
    rules = rules_mod.load(RULES_DIR) if rules is None else rules
    t, f, rid, kind = key.get("ticker") or "", key.get("field") or "", key.get("rule_id") or "", key.get("kind") or ""
    by_id = {r["id"]: r for r in rules}
    out = {}
    target = by_id.get(rid)
    if kind != "finding_unconfirmed" or not f:
        out["rule"] = {"why_not": "only a rule's finding on a field can be written as a rule"}
    elif not target or target["check"] == "explains" or target["severity"] != "warn":
        out["rule"] = {"why_not": f"{rid or 'this finding'} is not a warn rule in rules/; only a warn finding is explained by a rule"}
    else:
        labels = _labels(con, t, f)
        if not labels:
            out["rule"] = {"why_not": f"{t} reads {f} from no line, so a rule could name nothing; a rule never matches by pattern"}
        else:
            nid = rule_id(rid, f, labels)
            out["rule"] = {"id": nid, "rule": rid, "field": f, "row_labels": labels, "title": target.get("title") or rid}
            if nid in by_id:
                out["rule"]["why_not"] = f"already on file: rules/{nid}.yaml; rerun ledger rules"
    dk = None
    if kind == "blocked" and rid == "xbrl_reconcile" and f in ("revenue", "opex"):
        dk = f
    elif kind == "blocked" and rid == "cost_lines_summed":
        dk = "cost_lines"
    if not dk:
        out["definition"] = {"why_not": "a definition settles an XBRL disagreement on revenue or opex, or names the cost lines; this item is neither"}
    elif dk in (defs.get(t) or {}):
        out["definition"] = {"kind": dk, "why_not": f"{t} already has a {dk} definition in definitions/companies.yaml; edit it by hand"}
    else:
        out["definition"] = {"kind": dk, "ticker": t}
        if dk == "cost_lines":
            lines = _labels(con, t, "cost_of_revenue_part")
            out["definition"]["lines"] = lines
            if not lines:
                out["definition"]["why_not"] = f"{t} has no cost lines read; nothing to name"
    return out


def encode(con, key: str, as_: str, why: str, by: str, defs_path: Path | None = None, rules_dir: Path | None = None, at: str | None = None) -> dict:
    """The route's one call: the person (refused first when not on config.PEOPLE), the item by its key, what it may
    become (`offers`, from the database), then the one writer. Raises ValueError and writes nothing on any refusal."""
    person(str(by or ""))
    if as_ not in ("rule", "definition"):
        raise ValueError("write it as a rule or as a definition")
    k = resolutions.parse_key(str(key or ""))
    if not k or k["kind"] not in resolutions.LIVE_KINDS:
        raise ValueError(f"not a queue item's key: {key!r}")
    o = offers(con, k, definitions.load(defs_path or DEF_FILE), rules_mod.load(rules_dir or RULES_DIR))[as_]
    if o.get("why_not"):
        raise ValueError(o["why_not"])
    if as_ == "rule":
        return write_rule(o["rule"], o["field"], o["row_labels"], why, by, source=key, rules_dir=rules_dir, at=at)
    return write_definition(k["ticker"], o["kind"], why, by, lines=o.get("lines"), path=defs_path, at=at)


# ── the definition writer ───────────────────────────────────────────────────────────────────────────────────────────
def write_definition(ticker: str, kind: str, why: str, by: str, lines: list[str] | None = None, path: Path | None = None, at: str | None = None) -> dict:
    """One entry in definitions/companies.yaml, in the file's own block format (`  <kind>:` then `    lines`, `why`,
    `by`, `at`), at the end of the ticker's block or in a new block at the end of the file; the comment header and every
    other entry untouched (mapper._edit compares the whole parsed file). Refused: a name not on config.PEOPLE, a kind
    definitions.load does not accept, an empty reason, lines on anything but cost_lines (and none on it), an entry
    already there."""
    p = path or DEF_FILE
    ticker, kind, why, by = str(ticker or "").strip().upper(), str(kind or "").strip(), _one_line(why), person(str(by or ""))
    if not TICKER.fullmatch(ticker):
        raise ValueError(f"{ticker!r} is not a ticker")
    if kind not in DEFINITION_KINDS:
        raise ValueError(f"a definition is one of {DEFINITION_KINDS}, not {kind!r}")
    if not why:
        raise ValueError("a definition needs a reason: why the field means this for the company")
    if kind == "cost_lines":
        lines = [_one_line(l) for l in (lines or [])]
        if not lines or not all(lines):
            raise ValueError("a cost_lines definition names the lines")
    elif lines:
        raise ValueError(f"only cost_lines names lines, not {kind}")
    day = at or date.today().isoformat()
    entry = ({"lines": lines} if kind == "cost_lines" else {}) | {"why": why, "by": by, "at": day}
    text = [f"  {kind}:"] + ([f"    lines: [{', '.join(json.dumps(l) for l in lines)}]"] if kind == "cost_lines" else []) + [
        f"    why: {_scalar(why)}", f"    by: {_scalar(by)}", f"    at: {day}"]
    what = "definitions/companies.yaml"

    def change(ls: list[str], data: dict):
        if kind in (data.get(ticker) or {}):
            raise ValueError(f"{ticker} already has a {kind} definition; edit it by hand, nothing written")
        head = _ticker_line(ls, ticker, what)
        if head is None:
            while ls and not ls[-1].strip():
                ls.pop()
            ls += ["", f"{ticker}:", *text, ""]
        else:
            i = head + 1
            while i < len(ls) and (ls[i].startswith(" ") or not ls[i].strip()):
                i += 1
            while i > head + 1 and not ls[i - 1].strip():
                i -= 1
            ls[i:i] = text
        return ls, entry

    _edit(p, ticker, kind, change, what)
    definitions.load(p)  # the file as written still loads (it parsed in _edit; this runs the loader's own checks)
    return {"wrote": "definition", "file": what, "ticker": ticker, "kind": kind, **entry}


# ── the rule writer ─────────────────────────────────────────────────────────────────────────────────────────────────
def write_rule(target: str, field: str, row_labels: list[str], why: str, by: str, source: str = "", rules_dir: Path | None = None, at: str | None = None) -> dict:
    """One new file rules/<id>.yaml: an info `explains` rule naming the warn rule `target`, the `field` and the whole
    `row_labels` (rules._explains). The loader's checks run on it before anything is written, and the rule set is
    loaded before and after under one lock: the write must add exactly this rule and change no other file, or it is
    removed and refused. `by` must be a person on config.PEOPLE; `why` is their reason, kept as the rule's rationale."""
    d_ = Path(rules_dir or RULES_DIR)
    by, why = person(str(by or "")), _one_line(why)
    labels = sorted({_one_line(l): None for l in (row_labels or []) if _one_line(l)}, key=rules_mod.label_key)
    if not why:
        raise ValueError("a rule needs a reason: why these lines explain the finding")
    if not labels:
        raise ValueError("a rule names the lines it matches; with none it would match nothing, or everything")
    nid = rule_id(target, field, labels)
    day = at or date.today().isoformat()
    rule = {"id": nid, "severity": "info",
            "description": f"Explains a {target} finding on {field} wherever every line the field is read from is one this rule names.",
            "rationale": why, "owner": by, "check": "explains",
            "params": {"rule": target, "field": field, "condition": {"row_labels": labels}},
            "title": "A person's explanation, written once as a rule.", "plain": why,
            "action": "Nothing to decide: the explanation on file applies to every company whose lines it names.",
            "by": by, "why": why, "at": day, "source": source}
    text = yaml.safe_dump(rule, sort_keys=False, allow_unicode=True, width=120, default_flow_style=False)
    if yaml.safe_load(text) != rule:
        raise ValueError("the rule does not read back as written; nothing written")
    import fcntl
    lock = d_ / ".rules.lock"
    with open(lock, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            before = rules_mod.load(d_)  # the set on file must load as it is
            for r in before:
                p = r["params"]
                if r["check"] == "explains" and p["rule"] == target and p["field"] == field and \
                        {rules_mod.label_key(l) for l in p["condition"]["row_labels"]} == {rules_mod.label_key(l) for l in labels}:
                    raise ValueError(f"rules/{r['id']}.yaml already explains {target} on {field} for these lines; nothing written")
            dest = d_ / f"{nid}.yaml"
            if dest.exists():
                raise ValueError(f"rules/{nid}.yaml exists; nothing written")
            cand = copy.deepcopy(rule)
            rules_mod.check_rule(cand, dest.name)
            rules_mod._check_explains(before + [cand])
            fd, tmp = tempfile.mkstemp(dir=d_, prefix=f".{nid}.", suffix=".tmp")  # never *.yaml: the loader does not see it
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(text)
                os.replace(tmp, dest)
            except BaseException:
                if os.path.exists(tmp):
                    os.unlink(tmp)
                raise
            try:
                after = rules_mod.load(d_)
                was, now = {r["id"]: r["file_sha256"] for r in before}, {r["id"]: r["file_sha256"] for r in after}
                if set(now) != set(was) | {nid} or any(now[i] != h for i, h in was.items()):
                    raise ValueError("the rule set would change more than the one new rule; nothing written")
            except BaseException:
                dest.unlink(missing_ok=True)
                raise
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return {"wrote": "rule", "file": f"rules/{nid}.yaml", "id": nid, "rule": target, "field": field, "row_labels": labels, "by": by, "why": why, "at": day}
