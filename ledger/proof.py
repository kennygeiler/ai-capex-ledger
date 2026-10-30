"""Proof: for a company, every figure is checked, explained or open, stage by stage (docs/PROOF.md).

Checked: it matches an independent check. Explained: it does not, and a rule, a definition, a guard or a recorded
decision says why, by name. Open: neither; the only thing a person looks at. A company is proven when nothing is
open at any stage. `board()` is the Proof home: the proven set down, the stages across; `company()` is one
company's trail; `rules()` is every rule and definition with what it closed, and the open items grouped by what
is missing."""
from __future__ import annotations

import json
from pathlib import Path

from . import definitions, resolutions, store
from .guards import part_year, program_words
from .config import PROVEN, PROVEN_WHY, industry, tracked

STAGES = ("ingest", "values", "facts", "statements", "attribution", "plans", "release")
STAGE_LABEL = {"ingest": "Ingest", "values": "Values", "facts": "Facts", "statements": "Statements", "attribution": "Attribution", "plans": "Plans and projects", "release": "Release"}
EVAL = store.ROOT / "reports" / "evaluation.json"
RULE_NAMES = {"extraction_failed": "a citation that does not resolve", "note_extraction_failed": "a cited note cell that does not resolve", "attribution_failed": "an attribution the code could not recompute"}


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _has(con, name):
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def _eval_rows() -> list[dict]:
    return json.loads(EVAL.read_text())["rows"] if EVAL.exists() else []


def company(con, ticker: str, ev_rows: list[dict] | None = None, idx: dict | None = None, defs: dict | None = None) -> dict:
    """One company's proof trail: per stage, counts of checked / explained / open and the open items with what they need."""
    t = ticker.upper()
    ev_rows = _eval_rows() if ev_rows is None else ev_rows
    idx = resolutions.by_row() if idx is None else idx
    defs = definitions.load() if defs is None else defs
    stages = {}

    # ingest: every filing's tables located and every cited cell resolving
    docs = _rows(con, "select accession, form, period, table_count, income_tables, cash_flow_tables from documents where ticker = ? order by period", t)
    exc = _rows(con, "select rule_id, severity, field, period, subject, message from exceptions where ticker = ? ", t)
    unres = [e for e in exc if e["rule_id"] in ("extraction_failed", "note_extraction_failed")]
    located = [d for d in docs if (d["income_tables"] or "") and (d["cash_flow_tables"] or "")]
    amended = [d for d in docs if d not in located and amendment_without_statements(d)]
    stages["ingest"] = _stage(checked=len(located), explained=len(amended), open=[{"what": f"{e['rule_id'].replace('_', ' ')}: {e['subject']}", "detail": e["message"][:200], "needs": "a parser or unit rule"} for e in unres]
                              + [{"what": f"{d['form']} {d['period']}: a statement table not located", "detail": f"{d['table_count']} tables parsed", "needs": "a locator rule"} for d in docs if d not in located and d not in amended],
                              items=len(docs), explained_items=[{"what": f"{d['form']} {d['period']}", "by": "rule: an amendment without financial statements (Part III only)", "detail": f"{d['table_count']} tables parsed"} for d in amended])

    # values: agree with XBRL, or explained by a definition, a decision, or 'not reported'
    vals = _rows(con, 'select field, period, value, label, basis, extraction_ids from "values" where ticker = ? order by field, period', t)
    chk = [v for v in vals if v["label"] == "agree"]
    expl, opn = [], []
    for v in vals:
        if v["label"] == "agree":
            continue
        st = resolutions.status_of(idx, "values", t, v["field"], "", v["period"])
        if v["label"] == "definition_gap":
            expl.append({"what": f"{v['field']} {v['period']}", "by": "definition: " + ("cost lines" if v["field"] == "opex" else "revenue line"), "detail": v["basis"]})
        elif v["label"] == "not_reported":
            expl.append({"what": f"{v['field']} {v['period']}", "by": "the company reports no such line", "detail": ""})
        elif st in ("accepted", "explained"):
            expl.append({"what": f"{v['field']} {v['period']}", "by": f"decision: {st}", "detail": ""})
        elif v["label"] == "no_reference":
            expl.append({"what": f"{v['field']} {v['period']}", "by": "no XBRL tag to compare", "detail": ""})
        else:
            opn.append({"what": f"{v['field']} {v['period']}: {v['label']}", "detail": f"value {v['value']}", "needs": "a definition (which line the tag measures) or a unit rule"})
    stages["values"] = _stage(len(chk), len(expl), opn, items=len(vals), explained_items=expl)

    # facts: agree with the instance, or explained by 'no tag', a restatement between filings, or a decision
    facts = _rows(con, "select field, dimension, period, value, label, reference, accession from facts where ticker = ? order by field, dimension, period", t)
    chk = [f for f in facts if f["label"] == "agree"]
    expl, opn = [], []
    for f in facts:
        if f["label"] == "agree":
            continue
        where = f"{f['field']} {f['dimension'] or ''} {f['period']}".replace("  ", " ")
        st = resolutions.status_of(idx, "facts", t, f["field"], f["dimension"] or "", f["period"])
        if f["label"] == "no_reference":
            expl.append({"what": where, "by": "no tagged counterpart in the instance", "detail": ""})
        elif st in ("accepted", "explained"):
            expl.append({"what": where, "by": f"decision: {st}", "detail": ""})
        else:
            x = _restated(con, t, f)
            if x:
                expl.append({"what": where, "by": "restated between filings", "detail": x})
            else:
                opn.append({"what": f"{where}: differs from the tag", "detail": f"cell {f['value']}, tag {f['reference']}", "needs": "a definition (which concept the table line is) once the tag is named"})
    stages["facts"] = _stage(len(chk), len(expl), opn, items=len(facts), explained_items=expl)

    # statements: every quote verified at load; part-year and program statements carry their guard
    stmts = _rows(con, "select field, period, kind, scope, class, quote from ai_statements where ticker = ?", t) if _has(con, "ai_statements") else []
    guarded = [s for s in stmts if (s["class"] == "explicit_amount" and s["kind"] == "actual" and part_year(s["quote"])) or (s["kind"] == "outlook" and program_words(s["quote"]))]
    stages["statements"] = _stage(len(stmts) - len(guarded), len(guarded), [], items=len(stmts),
                                  explained_items=[{"what": f"{s['field']} {s['period']} {s['kind']}", "by": "guard: " + ("part-year amount, not the year's actual" if part_year(s["quote"]) else "a program, not a year's guidance"), "detail": s["quote"][:160]} for s in guarded])

    # attribution: against the reference set, same scope, or explained by comparability, a decision, or no stated figure
    attr = _rows(con, "select field, period, kind, method, ai_amount, ai_share, basis from attribution where ticker = ? and kind = 'actual' order by field, period", t)
    mine = [r for r in ev_rows if r["ticker"] == t]
    chk = [r for r in mine if r["outcome"] == "agree"]
    expl, opn = [], []
    for r in mine:
        if r["outcome"] == "agree":
            continue
        key = f"AI {r.get('field', 'capex')} {r['period']}"
        st = resolutions.status_of(idx, "attribution", t, r.get("field", "capex"), "", r["period"], "actual")
        if r["outcome"] == "consistent":
            expl.append({"what": key, "by": "comparability: a wider measure within tolerance of a narrower stated one", "detail": r.get("note", "")})
        elif r["outcome"] == "not_comparable":
            expl.append({"what": key, "by": "not comparable: the reference measures something else", "detail": r.get("note", "")})
        elif r["outcome"] == "no_estimate":
            expl.append({"what": key, "by": "no estimate: the thesis gives no method here", "detail": r.get("basis", "")[:160]})
        elif st in ("accepted", "explained"):
            expl.append({"what": key, "by": f"decision: {st}", "detail": ""})
        else:
            opn.append({"what": f"{key}: ours {r['ours']} vs stated {r['relation']} {r['reference']} ({r['measure']})", "detail": r.get("basis", "")[:200], "needs": "a comparability rule (scope of the reference) or a method fix"})
    unref = [a for a in attr if a["ai_amount"] is not None and not any(r["period"] == a["period"] and r.get("field", "capex") == a["field"] for r in mine)]
    for a in attr:
        if a["ai_share"] is not None and a["ai_share"] > 1:
            if a["method"] == "segment":  # the segment's capex is accrual (additions, financed or accrued); the total is cash purchases: a known basis difference, flagged share_over_total in every export
                expl.append({"what": f"AI {a['field']} {a['period']}: share {a['ai_share']:.0%} above the total", "by": "guard: accrual segment capex against cash capex, flagged share_over_total", "detail": a["basis"][:160]})
            elif resolutions.status_of(idx, "attribution", t, a["field"], "", a["period"], "actual") not in ("accepted", "explained"):
                opn.append({"what": f"AI {a['field']} {a['period']}: share {a['ai_share']:.0%} above the total", "detail": a["basis"][:200], "needs": "a method fix: the AI amount exceeds the whole"})
    stages["attribution"] = _stage(len(chk), len(expl), opn, items=len(attr), explained_items=expl, extra={"unreferenced": len(unref), "with_amount": sum(a["ai_amount"] is not None for a in attr)})

    # plans and projects: code only; program statements excluded by guard
    from .plans import plans as _plans
    pl = _plans(con, [t])
    pj = _rows(con, "select count(*) as n, sum(case when latest then 1 else 0 end) as latest from projects where ticker = ?", t)[0] if _has(con, "projects") else {"n": 0, "latest": 0}
    stages["plans"] = _stage(len(pl) + (pj["n"] or 0), 0, [], items=len(pl) + (pj["n"] or 0), extra={"plans": len(pl), "projects": pj["n"] or 0, "projects_latest": pj["latest"] or 0})

    # release: blocks from decisions and block-severity exceptions
    blocks = [e for e in exc if e["severity"] == "block" and e["rule_id"] not in ("extraction_failed", "note_extraction_failed")]
    blocking = [k for k, r in idx.items() if k[1] == t and r["state"] == "blocks"]
    stages["release"] = _stage(1 if not blocks and not blocking else 0, 0, [{"what": f"{e['rule_id']}: {e['field'] or ''} {e['period'] or ''}", "detail": e["message"][:200], "needs": "a definition or a fix"} for e in blocks]
                               + [{"what": f"blocks: {' '.join(k[2:5]).strip()}", "detail": r["reason"][:200], "needs": "the fix the decision names"} for k, r in idx.items() if k[1] == t and r["state"] == "blocks"], items=1)

    open_total = sum(len(s["open"]) for s in stages.values())
    name = next((c["name"] for c in tracked() if c["ticker"] == t), t)
    return {"ticker": t, "name": name, "layer": industry(t), "proven": open_total == 0, "open": open_total, "why": PROVEN_WHY.get(t, ""), "in_proven_set": t in PROVEN,
            "stages": stages, "definitions": sorted((defs or {}).get(t, {}).keys())}


def amendment_without_statements(doc: dict) -> bool:
    """A 10-K/A that carries no financial statements (the common Part III amendment: directors, compensation) is not a
    filing whose statements must be located (type 72). It is the form, with few tables and no statement table."""
    # the income match is not required to be empty: in AMD's three-table amendment the locator took a compensation table for an income statement
    return str(doc.get("form", "")).endswith("/A") and (doc.get("table_count") or 0) < 10 and not (doc.get("cash_flow_tables") or "")


def _stage(checked: int, explained: int, open: list, items: int, explained_items: list | None = None, extra: dict | None = None) -> dict:
    return {"checked": checked, "explained": explained, "open": open, "items": items, "explained_items": explained_items or [], **(extra or {})}


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
    """The Proof home: every proven-set company's stage counts, and the rest of the dataset in one line."""
    ev, idx, defs = _eval_rows(), resolutions.by_row(), definitions.load()
    proven = [company(con, t, ev, idx, defs) for t in PROVEN]
    others = [c["ticker"] for c in tracked() if c["ticker"] not in PROVEN]
    n_vals = con.execute('select count(*), sum(case when label = \'agree\' then 1 else 0 end) from "values" where ticker in (select unnest(?)) and value is not null', [others]).fetchone()
    n_attr = con.execute("select count(*), count(ai_amount) from attribution where ticker in (select unnest(?)) and kind = 'actual'", [others]).fetchone()
    return {"stages": [{"id": s, "label": STAGE_LABEL[s]} for s in STAGES], "proven": proven,
            "others": {"companies": len(others), "values": n_vals[0], "values_agree": n_vals[1], "attribution": n_attr[0], "with_amount": n_attr[1], "note": "not yet proven: in the dataset as they are, widened only when the five are proven"}}


GUARDS = [
    {"id": "part_year", "kind": "guard", "where": "attribution", "what": "a stated amount that covers a quarter, a half or N months is not the year's actual", "type": 68},
    {"id": "program_words", "kind": "guard", "where": "plans", "what": "an outlook statement with program words (joint venture, once completed, through 20XX) is not a year's guidance", "type": 69},
    {"id": "restated_between_filings", "kind": "guard", "where": "facts", "what": "a cell from a later 10-K against a tag from an earlier one is a restatement", "type": None},
    {"id": "comparability", "kind": "guard", "where": "attribution", "what": "a wider measure within tolerance above a narrower stated figure is consistent, not a disagreement; a planning floor or a different basis is not comparable", "type": None},
    {"id": "accrual_vs_cash", "kind": "guard", "where": "attribution", "what": "a segment's accrual capex above the company's cash capex is a basis difference, flagged share_over_total", "type": None},
    {"id": "amendment_without_statements", "kind": "guard", "where": "ingest", "what": "a 10-K/A with few tables and no statement table is a Part III amendment, not a filing to locate statements in", "type": 72},
]


def rules(con) -> dict:
    """Every rule, guard and definition with what it closed on the proven set, and the open items by what is missing."""
    from .rules import load as load_rules
    ev, idx, defs = _eval_rows(), resolutions.by_row(), definitions.load()
    cos = [company(con, t, ev, idx, defs) for t in PROVEN]
    exc = _rows(con, "select rule_id, severity, count(*) as n from exceptions where ticker in (select unnest(?)) group by 1, 2", PROVEN)
    fired = {}
    for e in exc:
        fired[e["rule_id"]] = fired.get(e["rule_id"], 0) + e["n"]
    out = [{"id": r["id"], "kind": "rule", "severity": r["severity"], "what": r["description"], "fired": fired.get(r["id"], 0)} for r in load_rules()]
    closed = {"part_year": sum(1 for c in cos for x in c["stages"]["statements"]["explained_items"] if "part-year" in x["by"]),
              "program_words": sum(1 for c in cos for x in c["stages"]["statements"]["explained_items"] if "program" in x["by"]),
              "restated_between_filings": sum(1 for c in cos for x in c["stages"]["facts"]["explained_items"] if x["by"].startswith("restated")),
              "comparability": sum(1 for c in cos for x in c["stages"]["attribution"]["explained_items"] if x["by"].startswith("comparability") or x["by"].startswith("not comparable")),
              "accrual_vs_cash": sum(1 for c in cos for x in c["stages"]["attribution"]["explained_items"] if x["by"].startswith("guard: accrual")),
              "amendment_without_statements": sum(1 for c in cos for x in c["stages"]["ingest"]["explained_items"] if "amendment" in x["by"])}
    out += [{**g, "fired": closed.get(g["id"], 0)} for g in GUARDS]
    out += [{"id": f"{t}:{k}", "kind": "definition", "where": "values", "what": f"{t}: {k} ({(v.get('why') or '')[:120]})", "fired": 1, "by": v.get("by")} for t in PROVEN for k, v in (defs.get(t) or {}).items() if isinstance(v, dict)]
    missing = {}
    for c in cos:
        for s, st in c["stages"].items():
            for o in st["open"]:
                missing.setdefault(o["needs"], []).append({"ticker": c["ticker"], "stage": s, **o})
    return {"rules": out, "open_by_need": [{"needs": k, "items": v} for k, v in sorted(missing.items(), key=lambda kv: -len(kv[1]))], "open": sum(len(v) for v in missing.values())}
