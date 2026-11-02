"""The taxonomy rows: one shape for spent, committed, planned, derived and company-stated AI (docs/TAXONOMY.md).

Built by code from the tables the readers filled; no agent and no estimate. Every row names the standard concept it
is an instance of (`standard_concept`), the company's own label (`reported_name`), and for an asset type the
us-gaap member it maps to (`standard_type`, from taxonomy/asset_types.yaml, with the note's words as evidence). A
reported asset type with no mapping is a row with `standard_type` empty, `mapped` false and `check` = unmapped, which
the Proof board shows as open. One whose entry no person confirmed (no `confirmed_by`, T63) carries the proposed member
in `standard_type` with `mapped` false and `check` = to_confirm (`check_method` label:to_confirm): open too.

The columns are declared once, in store.TAXONOMY (schema v11, T9–T17), in the order every row carries them:
  one meaning per column: `value_high` is a range high (planned, company_stated_ai), `change_from_prior` the derived
  year-over-year change, `kind`, `project_kind`, `status`, `location`, `capacity_mw`, `forward_looking`, `part_year`,
  `program` what `tags` used to pack (a project's kind has its own column, so `kind` means one thing), `relation` how a
  gathered figure's words relate to it; `source` keeps the internal ids and `accession`, `filed`, `source_url`,
  `source_kind` follow them to the filing; `check` is one vocabulary and `check_method` says what established it
  (status.py's `by`). `period_kind` comes from the company's fiscal calendar against the date the source was written.

Measures:
  spent      capex (the cash-flow line), segment_capex, segment_revenue (ASC 280)
  committed  purchase_obligations, finance_lease_liability (ASC 440, 842)
  derived    ppe_gross_by_type (the reported gross balance per asset type) and its year-over-year change
  planned    guidance (verbatim, forward-looking, with part-year and program flags), project (verbatim)
  company_stated_ai  a figure or share the company stated about AI, verbatim, scoped in its own words"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import quote

import yaml

from . import resolutions, store
from .status import confirmed
from .guards import part_year, program_words
from .release import split_ids

ROOT = store.ROOT
FILE = ROOT / "taxonomy" / "taxonomy.yaml"
ASSET_TYPES = ROOT / "taxonomy" / "asset_types.yaml"
STATED = ROOT / "taxonomy" / "stated_figures.yaml"  # figures companies stated, gathered from releases, calls and press: verbatim, with the source
MEASURES = store.MEASURES
COLUMNS = store.TAXONOMY_COLUMNS
CONCEPT = {"capex": "PaymentsToAcquirePropertyPlantAndEquipment", "segment_capex": "PaymentsToAcquirePropertyPlantAndEquipment (StatementBusinessSegmentsAxis)",
           "segment_revenue": "Revenues (StatementBusinessSegmentsAxis)", "purchase_commitments": "UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount",
           "finance_lease_liability": "FinanceLeaseLiability", "ppe_category": "PropertyPlantAndEquipmentGross (PropertyPlantAndEquipmentByTypeAxis)"}
CATEGORY = {"purchase_commitments": "purchase_obligations", "finance_lease_liability": "finance_lease_liability", "ppe_category": "ppe_gross_by_type"}
TEXT_KIND = {"mdna": "10-K MD&A", "earnings_release": "8-K release", "transcript": "transcript", "cfo_commentary": "cfo commentary"}  # texts.kind -> source_kind


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
    """Every column of store.TAXONOMY, in order, empty unless given; the constants (scale 1, currency USD) on every row."""
    base = dict.fromkeys(COLUMNS)
    base.update({"unit": "USD", "scale": 1, "currency": "USD", "period_kind": "reported", "mapped": True})
    base.update(kw)
    base["mapped"] = base["check"] not in ("unmapped", "to_confirm")  # T63: a mapping no person confirmed is not mapped
    base["has_value"] = base["value"] is not None or base["share"] is not None
    if not base["has_value"]:
        base["unit"] = None  # no figure, no unit; a project's capacity is in capacity_mw
    return base


def deep_link(url: str | None, row_label: str | None, cell_text: str | None) -> str | None:
    """The filing with a text fragment of the row label and the number, which scrolls the browser to the first place the
    filing shows those words: usually the row, sometimes prose (reports/*-validation.html links the same way). sec.gov
    offers no table anchor; the parsed table's id goes in `source_table`."""
    if not url:
        return None
    if not row_label:
        return url
    num = (cell_text or "").strip("()$ ").replace("—", "")
    return url + "#:~:text=" + quote(row_label) + ("," + quote(num) if num else "")


def quote_link(url: str | None, text: str | None) -> str | None:
    """A text opened at the first words of the quote."""
    if not url:
        return None
    words = " ".join((text or "").split()[:8])
    return url + "#:~:text=" + quote(words) if words else url


def _checked(label: str | None, resolution: dict | None, restated: str | None = None, definition: str | None = None) -> tuple[str, str]:
    """(check, check_method) for a reported row from its reconcile label and what is on file, the way status.state names
    `by` (status.METHOD_KINDS): agree by xbrl; no_reference and not_reported by their label; not_extracted (no cell while
    XBRL tags a value) open by its label, the way unmapped is open; a difference explained by resolution:<id>,
    definition:<name> or rule:restated_between_filings; otherwise differs, compared with xbrl."""
    if label == "agree":
        return "agree", "xbrl"
    if label in ("no_reference", "not_reported"):
        return ("no_reference", "label:no_reference") if label == "no_reference" else ("explained", "label:not_reported")
    if label == "not_extracted":
        return "not_extracted", "label:not_extracted"
    rid = (resolution or {}).get("id")
    if resolution and resolution.get("state") in ("accept", "explain"):
        return "explained", f"resolution:{rid}" if rid else "resolution"
    if definition:
        return "explained", f"definition:{definition}"
    if restated:
        return "explained", "rule:restated_between_filings"
    return "differs", "xbrl"


def fact_check(con, f: dict, idx: dict, lad: dict) -> tuple[str, str]:
    """(check, check_method) for a fact from the one ladder (ties.fact_state, T92), the state Proof gives the same fact:
    agree / xbrl; corroborated / rule:<id>_tie or reading:<accession>; no_reference / label:no_reference (citation only);
    explained by a resolution or the restatement guard; differs (rule:fact_readings_differ, or xbrl for a cell against
    its tag). An asset type's mapping check replaces it on a derived row while unmapped or unconfirmed (T63)."""
    from .ties import check_columns, fact_state
    res = resolutions.resolution_of(idx, "facts", f["ticker"], f["field"], f["dimension"] or "", f["period"])
    restated = _restated(con, f) if f["label"] == "unresolved" and not res else None
    return check_columns(fact_state(f, idx, lad, restated)[0])


def _period(year_end: dict, ticker: str, fiscal_year: str, written: str | None) -> dict:
    """period_end and period_kind for a figure about `fiscal_year` written on `written`: reported when the company's fiscal
    calendar (the 10-K that reports the year) knows the year's end and it is not after the date it was written; planned
    when the end is after that date or the calendar does not know it yet. Nothing is inferred about a year no 10-K reports."""
    end = year_end.get((ticker, fiscal_year))
    if end and (not written or end <= str(written)):
        return {"period_end": end, "period_kind": "reported"}
    return {"period_end": None, "period_kind": "planned"}


def rows(con, tickers: list[str] | None = None) -> list[dict]:
    where = "where ticker in (select unnest(?))" if tickers else ""
    p = [tickers] if tickers else []
    out = []
    types = asset_types()
    idx = resolutions.by_row()
    docs = {d["accession"]: d for d in _rows(con, "select accession, url, filed from documents")}
    cells = {e["extraction_id"]: e for e in _rows(con, f"select extraction_id, accession, table_id, row_label, cell_text from extractions {where}", *p)}
    notes = {e["extraction_id"]: e for e in _rows(con, f"select extraction_id, accession, table_id, row_label, cell_text from note_extractions {where}", *p)} if _has(con, "note_extractions") else {}
    year_end = {(v["ticker"], v["period"]): v["period_end"] for v in _rows(con, f'select ticker, period, period_end from "values" {where}', *p)}  # the company's fiscal calendar, from the 10-Ks read

    def filing(accession: str | None, cell: dict | None, kind: str) -> dict:
        d = docs.get(accession) or {}
        c = cell or {}
        return {"accession": accession, "filed": d.get("filed"), "source_table": c.get("table_id"), "source_url": deep_link(d.get("url"), c.get("row_label"), c.get("cell_text")), "source_kind": kind}

    def text_source(t: dict, text: str | None) -> dict:
        """A text's source columns: the 10-K's filing date through documents, an 8-K's from the text's date (its filing date);
        a transcript or CFO commentary has no filing, so no date."""
        filed = (docs.get(t["accession"]) or {}).get("filed") or (t["date"] if t["text_kind"] == "earnings_release" else None)
        return {"source": t["text_id"], "source_kind": TEXT_KIND[t["text_kind"]], "accession": t["accession"], "filed": filed, "source_url": quote_link(t["url"], text)}

    # spent: the cash-flow line
    for v in _rows(con, f'select ticker, field, period, period_end, value, label, extraction_ids from "values" {where}', *p):
        if v["field"] == "capex" and v["value"] is not None:
            ids = split_ids(v["extraction_ids"] or "")
            cell = cells.get(ids[0]) if ids else None
            check, how = _checked(v["label"], resolutions.resolution_of(idx, "values", v["ticker"], v["field"], "", v["period"]),
                                  definition="revenue" if v["label"] == "definition_gap" else None)
            out.append(_row(ticker=v["ticker"], fiscal_year=v["period"], period_end=v["period_end"], measure="spent", category="capex", reported_name="capital expenditures (cash-flow line)",
                            standard_concept=CONCEPT["capex"], value=v["value"], source=v["extraction_ids"], check=check, check_method=how,
                            **filing((cell or {}).get("accession") or (ids[0].split("|")[0] if ids else None), cell, "10-K table")))
    # facts: segments, committed, and the gross balances by asset type
    facts = _rows(con, f"select ticker, field, dimension, period, period_end, value, label, reference, accession, extraction_ids from facts {where} order by ticker, field, dimension, period", *p)
    from .ties import ladder
    lad = ladder(con, sorted({f["ticker"] for f in facts}))  # T92: the one ladder, as Proof reads the facts
    prev = {}
    for f in facts:
        src = f["extraction_ids"] or f["accession"]
        ids = split_ids(f["extraction_ids"] or "")  # a dimension may hold a comma ("Land, buildings and leasehold improvements"): never split inside an id
        cell = notes.get(ids[-1]) if ids else None
        check, how = fact_check(con, f, idx, lad)
        common = dict(ticker=f["ticker"], fiscal_year=f["period"], period_end=f["period_end"], value=f["value"], source=src, check=check, check_method=how, **filing(f["accession"], cell, "10-K note"))
        if f["field"] in ("segment_capex", "segment_revenue"):
            out.append(_row(measure="spent", category=f["field"], reported_name=f["dimension"], standard_concept=CONCEPT[f["field"]], **common))
        elif f["field"] in ("purchase_commitments", "finance_lease_liability"):
            out.append(_row(measure="committed", category=CATEGORY[f["field"]], reported_name=f["dimension"] or f["field"].replace("_", " "), standard_concept=CONCEPT[f["field"]], **common))
        elif f["field"] == "ppe_category":
            m = (types.get(f["ticker"]) or {}).get(f["dimension"]) or {}
            st = m.get("standard_type")
            key = (f["ticker"], f["dimension"])
            change = f["value"] - prev[key] if key in prev and prev[key] is not None and f["value"] is not None else None
            if not st:
                common.update(check="unmapped", check_method="none")
            elif not confirmed(m):  # T63: the entry is a proposal; the row says so, never agree on the strength of a value check
                common.update(check="to_confirm", check_method="label:to_confirm")
            out.append(_row(measure="derived", category="ppe_gross_by_type", reported_name=f["dimension"], standard_concept=CONCEPT["ppe_category"], standard_type=st, change_from_prior=change, **common))
            prev[key] = f["value"]
    # statements: guidance (planned, scope total) and company-stated AI (any scope ai with a figure)
    if _has(con, "ai_statements"):
        for s in _rows(con, f"""select s.ticker, s.field, s.period, s.kind, s.scope, s.class, s.amount_low, s.amount_high, s.share, s.quote, s.source, s.text_id, t.kind as text_kind, t.accession, t.url, t.date
                                 from ai_statements s join texts t on t.text_id = s.text_id {where.replace('ticker', 's.ticker')} order by s.ticker, s.field, s.period, t.date""", *p):
            flags = {"part_year": bool(part_year(s["quote"])), "program": bool(program_words(s["quote"]))}
            src = text_source(s, s["quote"])
            high = s["amount_high"] if s["amount_high"] is not None and s["amount_high"] != s["amount_low"] else None
            if s["scope"] == "total" and s["kind"] == "outlook" and s["class"] == "explicit_amount":
                out.append(_row(ticker=s["ticker"], fiscal_year=s["period"], period_kind="planned", measure="planned", category="guidance", reported_name=f"{s['field']} guidance", standard_concept="forward-looking statement (Reg S-K)",
                                value=s["amount_low"], value_high=high, period_as_stated=s["period"], quote=s["quote"], check="verbatim", check_method="quote", forward_looking=True, **flags, **src))
            elif s["scope"] == "ai" and s["class"] in ("explicit_amount", "explicit_share"):
                period = {"period_end": None, "period_kind": "planned"} if s["kind"] == "outlook" else _period(year_end, s["ticker"], s["period"], s["date"])
                out.append(_row(ticker=s["ticker"], fiscal_year=s["period"], measure="company_stated_ai", category=f"ai_{s['field']}", reported_name=f"the company's statement about AI {s['field']}", standard_concept="none: the company's own words",
                                value=s["amount_low"], value_high=high, share=s["share"], unit="USD" if s["share"] is None else "share", period_as_stated=s["period"], quote=s["quote"],
                                check="verbatim", check_method="quote", kind=s["kind"], forward_looking=s["kind"] == "outlook", **period, **flags, **src))
    # projects: planned, verbatim, the latest mention of each
    if _has(con, "projects"):
        for pj in _rows(con, f"""select p.ticker, p.period, p.name, p.kind, p.status, p.location, p.amount_low, p.amount_high, p.capacity_mw, p.quote, p.text_id, t.kind as text_kind, t.accession, t.url, t.date
                                  from projects p join texts t on t.text_id = p.text_id {where.replace('ticker', 'p.ticker') + ' and' if where else 'where'} p.latest""", *p):
            high = pj["amount_high"] if pj["amount_high"] is not None and pj["amount_high"] != pj["amount_low"] else None
            out.append(_row(ticker=pj["ticker"], fiscal_year=pj["period"], period_kind="planned", measure="planned", category="project", reported_name=pj["name"], standard_concept="none: a project the company named",
                            value=pj["amount_low"], value_high=high, period_as_stated=pj["period"], quote=pj["quote"], check="verbatim", check_method="quote",
                            project_kind=pj["kind"], status=pj["status"], location=pj["location"], capacity_mw=pj["capacity_mw"], **text_source(pj, pj["quote"])))
    if STATED.exists():
        for e in yaml.safe_load(STATED.read_text()) or []:
            if tickers and e["ticker"] not in tickers:
                continue
            src = e.get("source") or {}
            out.append(_row(ticker=e["ticker"], fiscal_year=e["period"], measure="company_stated_ai", category=f"ai_{e.get('field', 'capex')}", reported_name=f"a stated figure about AI {e.get('field', 'capex')}, gathered",
                            standard_concept="none: the company's own words, as reported", value=e["value"] if e["measure"] == "amount" else None, share=e["value"] if e["measure"] == "share" else None,
                            relation=e.get("relation", "eq"), unit="USD" if e["measure"] == "amount" else "share", period_as_stated=e["period"], quote=src.get("quote"), check="verbatim", check_method="gathered",
                            source="taxonomy/stated_figures.yaml", source_kind="gathered", source_url=src.get("url"), **_period(year_end, e["ticker"], e["period"], src.get("date"))))
    return out


def _restated(con, f: dict) -> str | None:
    """The restatement guard on a fact whose cell differs from the tag (proof._restated): a cell from a later 10-K against a
    tag from an earlier one is explained, not open."""
    from .proof import _restated as guard
    return guard(con, f["ticker"], f)


def unmapped(con, tickers: list[str] | None = None) -> list[dict]:
    """Reported asset types with no entry in taxonomy/asset_types.yaml, or an entry with no standard_type: open in the
    mapping stage (the other open items there are taxonomy.to_confirm's)."""
    types = asset_types()
    where = "where ticker in (select unnest(?))" if tickers else ""
    seen = _rows(con, f"select distinct ticker, dimension from facts {where + (' and' if where else 'where')} field = 'ppe_category' order by 1, 2", *([tickers] if tickers else []))
    return [{"ticker": s["ticker"], "reported_name": s["dimension"]} for s in seen if not ((types.get(s["ticker"]) or {}).get(s["dimension"]) or {}).get("standard_type")]  # an entry with no member is no mapping


def to_confirm(con, tickers: list[str] | None = None) -> list[dict]:
    """T63: reported asset types whose entry in taxonomy/asset_types.yaml has no `confirmed_by` (status.confirmed): a
    proposal, open on Proof and Reconcile and a G6 failure until a person confirms it. Its taxonomy rows carry the
    proposed member in `standard_type` with `mapped` false and `check` to_confirm."""
    types = asset_types()
    where = "where ticker in (select unnest(?))" if tickers else ""
    seen = _rows(con, f"select distinct ticker, dimension from facts {where + (' and' if where else 'where')} field = 'ppe_category' order by 1, 2", *([tickers] if tickers else []))
    out = []
    for s in seen:
        e = (types.get(s["ticker"]) or {}).get(s["dimension"])
        if e and e.get("standard_type") and not confirmed(e):
            out.append({"ticker": s["ticker"], "reported_name": s["dimension"], **{k: (str(v) if k == "at" and v is not None else v) for k, v in e.items()}})
    return out
