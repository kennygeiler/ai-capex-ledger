"""Resolve by rule (T36): a person's explanation in Reconcile, written once as a definition or a rule, so the next run
closes the same cause without asking again.

Two writers, one discipline (ledger/safewrite.py: an exclusive fcntl lock, the change computed on what is on disk,
a temporary file moved into place with os.replace). `write_definition` adds one entry to definitions/companies.yaml
through mapper._edit, the T63 writer, which parses the whole file before and after and allows only that entry to
change. `write_rule` adds one file to rules/ (cross-company: an info-severity `explains` rule, rules._explains): the
rule set on file must load, the new file passes the loader's own checks before it is written, and the set is loaded
again after; anything but exactly the one new rule, with every other file's hash unchanged, removes it and refuses.
Both record `by` (a person on config.PEOPLE, mapper.person, fail closed), `why` and `at`; both files are tracked in
git like every judgement file, and nothing here commits. `by` is the name typed in the signer box: until T6 (auth)
it is a claim made on a trusted local machine, not proof of who pressed the button, as for resolutions and gold.

What may be written is decided here, from the queue item's key and the database, never from what the page sends
beyond the reason and the name (`offers`). A rule targets only a label-driven warn rule (rules.EXPLAINABLE:
row_label_switch, a finding about which line was read) and names exactly the lines the company's field is read
from; it explains a finding only where the company reads the field from that same set of lines, never a subset, a
superset or a pattern. A definition is offered only for a cause a definition settles, found on file for a tracked
company: an xbrl_reconcile block on revenue or opex in one year (the entry records `periods`, that year, and applies
to no other), or a cost_lines_summed block (the entry names the lines)."""
from __future__ import annotations

import copy
import hashlib
import json
import re
from datetime import date
from pathlib import Path

import yaml

from . import definitions, resolutions, rules as rules_mod
from .config import tracked
from .mapper import _edit, _scalar, _ticker_line, person
from .safewrite import safe_write

DEF_FILE = definitions.FILE
RULES_DIR = rules_mod.RULES_DIR
DEFINITION_KINDS = ("revenue", "opex", "cost_lines")  # what definitions.load accepts
TICKER = re.compile(r"[A-Z][A-Z0-9.\-]{0,9}")
NAME = re.compile(r"[a-z][a-z0-9_]*")  # a rule id or a field, as it may stand in a file name


def _day(at: str | None) -> str:
    """Today, or `at` when it is an ISO date (tests pin it); anything else is refused."""
    if at is None:
        return date.today().isoformat()
    try:
        return date.fromisoformat(str(at)).isoformat()
    except ValueError:
        raise ValueError(f"at must be an ISO date, not {at!r}") from None


def _finding_on_file(con, ticker: str, rule: str, field: str | None = None, period: str | None = None) -> bool:
    """A finding of `rule` for the ticker (and field, and period when given) is in `exceptions`: the item exists."""
    if not con.execute("select count(*) from information_schema.tables where table_name = 'exceptions'").fetchone()[0]:
        return False
    sql, args = "select count(*) from exceptions where ticker = ? and rule_id = ?", [ticker, rule]
    if field:
        sql, args = sql + " and field = ?", args + [field]
    if period:
        sql, args = sql + " and period = ?", args + [period]
    return bool(con.execute(sql, args).fetchone()[0])


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
    elif not target or target["check"] == "explains" or target["severity"] != "warn" or rid not in rules_mod.EXPLAINABLE:
        out["rule"] = {"why_not": f"{rid or 'this finding'} is not a label-driven warn rule ({', '.join(rules_mod.EXPLAINABLE)}); a rule never explains a value once for every year"}
    else:
        labels = _labels(con, t, f)
        if not labels:
            out["rule"] = {"why_not": f"{t} reads {f} from no line, so a rule could name nothing; a rule never matches by pattern"}
        else:
            nid = rule_id(rid, f, labels)
            out["rule"] = {"id": nid, "rule": rid, "field": f, "row_labels": labels, "title": target.get("title") or rid}
            if nid in by_id:
                out["rule"]["why_not"] = f"already on file: rules/{nid}.yaml; rerun ledger rules"
    dk, period = None, key.get("period") or ""
    if kind == "blocked" and rid == "xbrl_reconcile" and f in ("revenue", "opex") and period:
        dk = f
    elif kind == "blocked" and rid == "cost_lines_summed":
        dk = "cost_lines"
    if not dk:
        out["definition"] = {"why_not": "a definition settles an XBRL disagreement on revenue or opex in a year, or names the cost lines; this item is neither"}
    elif dk in (defs.get(t) or {}):
        out["definition"] = {"kind": dk, "why_not": f"{t} already has a {dk} definition in definitions/companies.yaml; edit it by hand"}
    elif t not in {c["ticker"] for c in tracked()}:
        out["definition"] = {"kind": dk, "why_not": f"{t} is not a tracked company"}
    elif not _finding_on_file(con, t, rid, f if dk != "cost_lines" else None, period if dk != "cost_lines" else None):
        out["definition"] = {"kind": dk, "why_not": f"no {rid} finding for {t} {f} {period} on file; rerun ledger rules"}
    else:
        out["definition"] = {"kind": dk, "ticker": t} | ({"periods": [period]} if dk != "cost_lines" else {})
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
    return write_definition(k["ticker"], o["kind"], why, by, lines=o.get("lines"), periods=o.get("periods"), path=defs_path, at=at)


# ── the definition writer ───────────────────────────────────────────────────────────────────────────────────────────
def write_definition(ticker: str, kind: str, why: str, by: str, lines: list[str] | None = None, periods: list[str] | None = None,
                     path: Path | None = None, at: str | None = None) -> dict:
    """One entry in definitions/companies.yaml, in the file's own block format (`  <kind>:` then `    lines` or
    `    periods`, `why`, `by`, `at`). A revenue or opex entry always records `periods`, the fiscal years of the item the
    person saw, and reconcile applies it to those years only (definitions._applies); a cost_lines entry is scoped by
    its lines. It goes at the end of the ticker's block or in a new block at the end of the file; the comment header and every
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
    if kind == "cost_lines" and periods:
        raise ValueError("a cost_lines definition is scoped by its lines, not by periods")
    if kind != "cost_lines" and (not periods or not all(isinstance(q, str) and definitions.PERIOD.fullmatch(q) for q in periods)):
        raise ValueError(f"a {kind} definition names the fiscal years it was written for (periods: [FY2024]); it never applies to every year")
    day = _day(at)
    scope = {"lines": lines} if kind == "cost_lines" else {"periods": list(periods)}
    entry = scope | {"why": why, "by": by, "at": day}
    text = [f"  {kind}:"] + ([f"    lines: [{', '.join(json.dumps(l) for l in lines)}]"] if kind == "cost_lines" else [f"    periods: [{', '.join(periods)}]"]) + [
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
    """One new file rules/<id>.yaml: an info `explains` rule naming the label-driven warn rule `target`, the `field` and
    exactly the `row_labels` (rules._explains). Through safewrite.safe_write under a lock on the directory: the rule set
    on file must load, the loader's checks run on the new rule before anything is written, and after the write the set
    is loaded again; anything but exactly this one new rule, with every other file's hash unchanged, removes it and
    refuses. `by` must be a person on config.PEOPLE; `why` is their reason, kept as the rule's rationale."""
    d_ = Path(rules_dir or RULES_DIR)
    by, why = person(str(by or "")), _one_line(why)
    target, field = str(target or ""), str(field or "")
    if not NAME.fullmatch(target) or not NAME.fullmatch(field):
        raise ValueError(f"a rule id and a field are lower-case names, not {target!r} and {field!r}")
    labels = sorted({_one_line(l): None for l in (row_labels or []) if _one_line(l)}, key=rules_mod.label_key)
    if not why:
        raise ValueError("a rule needs a reason: why these lines explain the finding")
    if not labels:
        raise ValueError("a rule names the lines it matches; with none it would match nothing, or everything")
    nid = rule_id(target, field, labels)
    day = _day(at)
    rule = {"id": nid, "severity": "info",
            "description": f"Explains a {target} finding on {field} wherever the field is read from exactly the lines this rule names.",
            "rationale": why, "owner": by, "check": "explains",
            "params": {"rule": target, "field": field, "condition": {"row_labels": labels}},
            "title": "A person's explanation, written once as a rule.", "plain": why,
            "action": "Nothing to decide: the explanation on file applies to every company that reads the field from exactly these lines.",
            "by": by, "why": why, "at": day, "source": source}
    text = yaml.safe_dump(rule, sort_keys=False, allow_unicode=True, width=120, default_flow_style=False)
    if yaml.safe_load(text) != rule:
        raise ValueError("the rule does not read back as written; nothing written")
    dest, state = d_ / f"{nid}.yaml", {}

    def mutate(old):
        if old is not None:
            raise ValueError(f"rules/{nid}.yaml exists; nothing written")
        before = rules_mod.load(d_)  # the set on file must load as it is
        keys = {rules_mod.label_key(l) for l in labels}
        for r in before:
            p = r["params"]
            if r["check"] == "explains" and p["rule"] == target and p["field"] == field and {rules_mod.label_key(l) for l in p["condition"]["row_labels"]} == keys:
                raise ValueError(f"rules/{r['id']}.yaml already explains {target} on {field} for these lines; nothing written")
        cand = copy.deepcopy(rule)
        rules_mod.check_rule(cand, dest.name)
        rules_mod._check_explains(before + [cand])
        state["before"] = {r["id"]: r["file_sha256"] for r in before}
        return text

    def verify():
        now = {r["id"]: r["file_sha256"] for r in rules_mod.load(d_)}
        was = state["before"]
        if set(now) != set(was) | {nid} or any(now[i] != h for i, h in was.items()):
            raise ValueError("the rule set would change more than the one new rule; nothing written")

    safe_write(dest, d_ / ".rules.lock", mutate, verify)
    return {"wrote": "rule", "file": f"rules/{nid}.yaml", "id": nid, "rule": target, "field": field, "row_labels": labels, "by": by, "why": why, "at": day}
