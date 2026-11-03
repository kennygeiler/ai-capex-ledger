# Projects reader

The named-project reader. One call per gathered text, `ledger projects --run`; its rows are the `project` category of the Planned stage on the Proof board (ledger/checks/proof.py `stages["planned"]`, ledger/release/taxonomy.py).

## Owns

Table `projects`: one row per project per text, with `latest` true on the newest text's row per (ticker, project name) so a project announced, then built, then in service shows once at its latest status (ledger/cli/projects.py, ledger/extract/projects.py `rows_for`, `latest`). Kinds: data_center, fab, plant, power, gpu_cluster, cloud_commitment, network, other; statuses: announced, under_construction, in_service, contracted, cancelled (ledger/extract/projects.py `KINDS`, `STATUSES`). Size fields amount_low, amount_high, capacity_mw, gpus, announced, in_service are what the sentence states or null.

## Never touches

Filing tables (`extractions`, `values`, `note_extractions`, `facts`), `ai_statements`, `ai_spend`, the texts on disk, the XBRL reference, `decisions/`, `releases/`. Its task is the passages that name a project-like thing and give it a size (ledger/extract/projects.py `passages`: project words and size words in one paragraph, document order, at most 30). No tools.

## Input

One task file per text at `data/projects/tasks/<text_id>.md` (git-ignored, rebuilt by `--pack`): a header with ticker, source, period end, fiscal year, the text id as `Accession:`, the prompt version and the text date, then the passages numbered `[p01]`, `[p02]`, and so on (ledger/extract/projects.py `make_task`). The same texts the AI spend reader reads (`texts`: 10-K MD&A, 8-K earnings releases, transcripts, CFO commentary).

## Output

One JSON file per text at `data/projects/outputs/<text_id>.json`, shape `agents/schemas/projects@v1.json`: `accession` (the text id), `prompt_version`, `projects` (name, kind, status, location, counterparty, amount_low, amount_high, capacity_mw, gpus, announced, in_service, quote, passage, confidence). The runner adds `_run` (model, seconds, input_tokens, output_tokens, attempts, task_sha). An unanswerable text gets `{"error": reason, "rejected": ...}`.

## Model and tools

Model claude-opus-5-5, pinned in agents/agents.json. The same headless `claude -p` call as the Reader (ledger/extract/agent.py): no tools, no web, no shell, no MCP, empty working folder, minimal environment, one retry, 1200-second timeout, no paid API.

## Prompts

In use: projects@v1. On file: projects@v1 (agents/prompts/). Versioned, never edited in place; history with `by` in agents/agents.json.

## Checks that judge it

At the call and again at load: the output schema and every quote a verbatim part (at least 8 characters, normalised) of the passage it cites, which must be in the task (ledger/extract/projects.py `validate_output`); a name of 3 to 120 characters, kind and status in range, amount_low and amount_high together as integer dollars with 0 < low ≤ high, capacity_mw and gpus positive or null, dates YYYY, YYYY-MM or YYYY-MM-DD or null, confidence 0 to 1. A failure is a `projects_failed` block exception (loader-made, not a rule file). On the Proof board its latest rows are planned rows checked by `quote`, with guards part_year and program_words tagging a part-year amount or a program statement (ledger/checks/proof.py `GUARDS`, ledger/release/taxonomy.py). No rule in rules/*.yaml runs on `projects`. A check of a stated size against anything outside the text is not stated in code. Status `by` on its rows: quote, rule (ledger/core/status.py).

## Score

The Rules page shows the score for the six companies in scope (T49, ledger/checks/score.py, `/api/agents/projects_reader/runs` → `score`), each number with its denominator. Outputs: the `project` rows of the Planned stage of each company's Proof trail (the taxonomy's planned rows of category project: one per project at its latest mention, so fewer than the `projects` table's rows), as checked (a verified quote), explained (the part_year or program_words guard) or open by `status.state`, out of all of them. Twin: none; a project row is a quote, no structured twin exists for it, so the page says so instead of a number, and there is no interval either: a twin exists only where the filing tags the number (T53). Planted faults: not measured; `ledger faults` corrupts `extractions` only (ledger/checks/faults.py), no fault test exists for the projects step, and the page says so instead of a number.
