"""The DuckDB store, its contracts, and the data dictionary, all generated from one schema definition.

Every table is declared once in SCHEMA. From it come:
  - the DDL (`init`),
  - the write-time contract checks (`write` rejects a bad row before it reaches the database, and says why),
  - docs/DATA_DICTIONARY.md (`data_dictionary`).

Money is stored as BIGINT US dollars, unscaled: $96,221 million is 96221000000. No floats for money.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
import os
from pathlib import Path

import duckdb

from . import status as _status  # METHOD_KINDS: the check_method vocabulary, one place

ROOT = Path(os.environ["LEDGER_ROOT"]).resolve() if os.environ.get("LEDGER_ROOT") else Path(__file__).resolve().parents[1]  # LEDGER_ROOT: the golden harness runs the pipeline in a copy of the repo layout
DEFAULT_DB = ROOT / "data" / "ledger.duckdb"
SCHEMA_VERSION = 11  # v11: the taxonomy rows take one shape (T9–T17: group dropped, change_from_prior, tags unpacked, the source followed, one check vocabulary, mapped, has_value, periods, units); they are computed by ledger/taxonomy.py, not stored, so nothing migrates: the bump marks the packet shape. v10: ai_spend.ai_amount dropped; v9: projects table

FIELDS = ("revenue", "cost_of_revenue", "cost_of_revenue_part", "operating_income", "capex", "opex")
NOTE_FIELDS = ("segment_capex", "segment_revenue", "ppe_category", "finance_lease_liability", "purchase_commitments")  # ledger.notes.FIELDS
KINDS = ("accept", "override", "reject")  # what a person can decide about an exception
YEAR = re.compile(r"^FY\d{4}$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
ACCESSION = re.compile(r"^\d{10}-\d{2}-\d{6}$")


@dataclass(frozen=True)
class Col:
    name: str
    type: str  # DuckDB type
    doc: str
    nullable: bool = False
    enum: tuple[str, ...] | None = None
    pattern: re.Pattern | None = None


@dataclass(frozen=True)
class Table:
    name: str
    doc: str
    cols: tuple[Col, ...]
    key: tuple[str, ...]


def _c(name, type_, doc, **kw):
    return Col(name, type_, doc, **kw)


TICKER = _c("ticker", "VARCHAR", "Company ticker, e.g. NVDA.", pattern=re.compile(r"^[A-Z][A-Z0-9.\-]{0,9}$"))
FIELD = _c("field", "VARCHAR", "revenue, capex or opex (released); cost_of_revenue and operating_income (read to compute opex).", enum=FIELDS)
PERIOD = _c("period", "VARCHAR", "The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026).", pattern=YEAR)
ACCN = _c("accession", "VARCHAR", "SEC accession number of the filing, e.g. 0001045810-26-000075.", pattern=ACCESSION)

SCHEMA: tuple[Table, ...] = (
    Table("documents", "One row per filing's primary document: what was fetched and how it was parsed.", (
        ACCN, TICKER,
        _c("cik", "INTEGER", "SEC Central Index Key."),
        _c("form", "VARCHAR", "Form type: 10-K, or a 10-K/A that carries the financial statements.", enum=("10-K", "10-K/A")),
        _c("period", "VARCHAR", "Report period end date (YYYY-MM-DD).", pattern=DATE),
        _c("filed", "VARCHAR", "Filing date (YYYY-MM-DD).", pattern=DATE),
        _c("url", "VARCHAR", "Primary document URL on sec.gov."),
        _c("sha256", "VARCHAR", "SHA-256 of the document bytes as fetched.", pattern=re.compile(r"^[0-9a-f]{64}$")),
        _c("bytes", "BIGINT", "Size of the document."),
        _c("parser_version", "VARCHAR", "Table parser version that produced tables_path."),
        _c("table_count", "INTEGER", "Tables with at least one number."),
        _c("tables_path", "VARCHAR", "Parsed tables JSON, relative to the repo root."),
        _c("income_tables", "VARCHAR", "Table IDs of the income statement, comma-separated.", nullable=True),
        _c("cash_flow_tables", "VARCHAR", "Table IDs of the cash-flow statement, comma-separated.", nullable=True),
    ), key=("accession",)),
    Table("reference_values", "XBRL values from the reference pipeline (SEC companyfacts). Evidence for reconciliation, not truth.", (
        TICKER, FIELD, PERIOD,
        _c("value", "BIGINT", "US dollars, unscaled."),
        _c("method", "VARCHAR", "reported, or derived (opex = revenue − cost of revenue − operating income)."),
        _c("concept", "VARCHAR", "XBRL concept, e.g. us-gaap:Revenues."),
        _c("period_start", "VARCHAR", "Fiscal period start.", pattern=DATE),
        _c("period_end", "VARCHAR", "Fiscal period end.", pattern=DATE),
        ACCN,
        _c("restated", "BOOLEAN", "True if a later filing moved the value by more than config.RESTATEMENT_TOLERANCE (half the unit the first figure is rounded to)."),
        _c("original_value", "BIGINT", "First-filed value when restated.", nullable=True),
    ), key=("ticker", "field", "period")),
    Table("extractions", "One row per value an agent read from a 10-K column (one fiscal year).", (
        _c("extraction_id", "VARCHAR", "Stable ID: accession|field|period_start|period_end."),
        ACCN, TICKER, FIELD,
        _c("period_start", "VARCHAR", "Start of the period the column covers.", pattern=DATE),
        _c("period_end", "VARCHAR", "End of the period the column covers.", pattern=DATE),
        _c("value", "BIGINT", "US dollars, unscaled (cell value × scale; sign as the field defines it, capex positive)."),
        _c("unit_stated", "VARCHAR", "Unit text as written, e.g. '(In millions, except per share data)'."),
        _c("unit_source", "VARCHAR", "Where the unit was stated.", enum=("table", "statement", "document")),
        _c("scale", "BIGINT", "1000, 1000000 or 1000000000.", enum=None),
        _c("table_id", "VARCHAR", "Cited table, e.g. t0007."),
        _c("row_label", "VARCHAR", "Cited row label, verbatim."),
        _c("column_label", "VARCHAR", "Cited column label, verbatim."),
        _c("cell_text", "VARCHAR", "Cited cell text, verbatim, e.g. '(4,434)'."),
        _c("confidence", "DOUBLE", "Agent's confidence, 0 to 1."),
        _c("notes", "VARCHAR", "Agent's notes.", nullable=True),
        _c("prompt_version", "VARCHAR", "Prompt file and version, e.g. statements@v1."),
        _c("run_id", "VARCHAR", "Run that produced it."),
    ), key=("extraction_id",)),
    Table("values", "One value per (ticker, field, fiscal year): what a release ships.", (
        TICKER, FIELD, PERIOD,
        _c("period_end", "VARCHAR", "Fiscal year end date.", pattern=DATE),
        _c("value", "BIGINT", "US dollars, unscaled. Null when source is missing.", nullable=True),
        _c("source", "VARCHAR", "Where the shipped value comes from.", enum=("agent", "override", "missing")),
        _c("method", "VARCHAR", "reported (one cell), or computed (opex from three cells of the same 10-K column).", enum=("reported", "computed")),
        _c("label", "VARCHAR", "Reconciliation against the reference; not_reported when the company has no such line and XBRL tags none either; not_extracted when the 10-K has no cell for it but XBRL tags a value (open: the reader missed it, or the statement table was mislocated).", enum=("agree", "agent_wrong", "xbrl_wrong", "definition_gap", "unresolved", "no_reference", "not_reported", "not_extracted")),
        _c("basis", "VARCHAR", "as_reported, or restated: a later 10-K moved the first-reported figure by more than config.RESTATEMENT_TOLERANCE (half a rounding unit of the cell's scale).", enum=("as_reported", "restated")),
        _c("first_reported", "BIGINT", "The figure in the first 10-K that reported this fiscal year.", nullable=True),
        _c("extraction_ids", "VARCHAR", "Extractions used, comma-separated.", nullable=True),
        _c("input_hash", "VARCHAR", "Hash of everything this value depends on; decisions re-apply only when it matches."),
    ), key=("ticker", "field", "period")),
    Table("texts", "Every text the AI spend reader reads: 10-K MD&A, 8-K earnings releases, investor-page transcripts and CFO commentary, with the fiscal period each speaks to.", (
        _c("text_id", "VARCHAR", "Stable ID: ticker|kind|period_end|url hash."),
        TICKER,
        _c("kind", "VARCHAR", "mdna, earnings_release, transcript or cfo_commentary.", enum=("mdna", "earnings_release", "transcript", "cfo_commentary")),
        _c("accession", "VARCHAR", "SEC accession when the text is a filing exhibit or section.", nullable=True, pattern=ACCESSION),
        _c("url", "VARCHAR", "Where it came from."),
        _c("date", "VARCHAR", "Filing or quarter-end date.", pattern=DATE),
        _c("period_end", "VARCHAR", "The fiscal period end the text speaks to (year end for MD&A, quarter end otherwise).", pattern=DATE),
        _c("fiscal_year", "INTEGER", "The company's fiscal year of that period."),
        _c("path", "VARCHAR", "Plain text on disk, relative to the repo root."),
        _c("sha256", "VARCHAR", "SHA-256 of the text.", pattern=re.compile(r"^[0-9a-f]{64}$")),
        _c("chars", "INTEGER", "Length of the text."),
    ), key=("text_id",)),
    Table("ai_statements", "Table A for AI spend: every statement an agent read in a text about AI's part of capex or opex, verbatim.", (
        _c("statement_id", "VARCHAR", "Stable ID: text_id|field|period|kind|n."),
        _c("text_id", "VARCHAR", "The text it was read from (texts)."),
        _c("source", "VARCHAR", "mdna, earnings_release, transcript or cfo_commentary.", enum=("mdna", "earnings_release", "transcript", "cfo_commentary")),
        _c("accession", "VARCHAR", "SEC accession when the text is a filing.", nullable=True, pattern=ACCESSION),
        TICKER,
        _c("field", "VARCHAR", "capex, opex or revenue.", enum=("capex", "opex", "revenue")),
        PERIOD,
        _c("kind", "VARCHAR", "actual: the fiscal year the filing reports. outlook: a later year.", enum=("actual", "outlook")),
        _c("scope", "VARCHAR", "ai: the figure is the AI part. total: the company's total, with AI named as a driver.", enum=("ai", "total")),
        _c("class", "VARCHAR", "explicit_amount, explicit_share or qualitative.", enum=("explicit_amount", "explicit_share", "qualitative")),
        _c("amount_low", "BIGINT", "Stated amount or low end of a range, US dollars.", nullable=True),
        _c("amount_high", "BIGINT", "Stated amount or high end of a range, US dollars.", nullable=True),
        _c("share", "DOUBLE", "Stated share, 0 to 1.", nullable=True),
        _c("quote", "VARCHAR", "The sentence, verbatim from the filing."),
        _c("passage", "VARCHAR", "Passage tag in the task, e.g. p03."),
        _c("confidence", "DOUBLE", "Agent's confidence, 0 to 1."),
        _c("notes", "VARCHAR", "Agent's notes.", nullable=True),
        _c("prompt_version", "VARCHAR", "Prompt file and version, e.g. aispend@v1."),
        _c("run_id", "VARCHAR", "Run that produced it."),
    ), key=("statement_id",)),
    Table("ai_spend", "Table B for AI spend: per company, field, fiscal year and kind, the most specific statement from the newest filing, as stated: an amount range, a share, or words only.", (
        TICKER,
        _c("field", "VARCHAR", "capex, opex or revenue.", enum=("capex", "opex", "revenue")),
        PERIOD,
        _c("kind", "VARCHAR", "actual or outlook.", enum=("actual", "outlook")),
        _c("scope", "VARCHAR", "ai or total (see ai_statements).", enum=("ai", "total")),
        _c("class", "VARCHAR", "explicit_amount, explicit_share or qualitative.", enum=("explicit_amount", "explicit_share", "qualitative")),
        _c("amount_low", "BIGINT", "As stated.", nullable=True),
        _c("amount_high", "BIGINT", "As stated.", nullable=True),
        _c("share", "DOUBLE", "As stated.", nullable=True),
        _c("quote", "VARCHAR", "The sentence behind the row."),
        _c("text_id", "VARCHAR", "The text the quote comes from (texts)."),
        _c("source", "VARCHAR", "mdna, earnings_release, transcript or cfo_commentary.", enum=("mdna", "earnings_release", "transcript", "cfo_commentary")),
        _c("accession", "VARCHAR", "SEC accession when the text is a filing.", nullable=True, pattern=ACCESSION),
        _c("statement_ids", "VARCHAR", "Statements considered, comma-separated."),
        _c("input_hash", "VARCHAR", "Hash of everything this row depends on."),
    ), key=("ticker", "field", "period", "kind")),
    Table("note_extractions", "Table A for note facts: every cell the notes reader cited (segment capex and revenue, PP&E by category, finance lease liabilities, purchase commitments).", (
        _c("extraction_id", "VARCHAR", "Stable ID: accession|field|dimension|period_end."),
        ACCN, TICKER,
        _c("field", "VARCHAR", "segment_capex, segment_revenue, ppe_category, finance_lease_liability or purchase_commitments.", enum=("segment_capex", "segment_revenue", "ppe_category", "finance_lease_liability", "purchase_commitments")),
        _c("dimension", "VARCHAR", "Segment, market or PP&E category, as written in the filing. Null for a company total.", nullable=True),
        _c("period_end", "VARCHAR", "Fiscal year end the column refers to.", pattern=DATE),
        _c("months", "INTEGER", "12 for a flow (capex, revenue); 0 for a balance at period_end."),
        _c("value", "BIGINT", "US dollars, unscaled, positive."),
        _c("unit_stated", "VARCHAR", "Unit text as written.", nullable=True),
        _c("unit_source", "VARCHAR", "Where the unit was stated.", enum=("table", "statement", "document")),
        _c("scale", "BIGINT", "1, 1000, 1000000 or 1000000000."),
        _c("table_id", "VARCHAR", "Cited table."),
        _c("row_label", "VARCHAR", "Cited row label, verbatim."),
        _c("column_label", "VARCHAR", "Cited column label, verbatim."),
        _c("cell_text", "VARCHAR", "Cited cell text, verbatim."),
        _c("confidence", "DOUBLE", "Agent's confidence, 0 to 1."),
        _c("notes", "VARCHAR", "Agent's notes.", nullable=True),
        _c("prompt_version", "VARCHAR", "Prompt file and version, e.g. notes@v1."),
        _c("run_id", "VARCHAR", "Run that produced it."),
    ), key=("extraction_id",)),
    Table("facts", "Table B for note facts: one value per company, field, dimension and fiscal year from the newest filing, labelled against the filing's XBRL instance where the fact carries a matching member.", (
        TICKER,
        _c("field", "VARCHAR", "As in note_extractions.", enum=("segment_capex", "segment_revenue", "ppe_category", "finance_lease_liability", "purchase_commitments")),
        _c("dimension", "VARCHAR", "Segment, market or category; empty string for a company total (part of the key).",),
        PERIOD,
        _c("period_end", "VARCHAR", "Fiscal year end date.", pattern=DATE),
        _c("value", "BIGINT", "US dollars, unscaled."),
        _c("first_reported", "BIGINT", "The figure in the first 10-K that reported it."),
        _c("basis", "VARCHAR", "as_reported, or restated when a later 10-K moved it by more than config.RESTATEMENT_TOLERANCE (half a rounding unit).", enum=("as_reported", "restated")),
        _c("label", "VARCHAR", "agree or unresolved against the XBRL instance member; no_reference when no tagged fact matches the dimension.", enum=("agree", "unresolved", "no_reference")),
        _c("reference", "BIGINT", "The XBRL value compared with, when any.", nullable=True),
        ACCN,
        _c("extraction_ids", "VARCHAR", "Extractions used, comma-separated."),
        _c("input_hash", "VARCHAR", "Hash of everything this row depends on."),
    ), key=("ticker", "field", "dimension", "period")),
    Table("projects", "Project-level investment: every named project a text mentions (data center, fab, plant, power, GPU cluster, commitment), with size and stage; latest marks the newest mention per project.", (
        _c("project_id", "VARCHAR", "text_id|n."),
        TICKER,
        _c("text_id", "VARCHAR", "The text it was read from (texts)."),
        _c("source", "VARCHAR", "mdna, earnings_release, transcript or cfo_commentary.", enum=("mdna", "earnings_release", "transcript", "cfo_commentary")),
        _c("accession", "VARCHAR", "SEC accession when the text is a filing.", nullable=True, pattern=ACCESSION),
        _c("date", "VARCHAR", "The text's date.", pattern=DATE),
        PERIOD,
        _c("name", "VARCHAR", "The project as the company names it."),
        _c("kind", "VARCHAR", "data_center, fab, plant, power, gpu_cluster, cloud_commitment, network or other.", enum=("data_center", "fab", "plant", "power", "gpu_cluster", "cloud_commitment", "network", "other")),
        _c("status", "VARCHAR", "announced, under_construction, in_service, contracted or cancelled.", enum=("announced", "under_construction", "in_service", "contracted", "cancelled")),
        _c("location", "VARCHAR", "Place as stated.", nullable=True),
        _c("counterparty", "VARCHAR", "The other party when stated.", nullable=True),
        _c("amount_low", "BIGINT", "Stated size, US dollars.", nullable=True),
        _c("amount_high", "BIGINT", "Stated size, US dollars.", nullable=True),
        _c("capacity_mw", "DOUBLE", "Megawatts when stated.", nullable=True),
        _c("gpus", "BIGINT", "GPUs when stated.", nullable=True),
        _c("announced", "VARCHAR", "Date announced, when stated.", nullable=True),
        _c("in_service", "VARCHAR", "Date in service or expected, when stated.", nullable=True),
        _c("quote", "VARCHAR", "The sentence, verbatim."),
        _c("passage", "VARCHAR", "Passage tag in the task."),
        _c("confidence", "DOUBLE", "Agent's confidence."),
        _c("latest", "BOOLEAN", "True on the newest mention of this project for the company."),
        _c("prompt_version", "VARCHAR", "Prompt version."),
        _c("run_id", "VARCHAR", "Run that produced it."),
    ), key=("project_id",)),
    Table("rules", "The rule registry as loaded from rules/*.yaml.", (
        _c("rule_id", "VARCHAR", "Rule ID, e.g. unit_scale."),
        _c("severity", "VARCHAR", "block, warn or info.", enum=("block", "warn", "info")),
        _c("description", "VARCHAR", "What it checks."),
        _c("rationale", "VARCHAR", "Why the check exists: the judgement it encodes."),
        _c("check_name", "VARCHAR", "Python check function."),
        _c("params", "VARCHAR", "Check parameters, JSON."),
        _c("file_sha256", "VARCHAR", "Hash of the YAML file, so a rule change is visible in a release diff."),
    ), key=("rule_id",)),
    Table("exceptions", "One rule firing on one value.", (
        _c("exception_id", "VARCHAR", "Stable ID: rule_id|ticker|field|period (or the extraction/document it fired on)."),
        _c("rule_id", "VARCHAR", "Rule that fired."),
        _c("severity", "VARCHAR", "Copied from the rule at run time.", enum=("block", "warn", "info")),
        TICKER,
        _c("field", "VARCHAR", "Line item, if the rule is field-level: a values field, or a note field (T92: the ties and readings of the facts).", nullable=True, enum=FIELDS + NOTE_FIELDS),
        _c("period", "VARCHAR", "Fiscal year, if year-level.", nullable=True, pattern=YEAR),
        _c("subject", "VARCHAR", "What it fired on when not a released value: an accession or extraction ID.", nullable=True),
        _c("message", "VARCHAR", "Plain-language explanation with the numbers."),
        _c("input_hash", "VARCHAR", "Hash of the inputs it was raised on."),
    ), key=("exception_id",)),
    Table("decisions", "A person's resolution of an exception. Append-only: a later decision supersedes, never edits.", (
        _c("decision_id", "VARCHAR", "Unique ID."),
        _c("exception_id", "VARCHAR", "Exception decided."),
        _c("kind", "VARCHAR", "accept, override or reject.", enum=KINDS),
        _c("value", "BIGINT", "Override value, US dollars, unscaled.", nullable=True),
        _c("reason", "VARCHAR", "Why. Required for every kind."),
        _c("reviewer", "VARCHAR", "Who decided."),
        _c("decided_at", "VARCHAR", "UTC timestamp, ISO 8601."),
        _c("input_hash", "VARCHAR", "Input hash of the exception when decided."),
        _c("supersedes", "VARCHAR", "Earlier decision this replaces.", nullable=True),
    ), key=("decision_id",)),
    Table("runs", "One row per pipeline or agent step: what ran, on what, with which versions, and how it went.", (
        _c("run_id", "VARCHAR", "Run ID."),
        _c("step", "VARCHAR", "Step name.", enum=("run", "ingest", "parse", "extract", "reconcile", "texts", "aispend", "notes", "attribution", "eval", "rules", "faults", "evidence", "report", "review", "score", "release", "projects", "cost", "publish", "mapper")),
        _c("subject", "VARCHAR", "What it ran on (accession, ticker, release).", nullable=True),
        _c("started_at", "VARCHAR", "UTC timestamp."),
        _c("seconds", "DOUBLE", "Wall-clock duration."),
        _c("outcome", "VARCHAR", "ok, failed or skipped.", enum=("ok", "failed", "skipped")),
        _c("versions", "VARCHAR", "Versions used (parser, prompt, model, rules), JSON."),
        _c("detail", "VARCHAR", "Anything else worth keeping (tokens, cost, retries, error), JSON.", nullable=True),
    ), key=("run_id", "step", "subject")),
)
TABLES = {t.name: t for t in SCHEMA}

# The taxonomy rows (docs/TAXONOMY.md): the one shape of the dataset, `taxonomy.csv` in a release and /api/v1/taxonomy.
# Not a stored table: ledger/taxonomy.py builds the rows from the tables above on every read, in this column order,
# and the golden test freezes them (fixtures/expected/taxonomy.csv). Declared here so the dictionary, the packet README
# and tests/test_columns.py read one definition. Schema v11 (T9–T17). `layer` and `proven` are added by the API.
MEASURES = ("spent", "committed", "derived", "planned", "company_stated_ai")
CHECKS = ("agree", "explained", "differs", "no_reference", "not_extracted", "unmapped", "to_confirm", "verbatim")
SOURCE_KINDS = ("10-K table", "10-K note", "10-K MD&A", "8-K release", "transcript", "cfo commentary", "gathered")
TAXONOMY = Table("taxonomy", "One row per company, fiscal year, measure and category: an instance of a published standard's concept with the company's own label beside it, "
                 "or a verbatim quote. Built by code from the tables above; no agent, nothing estimated.", (
    TICKER,
    _c("fiscal_year", "VARCHAR", "The company's fiscal year label, e.g. FY2025.", pattern=YEAR),
    _c("period_end", "VARCHAR", "The fiscal period's last day, from the company's own fiscal calendar (the 10-K that reports that year), on every row whose period_kind is reported; empty on a planned row.", nullable=True, pattern=DATE),
    _c("period_kind", "VARCHAR", "reported: the figure is for a fiscal period that had ended when the source was written. planned: the period's end is after the source's date, or the calendar does not know it yet.", enum=("reported", "planned")),
    _c("measure", "VARCHAR", "spent, committed, derived (a reported balance and its arithmetic change), planned (verbatim) or company_stated_ai (verbatim).", enum=MEASURES),
    _c("category", "VARCHAR", "The taxonomy id (taxonomy/taxonomy.yaml): capex, segment_capex, segment_revenue, purchase_obligations, finance_lease_liability, ppe_gross_by_type, guidance, project, ai_capex, ai_opex, ai_revenue."),
    _c("reported_name", "VARCHAR", "The company's own label: the line, segment, asset type, project or statement as written."),
    _c("standard_concept", "VARCHAR", "The us-gaap concept (and axis) the row is an instance of; 'forward-looking statement (Reg S-K)' for guidance; 'none: ...' for a verbatim row with no standard."),
    _c("standard_type", "VARCHAR", "For an asset type: the us-gaap PropertyPlantAndEquipmentByTypeAxis member it maps to (taxonomy/asset_types.yaml); on a to_confirm row, the member proposed and not yet confirmed by a person. Empty elsewhere, and on an unmapped asset type.", nullable=True),
    _c("mapped", "BOOLEAN", "False exactly when check is unmapped (a reported asset type with no entry in taxonomy/asset_types.yaml) or to_confirm (an entry no person confirmed, T63). True on every other row."),
    _c("value", "BIGINT", "The figure as reported or quoted, in `unit`: a dollar amount, or the low end of a stated range. Empty when the company gave no figure (has_value false) or stated a share instead.", nullable=True),
    _c("value_high", "BIGINT", "The high end of a stated range, on planned and company_stated_ai rows only, and only when the range has two ends. Never anything else.", nullable=True),
    _c("change_from_prior", "BIGINT", "On derived rows only: this year's reported gross balance minus the prior year's, for the same asset type. Arithmetic on two reported figures; empty on the first year.", nullable=True),
    _c("share", "DOUBLE", "A share the company stated, 0 to 1, on company_stated_ai rows whose unit is share. Empty elsewhere.", nullable=True),
    _c("relation", "VARCHAR", "On a gathered figure: how the company's words relate to value or share: eq (the figure), ge (at least), le (at most). Empty elsewhere.", nullable=True, enum=("eq", "ge", "le")),
    _c("has_value", "BOOLEAN", "True when the row carries a figure (value or share). False on a project or statement the company named without an amount."),
    _c("unit", "VARCHAR", "USD for a dollar amount; share for a stated share. Empty when has_value is false. A project's capacity is in capacity_mw, in megawatts.", nullable=True, enum=("USD", "share")),
    _c("scale", "BIGINT", "Always 1: every amount is in whole units (whole dollars, a share of one, megawatts)."),
    _c("currency", "VARCHAR", "Always USD: the currency of value, value_high and change_from_prior.", enum=("USD",)),
    _c("period_as_stated", "VARCHAR", "On a verbatim row: the period the company named, as the reader labelled it (the fiscal year). Empty on reported rows.", nullable=True),
    _c("quote", "VARCHAR", "On a verbatim row: the sentence, as written in the source. Empty on reported rows.", nullable=True),
    _c("kind", "VARCHAR", "On a company_stated_ai statement read from a text: actual (the period the text reports) or outlook (a later period). Empty elsewhere.", nullable=True, enum=("actual", "outlook")),
    _c("project_kind", "VARCHAR", "On a project: data_center, fab, plant, power, gpu_cluster, cloud_commitment, network or other. Empty elsewhere.", nullable=True,
       enum=("data_center", "fab", "plant", "power", "gpu_cluster", "cloud_commitment", "network", "other")),
    _c("status", "VARCHAR", "On a project: announced, under_construction, in_service, contracted or cancelled, as stated. Empty elsewhere.", nullable=True, enum=("announced", "under_construction", "in_service", "contracted", "cancelled")),
    _c("location", "VARCHAR", "On a project: the place as stated. Empty elsewhere.", nullable=True),
    _c("capacity_mw", "DOUBLE", "On a project: megawatts when stated. Empty elsewhere.", nullable=True),
    _c("forward_looking", "BOOLEAN", "On a statement read from a text: True for guidance and an outlook statement (a forward-looking statement under Regulation S-K), False for a figure the text reports as actual. Empty where the source does not say: spent, committed and derived rows, projects, gathered figures.", nullable=True),
    _c("part_year", "BOOLEAN", "On a statement read from a text: True when its words cover part of a year (a quarter, a half), by rules/guards; the figure is never turned into a year. Empty elsewhere.", nullable=True),
    _c("program", "BOOLEAN", "On a statement read from a text: True when its words describe a multi-year program rather than a year's figure, by rules/guards. Empty elsewhere.", nullable=True),
    _c("source", "VARCHAR", "The internal id of what the row was read from: extraction ids (values), the fact's extraction ids (facts), a text id (statements, projects), or taxonomy/stated_figures.yaml."),
    _c("source_kind", "VARCHAR", "Where the figure is written: a 10-K statement table, a 10-K note, the 10-K's MD&A, an 8-K earnings release, a transcript, CFO commentary, or gathered (a figure a person recorded with its URL and quote).", enum=SOURCE_KINDS),
    _c("accession", "VARCHAR", "SEC accession number of the filing the row was read from. Empty when the source is not a filing.", nullable=True, pattern=ACCESSION),
    _c("filed", "VARCHAR", "The date the source was filed with the SEC (documents.filed for a 10-K, the 8-K's filing date for a release). Empty for a transcript, CFO commentary or a gathered figure, which have no filing date.", nullable=True, pattern=DATE),
    _c("source_table", "VARCHAR", "For a 10-K cell: the id of the parsed table the cell was read from (e.g. t0035), the table Kenny's Data Emporium shows; it is the parser's id, not an anchor on sec.gov. Empty elsewhere.", nullable=True, pattern=re.compile(r"^t\d{4}$")),
    _c("source_url", "VARCHAR", "A URL that opens the source. For a 10-K cell: the filing on sec.gov with a `#:~:text=<row label>,<number>` fragment that scrolls the browser to the first place the filing shows those words, usually the row, sometimes prose; sec.gov offers no table anchor. For a statement or project: the text with the quote's first words as the fragment. For a gathered figure: the page recorded with it.", nullable=True),
    _c("check", "VARCHAR", "agree: matches the SEC's XBRL. explained: differs and something on file says why (check_method). differs: differs and nothing on file says why. no_reference: no XBRL fact to compare. not_extracted: no cell read, while XBRL tags a value (open). unmapped: an asset type with no standard member. to_confirm: an asset type whose mapping no person has confirmed (no confirmed_by, T63; open, the value check not shown). verbatim: a quote verified against its text.", enum=CHECKS),
    _c("check_method", "VARCHAR", "What established the check, as status.py names `by`: `<kind>` or `<kind>:<id>` with the kind one of status.METHOD_KINDS: xbrl, quote, gathered, "
       "none (nothing to compare against), rule:<id>, definition:<name>, resolution:<id>, label:<label>, mapping:<member>. An open vocabulary: a later answer key adds a kind there.",
       pattern=re.compile(r"^(" + "|".join(_status.METHOD_KINDS) + r")(:.+)?$")),
), key=("ticker", "fiscal_year", "measure", "category", "reported_name", "source"))
TAXONOMY_COLUMNS = tuple(c.name for c in TAXONOMY.cols)


class ContractError(ValueError):
    pass


def _ddl(t: Table) -> str:
    cols = [f'"{c.name}" {c.type}{"" if c.nullable else " NOT NULL"}' for c in t.cols]
    cols.append(f"PRIMARY KEY ({', '.join(t.key)})")
    return f'CREATE TABLE IF NOT EXISTS "{t.name}" (\n  ' + ",\n  ".join(cols) + "\n)"


def init(path: Path | str = DEFAULT_DB) -> duckdb.DuckDBPyConnection:
    """Open (creating if needed) the store with every table in SCHEMA."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path))
    have = con.execute("select v from _meta where k = 'schema_version'").fetchone() if con.execute("select count(*) from information_schema.tables where table_name = '_meta'").fetchone()[0] else None
    if have and int(have[0]) < 7:  # v7 reshaped the AI-spend tables (text_id, source); they are rebuilt by `ledger aispend --load`
        for t in ("ai_statements", "ai_spend"):
            con.execute(f'DROP TABLE IF EXISTS "{t}"')
    if have and int(have[0]) < 10:  # v10 dropped the computed column; the rows are rebuilt by `ledger aispend --load`
        con.execute('DROP TABLE IF EXISTS "ai_spend"')
    # v11 (T9–T17) reshaped the taxonomy rows, which are computed from the tables on every read (TAXONOMY above), so no
    # stored table changes: the version bump records that a packet built from this schema carries the v11 columns.
    for t in SCHEMA:
        con.execute(_ddl(t))
    con.execute("CREATE TABLE IF NOT EXISTS _meta (k VARCHAR PRIMARY KEY, v VARCHAR)")
    con.execute("INSERT OR REPLACE INTO _meta VALUES ('schema_version', ?)", [str(SCHEMA_VERSION)])
    return con


_PY = {"VARCHAR": str, "BIGINT": int, "INTEGER": int, "DOUBLE": (int, float), "BOOLEAN": bool}


def check(table: str, row: dict) -> None:
    """Raise ContractError naming the row and the broken rule; return None when the row is valid."""
    t = TABLES[table]
    names = {c.name for c in t.cols}
    extra = set(row) - names
    if extra:
        raise ContractError(f"{table}: unknown column(s) {sorted(extra)} in {row}")
    for c in t.cols:
        v = row.get(c.name)
        if v is None:
            if not c.nullable:
                raise ContractError(f"{table}.{c.name} is required (null in {_short(row)})")
            continue
        want = _PY[c.type]
        if isinstance(v, bool) and c.type != "BOOLEAN" or not isinstance(v, want):
            raise ContractError(f"{table}.{c.name} must be {c.type}, got {type(v).__name__} {v!r} in {_short(row)}")
        if c.enum and v not in c.enum:
            raise ContractError(f"{table}.{c.name} must be one of {c.enum}, got {v!r} in {_short(row)}")
        if c.pattern and not c.pattern.match(str(v)):
            raise ContractError(f"{table}.{c.name} {v!r} does not match {c.pattern.pattern} in {_short(row)}")
    if table == "extractions" and row.get("scale") not in (1, 1_000, 1_000_000, 1_000_000_000):
        raise ContractError(f"extractions.scale must be 1, 1000, 1000000 or 1000000000, got {row.get('scale')!r} in {_short(row)}")
    if table == "values" and (row.get("source") == "missing") != (row.get("value") is None):
        raise ContractError(f"values: value must be null exactly when source is 'missing' ({_short(row)})")
    if table == "decisions" and row.get("kind") == "override" and row.get("value") is None:
        raise ContractError(f"decisions: an override needs a value ({_short(row)})")


def _short(row: dict) -> str:
    return json.dumps({k: row[k] for k in list(row)[:4]}, default=str)


def write(con: duckdb.DuckDBPyConnection, table: str, rows: list[dict], replace: bool = False) -> int:
    """Check every row against the contract, then insert them all (or none). A key collision is a contract error too."""
    t = TABLES[table]
    keys = set()
    for r in rows:
        check(table, r)
        k = tuple(r.get(c) for c in t.key)
        if k in keys:
            raise ContractError(f"{table}: duplicate key {dict(zip(t.key, k))} in this write")
        keys.add(k)
    if not rows:
        return 0
    cols = [c.name for c in t.cols]
    sql = f'INSERT {"OR REPLACE " if replace else ""}INTO "{table}" ({", ".join(chr(34) + c + chr(34) for c in cols)}) VALUES ({", ".join("?" * len(cols))})'
    con.execute("BEGIN")
    try:
        con.executemany(sql, [[r.get(c) for c in cols] for r in rows])
        con.execute("COMMIT")
    except duckdb.ConstraintException as e:
        con.execute("ROLLBACK")
        raise ContractError(f"{table}: {e}") from e
    return len(rows)


def data_dictionary() -> str:
    out = ["# Data dictionary", "",
           f"Generated from `ledger/store.py` (schema version {SCHEMA_VERSION}). Do not edit by hand: run `uv run python -m ledger.store`.", "",
           "Money is BIGINT US dollars, unscaled. Dates are `YYYY-MM-DD` strings; timestamps are UTC ISO 8601.", ""]
    for t in SCHEMA:
        out += [f"## `{t.name}`", "", t.doc, "", f"Key: `({', '.join(t.key)})`", ""] + _columns_table(t)
    out += ["## `taxonomy` (the release list, not a stored table)", "", TAXONOMY.doc, "",
            f"Columns in this order, then `layer` and `proven` from the API. A row is identified by `({', '.join(TAXONOMY.key)})`. "
            "Every amount is whole units (`scale` 1) in US dollars (`currency` USD); `value_high` is only a range high, `change_from_prior` only the derived change.", ""] + _columns_table(TAXONOMY)
    return "\n".join(out)


def _columns_table(t: Table) -> list[str]:
    out = ["| Column | Type | Required | Allowed values | Meaning |", "|---|---|---|---|---|"]
    for c in t.cols:
        allowed = ", ".join(f"`{e}`" for e in c.enum) if c.enum else (f"pattern `{c.pattern.pattern}`" if c.pattern else "")
        out.append(f"| `{c.name}` | {c.type} | {'no' if c.nullable else 'yes'} | {allowed} | {c.doc} |")
    out.append("")
    return out


if __name__ == "__main__":
    p = ROOT / "docs" / "DATA_DICTIONARY.md"
    p.write_text(data_dictionary())
    print(f"wrote {p.relative_to(ROOT)}")
