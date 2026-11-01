# AI spend reader

The reader of what a company says about AI's part of its spending. One call per gathered text, `ledger aispend --run`; the stage is Statements on the Proof board (ledger/proof.py `stages["statements"]`), and its outlook statements feed the planned rows of the taxonomy.

## Owns

Table `ai_statements` (table A, every statement read, verbatim quote and all) and, derived by code, `ai_spend` (table B: per company, field, fiscal year and kind, the most specific statement), both written by `ledger aispend --load` (ledger/cli/aispend.py, ledger/guidance.py `spend_rows`). Fields: capex, opex, revenue; kinds actual, outlook; scopes ai, total; classes explicit_amount, explicit_share, qualitative (ledger/guidance.py). Nothing it writes is a number the pipeline made up: an amount range, a share, or words only, each a quote.

## Never touches

Filing tables (`extractions`, `values`, `note_extractions`, `facts`), `projects`, the texts themselves on disk (code gathers them, ledger/texts.py), the XBRL reference, `decisions/`, `releases/`. Its task is the ranked passages only (ledger/guidance.py `passages`: spend words next to AI words, capex with an outlook word, capex inside Liquidity and Capital Resources, whole paragraphs, at most 30). No tools.

## Input

One task file per text at `data/aispend/tasks/<text_id>.md` (git-ignored, rebuilt by `--pack`): a header with ticker, source (10-K MD&A, earnings release, transcript, CFO commentary), period end, fiscal year, the text id as `Accession:` and the prompt version, then the passages numbered `[p01]`, `[p02]`, and so on (ledger/guidance.py `make_task`). A text with no passage is not asked: the runner records an empty answer with zero tokens and zero attempts (ledger/cli/aispend.py).

## Output

One JSON file per text at `data/aispend/outputs/<text_id>.json`, shape `agents/schemas/aispend@v4.json` (v1 on file too): `accession` (the text id), `prompt_version`, `statements` (field, fiscal_year, kind, scope, class, amount_low, amount_high, share, quote, passage, confidence, notes) and `none_found` (field, reason). The runner adds `_run` (model, seconds, input_tokens, output_tokens, attempts, task_sha). An unanswerable text gets `{"error": reason, "rejected": ...}`.

## Model and tools

Model claude-opus-5-5, pinned in agents/agents.json. The same headless `claude -p` call as the Reader (ledger/agent.py): no tools, no web, no shell, no MCP, empty working folder, minimal environment, one retry, 1200-second timeout, no paid API.

## Prompts

In use: aispend@v4. On file: aispend@v1, aispend@v2, aispend@v3, aispend@v4 (agents/prompts/). Versioned, never edited in place; history with `by` in agents/agents.json.

## Checks that judge it

At the call and again at load: the output schema and the one check that matters, every quote is a verbatim sentence (at least 20 characters, whitespace and quote marks normalised) of the passage it cites, which must be in the task (ledger/guidance.py `validate_output`); an explicit amount needs integer dollars 0 ≤ low ≤ high, an explicit share needs 0 < share ≤ 1, a fiscal year is 2015 to 2035 or null (code then assigns the filing's year, `period_of`, and says so in notes). A failure is an `ai_extraction_failed` block exception (loader-made, not a rule file). On the Proof board every statement is checked by `quote`, except that guard part_year tags an actual amount that covers a quarter, a half or N months and guard program_words tags an outlook with program words (ledger/proof.py `GUARDS`, ledger/guards.py); the same two guards tag its outlook rows under Planned. No rule in rules/*.yaml runs on `ai_statements` or `ai_spend`. The warning agents.json names for an AI amount above the company's own capex is not stated in code. Status `by` on its rows: quote, rule (ledger/status.py).

## Score

The Rules page shows the score for the six companies in scope (T49, ledger/score.py, `/api/agents/ai_reader/runs` → `score`), each number with its denominator. Outputs: the rows of `ai_statements` for those companies (the Statements stage of each company's Proof trail), as checked (a verified quote), explained (the part_year or program_words guard) or open by `status.state`, out of all of them. Twin: none; a statement is a quote, no structured twin exists for it, so the page says so instead of a number. Planted faults: not measured; `ledger faults` corrupts `extractions` only (ledger/faults.py), no fault test exists for the aispend step, and the page says so instead of a number.
