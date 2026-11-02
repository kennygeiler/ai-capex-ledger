# The read API: /api/v1

Served by DATAHQ (`ledger app`, http://127.0.0.1:3610; hosted read-only at https://datahq-production.up.railway.app) from the working database. What the pipeline holds now;
the production Postgres holds what was signed (`ledger publish`, `docs/HANDOFF.md`). Read-only except views.
JSON by default; CSV with `?format=csv` or a `.csv` suffix. No authentication: it binds to localhost. Put it
behind a proxy that authenticates before exposing it.

## Lists

| Path | One row per | Columns |
|---|---|---|
| `/api/v1/companies` | company | ticker, name, layer, group, role, note |
| `/api/v1/values` | company, field, fiscal year, with a value | ticker, field, period, period_end, value, check_label, basis, first_reported, source, extraction_ids, accession, filed, citations, layer, proven, status, flag |
| `/api/v1/facts` | company, note field, dimension, year | ticker, field, dimension, period, period_end, value, check_label, xbrl, accession, basis, layer, status, flag |
| `/api/v1/statements` | statement an agent read | statement_id, ticker, field, period, kind, scope, class, amount_low, amount_high, amount_mid, share, quote, source, date, url, layer |
| `/api/v1/projects` | named project | ticker, period, name, kind, location, amount_low, amount_high, status, announced, in_service, counterparty, quote, source, url, layer (empty until the projects reader has run) |
| `/api/v1/taxonomy` | one row per measure, category, company and year (`docs/TAXONOMY.md`; schema v11, every column described in `docs/DATA_DICTIONARY.md`) | ticker, fiscal_year, period_end, period_kind, measure (spent, committed, derived, planned, company_stated_ai), category, reported_name, standard_concept, standard_type, mapped, value, value_high, change_from_prior, share, relation, has_value, unit, scale, currency, period_as_stated, quote, kind, project_kind, status, location, capacity_mw, forward_looking, part_year, program, source, source_kind, accession, filed, source_table, source_url, check, check_method, layer, proven |
| `/api/v1/views` | saved view | id, name, measure, filters, group, show, note, by, at |

`proven` says whether the row's company is in the proven set (`docs/PROOF.md`): every number of a proven company is checked or
explained; a row with `proven: false` is as the pipeline left it. `status` is a person's latest decision on the row from `decisions/resolutions.jsonl` (`accepted`, `explained`, `fix_pending`, `blocks`, or empty);
`flag` is what the numbers say by themselves (`differs_from_xbrl` on a value or fact that does not match the SEC's data). A consumer excludes `fix_pending` and `blocks` rows and treats a flag as a caveat.

The measures (`docs/TAXONOMY.md`) are the `taxonomy` list: spent, committed and derived by us-gaap concept, planned and company-stated AI verbatim.

The proof pages (`docs/PROOF.md`): `/api/v1/proof` is the board (the proven set's stage counts and the rest in one line), `/api/v1/proof/<ticker>`
a company's trail (per stage: checked, explained, open items with what they need), `/api/v1/rules` every rule, guard and definition with what it closed
and the open items by what is missing, `/api/v1/golden` the golden test's last result, `/api/v1/failures` the failure types as data (T54, `taxonomy/failures.yaml`): `total`, `by_class`, `by_origin` and `by_check` (each a list of `{<key>, types}` largest first, a bar being a number of types, never instances; `none` is a check of its own), `none` (how many types no check in code catches) and `types` (id, name, class, origin, check, count; a null count stays null). Answer keys (T56, `docs/PROOF.md`): the board, each company
on it and each stage of a trail carry `keys`, `{twin, second_source, tie, later_truth, none, rows}`, rows counted once by the strongest key that vouches
for them, `none` for a row no key vouches for (a quote, a mapping, an explanation, an open item), so the five sum to `rows`; the board and a trail also carry
`key_grade`, the keys in strength order (five since T92: twin, second source, tie, later truth, second reading) with `id`, `label` and `why`. Every trail item carries `key` (the strongest answer key behind its `by`, or null) and
`keys` (every key that vouches for it; one today).

One screen's feed: `/api/v1/reconcile?scope=all|<layer>|<ticker>` is the Reconcile workbench's rows (`docs/PROOF.md`): one per open
item with `ours`, `reference`, `delta`, `delta_pct`, `measure` (usd or share), the cause, the evidence (cell, screenshot, quote, inputs) and the
resolution. `POST /api/resolve` records one decision `{key, hash, state, reason, by}`; `POST /api/resolve/bulk` takes `{items: [{key, hash}], state, reason, by}`.
Both write `author_kind: person` (T69) and refuse (400) a `by` not on `config.PEOPLE`; an agent or replication writer calls
`resolutions.resolve(..., author_kind="run")`, and its line waits on Reconcile's "to confirm" group and fails gate G6 until a person decides
the key. Bulk checks every item before writing any: one bad item is a 400 and nothing is written. A run line never supersedes a
person's line with the same key and hash, whatever came between, and lines are ordered by `at`, not file position (T100, `resolutions.latest`).
A row's `key` is `kind|ticker|field|period|dimension|rule_id|subject` (T62; `resolutions.key_for`: '' for a part the item lacks, `%` inside a part
escaped `%25` and `|` `%7C`), one per queue item, and `hash` is the item's content; a consumer treats both as opaque and sends them back as received.
The feed also carries the mapping stage's open items (T33): one row per reported PP&E category with no entry in `taxonomy/asset_types.yaml`
(cause `asset_types`, key `asset_types|<ticker>|<reported_name>`, `evidence: {reported_name, proposal, rejected, note}` where `proposal` is the
mapper's latest standing line from `decisions/mapping_proposals.jsonl`: `standard_type`, `evidence`, `confidence`, `reason`, `prompt_version`,
`model`, `at`), and `members`, the us-gaap members a mapping may use (the list in the header of `taxonomy/asset_types.yaml`).
`POST /api/mapping` `{ticker, reported_name, standard_type, evidence, by}` writes that entry to `taxonomy/asset_types.yaml` under `by` with
today's date (the one writer of the file): 400 when `standard_type` is not in `members`, when the (ticker, reported_name) already has an
entry, or when a field is empty; the reply is the entry written. `POST /api/mapping/reject` `{ticker, reported_name, standard_type, by,
reason}` appends a `rejected` line to the proposals log so the next `ledger mapper` run does not propose that member again.

The Release page (`docs/PROOF.md`): `/api/v1/release/checklist` (optional `?version=vX.Y.Z`; default the minor bump of the last
release folder) is the checklist as JSON: `version`, `previous`, `scope`, `hash` (of the packet built in memory), `ok`, `red` (the
required lines that fail), `lines` (each `{id, label, required, count, state: pass|fail|info|not_run, ok, link, note, detail}`),
`gates` (`table` per gate per company, `failing`), `diff` (per list: `rows`, `added`, `removed`, `changed`, `key`, `columns_added`,
`columns_removed`, `examples`), `golden` and `tests` (the two report files as they are, `tests` from `reports/tests.json` as `ledger test` writes it:
`{ok, count, failures: ["test id: first line of the error"], skipped, golden: true|false|null, at, git, dirty, seconds}`, null when
not run; the `tests` line is `pass` on this commit, `fail` on any failure, `info` with a "stale" note on another commit or a dirty tree). `POST /api/release/sign` `{version, by}` builds `releases/<version>/`, signs it as
`by` with the checklist stored under `checklist` in `SIGNOFF.json`, and publishes; 403 on the read-only copy, 400 while any
required line is red (checked twice: before the write and on the folder as written) or `by` is empty or not a string; one
signature at a time. The reply says `published` and, when the publish failed after the signature landed, `publish_error`;
`SIGNOFF.json` records the same (`published`, `published_at` and `rows` on success; `published: false` and `publish_error` on
failure; rerun `ledger publish`). `/api/outputs` carries per release `checklist: {open, unmapped, scope, unconfirmed, at}` from
that stored checklist, or null for a release signed before it existed, and `published` (false: signed, the publish failed).

A release's `manifest.json` (T66) carries `version`, `stage`, `scope`, `hash`, `files`, `rules` (rule id → sha256 prefix), `decisions`,
and `provenance`: `{prompts: {reader: [prompt_version, ...]}, models: [...], parser_versions: [...], unrecorded: {reader: n}, git: {head,
dirty}, inputs: {path: sha256}}`, computed over the rows the packet writes (the statement cells `values.csv` cites, the note cells
`facts.csv` cites, every statement and project in scope, the filings of the companies in scope). Readers are the ids in
`agents/agents.json` (`reader`, `notes_reader`, `ai_reader`, `projects_reader`); a row's model is the one its run recorded; a row
whose prompt version or model is not on record counts once under `unrecorded`, never guessed. `git.head` and `git.dirty` are null
without git (the hosted copy); `inputs` hashes `definitions/companies.yaml`, every `taxonomy/*.yaml` and `decisions/resolutions.jsonl`
(null when absent). `provenance` is the record; the top-level `prompt`, `parser` and `model` name the versions in use when the
packet was built and stay for older consumers. The manifest is not among the hashed files, so none of this moves `hash`.

Every POST (a decision, a view, a prompt, a signature) needs `Content-Type: application/json` and, when the browser sends an
`Origin`, this server's own (`http://127.0.0.1:<port>` or `http://localhost:<port>`); anything else is 403 before any route, so a
page on another site cannot write through the browser's permission to POST to localhost without a preflight. The body must be a
JSON object with a numeric `Content-Length`: a list, a bare value or a bad length is 400 on every route. The sign's reply may also
carry `record_error` when the publish's outcome could not be written into `SIGNOFF.json`; the publish itself stands as reported.

The agents (`docs/TICKETS.md` T48, T49): `/api/agents` is every live agent with its charter, history and runs; `/api/agents/<id>/runs`
(optional `?t=MSFT,NVDA`, default the proven set) is that agent's runs per company and its `score`: `{outputs, checked, explained, open,
blocked, twin, faults, stage, companies, note}`, counts with their denominators and no shares (the page divides). `outputs` is the
reader's rows in its Proof stage (`stage`) for those companies and the four states sum to it (`open` excludes `blocked` here); `twin`
is `{agree, of, interval}` over the rows XBRL tags, or null for a reader whose rows are quotes: `interval` is the Wilson 95% interval of
`agree / of` as `[low, high]` fractions to 4 dp (T53, `ledger/stats.py`), derived from the two counts alone, null when `of` is 0 (the page recomputes it from the counts rather than reading it); `faults` is `{caught, planted, no_effect, escaped}`
from the latest `ledger faults` run that covered each company, or null when the step has no fault test or no run covered them,
with the reason in `note`.

Two roll-ups, not lists: `/api/v1/coverage` (per layer and field: companies with an AI amount, words only, none,
not run) and `/api/v1/cost` (agent calls, tokens, seconds, attempts, failures and an estimated price at list, per
step and per company; `ledger cost` writes the same to `reports/cost.json`).

## One shape, two doors

`?release=vX.Y.Z` on any of companies, values, facts, statements, projects, taxonomy serves that signed
release's file instead of the working database, typed back from CSV and with a `release` column, so a consumer gets
the same columns from a release as from the live API. A release holds one CSV per list (`ledger release`), and
`ledger publish` pushes those same files to Postgres as `ledger_<list>` tables with `current_<list>` views. Column types follow
`publish.NUMERIC`, `DATE` and `BOOLEAN`; a column an older release published as text and schema v11 types boolean (`proven` in
`ledger_taxonomy`, from v1.7.0) is converted in place the first time a release publishes after the change
(`ALTER COLUMN … TYPE boolean USING (col = 'True' OR col = 'true')`, `publish.retypes`, guarded by the column's current type so it
runs once); older releases' rows keep their value, read as boolean.

## Point in time: `?as_of=D`

`values` carries one row per (company, field, fiscal year) that has a value: a row the newest 10-K gives no figure for (`not_reported`
in the database) is not a value and is not served or shipped (T64; the packet's QUALITY.md counts them). Beside the value: `first_reported`
(the first 10-K's figure) and `basis` (`restated` when a later 10-K moved it by more than `config.RESTATEMENT_TOLERANCE`, half a rounding
unit), `accession` and `filed` of the 10-K the value comes from (every cell behind a value is from that one filing), `extraction_ids` (the
cited cells' ids) and `citations` (each cell spelled out: accession, table, row label, column label, cell text, joined by ` ; `). `releases/<v>/values.csv`
is this list for the scope, with the same columns, and the release README's column tables are written from the headers that ship.

`values` and `taxonomy` carry the newest filing's figure (with `first_reported` and `basis` beside it on values). A backtest run on day D
must not see a figure a later 10-K restated: that is lookahead. `?as_of=YYYY-MM-DD` on `/api/v1/values` or `/api/v1/taxonomy` (JSON or
CSV, with the other filters) answers from `extractions` (every filing's cited cells are kept) joined to `documents.filed` (`ledger/pit.py`):
the figure the newest filing filed on or before D gave, by the values builder's own arithmetic (one cell per field, opex from the three cells
of the same 10-K column, cost-of-revenue lines summed when there is no total line, the newest filing by `filed` and on the same day the more
complete one). Every field of a year comes from that one newest filing, as in `values`: when it lacks the line the field is absent at
that date even if an older filing had it (`values` says not_reported there). A (company, field, year) no filing by D reports is absent,
never null-filled. Overrides are not applied. A bad date, `as_of` on any other list, or `as_of` together with `release=` (a release is a
fixed snapshot; the as-of answer reads the live cells) is 400.

- `values?as_of=D`: ticker, field, period, period_end, value, accession, filed, restated_later (a later filing changed the figure beyond its
  rounding, even one after D), vintage_check, basis, first_reported (both as `values` holds them today), source, extraction_ids, layer, proven,
  status, as_of. No `check_label` or `flag`: the XBRL comparison was made on the newest figure, not this one.
- **Older vintages are not reconciled.** Only the newest filing's figure is compared with XBRL (`reconcile.values_for`). An as-of row from the
  accession `values` checked carries that outcome in `vintage_check` (agree, unresolved, definition_gap, no_reference); every row from an older
  filing carries `vintage_check: "unchecked"`: the figure is the cell as the agent read it, never compared with its own filing's tags. The case
  that shows why this matters: AT&T revenue FY2022 is 120,741,000,000 in `values` with `first_reported` 120,741,000 and `basis` restated; the
  first 10-K's cell `120,741` was read against a `(000s)` unit line (scale 1,000) where the later 10-Ks say `(000,000)`, so the "restatement" is a
  1000× misread, and `as_of=2023-06-30` serves $120.7 million as what that filing said. The row says `unchecked`; it does not say right. The
  per-vintage check is T55b (`docs/TICKETS.md`). Every as-of JSON response carries `api.AS_OF_NOTE` as a top-level `note` (`ledger/app.py`).
- `taxonomy?as_of=D`: the `spent` / `capex` rows are re-pointed at the newest filing filed by D (value, source, accession, filed, source_table,
  source_url; `check` reads `not_checked` with method `none` when that filing is not the one the live row was checked against). Every other
  row is kept only when its own `filed` is on or before D: a 10-K note, MD&A or 8-K figure filed after D is dropped, not replaced by an earlier
  filing's (`facts` holds the newest filing's note figures only); a row with no filing date (transcript, CFO commentary, gathered) is dropped.
  So the taxonomy as-of is complete for capex and conservative (absent, never stale) for the rest: on the six today (1 Nov 2026) `as_of`
  set to today returns 590 of the live list's 617 rows, the 27 undated transcript, CFO commentary and gathered rows dropped, so as-of today
  is not the live taxonomy.

The canonical case, APLD's FY2025 revenue (`period_end` 2025-05-31), which moved 58% between two 10-Ks: the FY2025 10-K
(`0001144879-25-000021`, filed 2025-07-30) reported $144,193,000; the FY2026 10-K (`0001144879-26-000048`, filed 2026-07-29) restated it to
$228,569,000. `values` holds 228,569,000 with `first_reported` 144,193,000 and `basis` restated.

```
/api/v1/values?ticker=APLD&field=revenue&period=FY2025&as_of=2025-07-29   → no row (nothing filed yet)
/api/v1/values?ticker=APLD&field=revenue&period=FY2025&as_of=2026-07-28   → 144193000, accession 0001144879-25-000021, filed 2025-07-30, restated_later true
/api/v1/values?ticker=APLD&field=revenue&period=FY2025&as_of=2026-07-29   → 228569000, accession 0001144879-26-000048, filed 2026-07-29, restated_later false
```

`tests/test_pit.py` proves on the six that for every filing date D the returned accession's `filed <= D`, that today's answer equals `values`,
and the flip above. The release packet has no as-of file (T55: the packet holds the signed dataset once; the as-of answer is derived from the
same cells); the packet README names this endpoint.

## Filters and grouping

Every list takes `ticker`, `layer`, `period`, `field`, `kind`, `method`, `scope`, `dimension`, `source`, `measure`, `category`, `fiscal_year`, `standard_type`, `check`,
`source_kind`, `period_kind`, `has_value`, `mapped`, `status` as comma-separated values (and values and taxonomy `as_of`, above), matched without regard to case; a boolean takes `true` or `false`
(`has_value=false` is the rows the company named without a figure). `group=<column>` rolls the list up: one row per distinct
value with `rows`, `amount` (the sum of the list's amount column: value, amount_mid or amount) and
`with_amount`.

```
/api/v1/taxonomy?measure=spent&category=capex&layer=hyperscaler
/api/v1/taxonomy?category=ppe_gross_by_type&standard_type=TechnologyEquipmentMember&group=ticker
/api/v1/taxonomy?measure=company_stated_ai&ticker=MSFT&format=csv
/api/v1/taxonomy?check=differs,unmapped
/api/v1/taxonomy?source_kind=8-K%20release&has_value=true
/api/v1/facts?field=segment_capex&ticker=APLD
```

A JSON response is `{"list", "count", "filters", "rows"}`.

## Views

A view is a saved question: `{id, name, measure, filters, group, show, note}` where `measure` is one of the lists
above (taxonomy, values, facts, statements, projects), `filters` and `group` are as above, and `show` is
`grid`, `bars` (one bar per group), `lines` (one line per company by year), `shares` (a share grid) or `chart`, the Explorer's spec in `chart: {x, series, type, value}` (x and series from period, fiscal_year, ticker, layer, field, category, measure, standard_type, kind, dimension, status, scope, source, source_kind, period_kind, check; type bars, stacked, lines or share; `value: "change"` plots `change_from_prior`). Views live in `data/views.json`, tracked.

```
GET  /api/v1/views                 the saved views
GET  /api/v1/views/<id>/data       {"view", "rows"}: the view's query, run now (format=csv for the rows)
POST /api/v1/views                 {"view": {...}, "by": "name"}: save (same id replaces; the old one goes to history)
POST /api/v1/views/<id>/delete     {"by": "name"}
```

## Errors

`404` with `{"error", "lists"}` for an unknown list; `400` for a bad filter or view; `503` while the pipeline holds
the database (`{"error": "the pipeline is writing to the database; try again when the run ends"}`).
