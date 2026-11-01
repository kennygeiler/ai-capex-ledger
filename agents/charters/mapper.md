# Mapper

The mapping assistant (docs/TICKETS.md T33). One call per company, `ledger mapper <TICKER>`; the stage is Mapping on the Proof board (ledger/proof.py `stages["mapping"]`), where every reported PP&E category is mapped to a us-gaap member or open.

## Owns

Proposals only: one line per (ticker, reported_name) appended to `decisions/mapping_proposals.jsonl` (ledger/mapper.py `propose`), each a us-gaap `PropertyPlantAndEquipmentByTypeAxis` member from the list in the header of taxonomy/asset_types.yaml (ledger/mapper.py `members`), the note's words as evidence, a confidence (high, medium, low) and a reason. A proposal is a proposal until a person approves it on Reconcile (the "asset types" group): Approve or Edit calls `POST /api/mapping`, which writes the entry to taxonomy/asset_types.yaml with `by` = the person's name; Reject appends a rejection line to the same log so the next run does not propose the same member again; a proposal of a rejected member that arrives anyway (a delayed run) is never current and shows as "re-proposed after rejection" (T100, `by_name`), and a proposal after an approval changes nothing.

## Never touches

taxonomy/asset_types.yaml (only a person's approval writes it, through ledger/mapper.py `approve` behind the route), `facts`, `note_extractions`, every other table, `decisions/resolutions.jsonl`, `releases/`. Its task is the reported category names with no mapping and the note's own words around them (the parsed PP&E table and the text that introduces it); no XBRL member the filing tagged is in it. No tools.

## Input

One task file per company at `data/mapper/tasks/<TICKER>.md` (git-ignored, rebuilt by every run and by `--dry-run`): a header with the ticker and the prompt version, the allowed member list, the categories to map (each with the members a person already rejected for it, if any), then the note's words: for each PP&E table the categories were cited from, the text that introduces the table and the table as the notes reader saw it (ledger/mapper.py `make_task`, `note_words`).

## Output

One JSON object per call, shape `agents/schemas/mapper@v1.json`: `ticker`, `prompt_version`, `proposals` (reported_name, standard_type, evidence, confidence, reason). `standard_type` is a member from the list or `none`; `evidence` is words copied from the task. The runner appends one line per proposal to `decisions/mapping_proposals.jsonl` with `kind: proposed`, `prompt_version`, `model`, `at` and the run's `_run` (model, seconds, input_tokens, output_tokens, attempts), and writes a `runs` row (step `mapper`, subject the ticker). A rejected answer is retried once; a second rejection is the run's failure, recorded in `runs` and nowhere else.

## Model and tools

Model claude-opus-5-5, pinned in agents/agents.json. The same headless `claude -p` call as the Reader (ledger/agent.py): no tools, no web, no shell, no MCP, empty working folder, minimal environment, one retry, 1200-second timeout, no paid API (`LEDGER_CLAUDE`).

## Prompts

In use: mapper@v1. On file: mapper@v1 (agents/prompts/). Versioned, never edited in place; history with `by` in agents/agents.json.

## Checks that judge it

At the call: the output schema (ledger/mapper.py `validate_output`: every reported_name one the task asked for, `standard_type` in the member list or `none`, `evidence` words present in the task, `confidence` one of high, medium, low). On the Proof board: guard asset_type_mapping (every reported PP&E category maps to a us-gaap member with the note's words as evidence, or is open; ledger/proof.py `GUARDS`). The guard counts a category mapped only once a person approved it: a proposal closes nothing. The write itself refuses a member outside the list and a second entry for the same (ticker, reported_name) (ledger/mapper.py `approve`). Measured by T35: company seven's asset types mapped in under fifteen minutes of a person's time.

## Score

Not on the Rules page yet: `ledger/score.py` (T49) scores the readers whose outputs are rows of a table; the mapper's outputs are proposals, and a proposal closes nothing. Its score, when T35 measures company seven, is approved / edited / rejected out of proposed (`decisions/mapping_proposals.jsonl`: `kind` proposed, approved, rejected per (ticker, reported_name)), with the person's minutes beside it. Until then the page says "not measured" for the mapper, and the number that matters is the asset_type_mapping guard on the Proof board: categories mapped by a person's approval out of categories reported.
