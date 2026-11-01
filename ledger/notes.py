"""Facts from the notes: segment capex and revenue, PP&E by category, finance leases, purchase commitments.

  segment_capex           capital expenditures per reportable segment (ASC 280 note)        flow, per segment
  segment_revenue         revenue per segment or market (segment note, revenue by market)   flow, per segment
  ppe_category            property and equipment, gross, by category (PP&E note)            balance, per category
  finance_lease_liability total finance lease liabilities (lease note)                      balance
  purchase_commitments    purchase obligations / commitments (commitments or obligations)   balance

Same shape as the statement extractions: a third agent (`notes_reader`) reads candidate note tables and cites the cell;
code resolves every citation against the parsed table. Table A `note_extractions` keeps every cell read; table B
`facts` keeps one value per company, field, dimension and fiscal year from the newest filing, labelled against the
filing's own XBRL instance where the fact is tagged with a dimension (segment or PP&E type member)."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from . import agents, config
from .extract import Invalid, render_statement, resolve
from .store import ROOT

TASKS = ROOT / "data" / "notes" / "tasks"
OUTPUTS = ROOT / "data" / "notes" / "outputs"
FIELDS = ("segment_capex", "segment_revenue", "ppe_category", "finance_lease_liability", "purchase_commitments")
DIMENSIONED = ("segment_capex", "segment_revenue", "ppe_category")
BALANCES = ("ppe_category", "finance_lease_liability", "purchase_commitments")

# Which tables to show the agent, by what introduces them and what their rows say. Loose on purpose: the agent picks.
KINDS = {
    "segments": (re.compile(r"segment|by (specialized )?market|product and service offerings|by product", re.I),
                 re.compile(r"capital expenditure|purchases? of property|additions to property|^(total )?(net )?(revenues?|sales)|data center|operating (income|loss)", re.I)),
    "ppe": (re.compile(r"property(,| and) (plant and )?equipment", re.I),
            re.compile(r"^(land|buildings?|servers?|computer|network|equipment|machinery|leasehold|construction in progress|furniture|data ?center equipment|technical infrastructure|information technology|office space|corporate and other|property and equipment, (in service|gross)|assets not yet in service)", re.I)),
    "leases": (re.compile(r"lease", re.I), re.compile(r"finance lease", re.I)),
    "commitments": (re.compile(r"purchase (obligation|commitment)|contractual obligation|commitments", re.I),
                    re.compile(r"purchase (obligation|commitment)|contractual obligation|unconditional purchase", re.I)),
}


def prompt_version() -> str:
    return agents.load()["notes_reader"]["prompt"]


def prompt_versions() -> tuple[str, ...]:
    return tuple(agents.versions("notes_reader"))


def locate(tables: list[dict], primary: set[str]) -> dict[str, list[str]]:
    """Candidate note tables by kind: introduced by the kind's words, or carrying two or more of its row labels.
    The primary statements are left out; a table can be a candidate for more than one kind."""
    out = {k: [] for k in KINDS}
    for t in tables:
        if t["id"] in primary or not t["rows"]:
            continue
        before, labels = t["before"][-300:], [r["label"] for r in t["rows"]]
        for k, (cap, row) in KINDS.items():
            hits = sum(bool(row.search(l)) for l in labels)
            if (cap.search(before) and hits) or hits >= 2:
                out[k].append(t["id"])
    return out


def make_task(parsed: dict) -> str:
    parsed = with_units(parsed)
    primary = {t["id"] for k in ("income", "cash_flow") for t in (parsed["statements"][k] or [])}
    loc = locate(parsed["tables"], primary)
    by_id = {t["id"]: t for t in parsed["tables"]}
    head = (f"# Task: {parsed['ticker']} {parsed['form']} for the fiscal year ended {parsed['period']}\n\n"
            f"Accession: {parsed['accession']}\nPrompt version: {prompt_version()}\n")
    body = [render_statement({"segments": "Segment and market tables", "ppe": "Property and equipment tables", "leases": "Lease tables",
                              "commitments": "Commitments and obligations tables"}[k], [by_id[i] for i in ids]) for k, ids in loc.items() if ids]
    return head + "\n" + "\n\n".join(body) + "\n"


def with_units(parsed: dict) -> dict:
    """The parsed filing with every note table given a unit: its own when stated with it, else the unit of the
    primary statements (unit_source "document"), the same fallback the statements use."""
    stmts = [t for k in ("income", "cash_flow") for t in (parsed["statements"][k] or [])]
    fallback = next((t for t in stmts if t.get("scale")), None)
    tables = [{**t, "unit_source": t.get("unit_source", "table")} if t.get("scale") or not fallback else
              {**t, "scale": fallback["scale"], "unit_text": fallback["unit_text"], "unit_source": "document", "unit_context": fallback.get("unit_context", "")}
              for t in parsed["tables"]]
    return {**parsed, "tables": tables}


def write_tasks(parsed_docs: list[dict]) -> list[Path]:
    TASKS.mkdir(parents=True, exist_ok=True)
    out = []
    for p in parsed_docs:
        path = TASKS / f"{p['accession']}.md"
        path.write_text(make_task(p))
        out.append(path)
    return out


def validate_output(obj: dict, accession: str) -> None:
    if not isinstance(obj, dict):
        raise Invalid("output is not a JSON object")
    for k in ("accession", "prompt_version", "values", "not_found"):
        if k not in obj:
            raise Invalid(f"missing '{k}'")
    if obj["accession"] != accession:
        raise Invalid(f"accession {obj['accession']!r} is not the task's {accession!r}")
    if obj["prompt_version"] not in (known := prompt_versions()):
        raise Invalid(f"prompt_version {obj['prompt_version']!r}, expected one of {known}")
    if not isinstance(obj["values"], list) or not isinstance(obj["not_found"], list):
        raise Invalid("'values' and 'not_found' must be lists")
    req = ("field", "dimension", "table_id", "row_label", "column_label", "cell_text", "period_end", "months", "value", "confidence")
    for i, v in enumerate(obj["values"]):
        missing = [k for k in req if k not in v]
        if missing:
            raise Invalid(f"values[{i}] missing {missing}")
        if v["field"] not in FIELDS:
            raise Invalid(f"values[{i}].field {v['field']!r} is not one of {FIELDS}")
        if (v["field"] in DIMENSIONED) != bool(v["dimension"]):
            raise Invalid(f"values[{i}]: {v['field']} {'needs' if v['field'] in DIMENSIONED else 'takes no'} dimension")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(v["period_end"])):
            raise Invalid(f"values[{i}].period_end {v['period_end']!r} is not YYYY-MM-DD")
        if v["months"] != (0 if v["field"] in BALANCES else 12):
            raise Invalid(f"values[{i}].months must be {0 if v['field'] in BALANCES else 12} for {v['field']} (0 = a balance at period_end)")
        if not isinstance(v["value"], int) or isinstance(v["value"], bool) or v["value"] < 0:
            raise Invalid(f"values[{i}].value must be a non-negative integer number of dollars")
        if not (isinstance(v["confidence"], (int, float)) and 0 <= v["confidence"] <= 1):
            raise Invalid(f"values[{i}].confidence must be between 0 and 1")
    for i, n in enumerate(obj["not_found"]):
        if not isinstance(n, dict) or n.get("field") not in FIELDS or "reason" not in n:
            raise Invalid(f"not_found[{i}] needs a field and a reason")


def resolve_note(v: dict, parsed: dict) -> dict:
    """The statement resolver, with every note value stored positive however the table shows it (a segment note may
    put capex in parentheses, as the cash-flow statement does)."""
    return resolve({**v, "field": "cost_of_revenue_note"}, with_units(parsed))  # cost_of_revenue*: stored as abs(cell)


def fact_rows(ticker: str, extractions: list[dict], reference: dict, fye_label, docs: dict) -> list[dict]:
    """Table B: per (field, dimension, fiscal year), the newest filing's value. reference: (field, dimension_key, period)
    -> XBRL value from the filing's instance, matched on a normalised member name; label says whether they agree."""
    by = {}
    for e in extractions:
        period = f"FY{fye_label(e['period_end'])}"
        by.setdefault((e["field"], e["dimension"], period), []).append(e)
    out = []
    for (f, dim, period), es in sorted(by.items(), key=lambda kv: (kv[0][0], kv[0][1] or "", kv[0][2])):
        es.sort(key=lambda e: e["filed"])
        e = es[-1]
        r = reference.get((f, norm_dim(dim), period))
        tol = max(e["scale"], 1) // 2
        label = "no_reference" if r is None else "agree" if abs(e["value"] - r) <= tol else "unresolved"
        ids = [x["extraction_id"] for x in es]
        h = hashlib.sha256(json.dumps([e["value"], ids, label, sorted({docs[x["accession"]] for x in es})]).encode()).hexdigest()[:16]
        out.append({"ticker": ticker, "field": f, "dimension": dim, "period": period, "period_end": e["period_end"], "value": e["value"],
                    "first_reported": es[0]["value"], "basis": "restated" if config.restated(es[0]["value"], e["value"], max(e["scale"], 1)) else "as_reported",
                    "label": label, "reference": r, "accession": e["accession"], "extraction_ids": ",".join(ids), "input_hash": h})
    return out


def norm_dim(s: str | None) -> str:
    """'Servers, network equipment, and software' and 'msft:ServersNetworkEquipmentAndSoftwareMember' both become
    'serversnetworkequipmentandsoftware'."""
    if not s:
        return ""
    s = s.split(":")[-1].removesuffix("Member")
    return re.sub(r"[^a-z0-9]", "", s.lower().replace("&", "and"))
