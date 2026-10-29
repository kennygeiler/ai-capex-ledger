# Data dictionary

Generated from `ledger/store.py` (schema version 6). Do not edit by hand: run `uv run python -m ledger.store`.

Money is BIGINT US dollars, unscaled. Dates are `YYYY-MM-DD` strings; timestamps are UTC ISO 8601.

## `documents`

One row per filing's primary document: what was fetched and how it was parsed.

Key: `(accession)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `cik` | INTEGER | yes |  | SEC Central Index Key. |
| `form` | VARCHAR | yes | `10-K`, `10-K/A` | Form type: 10-K, or a 10-K/A that carries the financial statements. |
| `period` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Report period end date (YYYY-MM-DD). |
| `filed` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Filing date (YYYY-MM-DD). |
| `url` | VARCHAR | yes |  | Primary document URL on sec.gov. |
| `sha256` | VARCHAR | yes | pattern `^[0-9a-f]{64}$` | SHA-256 of the document bytes as fetched. |
| `bytes` | BIGINT | yes |  | Size of the document. |
| `parser_version` | VARCHAR | yes |  | Table parser version that produced tables_path. |
| `table_count` | INTEGER | yes |  | Tables with at least one number. |
| `tables_path` | VARCHAR | yes |  | Parsed tables JSON, relative to the repo root. |
| `income_tables` | VARCHAR | no |  | Table IDs of the income statement, comma-separated. |
| `cash_flow_tables` | VARCHAR | no |  | Table IDs of the cash-flow statement, comma-separated. |

## `reference_values`

XBRL values from the reference pipeline (SEC companyfacts). Evidence for reconciliation, not truth.

Key: `(ticker, field, period)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `revenue`, `cost_of_revenue`, `cost_of_revenue_part`, `operating_income`, `capex`, `opex` | revenue, capex or opex (released); cost_of_revenue and operating_income (read to compute opex). |
| `period` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026). |
| `value` | BIGINT | yes |  | US dollars, unscaled. |
| `method` | VARCHAR | yes |  | reported, or derived (opex = revenue − cost of revenue − operating income). |
| `concept` | VARCHAR | yes |  | XBRL concept, e.g. us-gaap:Revenues. |
| `period_start` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Fiscal period start. |
| `period_end` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Fiscal period end. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `restated` | BOOLEAN | yes |  | True if a later filing changed the value. |
| `original_value` | BIGINT | no |  | First-filed value when restated. |

## `extractions`

One row per value an agent read from a 10-K column (one fiscal year).

Key: `(extraction_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `extraction_id` | VARCHAR | yes |  | Stable ID: accession|field|period_start|period_end. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `revenue`, `cost_of_revenue`, `cost_of_revenue_part`, `operating_income`, `capex`, `opex` | revenue, capex or opex (released); cost_of_revenue and operating_income (read to compute opex). |
| `period_start` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Start of the period the column covers. |
| `period_end` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | End of the period the column covers. |
| `value` | BIGINT | yes |  | US dollars, unscaled (cell value × scale; sign as the field defines it, capex positive). |
| `unit_stated` | VARCHAR | yes |  | Unit text as written, e.g. '(In millions, except per share data)'. |
| `unit_source` | VARCHAR | yes | `table`, `statement`, `document` | Where the unit was stated. |
| `scale` | BIGINT | yes |  | 1000, 1000000 or 1000000000. |
| `table_id` | VARCHAR | yes |  | Cited table, e.g. t0007. |
| `row_label` | VARCHAR | yes |  | Cited row label, verbatim. |
| `column_label` | VARCHAR | yes |  | Cited column label, verbatim. |
| `cell_text` | VARCHAR | yes |  | Cited cell text, verbatim, e.g. '(4,434)'. |
| `confidence` | DOUBLE | yes |  | Agent's confidence, 0 to 1. |
| `notes` | VARCHAR | no |  | Agent's notes. |
| `prompt_version` | VARCHAR | yes |  | Prompt file and version, e.g. statements@v1. |
| `run_id` | VARCHAR | yes |  | Run that produced it. |

## `values`

One value per (ticker, field, fiscal year): what a release ships.

Key: `(ticker, field, period)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `revenue`, `cost_of_revenue`, `cost_of_revenue_part`, `operating_income`, `capex`, `opex` | revenue, capex or opex (released); cost_of_revenue and operating_income (read to compute opex). |
| `period` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026). |
| `period_end` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Fiscal year end date. |
| `value` | BIGINT | no |  | US dollars, unscaled. Null when source is missing. |
| `source` | VARCHAR | yes | `agent`, `override`, `missing` | Where the shipped value comes from. |
| `method` | VARCHAR | yes | `reported`, `computed` | reported (one cell), or computed (opex from three cells of the same 10-K column). |
| `label` | VARCHAR | yes | `agree`, `agent_wrong`, `xbrl_wrong`, `definition_gap`, `unresolved`, `no_reference`, `not_reported` | Reconciliation against the reference; not_reported when the company has no such line. |
| `basis` | VARCHAR | yes | `as_reported`, `restated` | as_reported, or restated (a later 10-K changed the first-reported figure by more than 1%). |
| `first_reported` | BIGINT | no |  | The figure in the first 10-K that reported this fiscal year. |
| `extraction_ids` | VARCHAR | no |  | Extractions used, comma-separated. |
| `input_hash` | VARCHAR | yes |  | Hash of everything this value depends on; decisions re-apply only when it matches. |

## `ai_statements`

Table A for AI spend: every statement an agent read in a 10-K's MD&A about AI's part of capex or opex, verbatim.

Key: `(statement_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `statement_id` | VARCHAR | yes |  | Stable ID: accession|field|period|kind|n. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `capex`, `opex` | capex or opex. |
| `period` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026). |
| `kind` | VARCHAR | yes | `actual`, `outlook` | actual: the fiscal year the filing reports. outlook: a later year. |
| `scope` | VARCHAR | yes | `ai`, `total` | ai: the figure is the AI part. total: the company's total, with AI named as a driver. |
| `class` | VARCHAR | yes | `explicit_amount`, `explicit_share`, `qualitative` | explicit_amount, explicit_share or qualitative. |
| `amount_low` | BIGINT | no |  | Stated amount or low end of a range, US dollars. |
| `amount_high` | BIGINT | no |  | Stated amount or high end of a range, US dollars. |
| `share` | DOUBLE | no |  | Stated share, 0 to 1. |
| `quote` | VARCHAR | yes |  | The sentence, verbatim from the filing. |
| `passage` | VARCHAR | yes |  | Passage tag in the task, e.g. p03. |
| `confidence` | DOUBLE | yes |  | Agent's confidence, 0 to 1. |
| `notes` | VARCHAR | no |  | Agent's notes. |
| `prompt_version` | VARCHAR | yes |  | Prompt file and version, e.g. aispend@v1. |
| `run_id` | VARCHAR | yes |  | Run that produced it. |

## `ai_spend`

Table B for AI spend: per company, field, fiscal year and kind, the most specific statement from the newest filing, and an AI dollar amount only where the filing supports one.

Key: `(ticker, field, period, kind)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `capex`, `opex` | capex or opex. |
| `period` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026). |
| `kind` | VARCHAR | yes | `actual`, `outlook` | actual or outlook. |
| `scope` | VARCHAR | yes | `ai`, `total` | ai or total (see ai_statements). |
| `class` | VARCHAR | yes | `explicit_amount`, `explicit_share`, `qualitative` | explicit_amount, explicit_share or qualitative. |
| `amount_low` | BIGINT | no |  | As stated. |
| `amount_high` | BIGINT | no |  | As stated. |
| `share` | DOUBLE | no |  | As stated. |
| `ai_amount` | BIGINT | no |  | AI dollars: the midpoint of an explicit AI amount, or an explicit AI share × our value for that year. Null when the filing gives only words or only a total. |
| `quote` | VARCHAR | yes |  | The sentence behind the row. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `statement_ids` | VARCHAR | yes |  | Statements considered, comma-separated. |
| `input_hash` | VARCHAR | yes |  | Hash of everything this row depends on. |

## `note_extractions`

Table A for note facts: every cell the notes reader cited (segment capex and revenue, PP&E by category, finance lease liabilities, purchase commitments).

Key: `(extraction_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `extraction_id` | VARCHAR | yes |  | Stable ID: accession|field|dimension|period_end. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `segment_capex`, `segment_revenue`, `ppe_category`, `finance_lease_liability`, `purchase_commitments` | segment_capex, segment_revenue, ppe_category, finance_lease_liability or purchase_commitments. |
| `dimension` | VARCHAR | no |  | Segment, market or PP&E category, as written in the filing. Null for a company total. |
| `period_end` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Fiscal year end the column refers to. |
| `months` | INTEGER | yes |  | 12 for a flow (capex, revenue); 0 for a balance at period_end. |
| `value` | BIGINT | yes |  | US dollars, unscaled, positive. |
| `unit_stated` | VARCHAR | no |  | Unit text as written. |
| `unit_source` | VARCHAR | yes | `table`, `statement`, `document` | Where the unit was stated. |
| `scale` | BIGINT | yes |  | 1, 1000, 1000000 or 1000000000. |
| `table_id` | VARCHAR | yes |  | Cited table. |
| `row_label` | VARCHAR | yes |  | Cited row label, verbatim. |
| `column_label` | VARCHAR | yes |  | Cited column label, verbatim. |
| `cell_text` | VARCHAR | yes |  | Cited cell text, verbatim. |
| `confidence` | DOUBLE | yes |  | Agent's confidence, 0 to 1. |
| `notes` | VARCHAR | no |  | Agent's notes. |
| `prompt_version` | VARCHAR | yes |  | Prompt file and version, e.g. notes@v1. |
| `run_id` | VARCHAR | yes |  | Run that produced it. |

## `facts`

Table B for note facts: one value per company, field, dimension and fiscal year from the newest filing, labelled against the filing's XBRL instance where the fact carries a matching member.

Key: `(ticker, field, dimension, period)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `segment_capex`, `segment_revenue`, `ppe_category`, `finance_lease_liability`, `purchase_commitments` | As in note_extractions. |
| `dimension` | VARCHAR | yes |  | Segment, market or category; empty string for a company total (part of the key). |
| `period` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026). |
| `period_end` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Fiscal year end date. |
| `value` | BIGINT | yes |  | US dollars, unscaled. |
| `first_reported` | BIGINT | yes |  | The figure in the first 10-K that reported it. |
| `basis` | VARCHAR | yes | `as_reported`, `restated` | as_reported, or restated when a later 10-K changed it. |
| `label` | VARCHAR | yes | `agree`, `unresolved`, `no_reference` | agree or unresolved against the XBRL instance member; no_reference when no tagged fact matches the dimension. |
| `reference` | BIGINT | no |  | The XBRL value compared with, when any. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `extraction_ids` | VARCHAR | yes |  | Extractions used, comma-separated. |
| `input_hash` | VARCHAR | yes |  | Hash of everything this row depends on. |

## `rules`

The rule registry as loaded from rules/*.yaml.

Key: `(rule_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `rule_id` | VARCHAR | yes |  | Rule ID, e.g. unit_scale. |
| `severity` | VARCHAR | yes | `block`, `warn`, `info` | block, warn or info. |
| `description` | VARCHAR | yes |  | What it checks. |
| `rationale` | VARCHAR | yes |  | Why the check exists: the judgement it encodes. |
| `check_name` | VARCHAR | yes |  | Python check function. |
| `params` | VARCHAR | yes |  | Check parameters, JSON. |
| `file_sha256` | VARCHAR | yes |  | Hash of the YAML file, so a rule change is visible in a release diff. |

## `exceptions`

One rule firing on one value.

Key: `(exception_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `exception_id` | VARCHAR | yes |  | Stable ID: rule_id|ticker|field|period (or the extraction/document it fired on). |
| `rule_id` | VARCHAR | yes |  | Rule that fired. |
| `severity` | VARCHAR | yes | `block`, `warn`, `info` | Copied from the rule at run time. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | no | `revenue`, `cost_of_revenue`, `cost_of_revenue_part`, `operating_income`, `capex`, `opex` | Line item, if the rule is field-level. |
| `period` | VARCHAR | no | pattern `^FY\d{4}$` | Fiscal year, if year-level. |
| `subject` | VARCHAR | no |  | What it fired on when not a released value: an accession or extraction ID. |
| `message` | VARCHAR | yes |  | Plain-language explanation with the numbers. |
| `input_hash` | VARCHAR | yes |  | Hash of the inputs it was raised on. |

## `decisions`

A person's resolution of an exception. Append-only: a later decision supersedes, never edits.

Key: `(decision_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `decision_id` | VARCHAR | yes |  | Unique ID. |
| `exception_id` | VARCHAR | yes |  | Exception decided. |
| `kind` | VARCHAR | yes | `accept`, `override`, `reject` | accept, override or reject. |
| `value` | BIGINT | no |  | Override value, US dollars, unscaled. |
| `reason` | VARCHAR | yes |  | Why. Required for every kind. |
| `reviewer` | VARCHAR | yes |  | Who decided. |
| `decided_at` | VARCHAR | yes |  | UTC timestamp, ISO 8601. |
| `input_hash` | VARCHAR | yes |  | Input hash of the exception when decided. |
| `supersedes` | VARCHAR | no |  | Earlier decision this replaces. |

## `runs`

One row per pipeline or agent step: what ran, on what, with which versions, and how it went.

Key: `(run_id, step, subject)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `run_id` | VARCHAR | yes |  | Run ID. |
| `step` | VARCHAR | yes | `run`, `ingest`, `parse`, `extract`, `reconcile`, `aispend`, `notes`, `rules`, `faults`, `evidence`, `report`, `review`, `score`, `release` | Step name. |
| `subject` | VARCHAR | no |  | What it ran on (accession, ticker, release). |
| `started_at` | VARCHAR | yes |  | UTC timestamp. |
| `seconds` | DOUBLE | yes |  | Wall-clock duration. |
| `outcome` | VARCHAR | yes | `ok`, `failed`, `skipped` | ok, failed or skipped. |
| `versions` | VARCHAR | yes |  | Versions used (parser, prompt, model, rules), JSON. |
| `detail` | VARCHAR | no |  | Anything else worth keeping (tokens, cost, retries, error), JSON. |
