# Notes reader

The note-table reader. One call per 10-K filing, `ledger notes --run`; the stages are Facts and Mapping on the Proof board (ledger/proof.py `stages["facts"]`, `stages["mapping"]`).

## Owns

Table `note_extractions` (table A, every cell read) and, derived from it by code, `facts` (table B: one value per company, field, dimension and fiscal year from the newest filing), both written by `ledger notes --load` (ledger/cli/notes.py, ledger/notes.py `fact_rows`). Fields: segment_capex, segment_revenue, ppe_category (each with a dimension), finance_lease_liability, purchase_commitments (ledger/notes.py `FIELDS`, `DIMENSIONED`, `BALANCES`). The derived PP&E rows and the asset-type mapping on the Proof board are built from `facts` by code (ledger/taxonomy.py, taxonomy/asset_types.yaml); the reader never writes them.

## Never touches

The income and cash-flow statements (`extractions`, `values`), texts, `ai_statements`, `projects`, the XBRL instance, `decisions/`, `releases/`. Its task is the candidate note tables only (ledger/notes.py `locate`: segment, PP&E, lease and commitments tables, the primary statements left out); no XBRL value or member name is in it. No tools.

## Input

One task file per filing at `data/notes/tasks/<accession>.md` (git-ignored, rebuilt by `--pack`): a header with ticker, form, fiscal year end, accession and the prompt version, then the candidate tables grouped as segment and market, property and equipment, lease, and commitments tables, each rendered like a statement table with a unit line (ledger/notes.py `make_task`, `with_units`: a note table with no unit of its own takes the primary statements' unit, marked `document`).

## Output

One JSON file per filing at `data/notes/outputs/<accession>.json`, shape `agents/schemas/notes@v1.json`: `accession`, `prompt_version`, `values` (field, dimension, table_id, row_label, column_label, cell_text, period_end, months, value, confidence, notes) and `not_found` (field, reason). months is 12 for a flow and 0 for a balance at period_end. The runner adds `_run` (model, seconds, input_tokens, output_tokens, attempts, task_sha). An unanswerable filing gets `{"error": reason, "rejected": ...}`.

## Model and tools

Model claude-opus-5-5, pinned in agents/agents.json. The same headless `claude -p` call as the Reader (ledger/agent.py): no tools, no web, no shell, no MCP, empty working folder, minimal environment, one retry, 1200-second timeout, no paid API.

## Prompts

In use: notes@v3. On file: notes@v1, notes@v2, notes@v3 (agents/prompts/). Versioned, never edited in place; history with `by` in agents/agents.json.

## Checks that judge it

At the call and again at load: the output schema (ledger/notes.py `validate_output`: field in range, dimension present exactly on the dimensioned fields, months 12 or 0, a non-negative integer value) and every citation resolved against the parsed table (`resolve_note`, the statement resolver with every value stored positive). A failure is a `note_extraction_failed` block exception (loader-made, not a rule file); two citations for the same fact in one filing is a failure too. Table B labels each fact against the filing's own XBRL instance where a segment or asset-type member matches (`fact_rows`: agree, unresolved, no_reference; ledger/reference/dimensions.py). On the Proof board: guard restated_between_filings (a cell from a later 10-K against a tag from an earlier one) on Facts, guard asset_type_mapping (every reported PP&E category maps to a us-gaap member or is open) on Mapping (ledger/proof.py `GUARDS`). No rule in rules/*.yaml runs on `note_extractions` or `facts`. Status `by` on its rows: xbrl, label, rule, resolution, mapping (ledger/status.py).

## Score

The Rules page shows three numbers for the six companies in scope (T49, ledger/score.py, `/api/agents/notes_reader/runs` → `score`), each with its denominator. Outputs: the rows of the `facts` table for those companies (the Facts stage of each company's Proof trail; the Mapping stage judges taxonomy/asset_types.yaml, not the reader, and is not counted), as checked, explained, open or blocked by `status.state`, out of all of them. Twin: among the facts the XBRL instance tags (label not `no_reference`), how many are checked by it (`answer_key(by) == "twin"`), out of those facts. Planted faults: not measured; `ledger faults` corrupts `extractions` only (ledger/faults.py), no fault test exists for the notes step, and the page says so instead of a number.
