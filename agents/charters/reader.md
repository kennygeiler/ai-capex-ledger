# Reader

The statement reader. One call per 10-K filing, `ledger extract --run`; the stage is Values on the Proof board (ledger/proof.py, `stages["values"]`).

## Owns

Table `extractions`: one row per filing, field, period and cited cell, written by `ledger extract --load` (ledger/cli/extract.py). Fields: revenue, cost_of_revenue, cost_of_revenue_part, operating_income, capex (ledger/extract.py `FIELDS`). The `values` table is built from `extractions` by code (`ledger reconcile`); the reader never writes it.

## Never touches

Note tables, texts, `facts`, `ai_statements`, `projects`, the XBRL reference, `decisions/`, `releases/`. Its task carries no XBRL value and no tag name (ledger/extract.py `make_task`: income and cash-flow statement tables only), so it cannot copy the answer key. It runs with no tools: it reads the task and answers.

## Input

One task file per filing at `data/extract/tasks/<accession>.md` (git-ignored, rebuilt by `--pack`): a header with ticker, form, period end, accession and the prompt version, then the located income statement and cash-flow statement tables rendered as rows of `label | [column] cell text` with each table's unit line and where the unit was found (ledger/extract.py `render_statement`).

## Output

One JSON file per filing at `data/extract/outputs/<accession>.json`, shape `agents/schemas/extraction@v2.json` (v1 outputs stay valid): `accession`, `prompt_version`, `values` (field, table_id, row_label, column_label, cell_text, period_end, months, value, confidence, notes) and `not_found` (field, reason). The runner adds `_run`: model, seconds, input_tokens, output_tokens, attempts, task_sha (ledger/agent.py `ask`). A filing the reader cannot answer gets `{"error": reason, "rejected": last answer}` instead, so the failure is on file, not guessed.

## Model and tools

Model claude-opus-5-5, pinned in agents/agents.json and read at call time (ledger/agent.py `model`). Runs headless as `claude -p --output-format json --tools "" --model <model> --setting-sources project --strict-mcp-config --disable-slash-commands --no-session-persistence` in an empty temporary folder with only HOME, PATH, USER and LANG in the environment (ledger/agent.py `_cmd`, `ENV`): no web, no shell, no MCP, no project instructions, no paid API. The binary is `LEDGER_CLAUDE` or `claude` on PATH. One retry when the answer breaks its contract, with the reason appended to the prompt; two attempts in all. Timeout 1200 seconds per call.

## Prompts

In use: statements@v2. On file: statements@v1, statements@v2 (agents/prompts/). Never edited in place: a change is the next version, saved and switched on as two separate logged steps (ledger/agents.py). The history with who changed what is in agents/agents.json.

## Checks that judge it

At the call (ledger/agent.py `extract`): the output schema (ledger/extract.py `validate_output`) and every citation resolved against the parsed filing (`resolve`: table, column, row and cell text must exist, the value must equal cell × unit under the sign convention). A failed check is one retry, then an error file. At load (`ledger extract --load`): the same two checks again, plus two values for one field and period in one filing; each failure is an `extraction_failed` block exception (loader-made, not a rule file). Then every rule in rules/*.yaml runs on `extractions` and `values` (ledger/rules.py): citation_resolves, column_matches_period, cost_lines_summed, period_length, sign, statement_tie, xbrl_reconcile (block); coverage, jump, outlier_vs_own_history, row_label_switch, unit_from_document (warn); definition_note, no_10k_yet, restated (info). coverage and no_10k_yet judge the filing set more than the reading. Chrome re-reads every cited cell on the rendered 10-K (`ledger evidence`, ledger/evidence.py) and `ledger faults` plants mistakes to see the checks catch them. No guard in proof.GUARDS fires on its outputs. Status `by` on its rows: xbrl, definition, label, rule, resolution (ledger/status.py).

## Score

The Rules page shows three numbers for the six companies in scope (T49, ledger/score.py, `/api/agents/reader/runs` → `score`), each with its denominator. Outputs: the rows of the `values` table for those companies (the Values stage of each company's Proof trail; the stage's warn findings are not counted), as checked, explained, open or blocked by `status.state`, out of all of them. Twin: among the values XBRL tags (label not `no_reference` or `not_reported`), how many are checked by it (`answer_key(by) == "twin"`), out of those values, with the share's Wilson 95% interval (T53, ledger/stats.py); the interval says how far the share can move on this many rows and covers only the values the filing tags, not the `no_reference` or `not_reported` rows, which have no twin to agree with. Planted faults: of the faults `ledger faults` planted in those companies' `extractions` in the latest run whose report holds them (`runs` table step `faults`, reports/<name>-faults.json), how many a rule or the XBRL comparison caught, out of all planted; a fault that reached no released value is counted apart, an escaped one is named.
