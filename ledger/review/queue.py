"""The queue's items, outside the web app (review of F15): every item a person may decide, each with its key
(resolutions.key_for) and the hash of what it holds. Reconcile lists them (app._flow) and every other page matches a
resolution against them (resolutions.index). `items_for` builds them once per stamp (the database and every input
file, `stamp()`), so a page that reads resolutions many times builds the queue once."""
import csv
import hashlib
import json

from ..core import store
from ..core.config import ADDED, tracked
from ..core.ids import split_ids
from ..release.release import RELEASES, releases
from . import resolutions

EVIDENCE = store.ROOT / "reports" / "evidence"
STAGE = 3


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def latest_signed():
    signed = [d for d in releases() if (d / "SIGNOFF.json").exists()]
    return signed[-1] if signed else None



def inputs() -> list:
    """Every file the queue and the counts read besides the database (F21): the decisions on exceptions, the mapping
    proposals, the EDGAR check (data/watch.json), the rules, the definitions, the taxonomy files (the mappings), and the
    evidence, faults and release files the snapshot reads."""
    from ..checks.rules import RULES_DIR
    from . import definitions, mapper, review
    from ..web.hq import WATCH
    return [review.LOG, mapper.PROPOSALS, WATCH, definitions.FILE, *sorted(RULES_DIR.glob("*.yaml")), *sorted((store.ROOT / "taxonomy").glob("*.yaml")),
            # what hq.snapshot reads, each file stat-ed (a folder's mtime misses a file rewritten in place): the re-reads and
            # crops (reports/evidence/*.json), the faults reports, and every release's manifest, signature and values
            *sorted(EVIDENCE.glob("*.json")), *sorted((store.ROOT / "reports").glob("*-faults.json")),
            *sorted(f for d in RELEASES.glob("v*") if d.is_dir() for f in (d / "manifest.json", d / "SIGNOFF.json", d / "values.csv", d / "facts.csv"))]


def _stamp() -> tuple:
    """What the app depends on: the database, the resolutions, the releases, the added companies, the evidence, and every
    input file (_inputs, F21): a decision, an EDGAR check, a rule, a definition or a mapping written after the queue was
    built gives a new stamp, so the next read builds it again. A file's mtime and size; 0 for one that is not there."""
    paths = [store.DEFAULT_DB, resolutions.LOG, RELEASES, ADDED, EVIDENCE, *_inputs()]
    return tuple((str(p), *((p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else (0, 0))) for p in paths)



def stamp() -> tuple:
    """What the queue and the counts depend on: the database, the resolutions, the releases, the added companies, the
    evidence, and every input file (inputs, F21): a decision, an EDGAR check, a rule, a definition or a mapping written
    after the queue was built gives a new stamp, so the next read builds it again. A file's mtime and size; 0 for one
    that is not there."""
    paths = [store.DEFAULT_DB, resolutions.LOG, RELEASES, ADDED, EVIDENCE, *inputs()]
    return tuple((str(p), *((p.stat().st_mtime_ns, p.stat().st_size) if p.exists() else (0, 0))) for p in paths)


# T62: the key names the item (resolutions.key_for, from its fields, never from `where`); the hash says what it holds. The
# fields hq added for the key in T62 (a finding's rule and subject; a question's subject, questions carried rule before) are
# left out, so every hash equals its pre-T62 value and no resolution expired on the change.
DIFFER_RULE = "fact_readings_differ"  # ties.DIFFER
ADDED_FOR_KEY = {"finding_unconfirmed": ("rule", "subject"), "blocked": ("subject",)}


def content_hash(kind: str, detail: dict) -> str:
    skip = ADDED_FOR_KEY.get(kind, ())
    return hashlib.sha256(json.dumps({k: v for k, v in detail.items() if k not in skip}, sort_keys=True, default=str).encode()).hexdigest()[:12]


def queue_items(con, tickers: list[str]) -> dict:
    """Every queue item of `tickers`, each with its key (resolutions.key_for) and the hash of what it holds
    (content_hash), on the caller's connection: {queue, changed, release, facts_changed}. The one producer of queue items:
    Reconcile lists them (_flow) and every other page matches a resolution against them (resolutions.index, F15), so a
    resolution closes only the item, key and hash, it was written for."""
    tickers = sorted(tickers)
    from ..web.hq import snapshot  # the snapshot the dashboard reads: questions, findings, the EDGAR watch
    from .workbench import FINDING_LABEL
    hqd = snapshot(con, STAGE, tickers)
    facts = _rows(con, "select ticker, field, dimension, period, value, label from facts where ticker in (select unnest(?))", tickers)
    cites = {e["extraction_id"]: e for e in _rows(con, "select extraction_id, accession, table_id, row_label, column_label, cell_text from note_extractions where ticker in (select unnest(?))", tickers)}
    urls = {d["accession"]: d["url"] for d in _rows(con, "select accession, url from documents where ticker in (select unnest(?))", tickers)}
    fact_ref = {(f["ticker"], f["field"], f["dimension"], f["period"]): f for f in _rows(con, "select ticker, field, dimension, period, reference, extraction_ids from facts where ticker in (select unnest(?))", tickers)}
    missing = _rows(con, 'select v.ticker, v.field, v.period, v.period_end, v.label, r.value as reference from "values" v left join reference_values r using (ticker, field, period) '
                         "where v.label = 'not_extracted' and v.ticker in (select unnest(?)) order by v.ticker, v.field, v.period", tickers)
    from ..checks import ties
    differ_live = ties.differ_findings(**(lambda d: {"facts": d["facts"], "extractions": d["extractions"]})(ties.load(con, tickers, [])))  # F-FL1: read live, as Proof's ladder reads them
    rel = latest_signed()
    rel_facts = {(r["ticker"], r["field"], r["dimension"], r["period"]): r["value"] for r in csv.DictReader((rel / "facts.csv").open())} if rel and (rel / "facts.csv").exists() else {}
    facts_changed = [f for f in facts if rel_facts and str(f["value"]) != rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"]), "")]
    since = hqd["since"] or {}
    changed = {"new_filings": [f for f in (hqd["watch"] or {}).get("new", []) if f["ticker"] in tickers],
               "filings_read": [f for f in since.get("new_filings", []) if f.split("|")[0] in tickers], "facts_changed": len(facts_changed),
               "release": rel.name if rel else None, "last_run": hqd["health"][0]["run_at"]}
    queue = []
    for f in changed["new_filings"]:
        queue.append({"kind": "new_filing", "key": resolutions.key_for("new_filing", f["ticker"], f["form"], f["period"]), "state": "new", "ticker": f["ticker"], "where": f"{f['form']} for the year ended {f['period']}", "impact": "values, facts and statements for the year", "action": "run", "detail": f})
    for e in hqd["questions"]:
        if e["ticker"] in tickers:
            queue.append({"kind": "blocked", "key": resolutions.key_for("blocked", e["ticker"], e["field"], e["period"], rule_id=e["rule"], subject=e.get("subject")), "state": "blocked", "ticker": e["ticker"], "where": f"{e['field'] or ''} {e['period'] or ''}".strip() or e["rule"], "impact": "blocks the release", "action": "definition",
                          "detail": {k: v for k, v in e.items() if k != "proposed"}, "proposed": e.get("proposed")})  # F14: a run's decision, off the hash (the item is the same finding)
    for f in facts_changed:
        queue.append({"kind": "fact_changed", "key": resolutions.key_for("fact_changed", f["ticker"], f["field"], f["period"], f["dimension"]), "state": "moved", "ticker": f["ticker"], "where": f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " "), "impact": "the next release", "dollars": 0, "new": True, "action": "release",
                      "detail": {**f, "release_value": (lambda v: None if v in (None, "") else float(v))(rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"])))}})
    for f in facts:
        if f["label"] == "unresolved":
            fr = fact_ref.get((f["ticker"], f["field"], f["dimension"], f["period"]), {})
            cite = cites.get((split_ids(fr.get("extraction_ids")) or [""])[-1])
            key = f"{f['ticker']}|{f['field']}|{f['dimension']}|{f['period']}"
            queue.append({"kind": "fact_differs", "key": resolutions.key_for("fact_differs", f["ticker"], f["field"], f["period"], f["dimension"]), "state": "disagrees", "ticker": f["ticker"], "where": f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " "),
                          "impact": "a cited cell against the filing's tag", "dollars": abs((f["value"] or 0) - (float(fr["reference"]) if fr.get("reference") not in (None, "") else (f["value"] or 0))),
                          "new": key not in {"|".join(k) for k in rel_facts}, "action": "definition",
                          "detail": {**f, "reference": fr.get("reference"), "cite": cite, "url": urls.get((cite or {}).get("accession")), "release_value": rel_facts.get((f["ticker"], f["field"], f["dimension"], f["period"]))}})
    for v in missing:  # T65: no cell read while XBRL tags a value; open on Proof by label:not_extracted, so open here too (closed by re-reading, never by a decision)
        queue.append({"kind": "value_missing", "key": resolutions.key_for("value_missing", v["ticker"], v["field"], v["period"]), "state": "missing", "ticker": v["ticker"], "where": f"{v['field']} {v['period']}", "impact": "a released value is blank while the filing tags one",
                      "action": "run", "detail": v})
    from ..extract.agent import unfingerprinted
    for u in unfingerprinted(con, tickers):  # F25: closed by re-reading, never by a decision (not a live resolution kind)
        queue.append({"kind": "reading_unfingerprinted", "key": resolutions.key_for("reading_unfingerprinted", u["ticker"], u["step"], subject=u["subject"]), "state": "missing",
                      "ticker": u["ticker"], "where": f"{u['what']} · {u['label']}", "impact": "rows from a reading nothing ties to the current task", "action": "run", "detail": u})
    names_ = {c["ticker"]: c["name"] for c in tracked()}
    findings = [x for x in hqd["findings"] if x.get("rule") != DIFFER_RULE] + [  # F-FL1: the readings that differ come from the ladder, never from a stale exceptions table
        {"ticker": x["ticker"], "company": names_.get(x["ticker"]), "field": x["field"], "period": x["period"], "confirmed": False, "message": x["message"],
         "rule": DIFFER_RULE, "subject": x["subject"], "kind": "other", "before": None, "after": None, "size": 0} for x in differ_live]
    for x in findings:
        if x["ticker"] in tickers and not x.get("confirmed", True):
            queue.append({"kind": "finding_unconfirmed", "key": resolutions.key_for("finding_unconfirmed", x["ticker"], x["field"], x["period"], rule_id=x.get("rule") or x["kind"], subject=x.get("subject")), "state": "look", "ticker": x["ticker"], "where": f"{x['field'] or ''} {x['period'] or ''}".strip(), "impact": FINDING_LABEL.get(x.get("rule") if x["kind"] == "other" else x["kind"]) or "a value SEC XBRL cannot confirm", "action": "open", "detail": x})
    for q_ in queue:
        q_.setdefault("dollars", 0); q_.setdefault("new", False)
        q_["hash"] = content_hash(q_["kind"], q_["detail"])
    return {"queue": queue, "changed": changed, "release": rel, "facts_changed": facts_changed}



_ITEMS: dict = {}


def _db_path(con) -> str | None:
    try:
        r = con.execute("select path from duckdb_databases() where database_name = current_database()").fetchone()
        return r[0] if r and r[0] else None
    except Exception:
        return None


def items_for(con, tickers) -> list[dict]:
    """queue_items(con, tickers)["queue"] as [{key, hash}], built once per (database file, tickers, stamp()): Proof,
    the API lists, the Grid, gold and the taxonomy rows each read resolutions.index, and the queue is built once until
    the database or an input file changes. An in-memory database is never cached."""
    path = _db_path(con)
    from pathlib import Path
    st = Path(path).stat() if path and Path(path).exists() else None
    key = (path, st.st_mtime_ns, st.st_size, tuple(sorted(tickers)), stamp()) if st else None
    if key and key in _ITEMS:
        return _ITEMS[key]
    out = [{"key": q["key"], "hash": q["hash"]} for q in queue_items(con, list(tickers))["queue"]]
    if key:
        if len(_ITEMS) > 24:
            _ITEMS.clear()
        _ITEMS[key] = out
    return out
