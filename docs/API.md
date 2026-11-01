# The read API: /api/v1

Served by DATAHQ (`ledger app`, http://127.0.0.1:3610; hosted read-only at https://datahq-production.up.railway.app) from the working database. What the pipeline holds now;
the production Postgres holds what was signed (`ledger publish`, `docs/HANDOFF.md`). Read-only except views.
JSON by default; CSV with `?format=csv` or a `.csv` suffix. No authentication: it binds to localhost. Put it
behind a proxy that authenticates before exposing it.

## Lists

| Path | One row per | Columns |
|---|---|---|
| `/api/v1/companies` | company | ticker, name, layer, group, role, note |
| `/api/v1/values` | company, field, fiscal year | ticker, field, period, period_end, value, check_label, basis, source, extraction_ids, layer, status, flag |
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
and the open items by what is missing, `/api/v1/golden` the golden test's last result.

One screen's feed: `/api/v1/reconcile?scope=all|<layer>|<ticker>` is the Reconcile workbench's rows (`docs/PROOF.md`): one per open
item with `ours`, `reference`, `delta`, `delta_pct`, `measure` (usd or share), the cause, the evidence (cell, screenshot, quote, inputs) and the
resolution. `POST /api/resolve` records one decision `{key, hash, state, reason, by}`; `POST /api/resolve/bulk` takes `{items: [{key, hash}], state, reason, by}`.
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

Every POST (a decision, a view, a prompt, a signature) needs `Content-Type: application/json` and, when the browser sends an
`Origin`, this server's own (`http://127.0.0.1:<port>` or `http://localhost:<port>`); anything else is 403 before any route, so a
page on another site cannot write through the browser's permission to POST to localhost without a preflight. The body must be a
JSON object with a numeric `Content-Length`: a list, a bare value or a bad length is 400 on every route. The sign's reply may also
carry `record_error` when the publish's outcome could not be written into `SIGNOFF.json`; the publish itself stands as reported.

The agents (`docs/TICKETS.md` T48, T49): `/api/agents` is every live agent with its charter, history and runs; `/api/agents/<id>/runs`
(optional `?t=MSFT,NVDA`, default the proven set) is that agent's runs per company and its `score`: `{outputs, checked, explained, open,
blocked, twin, faults, stage, companies, note}`, counts with their denominators and no shares (the page divides). `outputs` is the
reader's rows in its Proof stage (`stage`) for those companies and the four states sum to it (`open` excludes `blocked` here); `twin`
is `{agree, of}` over the rows XBRL tags, or null for a reader whose rows are quotes; `faults` is `{caught, planted, no_effect, escaped}`
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

## Filters and grouping

Every list takes `ticker`, `layer`, `period`, `field`, `kind`, `method`, `scope`, `dimension`, `source`, `measure`, `category`, `fiscal_year`, `standard_type`, `check`,
`source_kind`, `period_kind`, `has_value`, `mapped`, `status` as comma-separated values, matched without regard to case; a boolean takes `true` or `false`
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
