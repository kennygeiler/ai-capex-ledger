"""Proof: for a company, every figure is checked, explained, open or blocked, stage by stage (docs/PROOF.md).

The state of every item comes from one function, `status.state` (T1): checked when an independent check agrees,
explained when a rule, a definition, a guard or a person's resolution says why by name, open when neither, blocked when
a block rule or a resolution refuses the release. Reconcile reads the same function, so the two pages count the same
row the same way. A company is proven when nothing is open or blocked at any stage. `board()` is the Proof home: the
scope down, the stages across; `company()` is one company's trail; `rules()` is every rule and definition with what it
closed, and the open items grouped by what is missing."""
from __future__ import annotations

from . import definitions, resolutions, status, store
from .guards import part_year, program_words
from .review import decisions, open_items
from .taxonomy import asset_types, rows as taxonomy_rows
from .config import PROVEN, PROVEN_WHY, SCOPE, industry, tracked

STAGES = ("ingest", "values", "facts", "statements", "mapping", "planned", "release")
STAGE_LABEL = {"ingest": "Ingest", "values": "Values", "facts": "Facts", "statements": "Statements", "mapping": "Mapping", "planned": "Planned", "release": "Release"}
NEEDS = {"values": "a definition (which line the tag measures) or a unit rule", "facts": "a definition (which concept the table line is) once the tag is named",
         "finding": "a definition or a rule for what the finding found", "mapping": "a mapping to a us-gaap PropertyPlantAndEquipmentByTypeAxis member, with the note's words",
         "mapping_confirm": "a person's confirmation of the proposed member (Reconcile, asset types: Approve, Edit or Reject)",
         "ingest": "a parser or unit rule", "locate": "a locator rule", "release": "a definition or a fix", "decision": "the fix the decision names"}


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _has(con, name):
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def _item(what: str, st: dict, detail: str = "", needs: str = "") -> dict:
    """One trail item. `key` is the strongest answer key that vouches for it (status.KEY_GRADE), None when none does."""
    return {"what": what, "state": st["state"], "by": st["by"], "key": st.get("key"), "keys": st.get("keys") or [], "reason": st["reason"], "detail": detail, "needs": needs if status.is_open(st) else ""}


KEY_GRADE = [{"id": k, "label": status.KEY_LABEL[k], "why": status.KEY_WHY[k]} for k in status.KEY_GRADE]  # the four, strongest first, for the pages


def keys_of(items: list[dict]) -> dict:
    """Rows by the strongest answer key that vouches for them (T56): {twin, second_source, tie, later_truth, none, rows};
    `none` is every row no key vouches for (a quote, a located table, a mapping, an explanation, an open item), so the
    grades sum to `rows`, the denominator."""
    out = {k: 0 for k in status.KEY_GRADE} | {"none": 0, "rows": len(items)}
    for i in items:
        out[i.get("key") or "none"] += 1
    return out


def company(con, ticker: str, idx: dict | None = None, defs: dict | None = None) -> dict:
    """One company's proof trail: per stage, every item with its state from `status.state`, counts, and the open items
    with what they need."""
    t = ticker.upper()
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
            items.append(_item(what, status.state({"check": "located"}), f"{d['table_count']} tables parsed"))
        elif amendment_without_statements(d):
            items.append(_item(what, status.state({"rule": "amendment_without_statements", "reason": "an amendment without financial statements (Part III only)"}), f"{d['table_count']} tables parsed"))
        else:
            items.append(_item(f"{what}: a statement table not located", status.state({"reason": "no income or cash-flow table located"}), f"{d['table_count']} tables parsed", NEEDS["locate"]))
    for e in exc:
        if e["rule_id"] in ("extraction_failed", "note_extraction_failed"):
            items.append(_item(f"{e['rule_id'].replace('_', ' ')}: {e['subject']}", status.of_exception(e), e["message"][:200], NEEDS["ingest"]))
    stages["ingest"] = _stage(items)

    # values: agree with XBRL, or explained by a definition, a label or a decision; a warn finding takes the state of its rows
    vals = _rows(con, 'select field, period, value, label, basis, extraction_ids from "values" where ticker = ? order by field, period', t)
    vstate = {}
    items = []
    for v in vals:
        st = status.of_value(v, resolutions.resolution_of(idx, "values", t, v["field"], "", v["period"]))
        vstate[(v["field"], v["period"])] = st
        items.append(_item(f"{v['field']} {v['period']}" + (f": {v['label']}" if status.is_open(st) else ""), st, v["basis"] if st["by"].startswith("definition") else f"value {v['value']}" if status.is_open(st) else "", NEEDS["values"]))
    decided = {e["exception_id"] for e in exc} - {e["exception_id"] for e in open_items(exc, decisions())}
    for e in exc:
        if e["severity"] != "warn" or e["exception_id"] in decided:
            continue
        ef = {"cost_of_revenue": "opex", "operating_income": "opex"}.get(e["field"], e["field"])  # read to make opex: a finding on them is about opex
        rows = [s for (f, p), s in vstate.items() if f == (ef or f) and p == (e["period"] or p)]
        st = status.of_exception(e, resolutions.resolution_of(idx, "values", t, e["field"] or "", "", e["period"] or ""), rows)
        items.append(_item(f"{e['rule_id']}: {e['field'] or ''} {e['period'] or ''}".strip(), st, e["message"][:200], NEEDS["finding"]))
    stages["values"] = _stage(items)

    # facts: agree with the instance, or explained by 'no tag', a restatement between filings, or a decision
    facts = _rows(con, "select field, dimension, period, value, label, reference, accession from facts where ticker = ? order by field, dimension, period", t)
    items = []
    for f in facts:
        where = f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " ")
        res = resolutions.resolution_of(idx, "facts", t, f["field"], f["dimension"] or "", f["period"])
        st = status.of_fact(f, res, _restated(con, t, f) if f["label"] == "unresolved" else None)
        items.append(_item(where + (": differs from the tag" if status.is_open(st) else ""), st, f"cell {f['value']}, tag {f['reference']}" if status.is_open(st) else "", NEEDS["facts"]))
    stages["facts"] = _stage(items)

    # statements: every quote verified at load; part-year and program statements carry their guard
    stmts = _rows(con, "select field, period, kind, scope, class, quote from ai_statements where ticker = ?", t) if _has(con, "ai_statements") else []
    items = []
    for s in stmts:
        what = f"{s['field']} {s['period']} {s['kind']}"
        if s["class"] == "explicit_amount" and s["kind"] == "actual" and part_year(s["quote"]):
            items.append(_item(what, status.state({"rule": "part_year", "reason": "part-year amount, not the year's actual"}), s["quote"][:160]))
        elif s["kind"] == "outlook" and program_words(s["quote"]):
            items.append(_item(what, status.state({"rule": "program_words", "reason": "a program, not a year's guidance"}), s["quote"][:160]))
        else:
            items.append(_item(what, status.state({"check": "quote"})))
    stages["statements"] = _stage(items)

    # mapping: every reported asset type mapped to a standard us-gaap member (taxonomy/asset_types.yaml) and confirmed by
    # a person (T63, status.of_mapping); an entry without confirmed_by is a proposal, open as to confirm; no entry, open
    tax = taxonomy_rows(con, [t])
    derived = [r for r in tax if r["measure"] == "derived"]
    entries = asset_types().get(t) or {}
    items = []
    for name in sorted({r["reported_name"] for r in derived}):
        e = entries.get(name)
        st = status.of_mapping(e)
        if st["state"] == "checked":
            it = _item(name, st, f"by {e.get('by')}, confirmed by {e['confirmed_by']} {e.get('confirmed_at') or ''}".strip())
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
            items.append(_item(what, status.state({"check": "quote"})))
    stages["planned"] = _stage(items, extra={"guidance": sum(r["category"] == "guidance" for r in planned), "projects": sum(r["category"] == "project" for r in planned)})

    # release: blocks from decisions and block-severity rules; the company's gate is one item
    items = [_item(f"{e['rule_id']}: {e['field'] or ''} {e['period'] or ''}".strip(), status.of_exception(e), e["message"][:200], NEEDS["release"])
             for e in exc if e["severity"] == "block" and e["rule_id"] not in ("extraction_failed", "note_extraction_failed") and e["exception_id"] not in decided]
    items += [_item(f"blocks: {' '.join(k[2:5]).strip()}", status.state({"resolution": r}), r["reason"][:200], NEEDS["decision"]) for k, r in idx.items() if k[1] == t and r["state"] == "blocks"]
    stages["release"] = _stage(items or [_item("the release gate", status.state({"check": "located", "reason": "no block rule fired and no decision blocks"}))])

    open_total = sum(len(s["open"]) for s in stages.values())
    keys = keys_of([i for s in stages.values() for i in s["all"]])
    name = next((c["name"] for c in tracked() if c["ticker"] == t), t)
    return {"ticker": t, "name": name, "layer": industry(t), "proven": open_total == 0, "open": open_total, "why": PROVEN_WHY.get(t, ""), "in_proven_set": t in PROVEN,
            "stages": stages, "keys": keys, "key_grade": KEY_GRADE, "definitions": sorted((defs or {}).get(t, {}).keys())}


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
    idx, defs = resolutions.by_row(), definitions.load()
    proven = [company(con, t, idx, defs) for t in SCOPE]
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
    from .rules import load as load_rules
    idx, defs = resolutions.by_row(), definitions.load()
    cos = [company(con, t, idx, defs) for t in SCOPE]
    exc = _rows(con, "select rule_id, severity, count(*) as n from exceptions where ticker in (select unnest(?)) group by 1, 2", SCOPE)
    fired = {}
    for e in exc:
        fired[e["rule_id"]] = fired.get(e["rule_id"], 0) + e["n"]
    out = [{"id": r["id"], "kind": "rule", "severity": r["severity"], "what": r["description"], "fired": fired.get(r["id"], 0)} for r in load_rules()]
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
    return {"rules": out, "open_by_need": [{"needs": k, "items": v} for k, v in sorted(missing.items(), key=lambda kv: -len(kv[1]))], "open": sum(len(v) for v in missing.values())}
