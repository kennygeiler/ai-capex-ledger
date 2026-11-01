"""Per-agent score (docs/TICKETS.md T49): for one live reader and the companies in scope, how many of its outputs are
checked, explained, open and blocked (the states of `status.state`, read from the Proof trail stage the reader owns),
how many agree with their structured twin where one exists (`status.answer_key(by) == "twin"`: the SEC's XBRL today),
and how many planted faults the checks behind it caught (`ledger faults`, reports/<name>-faults.json), each count
with its denominator. Counts only: the page computes the shares, so no number is shown without what it is out of.
Nothing is reimplemented: the states come from `proof.company` (which reads `status.state`), the twin from the rows'
labels, the faults from the report of the latest `faults` run in the `runs` table that covered each company."""
from __future__ import annotations

import json

from . import proof, status, store

# which Proof stage holds each live reader's outputs (agents/charters/<id>.md says the same in words). The notes reader
# also feeds the Mapping stage, but a mapping judges taxonomy/asset_types.yaml, not the reader; it is not counted here.
AGENT_STAGE = {"reader": "values", "ai_reader": "statements", "notes_reader": "facts", "projects_reader": "planned"}
# the one step with a fault test: `ledger faults` corrupts `extractions` (ledger/faults.py), the reader's rows
FAULTED_STEP = "extract"
FAULT_CAUGHT = ("rule", "xbrl_only")
REPORTS = store.ROOT / "reports"


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def outputs(con, agent_id: str, ticker: str) -> list[dict]:
    """The reader's rows in its stage of the company's Proof trail, each with `state` and `by` from status.state.
    The Values stage also lists warn findings (rule items) and the Planned stage also lists guidance (the AI spend
    reader's outlooks); both are left out, so the list is the reader's own rows."""
    stage = AGENT_STAGE[agent_id]
    items = proof.company(con, ticker)["stages"][stage]["all"]
    if stage == "values":
        fields = {r["field"] for r in _rows(con, 'select distinct field from "values" where ticker = ?', ticker)}
        return [i for i in items if i["what"].split(" ")[0] in fields]
    if stage == "planned":
        return [i for i in items if i["what"].startswith("project ")]
    return items


def twin(con, agent_id: str, ticker: str, items: list[dict]) -> dict | None:
    """Agreement with the structured twin: among the reader's rows that have one (a value or a fact whose label is not
    no_reference / not_reported: XBRL tags the concept), how many are checked by it (`answer_key(by) == "twin"`).
    None for a reader whose rows have no twin (statements and projects are quotes)."""
    stage = AGENT_STAGE[agent_id]
    if stage == "values":
        labels = [r["label"] for r in _rows(con, 'select label from "values" where ticker = ? order by field, period', ticker)]
        without = ("no_reference", "not_reported")
    elif stage == "facts":
        labels = [r["label"] for r in _rows(con, "select label from facts where ticker = ? order by field, dimension, period", ticker)]
        without = ("no_reference",)
    else:
        return None
    of = sum(lab not in without for lab in labels)
    agree = sum(status.answer_key(i["by"] or "") == "twin" for i in items)
    return {"agree": agree, "of": of}


_REPORTS: dict = {}


def _report(name: str) -> list[dict] | None:
    if name not in _REPORTS:
        path = REPORTS / f"{name}-faults.json"
        try:
            _REPORTS[name] = json.loads(path.read_text()) if path.exists() else None
        except (OSError, ValueError):
            _REPORTS[name] = None
    return _REPORTS[name]


def faults(con, agent_id: str, tickers: list[str]) -> tuple[dict | None, str]:
    """The planted-fault catch rate of the checks behind the reader: for each company, the rows of the report written
    by the latest `ledger faults` run (runs table, step faults) whose report holds that company's extractions; caught is
    an outcome of rule or xbrl_only, no_effect is a fault that reached no released value, escaped is what got through.
    (None, reason) when the step has no fault test or no run covered the companies: never a made-up number."""
    from .cost import AGENT_STEP
    step = AGENT_STEP[agent_id]
    if step != FAULTED_STEP:
        return None, f"not measured: `ledger faults` corrupts `extractions` only (ledger/faults.py); no fault test exists for the {step} step's outputs"
    runs = _rows(con, "select subject, started_at from runs where step = 'faults' and outcome = 'ok' order by started_at desc")
    if not runs:
        return None, "not measured: no `ledger faults` run in the runs table"
    acc = {}
    for r in _rows(con, "select accession, ticker from documents where ticker in (select unnest(?))", tickers):
        acc[r["accession"]] = r["ticker"]
    tot = {"caught": 0, "planted": 0, "no_effect": 0, "escaped": 0}
    covered, used = [], []
    for t in tickers:
        mine = {a for a, tk in acc.items() if tk == t}
        for run in runs:
            rep = _report(run["subject"])
            rows = [x for x in rep or [] if x["extraction_id"].split("|")[0] in mine]
            if rows:
                tot["planted"] += len(rows)
                tot["caught"] += sum(x["outcome"] in FAULT_CAUGHT for x in rows)
                tot["no_effect"] += sum(x["outcome"] == "no_effect" for x in rows)
                tot["escaped"] += sum(x["outcome"] == "escaped" for x in rows)
                covered.append(t)
                used.append(f"{run['subject']} ({run['started_at'][:10]})")
                break
    if not covered:
        return None, "not measured: no `ledger faults` run covered these companies (reports/<name>-faults.json)"
    missing = [t for t in tickers if t not in covered]
    note = f"reports/<name>-faults.json of the latest faults run per company: {', '.join(sorted(set(used)))}; caught = a rule or the XBRL comparison fired; no_effect = the fault reached no released value"
    if missing:
        note += f"; no run covered {', '.join(missing)}"
    return tot, note


def score(con, agent_id: str, tickers: list[str]) -> dict:
    """The score: counts and denominators for the reader over `tickers` (see the module docstring). The page divides."""
    want = [t.upper() for t in tickers]
    n = {"outputs": 0, "checked": 0, "explained": 0, "open": 0, "blocked": 0}
    tw = None
    for t in want:
        items = outputs(con, agent_id, t)
        n["outputs"] += len(items)
        for s in status.STATES:
            n[s] += sum(i["state"] == s for i in items)
        w = twin(con, agent_id, t, items)
        if w is not None:
            tw = {k: (tw or {}).get(k, 0) + w[k] for k in ("agree", "of")}
    fl, fnote = faults(con, agent_id, want)
    stage = AGENT_STAGE[agent_id]
    note = (f"states from the {proof.STAGE_LABEL[stage]} stage of each company's Proof trail (status.state); open here excludes blocked, "
            f"so checked + explained + open + blocked = outputs; twin = " + ("rows XBRL tags, agree = checked by it" if tw is not None else "none, these rows are quotes") + f"; faults: {fnote}")
    return {**n, "twin": tw, "faults": fl, "stage": stage, "companies": len(want), "note": note}
