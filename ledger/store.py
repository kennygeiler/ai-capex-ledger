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
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "ledger.duckdb"
SCHEMA_VERSION = 7

FIELDS = ("revenue", "cost_of_revenue", "cost_of_revenue_part", "operating_income", "capex", "opex")
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
        _c("restated", "BOOLEAN", "True if a later filing changed the value."),
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
        _c("label", "VARCHAR", "Reconciliation against the reference; not_reported when the company has no such line.", enum=("agree", "agent_wrong", "xbrl_wrong", "definition_gap", "unresolved", "no_reference", "not_reported")),
        _c("basis", "VARCHAR", "as_reported, or restated (a later 10-K changed the first-reported figure by more than 1%).", enum=("as_reported", "restated")),
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
        _c("field", "VARCHAR", "capex or opex.", enum=("capex", "opex")),
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
    Table("ai_spend", "Table B for AI spend: per company, field, fiscal year and kind, the most specific statement from the newest filing, and an AI dollar amount only where the filing supports one.", (
        TICKER,
        _c("field", "VARCHAR", "capex or opex.", enum=("capex", "opex")),
        PERIOD,
        _c("kind", "VARCHAR", "actual or outlook.", enum=("actual", "outlook")),
        _c("scope", "VARCHAR", "ai or total (see ai_statements).", enum=("ai", "total")),
        _c("class", "VARCHAR", "explicit_amount, explicit_share or qualitative.", enum=("explicit_amount", "explicit_share", "qualitative")),
        _c("amount_low", "BIGINT", "As stated.", nullable=True),
        _c("amount_high", "BIGINT", "As stated.", nullable=True),
        _c("share", "DOUBLE", "As stated.", nullable=True),
        _c("ai_amount", "BIGINT", "AI dollars: the midpoint of an explicit AI amount, or an explicit AI share × our value for that year. Null when the filing gives only words or only a total.", nullable=True),
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
        _c("basis", "VARCHAR", "as_reported, or restated when a later 10-K changed it.", enum=("as_reported", "restated")),
        _c("label", "VARCHAR", "agree or unresolved against the XBRL instance member; no_reference when no tagged fact matches the dimension.", enum=("agree", "unresolved", "no_reference")),
        _c("reference", "BIGINT", "The XBRL value compared with, when any.", nullable=True),
        ACCN,
        _c("extraction_ids", "VARCHAR", "Extractions used, comma-separated."),
        _c("input_hash", "VARCHAR", "Hash of everything this row depends on."),
    ), key=("ticker", "field", "dimension", "period")),
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
        _c("field", "VARCHAR", "Line item, if the rule is field-level.", nullable=True, enum=FIELDS),
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
        _c("step", "VARCHAR", "Step name.", enum=("run", "ingest", "parse", "extract", "reconcile", "texts", "aispend", "notes", "rules", "faults", "evidence", "report", "review", "score", "release")),
        _c("subject", "VARCHAR", "What it ran on (accession, ticker, release).", nullable=True),
        _c("started_at", "VARCHAR", "UTC timestamp."),
        _c("seconds", "DOUBLE", "Wall-clock duration."),
        _c("outcome", "VARCHAR", "ok, failed or skipped.", enum=("ok", "failed", "skipped")),
        _c("versions", "VARCHAR", "Versions used (parser, prompt, model, rules), JSON."),
        _c("detail", "VARCHAR", "Anything else worth keeping (tokens, cost, retries, error), JSON.", nullable=True),
    ), key=("run_id", "step", "subject")),
)
TABLES = {t.name: t for t in SCHEMA}


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
        out += [f"## `{t.name}`", "", t.doc, "", f"Key: `({', '.join(t.key)})`", "",
                "| Column | Type | Required | Allowed values | Meaning |", "|---|---|---|---|---|"]
        for c in t.cols:
            allowed = ", ".join(f"`{e}`" for e in c.enum) if c.enum else (f"pattern `{c.pattern.pattern}`" if c.pattern else "")
            out.append(f"| `{c.name}` | {c.type} | {'no' if c.nullable else 'yes'} | {allowed} | {c.doc} |")
        out.append("")
    return "\n".join(out)


if __name__ == "__main__":
    p = ROOT / "docs" / "DATA_DICTIONARY.md"
    p.write_text(data_dictionary())
    print(f"wrote {p.relative_to(ROOT)}")
