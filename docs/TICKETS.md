# Tickets: the sign-with-confidence flow

*Written 1 Nov 2026 from a page-by-page review of DATAHQ at 1600px and a column audit of the v1.7.0 packet. The goal: a person
signs a release from the app, and the app has shown them everything that could make the signature wrong. Scope until that
works: the proven set only (`config.PROVEN`); the other companies stay in the database and leave the UI, the packet and the
published tables. Scale after.*

Each ticket: why, done when, what it touches. Order within a group is the order to do them. A ticket is closed by a commit that
names it (`T12`) and updates the README status.

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

- **T9 Drop `group`.** `layer` stays, documented as the reading aid it is. Touches taxonomy.py, api.py, publish.py, docs.
- **T10 `change_from_prior` column.** Derived rows put the year-over-year change there; `value_high` is a range high only.
- **T11 Unpack `tags`.** Columns `kind`, `status`, `location`, `capacity_mw`, `forward_looking`, `part_year`, `program`; `tags`
  goes. Empty where a measure has no such thing.
- **T12 Follow the source.** Columns `accession`, `filed`, `source_url`, `source_kind` (10-K table, 10-K note, 8-K release,
  transcript, gathered) on every row; `source` keeps the internal ids. Done when a row's `source_url` opens the filing at the
  cited table for every spent and derived row.
- **T13 One `check` vocabulary.** `check` ∈ agree / explained / differs / no_reference / unmapped / verbatim, plus `check_method`
  (xbrl, rule:<id>, definition:<name>, resolution:<id>, quote, gathered). "verbatim (gathered)" goes.
- **T14 `mapped` boolean and 0 unmapped in scope.** Every derived row in scope has a `standard_type`; the Release page refuses
  otherwise. Done when the six have 0 unmapped (today 0 for the six; keep it so).
- **T15 `has_value` and the valueless rows.** Projects without an amount keep their row with `value` empty and `has_value`
  false; the Dataset shows them under their own filter; counts on Proof say "N rows, M with a value".
- **T16 Periods.** `period_end` (date) on every reported row; `period_kind` ∈ reported / planned; `fiscal_year` stays the label.
- **T17 Units.** `unit` ∈ USD / share / MW; `scale` = 1 on every row (whole units), stated in the dictionary; `currency` = USD.
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

## Order

A first (T1–T4), then C (the schema), then B (the page that signs), then D in the order listed, E alongside. Production rails
(auth, decisions in Postgres, the self-hosted runner, the hosted copy reading Postgres) come after T6 signs v1.8.0.
