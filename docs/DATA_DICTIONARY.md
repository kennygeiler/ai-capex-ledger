# Data dictionary

Generated from `ledger/store.py` (schema version 11). Do not edit by hand: run `uv run python -m ledger.store`.

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
| `label` | VARCHAR | yes | `agree`, `agent_wrong`, `xbrl_wrong`, `definition_gap`, `unresolved`, `no_reference`, `not_reported`, `not_extracted` | Reconciliation against the reference; not_reported when the company has no such line and XBRL tags none either; not_extracted when the 10-K has no cell for it but XBRL tags a value (open: the reader missed it, or the statement table was mislocated). |
| `basis` | VARCHAR | yes | `as_reported`, `restated` | as_reported, or restated (a later 10-K changed the first-reported figure by more than 1%). |
| `first_reported` | BIGINT | no |  | The figure in the first 10-K that reported this fiscal year. |
| `extraction_ids` | VARCHAR | no |  | Extractions used, comma-separated. |
| `input_hash` | VARCHAR | yes |  | Hash of everything this value depends on; decisions re-apply only when it matches. |

## `texts`

Every text the AI spend reader reads: 10-K MD&A, 8-K earnings releases, investor-page transcripts and CFO commentary, with the fiscal period each speaks to.

Key: `(text_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `text_id` | VARCHAR | yes |  | Stable ID: ticker|kind|period_end|url hash. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `kind` | VARCHAR | yes | `mdna`, `earnings_release`, `transcript`, `cfo_commentary` | mdna, earnings_release, transcript or cfo_commentary. |
| `accession` | VARCHAR | no | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession when the text is a filing exhibit or section. |
| `url` | VARCHAR | yes |  | Where it came from. |
| `date` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | Filing or quarter-end date. |
| `period_end` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | The fiscal period end the text speaks to (year end for MD&A, quarter end otherwise). |
| `fiscal_year` | INTEGER | yes |  | The company's fiscal year of that period. |
| `path` | VARCHAR | yes |  | Plain text on disk, relative to the repo root. |
| `sha256` | VARCHAR | yes | pattern `^[0-9a-f]{64}$` | SHA-256 of the text. |
| `chars` | INTEGER | yes |  | Length of the text. |

## `ai_statements`

Table A for AI spend: every statement an agent read in a text about AI's part of capex or opex, verbatim.

Key: `(statement_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `statement_id` | VARCHAR | yes |  | Stable ID: text_id|field|period|kind|n. |
| `text_id` | VARCHAR | yes |  | The text it was read from (texts). |
| `source` | VARCHAR | yes | `mdna`, `earnings_release`, `transcript`, `cfo_commentary` | mdna, earnings_release, transcript or cfo_commentary. |
| `accession` | VARCHAR | no | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession when the text is a filing. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `capex`, `opex`, `revenue` | capex, opex or revenue. |
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

Table B for AI spend: per company, field, fiscal year and kind, the most specific statement from the newest filing, as stated: an amount range, a share, or words only.

Key: `(ticker, field, period, kind)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `field` | VARCHAR | yes | `capex`, `opex`, `revenue` | capex, opex or revenue. |
| `period` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026). |
| `kind` | VARCHAR | yes | `actual`, `outlook` | actual or outlook. |
| `scope` | VARCHAR | yes | `ai`, `total` | ai or total (see ai_statements). |
| `class` | VARCHAR | yes | `explicit_amount`, `explicit_share`, `qualitative` | explicit_amount, explicit_share or qualitative. |
| `amount_low` | BIGINT | no |  | As stated. |
| `amount_high` | BIGINT | no |  | As stated. |
| `share` | DOUBLE | no |  | As stated. |
| `quote` | VARCHAR | yes |  | The sentence behind the row. |
| `text_id` | VARCHAR | yes |  | The text the quote comes from (texts). |
| `source` | VARCHAR | yes | `mdna`, `earnings_release`, `transcript`, `cfo_commentary` | mdna, earnings_release, transcript or cfo_commentary. |
| `accession` | VARCHAR | no | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession when the text is a filing. |
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

## `projects`

Project-level investment: every named project a text mentions (data center, fab, plant, power, GPU cluster, commitment), with size and stage; latest marks the newest mention per project.

Key: `(project_id)`

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `project_id` | VARCHAR | yes |  | text_id|n. |
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `text_id` | VARCHAR | yes |  | The text it was read from (texts). |
| `source` | VARCHAR | yes | `mdna`, `earnings_release`, `transcript`, `cfo_commentary` | mdna, earnings_release, transcript or cfo_commentary. |
| `accession` | VARCHAR | no | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession when the text is a filing. |
| `date` | VARCHAR | yes | pattern `^\d{4}-\d{2}-\d{2}$` | The text's date. |
| `period` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year, e.g. FY2026 (NVDA's ended 25 Jan 2026). |
| `name` | VARCHAR | yes |  | The project as the company names it. |
| `kind` | VARCHAR | yes | `data_center`, `fab`, `plant`, `power`, `gpu_cluster`, `cloud_commitment`, `network`, `other` | data_center, fab, plant, power, gpu_cluster, cloud_commitment, network or other. |
| `status` | VARCHAR | yes | `announced`, `under_construction`, `in_service`, `contracted`, `cancelled` | announced, under_construction, in_service, contracted or cancelled. |
| `location` | VARCHAR | no |  | Place as stated. |
| `counterparty` | VARCHAR | no |  | The other party when stated. |
| `amount_low` | BIGINT | no |  | Stated size, US dollars. |
| `amount_high` | BIGINT | no |  | Stated size, US dollars. |
| `capacity_mw` | DOUBLE | no |  | Megawatts when stated. |
| `gpus` | BIGINT | no |  | GPUs when stated. |
| `announced` | VARCHAR | no |  | Date announced, when stated. |
| `in_service` | VARCHAR | no |  | Date in service or expected, when stated. |
| `quote` | VARCHAR | yes |  | The sentence, verbatim. |
| `passage` | VARCHAR | yes |  | Passage tag in the task. |
| `confidence` | DOUBLE | yes |  | Agent's confidence. |
| `latest` | BOOLEAN | yes |  | True on the newest mention of this project for the company. |
| `prompt_version` | VARCHAR | yes |  | Prompt version. |
| `run_id` | VARCHAR | yes |  | Run that produced it. |

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
| `step` | VARCHAR | yes | `run`, `ingest`, `parse`, `extract`, `reconcile`, `texts`, `aispend`, `notes`, `attribution`, `eval`, `rules`, `faults`, `evidence`, `report`, `review`, `score`, `release`, `projects`, `cost`, `publish`, `mapper` | Step name. |
| `subject` | VARCHAR | no |  | What it ran on (accession, ticker, release). |
| `started_at` | VARCHAR | yes |  | UTC timestamp. |
| `seconds` | DOUBLE | yes |  | Wall-clock duration. |
| `outcome` | VARCHAR | yes | `ok`, `failed`, `skipped` | ok, failed or skipped. |
| `versions` | VARCHAR | yes |  | Versions used (parser, prompt, model, rules), JSON. |
| `detail` | VARCHAR | no |  | Anything else worth keeping (tokens, cost, retries, error), JSON. |

## `taxonomy` (the release list, not a stored table)

One row per company, fiscal year, measure and category: an instance of a published standard's concept with the company's own label beside it, or a verbatim quote. Built by code from the tables above; no agent, nothing estimated.

Columns in this order, then `layer` and `proven` from the API. A row is identified by `(ticker, fiscal_year, measure, category, reported_name, source)`. Every amount is whole units (`scale` 1) in US dollars (`currency` USD); `value_high` is only a range high, `change_from_prior` only the derived change.

| Column | Type | Required | Allowed values | Meaning |
|---|---|---|---|---|
| `ticker` | VARCHAR | yes | pattern `^[A-Z][A-Z0-9.\-]{0,9}$` | Company ticker, e.g. NVDA. |
| `fiscal_year` | VARCHAR | yes | pattern `^FY\d{4}$` | The company's fiscal year label, e.g. FY2025. |
| `period_end` | VARCHAR | no | pattern `^\d{4}-\d{2}-\d{2}$` | The fiscal period's last day, from the company's own fiscal calendar (the 10-K that reports that year), on every row whose period_kind is reported; empty on a planned row. |
| `period_kind` | VARCHAR | yes | `reported`, `planned` | reported: the figure is for a fiscal period that had ended when the source was written. planned: the period's end is after the source's date, or the calendar does not know it yet. |
| `measure` | VARCHAR | yes | `spent`, `committed`, `derived`, `planned`, `company_stated_ai` | spent, committed, derived (a reported balance and its arithmetic change), planned (verbatim) or company_stated_ai (verbatim). |
| `category` | VARCHAR | yes |  | The taxonomy id (taxonomy/taxonomy.yaml): capex, segment_capex, segment_revenue, purchase_obligations, finance_lease_liability, ppe_gross_by_type, guidance, project, ai_capex, ai_opex, ai_revenue. |
| `reported_name` | VARCHAR | yes |  | The company's own label: the line, segment, asset type, project or statement as written. |
| `standard_concept` | VARCHAR | yes |  | The us-gaap concept (and axis) the row is an instance of; 'forward-looking statement (Reg S-K)' for guidance; 'none: ...' for a verbatim row with no standard. |
| `standard_type` | VARCHAR | no |  | For an asset type: the us-gaap PropertyPlantAndEquipmentByTypeAxis member it maps to (taxonomy/asset_types.yaml). Empty elsewhere, and on an unmapped asset type. |
| `mapped` | BOOLEAN | yes |  | False exactly when check is unmapped: a reported asset type with no entry in taxonomy/asset_types.yaml. True on every other row. |
| `value` | BIGINT | no |  | The figure as reported or quoted, in `unit`: a dollar amount, or the low end of a stated range. Empty when the company gave no figure (has_value false) or stated a share instead. |
| `value_high` | BIGINT | no |  | The high end of a stated range, on planned and company_stated_ai rows only, and only when the range has two ends. Never anything else. |
| `change_from_prior` | BIGINT | no |  | On derived rows only: this year's reported gross balance minus the prior year's, for the same asset type. Arithmetic on two reported figures; empty on the first year. |
| `share` | DOUBLE | no |  | A share the company stated, 0 to 1, on company_stated_ai rows whose unit is share. Empty elsewhere. |
| `relation` | VARCHAR | no | `eq`, `ge`, `le` | On a gathered figure: how the company's words relate to value or share: eq (the figure), ge (at least), le (at most). Empty elsewhere. |
| `has_value` | BOOLEAN | yes |  | True when the row carries a figure (value or share). False on a project or statement the company named without an amount. |
| `unit` | VARCHAR | no | `USD`, `share` | USD for a dollar amount; share for a stated share. Empty when has_value is false. A project's capacity is in capacity_mw, in megawatts. |
| `scale` | BIGINT | yes |  | Always 1: every amount is in whole units (whole dollars, a share of one, megawatts). |
| `currency` | VARCHAR | yes | `USD` | Always USD: the currency of value, value_high and change_from_prior. |
| `period_as_stated` | VARCHAR | no |  | On a verbatim row: the period the company named, as the reader labelled it (the fiscal year). Empty on reported rows. |
| `quote` | VARCHAR | no |  | On a verbatim row: the sentence, as written in the source. Empty on reported rows. |
| `kind` | VARCHAR | no | `actual`, `outlook` | On a company_stated_ai statement read from a text: actual (the period the text reports) or outlook (a later period). Empty elsewhere. |
| `project_kind` | VARCHAR | no | `data_center`, `fab`, `plant`, `power`, `gpu_cluster`, `cloud_commitment`, `network`, `other` | On a project: data_center, fab, plant, power, gpu_cluster, cloud_commitment, network or other. Empty elsewhere. |
| `status` | VARCHAR | no | `announced`, `under_construction`, `in_service`, `contracted`, `cancelled` | On a project: announced, under_construction, in_service, contracted or cancelled, as stated. Empty elsewhere. |
| `location` | VARCHAR | no |  | On a project: the place as stated. Empty elsewhere. |
| `capacity_mw` | DOUBLE | no |  | On a project: megawatts when stated. Empty elsewhere. |
| `forward_looking` | BOOLEAN | no |  | On a statement read from a text: True for guidance and an outlook statement (a forward-looking statement under Regulation S-K), False for a figure the text reports as actual. Empty where the source does not say: spent, committed and derived rows, projects, gathered figures. |
| `part_year` | BOOLEAN | no |  | On a statement read from a text: True when its words cover part of a year (a quarter, a half), by rules/guards; the figure is never turned into a year. Empty elsewhere. |
| `program` | BOOLEAN | no |  | On a statement read from a text: True when its words describe a multi-year program rather than a year's figure, by rules/guards. Empty elsewhere. |
| `source` | VARCHAR | yes |  | The internal id of what the row was read from: extraction ids (values), the fact's extraction ids (facts), a text id (statements, projects), or taxonomy/stated_figures.yaml. |
| `source_kind` | VARCHAR | yes | `10-K table`, `10-K note`, `10-K MD&A`, `8-K release`, `transcript`, `cfo commentary`, `gathered` | Where the figure is written: a 10-K statement table, a 10-K note, the 10-K's MD&A, an 8-K earnings release, a transcript, CFO commentary, or gathered (a figure a person recorded with its URL and quote). |
| `accession` | VARCHAR | no | pattern `^\d{10}-\d{2}-\d{6}$` | SEC accession number of the filing the row was read from. Empty when the source is not a filing. |
| `filed` | VARCHAR | no | pattern `^\d{4}-\d{2}-\d{2}$` | The date the source was filed with the SEC (documents.filed for a 10-K, the 8-K's filing date for a release). Empty for a transcript, CFO commentary or a gathered figure, which have no filing date. |
| `source_table` | VARCHAR | no | pattern `^t\d{4}$` | For a 10-K cell: the id of the parsed table the cell was read from (e.g. t0035), the table DATAHQ shows; it is the parser's id, not an anchor on sec.gov. Empty elsewhere. |
| `source_url` | VARCHAR | no |  | A URL that opens the source. For a 10-K cell: the filing on sec.gov with a `#:~:text=<row label>,<number>` fragment that scrolls the browser to the first place the filing shows those words, usually the row, sometimes prose; sec.gov offers no table anchor. For a statement or project: the text with the quote's first words as the fragment. For a gathered figure: the page recorded with it. |
| `check` | VARCHAR | yes | `agree`, `explained`, `differs`, `no_reference`, `not_extracted`, `unmapped`, `verbatim` | agree: matches the SEC's XBRL. explained: differs and something on file says why (check_method). differs: differs and nothing on file says why. no_reference: no XBRL fact to compare. not_extracted: no cell read, while XBRL tags a value (open). unmapped: an asset type with no standard member. verbatim: a quote verified against its text. |
| `check_method` | VARCHAR | yes | pattern `^(xbrl|esef|source|actual|quote|gathered|located|none|mapping|rule|definition|resolution|label)(:.+)?$` | What established the check, as status.py names `by`: `<kind>` or `<kind>:<id>` with the kind one of status.METHOD_KINDS: xbrl, quote, gathered, none (nothing to compare against), rule:<id>, definition:<name>, resolution:<id>, label:<label>, mapping:<member>. An open vocabulary: a later answer key adds a kind there. |
