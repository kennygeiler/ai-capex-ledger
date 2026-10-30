"""The taxonomy rows: one shape for spent, committed, planned, derived and company-stated AI (docs/TAXONOMY.md).

Built by code from the tables the readers filled; no agent and no estimate. Every row names the standard concept it
is an instance of (`standard_concept`), the company's own label (`reported_name`), and for an asset type the
us-gaap member it maps to (`standard_type`, from taxonomy/asset_types.yaml, with the note's words as evidence). A
reported asset type with no mapping is a row with `standard_type` empty and `check` = unmapped, which the Proof
board shows as open.

Measures:
  spent      capex (the cash-flow line), segment_capex, segment_revenue (ASC 280)
  committed  purchase_obligations, finance_lease_liability (ASC 440, 842)
  derived    ppe_gross_by_type (the reported gross balance per asset type) and its year-over-year change
  planned    guidance (verbatim, forward-looking, with part-year and program tags), project (verbatim)
  company_stated_ai  a figure or share the company stated about AI, verbatim, scoped in its own words"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from . import store
from .guards import part_year, program_words
from .config import industry

ROOT = store.ROOT
FILE = ROOT / "taxonomy" / "taxonomy.yaml"
ASSET_TYPES = ROOT / "taxonomy" / "asset_types.yaml"
STATED = ROOT / "taxonomy" / "stated_figures.yaml"  # figures companies stated, gathered from releases, calls and press: verbatim, with the source
MEASURES = ("spent", "committed", "derived", "planned", "company_stated_ai")
CONCEPT = {"capex": "PaymentsToAcquirePropertyPlantAndEquipment", "segment_capex": "PaymentsToAcquirePropertyPlantAndEquipment (StatementBusinessSegmentsAxis)",
           "segment_revenue": "Revenues (StatementBusinessSegmentsAxis)", "purchase_commitments": "UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount",
           "finance_lease_liability": "FinanceLeaseLiability", "ppe_category": "PropertyPlantAndEquipmentGross (PropertyPlantAndEquipmentByTypeAxis)"}
CATEGORY = {"purchase_commitments": "purchase_obligations", "finance_lease_liability": "finance_lease_liability", "ppe_category": "ppe_gross_by_type"}
CHECK = {"agree": "agree", "no_reference": "no_reference", "unresolved": "differs", "definition_gap": "explained", "not_reported": "not_reported"}


def load() -> dict:
    return yaml.safe_load(FILE.read_text())


def asset_types() -> dict:
    return yaml.safe_load(ASSET_TYPES.read_text()) if ASSET_TYPES.exists() else {}


def sic(con, ticker: str) -> dict:
    """The SEC's SIC code and description from the cached EDGAR submissions, or empty."""
    try:
        cik = con.execute("select cik from documents where ticker = ? limit 1", [ticker]).fetchone()
        if not cik:
            return {}
        p = ROOT / "data" / "raw" / f"{int(cik[0]):010d}" / "submissions.json"
        if not p.exists():
            return {}
        d = json.loads(p.read_text())
        return {"sic": d.get("sic"), "sic_description": d.get("sicDescription")}
    except Exception:
        return {}


def _rows(con, sql, *p):
    cur = con.execute(sql, list(p))
    return [dict(zip([c[0] for c in cur.description], r)) for r in cur.fetchall()]


def _has(con, name):
    return bool(con.execute("select count(*) from information_schema.tables where table_name = ?", [name]).fetchone()[0])


def _row(**kw) -> dict:
    base = {"ticker": None, "fiscal_year": None, "measure": None, "category": None, "reported_name": None, "standard_concept": None, "standard_type": None,
            "value": None, "value_high": None, "share": None, "unit": "USD", "period_as_stated": None, "quote": None, "source": None, "check": None, "tags": ""}
    base.update(kw)
    return base


def rows(con, tickers: list[str] | None = None) -> list[dict]:
    where = "where ticker in (select unnest(?))" if tickers else ""
    p = [tickers] if tickers else []
    out = []
    types = asset_types()
    # spent: the cash-flow line
    for v in _rows(con, f'select ticker, field, period, value, label, extraction_ids from "values" {where}', *p):
        if v["field"] == "capex" and v["value"] is not None:
            out.append(_row(ticker=v["ticker"], fiscal_year=v["period"], measure="spent", category="capex", reported_name="capital expenditures (cash-flow line)", standard_concept=CONCEPT["capex"],
                            value=v["value"], source=v["extraction_ids"], check=CHECK.get(v["label"], v["label"])))
    # facts: segments, committed, and the gross balances by asset type
    facts = _rows(con, f"select ticker, field, dimension, period, value, label, accession, extraction_ids from facts {where} order by ticker, field, dimension, period", *p)
    prev = {}
    for f in facts:
        src = f["extraction_ids"] or f["accession"]
        if f["field"] in ("segment_capex", "segment_revenue"):
            out.append(_row(ticker=f["ticker"], fiscal_year=f["period"], measure="spent", category=f["field"], reported_name=f["dimension"], standard_concept=CONCEPT[f["field"]],
                            value=f["value"], source=src, check=CHECK.get(f["label"], f["label"])))
        elif f["field"] in ("purchase_commitments", "finance_lease_liability"):
            out.append(_row(ticker=f["ticker"], fiscal_year=f["period"], measure="committed", category=CATEGORY[f["field"]], reported_name=f["dimension"] or f["field"].replace("_", " "),
                            standard_concept=CONCEPT[f["field"]], value=f["value"], source=src, check=CHECK.get(f["label"], f["label"])))
        elif f["field"] == "ppe_category":
            m = (types.get(f["ticker"]) or {}).get(f["dimension"]) or {}
            st = m.get("standard_type")
            key = (f["ticker"], f["dimension"])
            change = f["value"] - prev[key] if key in prev and prev[key] is not None and f["value"] is not None else None
            out.append(_row(ticker=f["ticker"], fiscal_year=f["period"], measure="derived", category="ppe_gross_by_type", reported_name=f["dimension"], standard_concept=CONCEPT["ppe_category"],
                            standard_type=st, value=f["value"], value_high=change, source=src, check=CHECK.get(f["label"], f["label"]) if st else "unmapped",
                            tags="change_from_prior_year_in_value_high" + ("" if st else ";no_asset_type_mapping")))
            prev[key] = f["value"]
    # statements: guidance (planned, scope total) and company-stated AI (any scope ai with a figure)
    if _has(con, "ai_statements"):
        for s in _rows(con, f"""select s.ticker, s.field, s.period, s.kind, s.scope, s.class, s.amount_low, s.amount_high, s.share, s.quote, s.source, s.text_id, t.date
                                 from ai_statements s join texts t on t.text_id = s.text_id {where.replace('ticker', 's.ticker')} order by s.ticker, s.field, s.period, t.date""", *p):
            tags = []
            if part_year(s["quote"]):
                tags.append("part_year")
            if program_words(s["quote"]):
                tags.append("program")
            if s["scope"] == "total" and s["kind"] == "outlook" and s["class"] == "explicit_amount":
                out.append(_row(ticker=s["ticker"], fiscal_year=s["period"], measure="planned", category="guidance", reported_name=f"{s['field']} guidance", standard_concept="forward-looking statement (Reg S-K)",
                                value=s["amount_low"], value_high=s["amount_high"], period_as_stated=s["period"], quote=s["quote"], source=s["text_id"], check="verbatim", tags=";".join(tags + ["forward_looking"])))
            elif s["scope"] == "ai" and s["class"] in ("explicit_amount", "explicit_share"):
                out.append(_row(ticker=s["ticker"], fiscal_year=s["period"], measure="company_stated_ai", category=f"ai_{s['field']}", reported_name=f"the company's statement about AI {s['field']}", standard_concept="none: the company's own words",
                                value=s["amount_low"], value_high=s["amount_high"], share=s["share"], unit="USD" if s["share"] is None else "share", period_as_stated=s["period"], quote=s["quote"], source=s["text_id"], check="verbatim",
                                tags=";".join(tags + [f"kind:{s['kind']}", f"source:{s['source']}"])))
    # projects: planned, verbatim, the latest mention of each
    if _has(con, "projects"):
        for pj in _rows(con, f"select ticker, period, name, kind, status, location, amount_low, amount_high, capacity_mw, quote, text_id from projects {where} and latest" if where else "select ticker, period, name, kind, status, location, amount_low, amount_high, capacity_mw, quote, text_id from projects where latest", *p):
            out.append(_row(ticker=pj["ticker"], fiscal_year=pj["period"], measure="planned", category="project", reported_name=pj["name"], standard_concept="none: a project the company named",
                            value=pj["amount_low"], value_high=pj["amount_high"], unit="USD", period_as_stated=pj["period"], quote=pj["quote"], source=pj["text_id"], check="verbatim",
                            tags=";".join(x for x in [f"kind:{pj['kind']}", f"status:{pj['status']}", f"location:{pj['location']}" if pj["location"] else "", f"capacity_mw:{pj['capacity_mw']}" if pj["capacity_mw"] else ""] if x)))
    if STATED.exists():
        for e in yaml.safe_load(STATED.read_text()) or []:
            if tickers and e["ticker"] not in tickers:
                continue
            src = e.get("source") or {}
            out.append(_row(ticker=e["ticker"], fiscal_year=e["period"], measure="company_stated_ai", category=f"ai_{e.get('field', 'capex')}", reported_name=f"a stated figure about AI {e.get('field', 'capex')}, gathered",
                            standard_concept="none: the company's own words, as reported", value=e["value"] if e["measure"] == "amount" else None, share=e["value"] if e["measure"] == "share" else None,
                            unit="USD" if e["measure"] == "amount" else "share", period_as_stated=e["period"], quote=src.get("quote"), source=src.get("url"), check="verbatim (gathered)",
                            tags=";".join(x for x in [f"relation:{e.get('relation', 'eq')}", f"source:{src.get('kind', '')}", f"scope:{e.get('scope', 'same')}", f"by:{e.get('by', '')}"] if x)))
    for r in out:
        r["group"] = industry(r["ticker"])
    return out


def unmapped(con, tickers: list[str] | None = None) -> list[dict]:
    """Reported asset types with no entry in taxonomy/asset_types.yaml: the open items of the mapping stage."""
    types = asset_types()
    where = "where ticker in (select unnest(?))" if tickers else ""
    seen = _rows(con, f"select distinct ticker, dimension from facts {where + (' and' if where else 'where')} field = 'ppe_category' order by 1, 2", *([tickers] if tickers else []))
    return [{"ticker": s["ticker"], "reported_name": s["dimension"]} for s in seen if not (types.get(s["ticker"]) or {}).get(s["dimension"])]
