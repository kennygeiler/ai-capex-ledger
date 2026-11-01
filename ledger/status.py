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

`by` names what decided the state: xbrl | esef:<tag> | source:<doc> | actual:<period> | quote | located |
mapping:<us-gaap member> | rule:<id> (a tie rule's id ends in _tie) | definition:<name> | label:<not_reported|no_reference> |
resolution:<id>. Empty when the state is open and nothing applies; label:not_extracted names an open value's cause (T65).

Answer keys (T40, docs/PROOF.md): four kinds of independent check vouch for a number. A structured twin (xbrl, esef:
the filer's own tagged number), a second source (source: another document by the same filer), an arithmetic tie
(rule:<id>_tie: numbers that must sum or bound; a tie that holds is a check, a tie that fails is the rule's finding),
a later truth (actual: the actual against the plan). `answer_key(by)` names the kind; quote, located, mapping and the
explanations are not answer keys.

Key grades (T56): the four keys are not equally independent of the row they vouch for. KEY_GRADE ranks them, strongest
first; `state()` carries `keys` (every answer key that agreed with the row) and `key` (the strongest of them), so Proof
counts rows by the strength of what vouches for them and a trail names it. A row today carries one `by`, so `keys` holds
at most one; T41–T43 add ties, second sources and later truths beside the twin without a change to the shape."""
from __future__ import annotations

STATES = ("checked", "explained", "open", "blocked")
# The kinds of `by`, and of the taxonomy rows' `check_method` (store.TAXONOMY): an open vocabulary of `<kind>` or
# `<kind>:<id>`. esef:<tag>, source:<doc> and actual:<period> are the answer keys T41–T45 will write; no row carries
# them yet (2 Nov 2026).
METHOD_KINDS = ("xbrl", "esef", "source", "actual", "quote", "gathered", "located", "none", "mapping", "rule", "definition", "resolution", "label")
# The four answer keys and the `by` kinds that carry each. A tie is a rule whose id ends in TIE (rule:quarters_tie,
# rule:statement_tie); any other rule:<id> explains or blocks, it is not an answer key.
ANSWER_KEYS = {"twin": ("xbrl", "esef"), "second_source": ("source",), "tie": ("rule",), "later_truth": ("actual",)}
TIE = "_tie"
# The four keys in strength order (T56): how independent each is of the number it vouches for, strongest first.
KEY_GRADE = ("twin", "second_source", "tie", "later_truth")
KEY_WHY = {
    "twin": "a separate preparer's machine-readable instance: the filer tagged the number for a different reader, by a different process, from the text the pipeline read",
    "second_source": "the same issuer's other document: the same finance team wrote both, so an error upstream of both documents is shared",
    "tie": "arithmetic inside the same document: the parts and the whole agree, which shows consistent reading, not a right number",
    "later_truth": "a later period's actual against the plan: the actual can itself be restated, and it proves the plan, not the reading",
}
KEY_LABEL = {"twin": "twin", "second_source": "second source", "tie": "tie", "later_truth": "later truth"}


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
    kind = method_kind(by or "")
    for key, kinds in ANSWER_KEYS.items():
        if kind in kinds and (kind != "rule" or by.endswith(TIE)):
            return key
    return None


ORDER = {"blocked": 0, "open": 1, "explained": 2, "checked": 3}  # worst first
CHECKS = ("xbrl", "quote", "located", "mapping")  # the bare checks; the keyed ones (esef:, source:, rule:*_tie, actual:) go through answer_key
REASONS = {"xbrl": "agrees with the SEC's XBRL", "esef": "agrees with the filer's own ESEF tag", "source": "agrees with a second document by the same filer",
           "rule": "the tie holds", "actual": "the actual for the period, against the plan", "quote": "a verbatim quote, verified against its text",
           "located": "statement tables located in the filing", "mapping": "mapped to a us-gaap member with the note's words"}
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


def confirmed(entry: dict | None) -> bool:
    """T63: an asset-type mapping (an entry of taxonomy/asset_types.yaml) is a person's only when it carries a non-empty
    `confirmed_by`. A field check, never a phrase match: `by` says who wrote it (a model, for the 47 entries of 1 Nov
    2026), `confirmed_by` who stands behind it."""
    return bool(entry) and bool(str(entry.get("confirmed_by") or "").strip())


UNMAPPED = "a reported PP&E category with no entry in taxonomy/asset_types.yaml"


def of_mapping(entry: dict | None) -> dict:
    """A reported asset type (the mapping stage, T63): checked by the mapping when a person confirmed it; open, by
    `label:to_confirm`, when the entry is a proposal (no `confirmed_by`: Reconcile's asset types group, Approve / Edit /
    Reject); open with nothing when there is no entry."""
    member = (entry or {}).get("standard_type")
    if not member:
        return state({"reason": UNMAPPED})
    if confirmed(entry):
        return state({"check": "mapping", "mapping_to": member, "reason": f"mapped to {member} with the note's words, confirmed by {entry['confirmed_by']}"})
    return state({"label": "to_confirm", "reason": f"{member} proposed by {entry.get('by') or 'nobody named'}; no person has confirmed it"})


def worst(states: list[dict]) -> dict | None:
    return min(states, key=lambda s: ORDER[s["state"]]) if states else None


def is_open(s: dict) -> bool:
    """Open for a person: open or blocked."""
    return s["state"] in ("open", "blocked")


# ── how each kind of row maps onto `state` (one place, so Proof and Reconcile read the same thing) ──────────────────
def of_value(v: dict, resolution: dict | None = None) -> dict:
    """A `values` row: label agree → checked by XBRL; definition_gap → the definition (cost lines for opex, the revenue
    line otherwise); not_reported / no_reference → explained by reconcile's label; not_extracted → open, by the label
    (the filing tags a value the reader did not extract); unresolved → open unless a person resolved it."""
    label = v.get("label")
    row = {"resolution": resolution}
    if label == "agree":
        row["check"] = "xbrl"
    elif label == "definition_gap":
        row["definition"] = "cost_lines" if v.get("field") == "opex" else "revenue"
    elif label in ("not_reported", "no_reference"):
        row["label"] = label
    elif label == "not_extracted":  # T65: no cell read while XBRL tags a value; the label names the cause, it explains nothing
        row |= {"label": label, "reason": "the filing tags a value the reader did not extract"}
    return state(row)


def of_fact(f: dict, resolution: dict | None = None, restated: str | None = None) -> dict:
    """A `facts` row: label agree → checked by XBRL; no_reference → the label; unresolved → the restatement guard when
    the cell and the tag come from different filings (`restated` is that finding's text), else open unless resolved."""
    label = f.get("label")
    row = {"resolution": resolution}
    if label == "agree":
        row["check"] = "xbrl"
    elif label == "no_reference":
        row["label"] = "no_reference"
    elif restated:
        row |= {"rule": "restated_between_filings", "reason": restated}
    return state(row)


def of_exception(e: dict, resolution: dict | None = None, rows: list[dict] | None = None) -> dict:
    """A rule's finding (an `exceptions` row): block → blocked; info → explained; warn → the worst state of the rows it
    fired on (`rows`, already through of_value / of_fact), or open when it fired on nothing the dataset holds."""
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
    if w:
        return keyed({**w, "reason": f"{e.get('rule_id')}: {w['reason']}"})
    return state({"rule": e.get("rule_id"), "severity": "warn", "reason": (e.get("message") or "")[:200]})
