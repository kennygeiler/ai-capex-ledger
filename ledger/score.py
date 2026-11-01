"""Per-agent score (docs/TICKETS.md T49): for one live reader and the companies in scope, how many of its outputs are
checked, explained, open and blocked (the states of `status.state`, read from the Proof trail stage the reader owns),
how many agree with their structured twin where one exists (`status.answer_key(by) == "twin"`: the SEC's XBRL today),
and how many planted faults the checks behind it caught (`ledger faults`, reports/<name>-faults.json), each count
with its denominator. Counts first: the page computes the shares, so no number is shown without what it is out of. The
twin's agreement also carries a Wilson 95% interval (T53, `ledger/stats.py`) derived from the same two counts, so the page
can show it or recompute it; it says how much the share can move on this many rows, not whether a row is right.
Nothing is reimplemented: the states come from `proof.company` (which reads `status.state`), the twin from the rows'
labels, the faults from the report named by the latest `faults` run in the `runs` table that covered each company.
`note` says what the stage holds that is not counted, so the number reconciles with the Proof board; `faults_note`
says where the fault numbers come from, or why there are none."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from . import proof, stats, status, store

# which Proof stage holds each live reader's outputs (agents/charters/<id>.md says the same in words). The notes reader
# also feeds the Mapping stage, but a mapping judges taxonomy/asset_types.yaml, not the reader; it is not counted here.
AGENT_STAGE = {"reader": "values", "ai_reader": "statements", "notes_reader": "facts", "projects_reader": "planned"}
# the one step with a fault test: `ledger faults` corrupts `extractions` (ledger/faults.py), the reader's rows
FAULTED_STEP = "extract"
FAULT_CAUGHT = ("rule", "xbrl_only")
# the labels of rows with no twin, per stage: XBRL tags nothing for them, so they are not in the twin's denominator
TWIN_WITHOUT = {"values": ("no_reference", "not_reported"), "facts": ("no_reference",)}
REPORTS = store.ROOT / "reports"


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def outputs(con, agent_id: str, ticker: str) -> dict:
    """The reader's rows in its stage of the company's Proof trail, each with `state` and `by` from status.state:
    {"rows": [...], "stage_rows": n, "excluded": {what: n}}. The Values stage also lists warn findings (rule items)
    and the Planned stage also lists guidance (the AI spend reader's outlooks); both are left out and counted in
    `excluded`, so the list is the reader's own rows and the difference from the Proof board is on record."""
    stage = AGENT_STAGE[agent_id]
    trail = proof.company(con, ticker)
    items = trail["stages"][stage]["all"]
    if stage == "values":
        fields = {r["field"] for r in _rows(con, 'select distinct field from "values" where ticker = ?', ticker)}
        rows = [i for i in items if i["what"].split(" ")[0] in fields]
        nr = sum(r["n"] for r in _rows(con, 'select count(*) as n from "values" where ticker = ? and label = \'not_reported\'', ticker))
        return {"rows": rows, "stage_rows": len(items), "excluded": {"warn_findings": len(items) - len(rows)}, "counted": {"not_reported": nr}}
    if stage == "planned":
        rows = [i for i in items if i["what"].startswith("project ")]
        return {"rows": rows, "stage_rows": len(items), "excluded": {"guidance_rows": len(items) - len(rows)}, "counted": {}}
    if stage == "facts":
        return {"rows": items, "stage_rows": len(items), "excluded": {"mapping_stage_items": len(trail["stages"]["mapping"]["all"])}, "counted": {}}
    return {"rows": items, "stage_rows": len(items), "excluded": {}, "counted": {}}


def twin(con, agent_id: str, ticker: str, items: list[dict]) -> dict | None:
    """Agreement with the structured twin: among the reader's rows that have one (a value or a fact whose label is not
    no_reference / not_reported: XBRL tags the concept), how many are checked by it (`answer_key(by) == "twin"`), with
    `interval`, the Wilson 95% interval of agree / of (`with_interval`). None for a reader whose rows have no twin
    (statements and projects are quotes). Not per field: the trail's items carry `what` ("capex FY2025"), not `field`;
    `proof.company` would have to put `field` on each item first (T53, keyed part, in docs/TICKETS.md)."""
    stage = AGENT_STAGE[agent_id]
    if stage == "values":
        labels = [r["label"] for r in _rows(con, 'select label from "values" where ticker = ?', ticker)]
    elif stage == "facts":
        labels = [r["label"] for r in _rows(con, "select label from facts where ticker = ?", ticker)]
    else:
        return None
    of = sum(lab not in TWIN_WITHOUT[stage] for lab in labels)
    agree = sum(status.answer_key(i["by"] or "") == "twin" for i in items)
    return with_interval({"agree": agree, "of": of})


def with_interval(tw: dict) -> dict:
    """The twin counts with `interval`: [low, high] of the Wilson 95% interval on agree / of as fractions to 4 dp, None
    when `of` is 0 (no rows the twin tags, no share). Derived from the two counts and nothing else, so the page may
    recompute it from them."""
    iv = stats.wilson(tw["agree"], tw["of"])
    return {"agree": tw["agree"], "of": tw["of"], "interval": [round(iv[0], 4), round(iv[1], 4)] if iv else None}


_REPORTS: dict = {}  # (path, mtime, size) -> rows: a rewritten report (ledger faults overwrites the file) is read again


def _report(name: str) -> tuple[list[dict] | None, str | None]:
    """The report's rows and the time the file was written (UTC), or (None, None) when there is no readable file."""
    path = REPORTS / f"{name}-faults.json"
    try:
        st = path.stat()
    except OSError:
        return None, None
    key = (str(path), st.st_mtime, st.st_size)
    if key not in _REPORTS:
        try:
            _REPORTS[key] = json.loads(path.read_text())
        except (OSError, ValueError):
            _REPORTS[key] = None
    written = datetime.fromtimestamp(st.st_mtime, timezone.utc).isoformat(timespec="seconds")
    return _REPORTS[key], written


def faults(con, agent_id: str, tickers: list[str]) -> tuple[dict | None, str]:
    """The planted-fault catch rate of the checks behind the reader: for each company, the rows of the report named by
    the latest `ledger faults` run (runs table, step faults, subject = the report name) whose file holds that company's
    extractions; caught is an outcome of rule or xbrl_only, no_effect is a fault that reached no released value, escaped
    is what got through. The report is a file keyed by its name, not by the run: `ledger faults` rewrites it without a
    runs row, so the note carries the file's own written time next to the run's date and says when the file is newer.
    (None, reason) when the step has no fault test or no run covered the companies: never a made-up number."""
    from .cost import AGENT_STEP
    step = AGENT_STEP[agent_id]
    if step != FAULTED_STEP:
        return None, f"not measured: `ledger faults` corrupts `extractions` only (ledger/faults.py); no fault test exists for the {step} step's outputs"
    runs = _rows(con, "select subject, started_at from runs where step = 'faults' and outcome = 'ok' order by started_at desc")
    if not runs:
        return None, "not measured: no `ledger faults` run in the runs table"
    acc = {r["accession"]: r["ticker"] for r in _rows(con, "select accession, ticker from documents where ticker in (select unnest(?))", tickers)}
    tot = {"caught": 0, "planted": 0, "no_effect": 0, "escaped": 0}
    covered, used = [], {}
    for t in tickers:
        mine = {a for a, tk in acc.items() if tk == t}
        for run in runs:
            rep, written = _report(run["subject"])
            rows = [x for x in rep or [] if x["extraction_id"].split("|")[0] in mine]
            if rows:
                tot["planted"] += len(rows)
                tot["caught"] += sum(x["outcome"] in FAULT_CAUGHT for x in rows)
                tot["no_effect"] += sum(x["outcome"] == "no_effect" for x in rows)
                tot["escaped"] += sum(x["outcome"] == "escaped" for x in rows)
                covered.append(t)
                used[run["subject"]] = (run["started_at"] or "", written or "")
                break
    if not covered:
        return None, "not measured: no `ledger faults` run covered these companies (reports/<name>-faults.json)"
    missing = [t for t in tickers if t not in covered]
    parts = []
    for name, (ran, written) in sorted(used.items()):
        p = f"reports/{name}-faults.json: run {ran[:10]}, file written {written[:10]}"
        if written[:19] > ran[:19]:
            p += " (report newer than its run: `ledger faults` rewrites the file without a runs row, so the numbers are the file's)"
        parts.append(p)
    note = "; ".join(parts) + "; caught = a rule or the XBRL comparison fired; no_effect = the fault reached no released value"
    if missing:
        note += f"; no run covered {', '.join(missing)}"
    return tot, note


def score(con, agent_id: str, tickers: list[str]) -> dict:
    """The score: counts and denominators for the reader over `tickers` (see the module docstring). The page divides."""
    want = [t.upper() for t in tickers]
    n = {"outputs": 0, "checked": 0, "explained": 0, "open": 0, "blocked": 0}
    tw, stage_rows, excluded, counted = None, 0, {}, {}
    for t in want:
        o = outputs(con, agent_id, t)
        items = o["rows"]
        n["outputs"] += len(items)
        stage_rows += o["stage_rows"]
        for k, v in o["excluded"].items():
            excluded[k] = excluded.get(k, 0) + v
        for k, v in o["counted"].items():
            counted[k] = counted.get(k, 0) + v
        for s in status.STATES:
            n[s] += sum(i["state"] == s for i in items)
        w = twin(con, agent_id, t, items)
        if w is not None:
            tw = {k: (tw or {}).get(k, 0) + w[k] for k in ("agree", "of")}
    if tw is not None:
        tw = with_interval(tw)  # one interval on the sum over the companies, not a sum of per-company intervals
    fl, fnote = faults(con, agent_id, want)
    stage = AGENT_STAGE[agent_id]
    label = proof.STAGE_LABEL[stage]
    what = {"values": f"{n['outputs']} value rows of the {label} stage ({excluded.get('warn_findings', 0)} warn findings in the stage are not outputs; "
                      f"{counted.get('not_reported', 0)} not_reported rows are counted here and left out of a release's values list)",
            "facts": f"{n['outputs']} fact rows of the {label} stage (the Mapping stage's {excluded.get('mapping_stage_items', 0)} items judge taxonomy/asset_types.yaml, not the reader, and are not counted)",
            "statements": f"{n['outputs']} statement rows of the {label} stage",
            "planned": f"{n['outputs']} planned project rows of the {label} stage ({excluded.get('guidance_rows', 0)} guidance rows in the stage are the AI spend reader's and are not counted)"}[stage]
    note = (f"{what}; states from each company's Proof trail (status.state); open here excludes blocked, so checked + explained + open + blocked = outputs; "
            + (f"twin = the rows XBRL tags (not {' / '.join(TWIN_WITHOUT[stage])} rows), agree = checked by it; the interval is Wilson 95% on agree / of and covers only those tagged rows"
               if tw is not None else "no twin: these rows are quotes"))
    return {**n, "twin": tw, "faults": fl, "faults_note": fnote, "stage": stage, "stage_rows": stage_rows, "excluded": excluded, "companies": len(want), "note": note}
