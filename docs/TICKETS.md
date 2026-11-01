# Tickets: the sign-with-confidence flow

*Written 1 Nov 2026 from a page-by-page review of DATAHQ at 1600px and a column audit of the v1.7.0 packet. The goal: a person
signs a release from the app, and the app has shown them everything that could make the signature wrong. Scope until that
works: the proven set only (`config.PROVEN`); the other companies stay in the database and leave the UI, the packet and the
published tables. Scale after.*

Decisions folded in (1 Nov, Kenny + review):
- The scope is the six proven companies, AMD included: six are proven and golden-green, dropping to five discards finished work.
- The other companies are hidden behind `SCOPE`, never deleted: re-ingesting them costs thirty minutes and agent time.
- Order: A, then C, then B. The schema changes before the first release signed from the app, so no signature lands on a shape
  that changes the week after.
- C is one commit series: schema v11, every reader and writer, golden re-frozen once, dictionary regenerated, tests, v1.8.0.
  Never scattered across unrelated commits. See "How C runs".
- Company seven is measured before any promise of a hundred: F below.
- A second reviewer is a ticket (T34). One person signing their own work stays a weakness until then.
- Production rails (auth, decisions in Postgres, the self-hosted runner, the hosted copy on Postgres) start after T6.

Each ticket: why, done when, what it touches. Order within a group is the order to do them. A ticket is closed by a commit that
names it (`T12`) and updates the README status.

## Zero. Make parallel work possible

- **T0 Split `ledger/app.html`.** One file of 830 lines is why two agents cannot work on two pages at once. `ledger/app.html`
  becomes a shell (head, nav, router, shared helpers) plus `ledger/pages/<page>.js` (proof, trail, rules, reconcile, data,
  explore, release, docs), served by `app.py` from `/pages/<name>.js`; shared helpers in `ledger/pages/_shared.js`. No behaviour
  change; every page screenshot before equals after at 1600px. Done when each page is its own file and the router imports them.

## A. One definition of open

The root fault: Proof counts an item explained when a rule or a definition covers it; Reconcile counts it open until a person
decides. Both are "right", and they contradict each other on the same row (Amazon FY2024 Equipment: Proof 0 open, Reconcile
open). Until these agree, no page can say whether a release is signable.

- **T1 One `open` function.** `ledger/proof.py` and `ledger/workbench.py` call one function, `ledger/status.py:state(row)`, that
  returns checked / explained / open / blocked with the reason (rule id, definition name, resolution id). Proof, trail, Reconcile,
  Dataset and the Release page all read it. Done when the Proof board's open count equals Reconcile's open count for the same
  scope, and a test asserts it on the fixtures.
- **T2 Scope the UI to the proven set.** `config.SCOPE = PROVEN` until widened. Every list, page, chart, packet and published
  table reads `SCOPE`; the jump box only offers scoped companies; "The other 94" line goes. The database keeps every company. Done
  when `/api/v1/*` with no filter returns scoped rows only and `#data` shows six companies.
- **T3 The 7 unconfirmed decisions.** `decisions/resolutions.jsonl` has 7 rows "for Kenny Geiler to confirm" from the
  replication run. Surface them on Reconcile as their own group, first; Kenny confirms or overturns each; the Release page
  blocks while any remain. Done when zero remain and the Release page shows the check.
- **T4 Gates per company in scope.** `release.gates()` runs for every company in `SCOPE`, not the proven set alone, and reports
  per company. Done when `ledger release` prints a per-company table and refuses on any failing row.

## B. The Release page (the last page)

- **T5 Release page, `#release`.** The checklist, each line green or red with the count and a link to the rows: gates per
  company (T4); open items from T1 for the scope; unconfirmed decisions (T3); unmapped asset types (0 required in scope);
  rows with empty value by measure; diff from the previous release in rows added, removed, changed; golden status and the last
  test run (T30); the packet's files and hash. Done when every line links to the page that fixes it.
- **T6 Sign from the page.** A Sign button, enabled only when every line is green, that runs `signoff` and `publish` and writes
  who, when, hash and the checklist as it was at signing into `SIGNOFF.json`. Refused on the read-only copy. Done when v1.8.0
  is signed from the page and `SIGNOFF.json` carries the checklist.
- **T7 What a signature meant.** The Releases table on Proof shows, per release, open at signing, unmapped at signing, companies
  in scope. Older releases show "before the checklist". Done when v1.7.0's row says what it had open.
- **T8 Release diff in rows.** `DIFF.md` lists rows added, removed and changed per list, not values alone; the page shows the
  same. Done when a changed `check` on one row appears in the diff.

## C. Columns: one shape that a stranger can read

Audit of `taxonomy.csv` v1.7.0: 19 columns, 6,700 rows. `group` = `layer` on every row; `value_high` is a range high on planned
rows and a year-over-year change on derived rows; `tags` packs kind, status, location, capacity_mw, forward_looking and part_year
into one string; `source` is an extraction id on 6,674 rows with no accession, filing date or URL; `check` mixes three
vocabularies; 2,404 rows unmapped; 1,029 rows with no value. Schema version 11, golden re-frozen on purpose, v1.8.0.

**How C runs.** One agent, one branch `schema-v11`, one ordered series, nothing else on the branch:
1. `store.py`: `SCHEMA_VERSION = 11`, the migration, column descriptions.
2. `taxonomy.py`: the row shape (T9–T17), with `tests/test_taxonomy.py` updated in the same commit.
3. `api.py`, `publish.py` (`NUMERIC`, `DATE`, tables), `release.py` (packet README columns), `app.py` (`FIELD_KIND`, `/api/data`).
4. `ledger/pages/data.js`, `explore.js`, `trail.js`: the columns the pages read.
5. `ledger rules` on the six, then `ledger golden --freeze` in its own commit whose message says which columns changed and why,
   then `golden --check` equal.
6. `python -m ledger.store` regenerates `docs/DATA_DICTIONARY.md`; `docs/TAXONOMY.md` and `docs/API.md` say the new columns.
7. `ledger release v1.8.0 --stage 3`, unsigned, in its own commit; Kenny signs from the Release page (T6).
Each commit passes the full test suite; the branch merges to main as one merge commit named "Schema v11: one shape a stranger
can read (T9–T18)". A reviewer agent reads the whole diff against the ticket list before the merge.

- **T9 Drop `group`.** `layer` stays, documented as the reading aid it is. Touches taxonomy.py, api.py, publish.py, docs.
- **T10 `change_from_prior` column.** Derived rows put the year-over-year change there; `value_high` is a range high only.
- **T11 Unpack `tags`.** Columns `kind`, `status`, `location`, `capacity_mw`, `forward_looking`, `part_year`, `program`; `tags`
  goes. Empty where a measure has no such thing. *As built (schema v11):* a project's kind is its own column, `project_kind`, so
  `kind` means one thing (a statement's actual / outlook); `forward_looking` is empty where the source does not say (projects,
  gathered figures), never a hard-coded value; a gathered figure also carries `relation` (eq / ge / le).
- **T12 Follow the source.** Columns `accession`, `filed`, `source_url`, `source_kind` (10-K table, 10-K note, 8-K release,
  transcript, gathered) on every row; `source` keeps the internal ids. Done when a row's `source_url` opens the filing at the
  cited table for every spent and derived row. *As built:* `source_kind` also has `10-K MD&A` and `cfo commentary`, the two
  text kinds the list had no word for. The rendered 10-K on sec.gov has no stable table anchors, so `source_url` guarantees
  less than "at the cited table": it opens the filing with `?table=<id>` (the parsed table the cell was read from, which DATAHQ
  can show) and a `#:~:text=<row label>,<number>` fragment that scrolls the browser to the first place the filing shows those
  words, usually the row, sometimes prose. `filed` is the SEC filing date (10-K through `documents`, 8-K from the text's date);
  empty for a transcript, CFO commentary or a gathered figure.
- **T13 One `check` vocabulary.** `check` ∈ agree / explained / differs / no_reference / unmapped / verbatim, plus `check_method`
  (xbrl, rule:<id>, definition:<name>, resolution:<id>, quote, gathered). "verbatim (gathered)" goes. *As built:* `check_method`
  is an open vocabulary, `<kind>` or `<kind>:<id>`, the kinds in one place, `status.METHOD_KINDS` (xbrl, quote, gathered, located,
  none, mapping, rule, definition, resolution, label), the same words `status.state` gives `by`; `no_reference` and `not_reported`
  rows read `label:<label>`. A later answer key (esef:<tag>, source:<doc>, actual:<period>) is one entry there.
- **T14 `mapped` boolean and 0 unmapped in scope.** Every derived row in scope has a `standard_type`; the Release page refuses
  otherwise. Done when the six have 0 unmapped (today 0 for the six; keep it so).
- **T15 `has_value` and the valueless rows.** Projects without an amount keep their row with `value` empty and `has_value`
  false; the Dataset shows them under their own filter; counts on Proof say "N rows, M with a value".
- **T16 Periods.** `period_end` (date) on every reported row; `period_kind` ∈ reported / planned; `fiscal_year` stays the label.
- **T17 Units.** `unit` ∈ USD / share / MW; `scale` = 1 on every row (whole units), stated in the dictionary; `currency` = USD.
  *As built:* `unit` ∈ USD / share and empty when `has_value` is false; a project's capacity is in `capacity_mw`, megawatts by
  name, so no row's `value` is ever in MW.
- **T16, as built:** `period_kind` is reported only when the company's fiscal calendar (the 10-K that reports the year) knows the
  year's end and the source was written on or after it; planned when the end is later or unknown (NVDA FY2027 statements are
  planned, whatever the reader called them).
- **T18 Dictionary from the schema.** `docs/DATA_DICTIONARY.md` regenerated from `store.py` descriptions, every column of every
  release list described, the vocabularies of `check`, `measure`, `category`, `kind`, `status` enumerated with counts. The app
  reads it (T26).

## D. Pages

### Proof
- **T19 Readable stage cells.** `5·0·0` becomes three marks with hover text and a link to the rows counted; the legend line goes.
- **T20 Stage counts link.** Each count opens the Dataset rows filtered to that company, stage and state.

### Company trail
- **T21 The trail shows numbers.** The company's rows (T1 state inline), grouped by measure, each row with its check mark, the
  rule or definition that explained it, and the evidence (cell, screenshot, XBRL fact) one click away. The seven empty cards go.
  Done when number → cell → screenshot is two clicks from Proof.

### Rules
- **T22 What a rule fired on.** Click a rule: the rows it fired or closed, in scope. "Fired or closed" becomes two columns.
- **T23 Agents first.** The readers (model, prompt in use, prompt history, what each decides) move above the rule list; the
  prompt history opens inline.

### Reconcile
- **T24 Plain causes and a real gap.** Cause names in words ("the filing renamed the category", "our cell is the segment, the
  tag is the total"); the gap bar gets a zero and a scale or goes; "at stake" names what it sums. Each item says what accepting,
  fixing, explaining or blocking does to the dataset.

### Dataset
- **T25 Sticky header and ticker column; column descriptions on hover; per-column filter; a legend for `check`.** Rows view only.
- **T26 Docs in the app, `#docs/<name>`.** `docs/*.md` rendered in DATAHQ (marked.js from cdnjs, pinned), left nav from the file
  list, TAXONOMY and DATA_DICTIONARY first; Dataset column hovers read the dictionary. The nav gets Docs.
- **T27 Grid: totals and restatements.** A totals row per year; a renamed or split category shows the link between the old and
  new rows, not only a ≠.

### Explore
- **T28 Charts carry the check.** Unverified rows (differs, unmapped, no_reference) are hatched or excluded by a default toggle
  "verified only"; the legend says which.

### Global
- **T29 The page says what it shows.** Header: scope (six companies), data as of (last run), release (if a release is selected),
  read-only or not. `signed as` becomes the session once auth exists (production rails, after these).

## E. Tests and the bar

- **T30 Tests in the Release checklist.** `reports/tests.json` written by the test run (count, failures, golden ok, at), read by
  the Release page. Later the self-hosted runner writes it.
- **T31 Golden covers the taxonomy rows.** `fixtures/expected/taxonomy.csv` frozen for the six; `golden --check` compares it.
- **T32 A test per ticket in C.** Each column change has a test on the fixtures that asserts the column's vocabulary and that no
  row carries two meanings in one column.

## F. Scale: the tools that make a hundred companies resolvable

The six cost a person-day each at the mapping and reconcile stages. A hundred cannot. These tickets cut the per-company cost
before scale is attempted; T35 measures it.

- **T33 Mapping assistant.** For a company's unmapped asset types, an agent proposes the us-gaap member with the note's words as
  evidence and a confidence; the person approves, edits or rejects each in Reconcile (a new group, "asset types"); approved
  mappings land in `taxonomy/asset_types.yaml` with `by` and the evidence. The agent runs headless (`LEDGER_CLAUDE`), prompt
  versioned under `agents/prompts/`. Done when company seven's asset types are mapped in under fifteen minutes of a person's time.
- **T34 Second reviewer.** A resolution has `by` and `confirmed_by`; a release's checklist counts items confirmed by a second
  person; `SCOPE` companies need one confirmer per company. The read-only copy stays read-only. Done when the Release page
  shows "confirmed by" per company.
- **T35 Company seven, measured.** Micron added to `SCOPE` through every stage with a stopwatch on each: agent minutes, person
  minutes, open items at each stage, rules fired, mapping proposals accepted. Written to `reports/company-cost.md`. The number
  decides whether a hundred is a week or a quarter. Done when the report exists and `PROVEN` has seven.
- **T36 Resolve-by-rule.** When a person explains a difference, Reconcile offers "make this a definition" or "make this a
  rule" with the text prefilled from the reason; the definition file or rule yaml is written, versioned, and the next run closes
  the same cause everywhere. Done when one explanation on company seven closes the same cause on an eighth without a person.
- **T37 Bulk by cause with preview.** Select-all-by-cause shows what each decision does to the dataset (rows that change
  `check`, rows that leave the packet) before it is applied. Done when the preview counts equal the counts after.
- **T38 Cost and time per stage on Proof.** Agent calls, tokens, wall time and person minutes per company per stage, from
  `ledger/cost.py`, on the company trail. Done when the trail shows them for the six.

## G. How the work runs: the swarm

Agents build this, a person signs. The rules every agent follows, in the brief and checked by the reviewer:

- **Roles.** *Investigator* (read-only: locates code, reports file:line, never fixes). *Builder* (one ticket or one ordered
  series, one branch, tests in the same commit). *Reviewer* (reads the diff against the ticket's "done when" and these rules;
  one line per finding; nothing merges with an open finding). *Designer* (D tickets only; loads `emil-design-eng`,
  `web-design-guidelines` and `dataviz` before touching a page; screenshots at 1600px before and after).
- **Files decide parallelism.** Two builders never hold the same file. Until T0 lands, one builder on `app.html` at a time.
  After T0, one builder per page file. A, C and B are sequential series, each one builder. D runs in parallel per page. E runs
  alongside anything.
- **The bar, unchanged.** `ledger golden --check` before any commit that touches a parser, a rule, a loader, the taxonomy or the
  schema; `--freeze` only on purpose, in its own commit saying why; `LEDGER_SKIP_GOLDEN=1` for the fast suite in between. The
  README status block in every commit. `docs/HANDOFF.md` stays the start page. Nothing inferred: no column holds a number the
  pipeline made up, no page shows a number without its check.
- **Skills are mandatory, not optional.** A builder on a page loads the three design skills; a builder on a schema change
  reads `docs/TAXONOMY.md` and `docs/PROOF.md` first; a builder on agents reads `agents/prompts/` and versions, never edits in
  place. The reviewer refuses a diff whose brief did not name the skills it used.
- **Headless only.** Agents that read filings run through `LEDGER_CLAUDE="$CLAUDE_CODE_EXECPATH"`; no API key, no paid calls.
- **One signer, one place.** Only the Release page signs; agents never run `signoff` or `publish`.
- **Phases.** 1: T0 (worktree) and A (main checkout) in parallel, merge, screenshots equal. 2: C on `schema-v11`, one builder,
  one reviewer, merge. 3: B. 4: D per page in parallel, E alongside. 5: F, starting with T35, which decides the scale plan.
  Production rails after phase 3.

## Order

T0 and A first, then C (the schema, one series), then B (the page that signs), then D per page in parallel with E
alongside, then F. Production rails (auth, decisions in Postgres, the self-hosted runner, the hosted copy reading Postgres)
come after T6 signs v1.8.0.
