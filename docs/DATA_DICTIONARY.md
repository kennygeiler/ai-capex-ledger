# Data dictionary

Generated from `ledger/store.py` (schema version 3). Do not edit by hand: run `uv run python -m ledger.store`.

Money is BIGINT US dollars, unscaled. Dates are `YYYY-MM-DD` strings; timestamps are UTC ISO 8601.

## `documents`

One row per filing's primary document: what was fetched and how it was parsed.

Key: `(accession)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `cik` | INTEGER | yes |  | SEC Central Index Key. |
| `form` | VARCHAR | yes | `10-Q`, `10-K` | Form type. |
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

Key: `(ticker, field, cal_q)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `revenue`, `cost_of_revenue`, `operating_income`, `capex` | Line item: revenue, cost_of_revenue, operating_income or capex. |
| `cal_q` | VARCHAR | yes | pattern `^\d{4}Q[1-4]$` | Calendar quarter the value belongs to, e.g. 2026Q2 (majority of days). |
| `value` | BIGINT | yes |  | US dollars, unscaled. |
| `method` | VARCHAR | yes |  | How the quarter was derived (reported, ytd_diff, q4_derived, ...). |
| `concept` | VARCHAR | yes |  | XBRL concept, e.g. us-gaap:Revenues. |
| `period_start` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Fiscal period start. |
| `period_end` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Fiscal period end. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `restated` | BOOLEAN | yes |  | True if a later filing changed the value. |
| `original_value` | BIGINT | no |  | First-filed value when restated. |

## `extractions`

One row per value an agent read from a filing, as stated (three months, year to date, or full year).

Key: `(extraction_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `extraction_id` | VARCHAR | yes |  | Stable ID: accession|field|period_start|period_end. |
| `accession` | VARCHAR | yes | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing, e.g. 0001045810-26-000075. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `revenue`, `cost_of_revenue`, `operating_income`, `capex` | Line item: revenue, cost_of_revenue, operating_income or capex. |
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

One quarterly value per (ticker, field, quarter): what a release ships.

Key: `(ticker, field, cal_q)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `revenue`, `cost_of_revenue`, `operating_income`, `capex` | Line item: revenue, cost_of_revenue, operating_income or capex. |
| `cal_q` | VARCHAR | yes | pattern `^\d{4}Q[1-4]$` | Calendar quarter the value belongs to, e.g. 2026Q2 (majority of days). |
| `fiscal_period` | VARCHAR | yes | pattern `^FY\d{4} Q[1-4]$` | The company's own label for the quarter, e.g. FY2027 Q2 (NVDA's quarter ended 26 Jul 2026). |
| `value` | BIGINT | no |  | US dollars, unscaled. Null when source is missing. |
| `source` | VARCHAR | yes | `agent`, `override`, `missing` | Where the shipped value comes from. |
| `method` | VARCHAR | no |  | Quarter derivation: reported, ytd_diff, q4_derived, fy_minus_quarters. |
| `label` | VARCHAR | yes | `agree`, `agent_wrong`, `xbrl_wrong`, `definition_gap`, `unresolved`, `no_reference`, `mixed_basis` | Reconciliation against the reference. |
| `basis` | VARCHAR | yes | `as_reported`, `restated`, `mixed` | as_reported, restated (built from filings after the company's restatement), or mixed (no single basis; value left blank). |
| `first_reported` | BIGINT | no |  | The same quarter built only from first-filed numbers (as first reported). |
| `extraction_ids` | VARCHAR | no |  | Extractions used, comma-separated. |
| `input_hash` | VARCHAR | yes |  | Hash of everything this value depends on; decisions re-apply only when it matches. |

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
| `exception_id` | VARCHAR | yes |  | Stable ID: rule_id|ticker|field|cal_q (or the extraction/document it fired on). |
| `rule_id` | VARCHAR | yes |  | Rule that fired. |
| `severity` | VARCHAR | yes | `block`, `warn`, `info` | Copied from the rule at run time. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | no | `revenue`, `cost_of_revenue`, `operating_income`, `capex` | Line item, if the rule is field-level. |
| `cal_q` | VARCHAR | no | pattern `^\d{4}Q[1-4]$` | Quarter, if quarter-level. |
| `subject` | VARCHAR | no |  | What it fired on when not a quarterly value: an accession or extraction ID. |
| `message` | VARCHAR | yes |  | Plain-language explanation with the numbers. |
| `input_hash` | VARCHAR | yes |  | Hash of the inputs it was raised on. |

## `decisions`

A person's resolution of an exception. Append-only: a later decision supersedes, never edits.

Key: `(decision_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `decision_id` | VARCHAR | yes |  | Unique ID. |
| `exception_id` | VARCHAR | yes |  | Exception decided. |
| `kind` | VARCHAR | yes | `accept`, `override`, `reject`, `fix_rule` | accept, override, reject or fix_rule. |
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
| `step` | VARCHAR | yes | `ingest`, `parse`, `extract`, `reconcile`, `rules`, `review`, `score`, `release` | Step name. |
| `subject` | VARCHAR | no |  | What it ran on (accession, ticker, release). |
| `started_at` | VARCHAR | yes |  | UTC timestamp. |
| `seconds` | DOUBLE | yes |  | Wall-clock duration. |
| `outcome` | VARCHAR | yes | `ok`, `failed`, `skipped` | ok, failed or skipped. |
| `versions` | VARCHAR | yes |  | Versions used (parser, prompt, model, rules), JSON. |
| `detail` | VARCHAR | no |  | Anything else worth keeping (tokens, cost, retries, error), JSON. |
