# Map: where is X

A map, not a manual. Tables are DuckDB (`ledger/core/store.py` declares them); files are tracked unless marked. The
state machines are `ledger/core/states.py` (docs/STATES.md). Commands are `uv run python -m ledger <command>`, one module
each in `ledger/cli/` (they do the table writes: `store.write`).

## Packages

| Package | Job | Writes | Reads |
|---|---|---|---|
| `ledger/core/` | the store, config, the state machines, the one definition of open | the schema | everything |
| `ledger/ingest/` | fetch and parse filings; texts; the XBRL answer key (`reference/`) | `documents`, `reference_values`, `texts`; `data/raw`, `data/docs`, `data/text` (untracked) | the SEC (or `data/raw` offline) |
| `ledger/extract/` | the agents: tasks, headless runs, output contracts, loaders | `extractions`, `note_extractions`, `facts`, `ai_statements`, `ai_spend`, `projects`, `runs`; `data/*/outputs/` | `documents`, `texts` |
| `ledger/checks/` | everything that checks a number: reconcile labels, rules, ties, crops, faults, Proof, golden | `values`, `exceptions`, `rules`; `reports/evidence/crops.json` | the extracted tables |
| `ledger/review/` | what a person decides: resolutions, decisions, mappings, definitions, gold verdicts, Reconcile | `decisions/*.jsonl`, `taxonomy/asset_types.yaml`, `definitions/companies.yaml`, `rules/*.yaml` (explains rules), `gold/*.json` | the checks |
| `ledger/release/` | what ships: the taxonomy rows, the checklist, the packet, signing, publishing, the claims register | `releases/v*/`, Postgres, `reports/tests.json`, `docs/CLAIMS.md`, `claims/hosted.json` | everything above |
| `ledger/web/` | Kenny's Data Emporium (port 3610): routes, the read API, trail cards, the filing viewer, pages | `data/views.json` | everything above |

## Key modules

| Module | Owns | State machine it decides |
|---|---|---|
| `core/status.py` | the one definition of open: checked / explained / open / blocked (`_state`, `of_value`, `of_fact`, `of_mapping`) | row groups (M1) |
| `core/states.py` | every state that reaches a page: its states, moves, deciding function, page word; `/pages/_states.js`, `/api/v1/states` | all ten: row, ladder, check, mapping, crop, gold, gold_group, crosscheck, line, edgar |
| `core/store.py` | DuckDB schema, write contracts, `data/ledger.duckdb`, `docs/DATA_DICTIONARY.md` | |
| `core/config.py` | companies, years, fields, `PROVEN`, `SCOPE`, `PEOPLE`, `INDUSTRIES` | |
| `ingest/edgar.py` | the SEC client, its cache, `LEDGER_OFFLINE` | |
| `ingest/tables.py`, `statements.py` | the table parser, the statement locator | |
| `extract/extract.py`, `notes.py`, `guidance.py`, `projects.py` | task packing, output contract and loader per reader (statements, notes, AI statements, projects) | |
| `extract/agent.py`, `agents.py` | the headless `claude -p` run; the named agents (`agents/agents.json`) | |
| `checks/reconcile.py` | fiscal-year `values` and their label against XBRL | check (M1a) |
| `checks/rules.py`, `guards.py` | the rule engine over `rules/*.yaml`; the part-year and program guards | |
| `checks/ties.py` | readings across filings and ties to totals: the note-figure ladder (`fact_state`) | ladder (M1b) |
| `checks/crops.py` | a picture of every cited cell, `reports/evidence/crops.json` | crop (M14) |
| `checks/calc.py` | a figure calculated from several cells: formula, arithmetic, roles, cross-checks (filing total, XBRL) | crosscheck (M18) |
| `checks/proof.py` | Proof: every row's state per stage per company | |
| `checks/golden.py` | the golden test (`fixtures/`) | |
| `review/resolutions.py` | `decisions/resolutions.jsonl`, keys (`key_for`) | |
| `review/workbench.py` | Reconcile's rows | |
| `review/mapper.py`, `mapcard.py` | the mapping assistant and the mapping decision card | mapping (M5, via `status.of_mapping`) |
| `review/gold.py` | the gold set, verdicts, error rate per group, hard items first | gold (M7), gold_group (M17) |
| `release/taxonomy.py` | the taxonomy rows (`/api/v1/taxonomy`, `taxonomy.csv`) | |
| `release/checklist.py` | the Release page's checklist and the Sign act | line (M9) |
| `release/claims.py` | the claims register, the page scan, `docs/CLAIMS.md` | |
| `web/app.py` | every route; `pages/*.js` and `app.html` | |
| `web/cards.py` | the trail's evidence cards and status tiles | edgar freshness via `states.edgar` (M12) |

## If you want to change X, edit Y

| To change | Edit | Then |
|---|---|---|
| notes extraction logic | `ledger/extract/notes.py` (contract, loader); the prompt is a new version in `agents/prompts/` (never in place) | `ledger notes --run` then `--load`; `golden --check` |
| a rule | `rules/<id>.yaml`; a new check function in `ledger/checks/rules.py` | `ledger rules`; `golden --check` |
| a company-specific definition | `definitions/companies.yaml` (who, why, `periods`), or "Make this a definition" on Reconcile | `ledger reconcile`, `ledger rules` |
| a category mapping | Reconcile's asset types group (writes `taxonomy/asset_types.yaml` confirmed), or `ledger mapper <T>` for proposals | any taxonomy read |
| UI copy, a state's label | a state word: `ledger/core/states.py` only; other copy: `ledger/web/pages/<page>.js` or `web/cards.py`; register every shown string in `claims/claims.yaml` | `ledger claims`; `tests.test_states`, `tests.test_claims` |
| a new state | declare it in `ledger/core/states.py` (kind, word, moves), return it from the machine's deciding function | `tests/test_states.py` |
| adding a company | `ledger run --ticker X`; its industry in `ledger/core/config.py` `INDUSTRIES` | `docs/COMPANIES.md` |
| crops | `ledger/checks/crops.py`; pictures are untracked | `ledger evidence --crops --ticker …` |
| the release gate | `ledger/release/checklist.py` (lines), `ledger/release/release.py` (`GATES`: G1, G4, G5, G6) | `tests/test_checklist.py` |

## Naming

- Finding ids (`claims/findings.jsonl`, append-only, union-merged): `F-<BRANCH CODE><n>` (`F-RC7`), or `S-<n>` for a
  state finding; plain `F<n>` stops at F30. Close one by appending a line with the same id, new `status` and `at`.
- Prompt versions: `<agent>@v<n>` (`notes@v3`); a change is the next version, switched on as a second step.
- Change records: the commit message (what, why, what is left open); there is no status diary. `docs/CLAIMS.md` is
  generated: `ledger claims` after every merge.
