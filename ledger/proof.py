"""Proof: for a company, every figure is checked, explained, open or blocked, stage by stage (docs/PROOF.md).

The state of every item comes from one function, `status.state` (T1): checked when an independent check agrees,
explained when a rule, a definition, a guard or a person's resolution says why by name, open when neither, blocked when
a block rule or a resolution refuses the release. Reconcile reads the same function, so the two pages count the same
row the same way. A company is proven when nothing is open or blocked at any stage. `board()` is the Proof home: the
scope down, the stages across; `company()` is one company's trail; `rules()` is every rule and definition with what it
closed, and the open items grouped by what is missing."""
from __future__ import annotations

from . import definitions, resolutions, status, store, ties
from .notes import FIELDS as NOTE_FIELDS
from .guards import part_year, program_words
from .review import decisions, open_items
from .rules import explain_key, explained
from .taxonomy import asset_types, rows as taxonomy_rows
from .config import PROVEN, PROVEN_WHY, SCOPE, industry, tracked

STAGES = ("ingest", "values", "facts", "statements", "mapping", "planned", "release")
STAGE_LABEL = {"ingest": "Ingest", "values": "Values", "facts": "Facts", "statements": "Statements", "mapping": "Mapping", "planned": "Planned", "release": "Release"}
NEEDS = {"values": "a definition (which line the tag measures) or a unit rule", "facts": "a definition (which concept the table line is) once the tag is named",
         "finding": "a definition or a rule for what the finding found", "mapping": "a mapping to a us-gaap PropertyPlantAndEquipmentByTypeAxis member, with the note's words",
         "mapping_confirm": "a person's confirmation of the proposed member (Reconcile, asset types: Approve, Edit or Reject)",
         "readings": "a person's resolution saying which reading is right, or a re-read (Reconcile)",
         "tie": "a person's resolution naming the reconciling line, or a re-read of the parts (Reconcile)",
         "ingest": "a parser or unit rule", "locate": "a locator rule", "release": "a definition or a fix", "decision": "the fix the decision names"}


# The exceptions a loader writes when a stage failed (cli/extract, cli/notes, cli/aispend, cli/projects): failures, never
# explanations, and no rule on file names them. They sit on the ingest stage, open or blocked by their severity, and never
# take the state of other rows (T80: a warn failure with no field used to take the worst state of every value).
FAILURES = ("extraction_failed", "note_extraction_failed", "ai_extraction_failed", "projects_failed")


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _has(con, name):
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def _item(what: str, st: dict, detail: str = "", needs: str = "", ref: dict | None = None) -> dict:
    """One trail item. `key` is the strongest answer key that vouches for it (status.KEY_GRADE), None when none does.
    `ref` is the record its check rests on (T80, status.evidence_gap): given here, or carried on the state (a warn
    finding takes the state, and the record, of the row it fired on)."""
    return {"what": what, "state": st["state"], "by": st["by"], "key": st.get("key"), "keys": st.get("keys") or [], "reason": st["reason"], "detail": detail,
            "needs": needs if status.is_open(st) else "", "ref": ref if ref is not None else st.get("ref") or {}}


KEY_GRADE = [{"id": k, "label": status.KEY_LABEL[k], "why": status.KEY_WHY[k]} for k in status.KEY_GRADE]  # the keys, strongest first, for the pages


def keys_of(items: list[dict]) -> dict:
    """Rows by the strongest answer key that vouches for them (T56): {twin, second_source, tie, later_truth, second_reading, none, rows};
    `none` is every row no key vouches for (a quote, a located table, a mapping, an explanation, an open item), so the
    grades sum to `rows`, the denominator."""
    out = {k: 0 for k in status.KEY_GRADE} | {"none": 0, "rows": len(items)}
    for i in items:
        out[i.get("key") or "none"] += 1
    return out


def rules_on_file() -> tuple[list[dict], str | None]:
    """(the rules in rules/*.yaml, None), or ([], why) when a file does not load (a hand edit that breaks a check): Proof
    shows the error as an open item instead of failing, and nothing is explained by a rule until it is fixed."""
    from .rules import load as load_rules
    try:
        return load_rules(), None
    except (ValueError, OSError) as e:
        return [], str(e)


def company(con, ticker: str, idx: dict | None = None, defs: dict | None = None, rset: tuple | None = None) -> dict:
    """One company's proof trail: per stage, every item with its state from `status.state`, counts, and the open items
    with what they need. `rset` is rules_on_file(), read once per request by the caller (board, rules, unevidenced)."""
    t = ticker.upper()
    rset = rules_on_file() if rset is None else rset
    idx = resolutions.by_row() if idx is None else idx
    defs = definitions.load() if defs is None else defs
    stages = {}

    # ingest: every filing's tables located and every cited cell resolving
    docs = _rows(con, "select accession, form, period, table_count, income_tables, cash_flow_tables from documents where ticker = ? order by period", t)
    exc = _rows(con, "select * from exceptions where ticker = ? ", t)
    items = []
    for d in docs:
        what = f"{d['form']} {d['period']}"
        if (d["income_tables"] or "") and (d["cash_flow_tables"] or ""):
            items.append(_item(what, status.state({"check": "located"}), f"{d['table_count']} tables parsed", ref={"accession": d["accession"], "income_tables": d["income_tables"], "cash_flow_tables": d["cash_flow_tables"]}))
        elif amendment_without_statements(d):
            items.append(_item(what, status.state({"rule": "amendment_without_statements", "reason": "an amendment without financial statements (Part III only)"}), f"{d['table_count']} tables parsed"))
        else:
            items.append(_item(f"{what}: a statement table not located", status.state({"reason": "no income or cash-flow table located"}), f"{d['table_count']} tables parsed", NEEDS["locate"]))
    for e in exc:
        if e["rule_id"] in FAILURES:
            items.append(_item(f"{e['rule_id'].replace('_', ' ')}: {e['subject']}", status.of_exception(e), e["message"][:200], NEEDS["ingest"]))
    stages["ingest"] = _stage(items)

    # values: agree with XBRL, or explained by a definition, a label or a decision; a warn finding takes the state of its rows
    vals = _rows(con, 'select field, period, value, label, basis, extraction_ids from "values" where ticker = ? order by field, period', t)
    xref = {(r["field"], r["period"]): r["value"] for r in _rows(con, "select field, period, value from reference_values where ticker = ?", t)} if _has(con, "reference_values") else {}
    looked = bool(xref)  # T80: the XBRL lookup ran for this ticker only when reference_values holds its rows; an empty dict is no answer, not "nothing there"
    vstate = {}
    items = []
    for v in vals:
        vref = {"ticker": t, "field": v["field"], "period": v["period"], "reference": xref.get((v["field"], v["period"])), "looked_up": looked}
        st = {**status.of_value(v, resolutions.resolution_of(idx, "values", t, v["field"], "", v["period"]), vref), "ref": vref}
        vstate[(v["field"], v["period"])] = st
        items.append(_item(f"{v['field']} {v['period']}" + (f": {v['label']}" if status.is_open(st) else ""), st, v["basis"] if st["by"].startswith("definition") else f"value {v['value']}" if status.is_open(st) else "", NEEDS["values"]))
    decided = {e["exception_id"] for e in exc} - {e["exception_id"] for e in open_items(exc, decisions())}
    xp = explained(exc, rset[0]) if any(e["severity"] == "info" for e in exc) else {}  # T36: a person's explanation written as a rule, by the finding it names
    for e in exc:
        if e["severity"] != "warn" or e["exception_id"] in decided or e["rule_id"] in FAILURES or e["field"] in NOTE_FIELDS:
            continue  # a finding on a note field (a tie, two readings) sits on the facts stage
        ef = {"cost_of_revenue": "opex", "operating_income": "opex"}.get(e["field"], e["field"])  # read to make opex: a finding on them is about opex
        rows = [s for (f, p), s in vstate.items() if f == (ef or f) and p == (e["period"] or p)]
        st = status.of_exception(e, resolutions.resolution_of(idx, "values", t, e["field"] or "", "", e["period"] or ""), rows,
                                 xp.get(explain_key(e["rule_id"], t, e["field"], e["period"], e["subject"])))
        items.append(_item(f"{e['rule_id']}: {e['field'] or ''} {e['period'] or ''}".strip(), st, e["message"][:200], NEEDS["finding"]))
    stages["values"] = _stage(items)

    # facts: agree with the instance; an untagged one climbs the ladder (T92, ledger/ties.py): readings that differ are
    # open, a tie to the filing's tagged total or a second filing agreeing checks it, else the label explains it
    facts = _rows(con, "select field, dimension, period, value, label, reference, accession from facts where ticker = ? order by field, dimension, period", t)
    ciks = {d["accession"]: d["cik"] for d in _rows(con, "select accession, cik from documents where ticker = ?", t)}
    lad = ladder(con, [t], rset[0])
    items = []
    for f in facts:
        where = f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " ")
        k = lad.get((t, f["field"], f["dimension"] or "", f["period"])) or {"readings": [], "tie": None}
        rs, g = k["readings"], k["tie"]
        ref = {"ticker": t, "field": f["field"], "dimension": f["dimension"] or "", "period": f["period"], "reference": f["reference"],
               "looked_up": instance_on_file(ciks.get(f["accession"]), f["accession"])}
        differs = f["label"] == "no_reference" and ties.differ(rs)
        holds = g if f["label"] == "no_reference" and g and g["holds"] else None
        second = f["label"] == "no_reference" and ties.corroborated(rs)
        if len({r["accession"] for r in rs}) >= 2:
            ref["readings"] = rs
        if holds:
            ref["tie"] = {k_: holds[k_] for k_ in ("rule", "key", "accession", "concept", "total", "sum", "tolerance", "dimensions")}
        # a finding on the row (two readings) is the finding Reconcile shows: its resolution is keyed as a finding's
        res = resolutions.resolution_of(idx, "values" if differs else "facts", t, f["field"], "" if differs else f["dimension"] or "", f["period"])
        st = status.of_fact(f, res, _restated(con, t, f) if f["label"] == "unresolved" else None, differ=ties.differ_message(rs) if differs else None,
                            tie=holds["rule"] if holds else None, reading=next((r["accession"] for r in rs if r["accession"] != f["accession"]), None) if second else None)
        what = where + (": readings differ" if differs and status.is_open(st) else ": differs from the tag" if status.is_open(st) else "")
        detail = ties.differ_message(rs) if differs else f"cell {f['value']}, tag {f['reference']}" if status.is_open(st) else ""
        items.append(_item(what, st, detail, NEEDS["readings"] if differs else NEEDS["facts"], ref=ref))
    for e in exc:  # a tie that fails (or two readings Proof did not see as a fact item): open on the group, never checked
        if e["severity"] != "warn" or e["exception_id"] in decided or e["field"] not in NOTE_FIELDS or e["rule_id"] == status.DIFFER:
            continue
        st = status.of_exception(e, resolutions.resolution_of(idx, "values", t, e["field"] or "", "", e["period"] or ""), [],
                                 xp.get(explain_key(e["rule_id"], t, e["field"], e["period"], e["subject"])))
        items.append(_item(f"{e['rule_id']}: {e['field']} {e['period'] or ''} ({e['subject'] or ''})".strip(), st, e["message"][:300], NEEDS["tie"],
                           ref={"ticker": t, "field": e["field"], "period": e["period"], "accession": e["subject"], "finding": e["rule_id"]}))
    stages["facts"] = _stage(items)

    # statements: every quote verified at load; part-year and program statements carry their guard
    stmts = _rows(con, "select statement_id, field, period, kind, scope, class, quote, text_id from ai_statements where ticker = ?", t) if _has(con, "ai_statements") else []
    items = []
    for s in stmts:
        what = f"{s['field']} {s['period']} {s['kind']}"
        if s["class"] == "explicit_amount" and s["kind"] == "actual" and part_year(s["quote"]):
            items.append(_item(what, status.state({"rule": "part_year", "reason": "part-year amount, not the year's actual"}), s["quote"][:160]))
        elif s["kind"] == "outlook" and program_words(s["quote"]):
            items.append(_item(what, status.state({"rule": "program_words", "reason": "a program, not a year's guidance"}), s["quote"][:160]))
        else:
            items.append(_item(what, status.state({"check": "quote"}), ref={"statement_id": s["statement_id"], "text_id": s["text_id"]}))
    stages["statements"] = _stage(items)

    # mapping: every reported asset type mapped to a standard us-gaap member (taxonomy/asset_types.yaml) and confirmed by
    # a person (T63, status.of_mapping); an entry without confirmed_by is a proposal, open as to confirm; no entry, open
    tax = taxonomy_rows(con, [t])
    derived = [r for r in tax if r["measure"] == "derived"]
    entries = asset_types().get(t) or {}
    items = []
    for name in sorted({r["reported_name"] for r in derived}):
        e = entries.get(name)
        st = {**status.of_mapping(e), "ref": {"ticker": t, "name": name}}
        if st["state"] == "checked":
            it = _item(name, st, f"by {e.get('by')}, confirmed by {e.get('confirmed_by')} {e.get('confirmed_at') or ''}".strip())
        elif e and e.get("standard_type"):
            it = _item(f"{name}: {e['standard_type']}, to confirm", st, f"proposed by {e.get('by')}; Reconcile, asset types: Approve, Edit or Reject", NEEDS["mapping_confirm"])
        else:
            it = _item(f"{name}: no standard asset type", st, status.UNMAPPED, NEEDS["mapping"])
        items.append({**it, "name": name})  # the reported name itself, for the pages and the tests (`what` decorates it)
    stages["mapping"] = _stage(items, extra={"derived_rows": len(derived), "company_stated_ai": sum(r["measure"] == "company_stated_ai" for r in tax), "committed_rows": sum(r["measure"] == "committed" for r in tax)})

    # planned: guidance and projects, verbatim; a part-year or program statement carries its flag (taxonomy.part_year, .program)
    planned = [r for r in tax if r["measure"] == "planned"]
    items = []
    for r in planned:
        what = f"{r['category']} {r['fiscal_year']}: {r['reported_name']}"
        if r["part_year"]:
            items.append(_item(what, status.state({"rule": "part_year", "reason": "part-year amount"}), (r["quote"] or "")[:160]))
        elif r["program"]:
            items.append(_item(what, status.state({"rule": "program_words", "reason": "a program, not a year's guidance"}), (r["quote"] or "")[:160]))
        else:
            items.append(_item(what, status.state({"check": "quote"}), ref={"text_id": r.get("source"), "ticker": t, "category": r["category"], "fiscal_year": r["fiscal_year"], "reported_name": r["reported_name"]}))
    stages["planned"] = _stage(items, extra={"guidance": sum(r["category"] == "guidance" for r in planned), "projects": sum(r["category"] == "project" for r in planned)})

    # release: blocks from decisions and block-severity rules; the company's gate is one item
    items = [_item(f"{e['rule_id']}: {e['field'] or ''} {e['period'] or ''}".strip(), status.of_exception(e), e["message"][:200], NEEDS["release"])
             for e in exc if e["severity"] == "block" and e["rule_id"] not in FAILURES and e["exception_id"] not in decided]
    items += [_item(f"blocks: {' '.join(k[2:5]).strip()}", status.state({"resolution": r}), r["reason"][:200], NEEDS["decision"]) for k, r in idx.items() if k[1] == t and r["state"] == "blocks"]
    if rset[1]:  # a rule file that does not load: open, never a crash, and no rule explains anything until it is fixed
        items.append(_item("rules/ does not load", status.state({"reason": rset[1][:200]}), rset[1][:200], "a rule file that passes rules.load"))
    stages["release"] = _stage(items or [_item("the release gate", status.state({"check": "gate"}), ref={"stage": "release", "blocks": len(items)})])

    open_total = sum(len(s["open"]) for s in stages.values())
    keys = keys_of([i for s in stages.values() for i in s["all"]])
    name = next((c["name"] for c in tracked() if c["ticker"] == t), t)
    return {"ticker": t, "name": name, "layer": industry(t), "proven": open_total == 0, "open": open_total, "why": PROVEN_WHY.get(t, ""), "in_proven_set": t in PROVEN,
            "stages": stages, "keys": keys, "key_grade": KEY_GRADE, "definitions": sorted((defs or {}).get(t, {}).keys())}


def ladder(con, tickers: list[str], rules: list[dict]) -> dict:
    """The readings and the tie group behind every fact of `tickers` (ties.by_fact over ties.load): what the facts stage
    climbs, and what the evidence walk recomputes. An empty answer when the note tables are absent."""
    return ties.by_fact(ties.load(con, tickers, rules), rules)


def instance_on_file(cik, accession: str | None) -> bool:
    """T80: the filing's XBRL instance is on disk (the distilled facts or the XML, data/raw/<cik>/filings/), so a fact's
    empty reference is an answer from it, not a lookup that never ran. Never fetched here."""
    from .ingest.edgar import RAW
    if cik is None or not accession:
        return False
    d = RAW / f"{int(cik):010d}" / "filings"
    return (d / f"{accession}.facts.json").exists() or (d / f"{accession}.xml").exists()


def amendment_without_statements(doc: dict) -> bool:
    """A 10-K/A that carries no financial statements (the common Part III amendment: directors, compensation) is not a
    filing whose statements must be located (type 72). It is the form, with few tables and no statement table."""
    # the income match is not required to be empty: in AMD's three-table amendment the locator took a compensation table for an income statement
    return str(doc.get("form", "")).endswith("/A") and (doc.get("table_count") or 0) < 10 and not (doc.get("cash_flow_tables") or "")


def _stage(items: list[dict], extra: dict | None = None) -> dict:
    """Counts per state, the open items (open and blocked), the explained items with what explained them."""
    return {"checked": sum(i["state"] == "checked" for i in items), "explained": sum(i["state"] == "explained" for i in items),
            "blocked": sum(i["state"] == "blocked" for i in items), "open": [i for i in items if i["state"] in ("open", "blocked")],
            "items": len(items), "explained_items": [i for i in items if i["state"] == "explained"], "keys": keys_of(items), "all": items, **(extra or {})}


def _restated(con, ticker: str, f: dict) -> str | None:
    """A fact's cell from a later 10-K against a tag from an earlier one is a restatement, not a disagreement."""
    try:
        from .workbench import xbrl_name
        pe = con.execute("select period_end from facts where ticker = ? and field = ? and coalesce(dimension, '') = ? and period = ?", [ticker, f["field"], f["dimension"] or "", f["period"]]).fetchone()
        x = xbrl_name(con, f["accession"], pe[0] if pe else None, f["reference"])
        if x and x.get("accession") and x["accession"] != f["accession"]:
            return f"cell from {f['accession']}, tag {x['concept']}{' / ' + x['member'] if x.get('member') else ''} from {x['accession']}"
    except Exception:
        return None
    return None


def board(con) -> dict:
    """The Proof home: every company in scope (config.SCOPE) with its stage counts. The database keeps every company; the board shows the scope (T2)."""
    idx, defs, rset = resolutions.by_row(), definitions.load(), rules_on_file()
    proven = [company(con, t, idx, defs, rset) for t in SCOPE]
    keys = {k: sum(c["keys"][k] for c in proven) for k in (*status.KEY_GRADE, "none", "rows")}  # per company on each row; the total over the scope here
    return {"stages": [{"id": s, "label": STAGE_LABEL[s]} for s in STAGES], "proven": proven, "scope": list(SCOPE), "open": sum(c["open"] for c in proven),
            "keys": keys, "key_grade": KEY_GRADE}


GUARDS = [
    {"id": "part_year", "kind": "guard", "where": "planned", "what": "a stated amount that covers a quarter, a half or N months is tagged part-year, never a year's figure", "type": 68},
    {"id": "program_words", "kind": "guard", "where": "planned", "what": "an outlook statement with program words (joint venture, once completed, through 20XX) is tagged program, not a year's guidance", "type": 69},
    {"id": "asset_type_mapping", "kind": "guard", "where": "mapping", "what": "every reported PP&E category maps to a us-gaap asset-type member with the note's words as evidence and a person's confirmed_by (T63), or is open", "type": None},
    {"id": "restated_between_filings", "kind": "guard", "where": "facts", "what": "a cell from a later 10-K against a tag from an earlier one is a restatement", "type": None},
    {"id": "amendment_without_statements", "kind": "guard", "where": "ingest", "what": "a 10-K/A with few tables and no statement table is a Part III amendment, not a filing to locate statements in", "type": 72},
]


def rules(con) -> dict:
    """Every rule, guard and definition with what it closed in scope, and the open items by what is missing."""
    idx, defs, rset = resolutions.by_row(), definitions.load(), rules_on_file()
    cos = [company(con, t, idx, defs, rset) for t in SCOPE]
    exc = _rows(con, "select rule_id, severity, count(*) as n from exceptions where ticker in (select unnest(?)) group by 1, 2", SCOPE)
    fired = {}
    for e in exc:
        fired[e["rule_id"]] = fired.get(e["rule_id"], 0) + e["n"]
    out = [{"id": r["id"], "kind": "rule", "severity": r["severity"], "what": r["description"], "fired": fired.get(r["id"], 0)} for r in rset[0]]
    closed = {g["id"]: sum(1 for c in cos for s in c["stages"].values() for x in s["all"] if x["by"] == f"rule:{g['id']}") for g in GUARDS}
    closed["asset_type_mapping"] = sum(c["stages"]["mapping"]["checked"] for c in cos)
    out += [{**g, "fired": closed.get(g["id"], 0)} for g in GUARDS]
    out += [{"id": f"{t}:{k}", "kind": "definition", "where": "values", "what": f"{t}: {k} ({(v.get('why') or '')[:120]})", "fired": 1, "by": v.get("by")} for t in SCOPE for k, v in (defs.get(t) or {}).items() if isinstance(v, dict)]
    types = asset_types()
    out += [{"id": f"{t}:{name}", "kind": "mapping", "where": "mapping", "what": f"{t}: {name} → {m.get('standard_type')} ({(m.get('evidence') or '')[:100]})", "fired": 1, "by": m.get("by"),
             "confirmed_by": m.get("confirmed_by"), "confirmed": status.confirmed(m)} for t in SCOPE for name, m in (types.get(t) or {}).items()]
    missing = {}
    for c in cos:
        for s, st in c["stages"].items():
            for o in st["open"]:
                missing.setdefault(o["needs"], []).append({"ticker": c["ticker"], "stage": s, **o})
    return {"rules": out, "rules_error": rset[1], "open_by_need": [{"needs": k, "items": v} for k, v in sorted(missing.items(), key=lambda kv: -len(kv[1]))], "open": sum(len(v) for v in missing.values())}


# ── T80: a label never counts as a check ────────────────────────────────────────────────────────────────────────────
def person_wrote(line: dict) -> bool:
    """A resolution a person wrote, failing closed: `author_kind` person when the line carries the field (T69, set by
    the route that wrote it); before it, a `by` on config.PEOPLE that names no model, agent or run (status.is_person)
    and no "to confirm" in `by` or `reason`. One rule, in resolutions.by_person, which latest() also reads."""
    return resolutions.by_person(line)


def rule_severities(rules: list[dict]) -> dict:
    """{id: severity} over rules/*.yaml, then the guards (info) for ids no rule has. A rule id twice is an error: two
    severities for one id would let the walk pick the kinder one."""
    out = {}
    for r in rules:
        if r["id"] in out:
            raise ValueError(f"rule id {r['id']!r} is on file twice")
        out[r["id"]] = r["severity"]
    return out | {g["id"]: "info" for g in GUARDS if g["id"] not in out}


def evidence(con, defs: dict | None = None, log: list[dict] | None = None, types: dict | None = None, tickers=None) -> dict:
    """What is on file, for status.evidence_gap: the definitions, the rules with their severity (rule_severities), the
    resolutions by id with the ids a person wrote, the asset-type entries, the texts by id (read once, normalised) and
    the quotes of the statements and planned rows (the items carry ids, not quotes)."""
    tickers = list(tickers or PROVEN)
    rset = rules_on_file()
    lines = {r["id"]: r for r in (resolutions.load() if log is None else log) if r.get("id")}
    paths = {r["text_id"]: r["path"] for r in _rows(con, "select text_id, path from texts")} if _has(con, "texts") else {}
    stmts = {r["statement_id"]: r["quote"] for r in _rows(con, "select statement_id, quote from ai_statements where ticker in (select unnest(?))", tickers)} if _has(con, "ai_statements") else {}
    planned: dict = {}
    for r in taxonomy_rows(con, tickers):
        if r["measure"] == "planned":
            planned.setdefault((r["ticker"], r.get("source"), r["category"], r["fiscal_year"], r["reported_name"]), []).append(r["quote"])
    cache: dict = {}

    def text(text_id):
        if text_id not in cache:
            p = paths.get(text_id) and store.ROOT / paths[text_id]
            cache[text_id] = status.norm(p.read_text()) if p and p.exists() else None
        return cache[text_id]

    def quote(item) -> list:
        ref = item.get("ref") or {}
        if ref.get("statement_id"):
            return [stmts.get(ref["statement_id"])]
        return planned.get((ref.get("ticker"), ref.get("text_id"), ref.get("category"), ref.get("fiscal_year"), ref.get("reported_name"))) or []
    lad = ladder(con, tickers, rset[0])  # T92: the tie groups and the readings, recomputed from what is on file
    return {"ties": lad["groups"], "readings": {k: v["readings"] for k, v in lad.items() if k != "groups"},
            "definitions": definitions.load() if defs is None else defs, "rules": rule_severities(rset[0]), "resolutions": lines,
            "explains_by": {r["id"]: r.get("by") for r in rset[0] if r["check"] == "explains"},
            "person_ids": {i for i, r in lines.items() if person_wrote(r)}, "asset_types": asset_types() if types is None else types, "text": text, "quote": quote}


def unevidenced(con, tickers=None, companies: list[dict] | None = None, ev: dict | None = None) -> list[dict]:
    """Every checked or explained item of `tickers` (the proven set by default) whose `by` names no evidence record,
    or one that does not exist (status.evidence_gap): [{ticker, stage, what, state, by, gap}]. Empty is the rule held.
    The resolutions, definitions and asset types are read once, as board() does."""
    tickers = list(tickers or PROVEN)
    defs, types = definitions.load(), asset_types()
    ev = evidence(con, defs=defs, types=types, tickers=tickers) if ev is None else ev
    if companies is None:
        idx, rset = resolutions.by_row(), rules_on_file()
        companies = [company(con, t, idx, defs, rset) for t in tickers]
    return [{"ticker": c["ticker"], "stage": s, "what": i["what"], "state": i["state"], "by": i["by"], "gap": gap}
            for c in companies for s, st in c["stages"].items() for i in st["all"] if (gap := status.evidence_gap(i, ev))]


# ── T81: completeness against the answer key ─────────────────────────────────────────────────────────────────────────

def _decision_by_person(d: dict) -> bool:
    """A review decision (decisions/decisions.jsonl) a person made: person_wrote on its reviewer, the one test of a person."""
    return person_wrote({"by": d.get("reviewer"), "reason": d.get("reason"), **({"author_kind": d["author_kind"]} if "author_kind" in d else {})})


def missing_from_dataset(con, tickers, ds: list[dict], idx: dict | None = None) -> list[dict]:
    """The silent blanks of `tickers`: [{ticker, field, period, reference, label, why}]. Empty
    is the rule held; the Release checklist's required line "Answer-key values missing from the dataset" counts it (T81).

    A cell is a release field (config.RELEASE_FIELDS, the list `coverage` reads) and fiscal year in config.MVP_YEARS,
    not before the company's first `values` row (rules.first_periods, as `coverage` and `no_10k_yet` read it), where
    XBRL (reference_values) holds a value. Its released value is the `values` row after the review decisions
    (review.apply: an override fills it, a reject empties it). A cell with no released value is accounted for when:
      - the value row is open or blocked (status.of_value: not_extracted, not_reported over an XBRL value, a fix);
      - an undecided open finding names the cell (review.open_items: a `coverage` finding on a missing row);
      - a person's resolution on the value row explains it, or a person's review decision (accept or reject) on a
        finding for the cell decided it (proof.person_wrote).
    Those are on the Open line or decided by a person; anything else is silent. A ticker with no reference rows (or no
    reference_values table) is one entry, "no XBRL answer loaded": an absent answer key is no answer (T80's looked_up).
    `ds` is the review decisions (review.decisions()), passed in so nothing global is read for them. Facts are out of scope (docs/PROOF.md, "Completeness")."""
    from .config import MVP_YEARS, RELEASE_FIELDS
    from .review import apply, latest
    from .rules import first_periods
    tickers = list(tickers)
    has_ref = _has(con, "reference_values")
    loaded = {r["ticker"] for r in _rows(con, "select distinct ticker from reference_values where ticker in (select unnest(?))", tickers)} if has_ref else set()
    out = [{"ticker": t, "field": None, "period": None, "reference": None, "label": None, "why": "no XBRL answer loaded"} for t in tickers if t not in loaded]
    if not loaded:
        return out
    refs = _rows(con, "select ticker, field, period, value from reference_values where ticker in (select unnest(?)) and value is not null "
                      "and field in (select unnest(?)) and period in (select unnest(?)) order by ticker, field, period", tickers, list(RELEASE_FIELDS), list(MVP_YEARS))
    vals = _rows(con, 'select * from "values" where ticker in (select unnest(?))', tickers)
    excs = _rows(con, "select * from exceptions where ticker in (select unnest(?))", tickers) if _has(con, "exceptions") else []
    idx = resolutions.by_row() if idx is None else idx
    first = first_periods(vals)
    released = {(v["ticker"], v["field"], v["period"]): v for v in apply(vals, excs, ds)}
    pending = {(e["ticker"], e["field"], e["period"]) for e in open_items(excs, ds)}
    cur, decided = latest(ds), {}
    for e in excs:  # the current decisions on the findings of a cell, to name who decided it
        d = cur.get(e["exception_id"])
        if d and d["input_hash"] == e["input_hash"] and e["period"]:
            decided.setdefault((e["ticker"], e["field"], e["period"]), []).append(d)
    for r in refs:
        k = (r["ticker"], r["field"], r["period"])
        if k[2] < first.get(k[0], k[2]):
            continue  # before the company's first 10-K row: no_10k_yet names it, coverage skips it
        v = released.get(k)
        if v is not None and v.get("value") is not None:
            continue
        if k in pending:
            continue  # an open finding on the cell: the Open line counts it
        if any(_decision_by_person(d) for d in decided.get(k, [])):
            continue  # a person decided a finding on the cell
        row = {"ticker": k[0], "field": k[1], "period": k[2], "reference": r["value"], "label": (v or {}).get("label")}
        if v is None:
            out.append({**row, "why": "no row in values"})
            continue
        res = resolutions.resolution_of(idx, "values", *k[:2], "", k[2])
        st = status.of_value(v, res, {"reference": r["value"], "looked_up": True})
        if status.is_open(st):
            continue  # an open value row: the Open line counts it
        if st["by"].startswith("resolution:") and res and person_wrote(res):
            continue  # a person's resolution explains the blank
        if decided.get(k):
            out.append({**row, "why": "emptied or decided by " + ", ".join(repr(d.get("reviewer")) for d in decided[k]) + ", not a person on config.PEOPLE"})
            continue
        out.append({**row, "why": f"{st['state']} by {st['by'] or 'nothing'} with no value"})
    return out
