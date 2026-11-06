"""One definition of open (T1, docs/PROOF.md). Proof, Reconcile, the trail and the Release gates all read it.

A row of the dataset (a value, a fact, a statement, a reported asset type, a filing, a rule's finding) is in exactly one
of four states:

  checked    it agrees with an independent check: the SEC's XBRL (values, facts), a quote verified against the text it
             came from (statements, planned rows), a statement table located in the filing (ingest), a reported asset
             type mapped to a us-gaap member with the note's words as evidence and confirmed by a person (mapping, T63:
             an entry without `confirmed_by` is a proposal and stays open, `label:to_confirm`).
  explained  it does not match, and something on file says why, by name: a definition (definitions/companies.yaml), an
             info-severity rule or a guard (rules/*.yaml, proof.GUARDS), a label reconcile wrote because the filing has
             no such line or XBRL has no such tag (not_reported, no_reference; docs/FIELDS.md), or a person's resolution
             that says accept or explain (decisions/resolutions.jsonl).
  blocked    a block-severity rule fired on it, or a person's resolution says blocks. Blocked is open that also refuses
             the release; every count of open includes it.
  open       none of the above, or a person's resolution says fix. The only thing a person looks at.

Precedence when more than one applies: blocked, then checked, then a person's fix (open), then explained, then open.
A warn-severity rule finding (a jump, a renamed line, an outlier) has no state of its own: it takes the worst state of
the rows it fired on. A jump on a value XBRL confirms is checked; on a value a definition covers, explained; on an
unresolved value, open. So Proof and Reconcile count the same row the same way: a rule or a definition on file closes
it on both pages, and a person's decision is needed only where nothing on file applies.

`by` names what decided the state: xbrl | esef:<tag> | source:<doc> | actual:<period> | reading:<accession> | quote | located | gate |
mapping:<us-gaap member> | mapping:filer_tag | rule:<id> (a tie rule's id ends in _tie) | definition:<name> | label:<not_reported|no_reference> |
resolution:<id>. Empty when the state is open and nothing applies; label:not_extracted names an open value's cause (T65).
`gate` is the release stage's one item when no block rule fired and no decision blocks (T80: it used to say `located`).

A label never counts as a check (T80, `evidence_gap`): a checked or explained row's `by` must name a record that exists
and says so. The record a check rests on travels with the row as `ref` (proof.company sets it), and `evidence_gap`
returns why it does not hold, or None.

Answer keys (T40, docs/PROOF.md): five kinds of independent check vouch for a number (the fifth, a second reading, T92). A structured twin (xbrl, esef:
the filer's own tagged number), a second source (source: another document by the same filer), an arithmetic tie
(rule:<id>_tie: numbers that must sum or bound; a tie that holds is a check, a tie that fails is the rule's finding),
a later truth (actual: the actual against the plan), a second reading (reading:<accession>: an untagged note figure the
filer's next 10-K prints the same, T92). `answer_key(by)` names the kind; quote, located, mapping and the
explanations are not answer keys.

Key grades (T56): the keys are not equally independent of the row they vouch for. KEY_GRADE ranks them, strongest
first; `state()` carries `keys` (every answer key that agreed with the row) and `key` (the strongest of them), so Proof
counts rows by the strength of what vouches for them and a trail names it. A row today carries one `by`, so `keys` holds
at most one; T41–T43 add ties, second sources and later truths beside the twin without a change to the shape."""
from __future__ import annotations

import re

STATES = ("checked", "explained", "open", "blocked")
# The kinds of `by`, and of the taxonomy rows' `check_method` (store.TAXONOMY): an open vocabulary of `<kind>` or
# `<kind>:<id>`. esef:<tag>, source:<doc> and actual:<period> are the answer keys T41–T45 will write; no row carries
# them yet (2 Nov 2026).
METHOD_KINDS = ("xbrl", "esef", "source", "actual", "reading", "quote", "gathered", "located", "gate", "none", "mapping", "rule", "definition", "resolution", "label")
# The answer keys and the `by` kinds that carry each. A tie is a rule whose id ends in TIE (rule:quarters_tie,
# rule:statement_tie); any other rule:<id> explains or blocks, it is not an answer key.
# T92: a second reading (reading:<accession>) is the same untagged note figure printed by another 10-K of the same filer
# (the next 10-K's comparative column) and agreeing with it; the weakest key, below the tie (docs/PROOF.md, "The ladder").
ANSWER_KEYS = {"twin": ("xbrl", "esef"), "second_source": ("source",), "tie": ("rule",), "later_truth": ("actual",), "second_reading": ("reading",)}
TIE = "_tie"
# The keys in strength order (T56): how independent each is of the number it vouches for, strongest first.
KEY_GRADE = ("twin", "second_source", "tie", "later_truth", "second_reading")
KEY_WHY = {
    "twin": "a separate preparer's machine-readable instance: the filer tagged the number for a different reader, by a different process, from the text the pipeline read",
    "second_source": "the same issuer's other document: the same finance team wrote both, so an error upstream of both documents is shared",
    "tie": "arithmetic inside the same document: the parts and the whole agree, which shows consistent reading, not a right number",
    "later_truth": "a later period's actual against the plan: the actual can itself be restated, and it proves the plan, not the reading",
    "second_reading": "the same filer's next 10-K printing the same figure: usually the table carried forward by the same preparer and read by the same reader, so it rules out a one-off misread, nothing upstream",
}
KEY_LABEL = {"twin": "twin", "second_source": "second source", "tie": "tie", "later_truth": "later truth", "second_reading": "second reading"}


def grade(key: str | None) -> int:
    """The rank of an answer key, 0 strongest; len(KEY_GRADE) for no key, so min() over keys picks the strongest."""
    return KEY_GRADE.index(key) if key in KEY_GRADE else len(KEY_GRADE)


def strongest(keys) -> str | None:
    """The strongest answer key among `keys` (a list of key names, Nones ignored), or None when none is a key."""
    ks = [k for k in keys if k in KEY_GRADE]
    return min(ks, key=grade) if ks else None


def method_kind(by: str) -> str:
    return by.partition(":")[0]


def answer_key(by: str) -> str | None:
    """The answer-key kind behind a `by` (or a check_method): twin | second_source | tie | later_truth, or None when the
    method is not an answer key (a quote, a located table, a mapping, an explanation, nothing)."""
    if by == FILER_TAG:  # the company's own tag for a category mapping (ledger/checks/filertag.py): the filer's instance, a twin
        return "twin"
    kind = method_kind(by or "")
    for key, kinds in ANSWER_KEYS.items():
        if kind in kinds and (kind != "rule" or by.endswith(TIE)):
            return key
    return None


ORDER = {"blocked": 0, "open": 1, "explained": 2, "checked": 3}  # worst first
CHECKS = ("xbrl", "quote", "located", "gate", "mapping")  # the bare checks; the keyed ones (esef:, source:, rule:*_tie, actual:) go through answer_key
REASONS = {"xbrl": "agrees with the SEC's XBRL", "esef": "agrees with the filer's own ESEF tag", "source": "agrees with a second document by the same filer",
           "reading": "read the same in two or more of the filer's 10-Ks",
           "rule": "the tie holds", "actual": "the actual for the period, against the plan", "quote": "a verbatim quote, verified against its text",
           "located": "statement tables located in the filing", "gate": "no block rule fired and no decision blocks", "mapping": "mapped to a us-gaap member with the note's words"}
GUARD_IDS = ("part_year", "program_words", "asset_type_mapping", "restated_between_filings", "amendment_without_statements")  # proof.GUARDS: info by nature


def _res(resolution: dict | None) -> tuple[str, str, str]:
    if not resolution:
        return "", "", ""
    rid = resolution.get("id") or ""
    return resolution.get("state") or "", f"resolution:{rid}" if rid else "resolution", (resolution.get("reason") or "")[:200]


def keyed(st: dict) -> dict:
    """`st` with `keys` (every answer key that vouches for a checked row; a `by` carries one today) and `key` (the
    strongest, KEY_GRADE). Only a checked row has keys: a failed tie's `rule:<id>_tie` is a finding, not a key."""
    keys = [k for k in [answer_key(st.get("by") or "")] if k] if st.get("state") == "checked" else []
    return {**st, "keys": keys, "key": strongest(keys)}


def state(row: dict) -> dict:
    """The one function. `row` carries what is known about a dataset row, every key optional:
    check: xbrl | quote | located | mapping (what vouches for it); mapping_to: the us-gaap member when check is mapping;
           or a keyed answer key that agreed: esef:<tag> | source:<doc> | rule:<id>_tie | actual:<period> (T40). A tie
           that fails is not a check: it is the rule's finding (`rule`, `severity`), open until something explains it.
    rule, severity: the rule or guard that fired on it (block | warn | info; a guard counts as info)
    definition: the name of the definition on file that covers it
    label: a reconcile label (not_reported, no_reference) that explains it
    resolution: the person's latest resolution on it, {id, state, reason}
    Returns {"state", "reason", "by", "keys", "key"}: keys = the answer keys that vouch for a checked row, key = the
    strongest (T56); [] and None otherwise."""
    return keyed(_state(row))


def _state(row: dict) -> dict:
    rs, rby, rreason = _res(row.get("resolution"))
    rule, sev = row.get("rule"), row.get("severity") or ("info" if row.get("rule") in GUARD_IDS else None)
    if rs == "blocks":
        return {"state": "blocked", "reason": rreason or "a person's decision blocks the release", "by": rby}
    if rule and sev == "block":
        return {"state": "blocked", "reason": row.get("reason") or f"rule {rule} blocks the release", "by": f"rule:{rule}"}
    check = row.get("check") or ""
    if check in CHECKS or answer_key(check):
        by = f"mapping:{row.get('mapping_to') or ''}" if check == "mapping" else check
        return {"state": "checked", "reason": row.get("reason") or REASONS[method_kind(check)], "by": by}
    if rs == "fix":
        return {"state": "open", "reason": rreason or "a person said fix; open until fixed", "by": rby}
    if rs in ("accept", "explain"):
        return {"state": "explained", "reason": rreason or f"a person said {rs}", "by": rby}
    if row.get("definition"):
        return {"state": "explained", "reason": row.get("reason") or f"a definition on file: {row['definition']}", "by": f"definition:{row['definition']}"}
    if rule and sev == "info":
        return {"state": "explained", "reason": row.get("reason") or f"rule {rule} says why", "by": f"rule:{rule}"}
    if row.get("label") in ("not_reported", "no_reference"):
        return {"state": "explained", "reason": row.get("reason") or {"not_reported": "the company reports no such line", "no_reference": "no XBRL tag to compare"}[row["label"]], "by": f"label:{row['label']}"}
    return {"state": "open", "reason": row.get("reason") or (f"rule {rule} fired and nothing on file says why" if rule else "neither checked nor explained"),
            "by": f"rule:{rule}" if rule else f"label:{row['label']}" if row.get("label") else ""}


FILER_TAG = "mapping:filer_tag"  # filertag.FILER_TAG: a mapping checked by the company's own tag


NOT_A_PERSON = re.compile(r"\b(claude|fable|opus|sonnet|haiku|gemini|gpt|agent|run|replication|model|bot)\b", re.I)


def is_person(name) -> bool:
    """A name that stands behind a row (T80): on config.PEOPLE and naming no model, agent or run. Fail closed: a name
    not on the list is not a person here, whatever it looks like."""
    from .config import PEOPLE
    n = str(name or "").strip()
    return bool(n) and n in PEOPLE and not NOT_A_PERSON.search(n)


def confirmed(entry: dict | None) -> bool:
    """T63: an asset-type mapping (an entry of taxonomy/asset_types.yaml) is a person's only when it carries a
    `confirmed_by` that is a person (T80, `is_person`: on config.PEOPLE, no model or agent name; a hand edit
    `confirmed_by: Claude` does not count). `by` says who wrote it (a model, for the 47 entries of 1 Nov 2026),
    `confirmed_by` who stands behind it."""
    return bool(entry) and is_person(entry.get("confirmed_by"))


UNMAPPED = "a reported PP&E category with no entry in taxonomy/asset_types.yaml"


def of_mapping(entry: dict | None, tag: dict | None = None) -> dict:
    """A reported asset type (the mapping stage, T63): checked by the mapping when a person confirmed it; else checked by
    `mapping:filer_tag` when the company's own XBRL tags the category with exactly the proposed member, unambiguously
    (`tag` is filertag.verdicts' verdict for the category; filertag.verified); open, by `label:to_confirm`, when the entry
    is a proposal neither confirms (Reconcile's asset types group, Approve / Choose another / Reject); open with nothing
    when there is no entry. A person's confirmation comes first: it stands whatever the company tags."""
    from ..checks.filertag import verified
    member = (entry or {}).get("standard_type")
    if not member:
        return state({"reason": UNMAPPED})
    if confirmed(entry):
        return state({"check": "mapping", "mapping_to": member, "reason": f"mapped to {member} with the note's words, confirmed by {entry['confirmed_by']}"})
    if verified(entry, tag):
        return state({"check": "mapping", "mapping_to": "filer_tag", "reason": f"{member}: the company's own XBRL tags the category's value with it, one member, in every extracted year"})
    return state({"label": "to_confirm", "reason": f"{member} proposed by {entry.get('by') or 'nobody named'}; no person has confirmed it"})


def worst(states: list[dict]) -> dict | None:
    return min(states, key=lambda s: ORDER[s["state"]]) if states else None


def is_open(s: dict) -> bool:
    """Open for a person: open or blocked."""
    return s["state"] in ("open", "blocked")


# ── how each kind of row maps onto `state` (one place, so Proof and Reconcile read the same thing) ──────────────────
def of_value(v: dict, resolution: dict | None = None, ref: dict | None = None) -> dict:
    """A `values` row: label agree → checked by XBRL; definition_gap → the definition (cost lines for opex, the revenue
    line otherwise); no_reference → explained by reconcile's label; not_reported → explained only when `ref` says XBRL
    was looked up and holds nothing ({reference: None, looked_up: True}, T80's marker), else open by label:not_reported
    (T81: XBRL holds a value, or nobody asked; one verdict per cell with the completeness line and `coverage`);
    not_extracted → open, by the label (the filing tags a value the reader did not extract); unresolved → open unless a
    person resolved it."""
    label = v.get("label")
    row = {"resolution": resolution}
    if label == "not_reported" and not (ref and ref.get("looked_up") and ref.get("reference") is None):
        why = f"labelled not_reported while XBRL holds {ref['reference']}" if ref and ref.get("reference") is not None else "labelled not_reported, XBRL not looked up"
        st = state({**row, "reason": why})
        return {**st, "by": st["by"] or "label:not_reported"}
    if label == "agree":
        row["check"] = "xbrl"
    elif label == "definition_gap":
        row["definition"] = "cost_lines" if v.get("field") == "opex" else "revenue"
    elif label in ("not_reported", "no_reference"):
        row["label"] = label
    elif label == "not_extracted":  # T65: no cell read while XBRL tags a value; the label names the cause, it explains nothing
        row |= {"label": label, "reason": "the filing tags a value the reader did not extract"}
    return state(row)


DIFFER = "fact_readings_differ"  # ties.DIFFER; the rule (rules/fact_readings_differ.yaml) whose finding opens an untagged fact read two ways


def of_fact(f: dict, resolution: dict | None = None, restated: str | None = None, differ: str | None = None,
            tie: str | None = None, reading: str | None = None, filer: bool = False, looked_up: bool = True) -> dict:
    """A `facts` row: label agree → checked by XBRL; unresolved → the restatement guard when the cell and the tag come
    from different filings (`restated` is that finding's text), else open unless resolved. no_reference (no XBRL value)
    climbs the ladder (T92, ledger/checks/ties.py): readings across filings that differ (`differ`, the finding's text) → open by
    rule:fact_readings_differ, explained only by a person's resolution, never by the label; else, for a PP&E category
    the company's own tag checks (`filer`, ledger/checks/filertag.py), checked by mapping:filer_tag: the filing's instance tags
    this very value with the category's member, a twin, so it is never "no XBRL to compare"; else a tie that holds for its
    filing's group (`tie`, the rule id) → checked by rule:<id>_tie; else two or more filings agreeing (`reading`, the
    other filing's accession) → checked by reading:<accession>; else the label, explained, citation only, but only when
    the filing's XBRL instance was loaded (`looked_up`, proof.instance_on_file): without it the empty tag is no answer, and
    the fact is open by label:not_looked_up, "XBRL instance not loaded" (F17)."""
    label = f.get("label")
    row = {"resolution": resolution}
    if label == "agree":
        row["check"] = "xbrl"
    elif label == "no_reference" and differ:
        row |= {"rule": DIFFER, "severity": "warn", "reason": differ}
    elif label == "no_reference" and filer:  # the category's value is in the company's own instance under its mapped member
        row |= {"check": "mapping", "mapping_to": "filer_tag", "reason": "the company's own XBRL tags this value with the category's member"}
    elif label == "no_reference" and tie:
        row |= {"check": f"rule:{tie}", "reason": "the parts sum to the filing's tagged total"}
    elif label == "no_reference" and reading:
        row |= {"check": f"reading:{reading}"}
    elif label == "no_reference" and not looked_up:
        row |= {"label": "not_looked_up", "reason": "the filing's XBRL instance was not loaded: the tag lookup did not run"}
    elif label == "no_reference":
        row["label"] = "no_reference"
    elif restated:
        row |= {"rule": "restated_between_filings", "reason": restated}
    return state(row)


def of_exception(e: dict, resolution: dict | None = None, rows: list[dict] | None = None, explained_by: str | None = None) -> dict:
    """A rule's finding (an `exceptions` row): block → blocked; info → explained; warn → the worst state of the rows it
    fired on (`rows`, already through of_value / of_fact), or open when it fired on nothing the dataset holds.
    `explained_by` (T36, rules.explained): the id of an info `explains` rule on file that names this finding; it
    explains a warn finding whose rows are open, after a person's decision and never over a blocked or checked row
    (the precedence above), and never one that fired on no value row."""
    sev = e.get("severity")
    if sev in ("block", "info"):
        return state({"rule": e.get("rule_id"), "severity": sev, "reason": (e.get("message") or "")[:200], "resolution": resolution})
    rs, rby, rreason = _res(resolution)
    if rs == "blocks":
        return keyed({"state": "blocked", "reason": rreason, "by": rby})
    if rs == "fix":
        return keyed({"state": "open", "reason": rreason, "by": rby})
    if rs in ("accept", "explain"):
        return keyed({"state": "explained", "reason": rreason, "by": rby})
    w = worst(rows or [])
    if explained_by and w is not None and w["state"] == "open":  # a finding on no value row stays open: nothing the person saw
        return state({"rule": explained_by, "severity": "info", "reason": f"rule {explained_by} explains this {e.get('rule_id')} finding"})
    if w:
        return keyed({**w, "reason": f"{e.get('rule_id')}: {w['reason']}"})
    return state({"rule": e.get("rule_id"), "severity": "warn", "reason": (e.get("message") or "")[:200]})



# ── T80: a label never counts as a check ────────────────────────────────────────────────────────────────────────────
EXPLAINING_LABELS = ("not_reported", "no_reference")  # the only labels that explain, and only when XBRL was looked up and holds no value
KEY_FIELD = {"esef": "esef", "source": "source", "actual": "actual", "rule": "tie", "reading": "readings"}  # each answer key's own value on `ref`; xbrl reads `reference`


def evidence_gap(item: dict, ev: dict) -> str | None:
    """Why a checked or explained `item` (a state with `by` and `ref`, as proof.company makes it) is not backed by the
    record its `by` names, or None when it is (or when the item is open or blocked: an open row claims nothing).

    `ref` is the record the check rests on: {reference, looked_up} the XBRL value and whether the lookup ran (True only
    when the answer key was loaded for that row: reference_values for the ticker, the filing's instance for a fact);
    {esef | source | actual | tie} the other answer keys' own values; {text_id} the text a quote must be in, with `ev`
    supplying the quote; {income_tables, cash_flow_tables} a filing's located tables; {stage, blocks} the release
    stage's block items; {ticker, name} a reported asset type; {ticker} for a definition. `ev` holds what is on file:
    definitions {ticker: {name: entry}}, rules {id: severity} (the rules/*.yaml ids and the guards, info), resolutions
    {id: line}, person_ids (the resolution ids a person wrote), asset_types {ticker: {name: entry}}, text(text_id) -> the
    text normalised or None, and quote(item) -> the quotes on file for the item's row (a list).

    What counts: checked by xbrl: an XBRL value on the row; by esef / source / actual / a tie: that key's own value,
    never the XBRL one; quote: the quote found in its text, normalised; located: both statement tables named; gate:
    the release stage with no block item; mapping:<member>: the entry has that member and a person's confirmed_by; mapping:filer_tag: the company tag recorded on the row
    (`ref.filer_tag`) is the one recomputed from disk (`ev["filer_tags"]`) and is the entry's member (filertag.gap);
    definition:<name>: the ticker's entry by that name; rule:<id>: a rule on file of info severity, or a guard;
    resolution:<id>: a line with that id a person wrote; label:not_reported or label:no_reference: XBRL looked up and
    holding no value. Any other label explains nothing, and a missing lookup marker is a gap, never an empty answer."""
    if item.get("state") not in ("checked", "explained"):
        return None
    by, ref = item.get("by") or "", item.get("ref") or {}
    kind, _, ident = by.partition(":")
    if not by:
        return "names no evidence"
    if by == FILER_TAG:
        if item["state"] != "checked":
            return f"{by}: an answer key checks, it does not explain"
        from ..checks.filertag import gap
        tags = ev.get("filer_tags")
        if tags is None:
            return f"{by}: no company tags on file to check against"
        name = ref.get("name") or ref.get("dimension")  # a mapping item, or a fact of the category (of_fact's filer)
        e = (ev["asset_types"].get(ref.get("ticker")) or {}).get(name)
        return gap(ref, e, tags.get((ref.get("ticker"), name)))
    if answer_key(by):
        if item["state"] != "checked":
            return f"{by}: an answer key checks, it does not explain"
        if kind == "xbrl":
            return None if ref.get("looked_up") and ref.get("reference") is not None else f"{by}: no XBRL value on the row"
        field = KEY_FIELD.get(kind)
        if not field or ref.get(field) is None:
            return f"{by}: no {field or kind} value on the row"
        if kind == "rule":
            return _tie_gap(by, ident, ref, ev) if isinstance(ref["tie"], dict) else f"{by}: the tie on the row names no group"
        if kind == "reading":
            return _reading_gap(by, ref, ev)
        return None
    if kind == "quote":
        text = ev["text"](ref.get("text_id")) if ref.get("text_id") else None
        if text is None:
            return f"quote: no text on file for {ref.get('text_id')!r}"
        qs = [norm(q or "") for q in ev["quote"](item) or []]
        if not qs or not all(qs):
            return f"quote: no quote on file for the row in {ref['text_id']}"
        return None if all(q in text for q in qs) else f"quote: not found in {ref['text_id']}"
    if kind == "located":
        return None if ref.get("income_tables") and ref.get("cash_flow_tables") else "located: no income and cash-flow table named on the filing"
    if kind == "gate":
        if ref.get("stage") != "release":
            return f"gate: only the release stage has a gate, not {ref.get('stage') or 'an unnamed stage'}"
        return None if ref.get("blocks") == 0 else "gate: the release stage holds block items, or nobody counted them"
    if kind == "mapping":
        e = (ev["asset_types"].get(ref.get("ticker")) or {}).get(ref.get("name")) or {}
        if not e:
            return f"{by}: no entry for {ref.get('ticker')} {ref.get('name')!r} in taxonomy/asset_types.yaml"
        if e.get("standard_type") != ident:
            return f"{by}: the entry maps to {e.get('standard_type')}"
        if not str(e.get("confirmed_by") or "").strip():
            return f"{by}: the entry has no confirmed_by"
        return None if is_person(e["confirmed_by"]) else f"{by}: confirmed_by {e['confirmed_by']!r} is not a person on config.PEOPLE"
    if kind == "definition":
        return None if ident in (ev["definitions"].get(ref.get("ticker")) or {}) else f"{by}: no such definition for {ref.get('ticker')} in definitions/companies.yaml"
    if kind == "rule":
        sev = ev["rules"].get(ident)
        if sev is None:
            return f"{by}: no such rule in rules/*.yaml or proof.GUARDS"
        if ident in (ev.get("explains_by") or {}) and not is_person(ev["explains_by"][ident]):
            return f"{by}: an explains rule written by {ev['explains_by'][ident]!r}, not a person on config.PEOPLE"
        return None if sev == "info" else f"{by}: a {sev} rule explains nothing"
    if kind == "resolution":
        if ident not in ev["resolutions"]:
            return f"{by}: no such resolution in decisions/resolutions.jsonl"
        return None if ident in ev["person_ids"] else f"{by}: written by {ev['resolutions'][ident].get('by')!r}, not a person on config.PEOPLE"
    if kind == "label":
        if ident not in EXPLAINING_LABELS:
            return f"{by}: a bare label explains nothing"
        if not ref.get("looked_up"):
            return f"{by}: XBRL was not looked up for this row"
        return None if ref.get("reference") is None else f"{by}: XBRL holds {ref['reference']}"
    return f"{by}: not a kind of evidence"


def _tie_gap(by: str, rule_id: str, ref: dict, ev: dict) -> str | None:
    """T92: a tie checks a part only when its filing's group ties on file. The groups on file (`ev["ties"]`,
    proof.evidence recomputes them) are required; the row's `ref.tie` names its group, which must exist under the same
    rule, hold there with the on-file tolerance (never the row's), carry the same sum and total, and hold the part."""
    t = ref["tie"]
    groups = ev.get("ties")
    if groups is None:
        return f"{by}: no tie groups on file to check against"
    if t.get("rule") != rule_id:
        return f"{by}: the tie on the row is {t.get('rule')!r}"
    g = groups.get(t.get("key"))
    if not g:
        return f"{by}: no group {t.get('key')!r} on file"
    if g["rule"] != rule_id or abs(g["sum"] - g["total"]) > g["tolerance"] or not g["holds"]:
        return f"{by}: on file the group's parts sum to {g['sum']} against {g['concept']} {g['total']}: it does not tie"
    if (t.get("sum"), t.get("total")) != (g["sum"], g["total"]):
        return f"{by}: the row's tie ({t.get('sum')} against {t.get('total')}) is not the group on file"
    if (ref.get("dimension") or "") not in g["dimensions"]:
        return f"{by}: {ref.get('dimension')!r} is not a part of the group"
    return None


def _reading_gap(by: str, ref: dict, ev: dict) -> str | None:
    """T92: a second reading needs two or more lineages (a later fiscal year's 10-K; a 10-K/A folds into the 10-K it
    amends) whose readings agree (ties.corroborated), the `by` accession among them, and, when `ev` holds the readings
    on file (`ev["readings"]`, proof.evidence), the same readings."""
    from ..checks.ties import corroborated, lineages
    rs = ref["readings"]
    if len(lineages(rs)) < 2:
        return f"{by}: fewer than two filings read it (an amendment is its original's filing)"
    if not corroborated(rs):
        return f"{by}: the readings differ"
    if by.partition(":")[2] not in {r.get("accession") for r in rs}:
        return f"{by}: the accession it names is not one of the row's readings"
    on_file = ev.get("readings")
    if on_file is not None:
        k = (ref.get("ticker"), ref.get("field"), ref.get("dimension") or "", ref.get("period"))
        if [(r["accession"], r["value"]) for r in on_file.get(k) or []] != [(r.get("accession"), r.get("value")) for r in rs]:
            return f"{by}: the readings on the row are not the ones on file"
    return None


def norm(s: str) -> str:
    """Text normalised the way the loaders compare a quote with its passage (guidance._norm): quotes straightened,
    whitespace collapsed, lower case."""
    return re.sub(r"[\s\u00a0]+", " ", s.replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')).strip().lower()
