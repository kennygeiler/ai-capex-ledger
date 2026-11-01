"""One definition of open (T1, docs/PROOF.md). Proof, Reconcile, the trail and the Release gates all read it.

A row of the dataset (a value, a fact, a statement, a reported asset type, a filing, a rule's finding) is in exactly one
of four states:

  checked    it agrees with an independent check: the SEC's XBRL (values, facts), a quote verified against the text it
             came from (statements, planned rows), a statement table located in the filing (ingest), a reported asset
             type mapped to a us-gaap member with the note's words as evidence (mapping).
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

`by` names what decided the state: xbrl | quote | located | mapping:<us-gaap member> | rule:<id> | definition:<name> |
label:<not_reported|no_reference> | resolution:<id>. Empty when the state is open and nothing applies."""
from __future__ import annotations

STATES = ("checked", "explained", "open", "blocked")
# The kinds of `by`, and of the taxonomy rows' `check_method` (store.TAXONOMY): an open vocabulary of `<kind>` or
# `<kind>:<id>`. A later answer key (esef:<tag>, source:<doc>, actual:<period>) is one entry here.
METHOD_KINDS = ("xbrl", "quote", "gathered", "located", "none", "mapping", "rule", "definition", "resolution", "label")


def method_kind(by: str) -> str:
    return by.partition(":")[0]
ORDER = {"blocked": 0, "open": 1, "explained": 2, "checked": 3}  # worst first
CHECKS = ("xbrl", "quote", "located", "mapping")
GUARD_IDS = ("part_year", "program_words", "asset_type_mapping", "restated_between_filings", "amendment_without_statements")  # proof.GUARDS: info by nature


def _res(resolution: dict | None) -> tuple[str, str, str]:
    if not resolution:
        return "", "", ""
    rid = resolution.get("id") or ""
    return resolution.get("state") or "", f"resolution:{rid}" if rid else "resolution", (resolution.get("reason") or "")[:200]


def state(row: dict) -> dict:
    """The one function. `row` carries what is known about a dataset row, every key optional:
    check: xbrl | quote | located | mapping (what vouches for it); mapping_to: the us-gaap member when check is mapping
    rule, severity: the rule or guard that fired on it (block | warn | info; a guard counts as info)
    definition: the name of the definition on file that covers it
    label: a reconcile label (not_reported, no_reference) that explains it
    resolution: the person's latest resolution on it, {id, state, reason}
    Returns {"state", "reason", "by"}."""
    rs, rby, rreason = _res(row.get("resolution"))
    rule, sev = row.get("rule"), row.get("severity") or ("info" if row.get("rule") in GUARD_IDS else None)
    if rs == "blocks":
        return {"state": "blocked", "reason": rreason or "a person's decision blocks the release", "by": rby}
    if rule and sev == "block":
        return {"state": "blocked", "reason": row.get("reason") or f"rule {rule} blocks the release", "by": f"rule:{rule}"}
    check = row.get("check")
    if check in CHECKS:
        by = f"mapping:{row.get('mapping_to') or ''}" if check == "mapping" else check
        return {"state": "checked", "reason": row.get("reason") or {"xbrl": "agrees with the SEC's XBRL", "quote": "a verbatim quote, verified against its text", "located": "statement tables located in the filing"}.get(check, "mapped to a us-gaap member with the note's words"), "by": by}
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
    return {"state": "open", "reason": row.get("reason") or (f"rule {rule} fired and nothing on file says why" if rule else "neither checked nor explained"), "by": f"rule:{rule}" if rule else ""}


def worst(states: list[dict]) -> dict | None:
    return min(states, key=lambda s: ORDER[s["state"]]) if states else None


def is_open(s: dict) -> bool:
    """Open for a person: open or blocked."""
    return s["state"] in ("open", "blocked")


# ── how each kind of row maps onto `state` (one place, so Proof and Reconcile read the same thing) ──────────────────
def of_value(v: dict, resolution: dict | None = None) -> dict:
    """A `values` row: label agree → checked by XBRL; definition_gap → the definition (cost lines for opex, the revenue
    line otherwise); not_reported / no_reference → reconcile's label; unresolved → open unless a person resolved it."""
    label = v.get("label")
    row = {"resolution": resolution}
    if label == "agree":
        row["check"] = "xbrl"
    elif label == "definition_gap":
        row["definition"] = "cost_lines" if v.get("field") == "opex" else "revenue"
    elif label in ("not_reported", "no_reference"):
        row["label"] = label
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
        return {"state": "blocked", "reason": rreason, "by": rby}
    if rs == "fix":
        return {"state": "open", "reason": rreason, "by": rby}
    if rs in ("accept", "explain"):
        return {"state": "explained", "reason": rreason, "by": rby}
    w = worst(rows or [])
    if w:
        return {**w, "reason": f"{e.get('rule_id')}: {w['reason']}"}
    return state({"rule": e.get("rule_id"), "severity": "warn", "reason": (e.get("message") or "")[:200]})
