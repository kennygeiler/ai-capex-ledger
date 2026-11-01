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

**Order against the calendar** (Kenny, 2 Nov: "build ASML to the full bar as company 8, add a score per agent, I want to
get to 100 companies"; the Arctal call is 11/12 Nov). Before the call, three tracks in parallel after C and B:
1. C merged and golden re-frozen → B (T5–T6, sign v1.8.0 from the app). Everything else branches from here.
2. Scale track: T33 mapping assistant → T36 resolve-by-rule → T37 bulk with preview, each measured by T35/T38, then T52 in
   batches (7, 10, 25, 50, 100), golden green per batch, each batch run planned around the session limit (resets 1:30am ET).
3. Source track: T40 vocabulary → T44 spike as the first step of T45 → T45 ASML in PROVEN as company eight.
4. Agents track: T48 charters and section → T49 score per agent.
Then T41, T42, T43 if time. After the call: T45 (Kenny, 1 Nov: the spike plus a measured error rate before the call, the full source after), T46, T47 as picked. Group J (measured rigor, the judgement ledger) and the day-by-day rollout are at the end of the file. T51 (the name) whenever Kenny names it, last.
The honest estimate against this order is at the end of F.

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

*As built (B, 2 Nov):* `ledger/checklist.py` holds the checklist and the sign; `ledger/pages/release.js` renders it and recomputes
nothing; `ledger release` builds its packet through the same `checklist.packet`, so the page's hash is the command's. The signer is
the name in the header's signer box, recorded as given: who may press the button is a later ticket (auth, production rails). The
test-run line reads `reports/tests.json` `{ok, count, failures, at}` (T30 writes it); absent, it reads "not run" and does not block,
so v1.8.0 can be signed before T30 lands; present and failing, it blocks. The rows diff keys `taxonomy.csv` on ticker + fiscal_year +
measure + category + reported_name, which repeats (259 rows in v1.7.0: several statements under one category and name), so rows under
one key are paired best-match-first on the columns both releases carry and only a real move counts as changed; a column only one
release has is listed as added or removed, not as every row changed. `SIGNOFF.json` stores the checklist with the diff's counts, not
its examples (`DIFF.md` has those). *Review fixes (2 Nov):* every POST needs `Content-Type: application/json` and, with an `Origin`,
the server's own (403 otherwise, before any route); the next version is the lowest unsigned folder after the last signed one;
`releases/v1.8.0` was rebuilt through `checklist.packet` (the one main built predated the rows section); the sign checks the
checklist again after the write, records the publish's outcome in `SIGNOFF.json`, runs under a lock, and a signature is never
replaced; `ledger release` refuses on the page's checklist; `write` renames a whole folder into place. *Third review:* a broken
folder before the version (no manifest, a manifest that is not an object with a str hash, no `values.csv`, not UTF-8) is a red
required line, never a 500, and the diff runs against the last readable folder; folder names that are not versions are ignored;
a failed `record` after a successful publish is `record_error` in the reply, never a `published: false`; every POST body must be a
JSON object with a numeric Content-Length (400 otherwise).

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
- **T12 Follow the source.** Columns `accession`, `filed`, `source_url`, `source_table`, `source_kind` (10-K table, 10-K note,
  10-K MD&A, 8-K release, transcript, cfo commentary, gathered) on every row; `source` keeps the internal ids. Done when
  `source_url` opens the filing at the first place it shows the cited row label and number; `source_table` names the parsed
  table DATAHQ shows; every spent and derived 10-K row has both. *Note:* the original wording ("opens the filing at the cited
  table") asked for a table anchor sec.gov does not provide: the rendered 10-K has no stable table ids, and a query string is
  ignored, so the link is the filing plus a `#:~:text=<row label>,<number>` fragment (usually the row, sometimes prose) and the
  parser's table id lives in its own column. `filed` is the SEC filing date (10-K through `documents`, 8-K from the text's
  date); empty for a transcript, CFO commentary or a gathered figure.
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

  *As built (1 Nov):* `ledger test [--fast]` (`ledger/cli/test.py`, `ledger/testreport.py`) runs the unittest suite in process and
  writes `reports/tests.json`: `{ok, count, failures: ["test id: first line of the error"], skipped, golden: true|false|null,
  at, git: short sha|null, dirty, seconds}`; `--fast` sets `LEDGER_SKIP_GOLDEN=1` (golden null); exit 0 only when ok. The file
  is tracked, like `reports/golden.json`, so the hosted copy shows the last run. `checklist.tests_line` reads it: absent, "not
  run", grey, does not block (as before); ran and failed, red and required whatever commit it ran on; passed on this HEAD with a
  clean tree, green and required, the note naming count, golden and sha; passed on another commit or a dirty tree, "stale",
  informs, "run `ledger test`" (it neither blocks nor vouches: the code tested is not the code signed). Commits since the run
  that changed only `reports/tests.json` are forgiven, so the commit that records the run keeps the line green; an untracked
  file under `ledger/ tests/ taxonomy/ fixtures/` counts as dirty. Without git on either side (the hosted copy ships no
  `.git`) the commit cannot be compared: informs, "commit not compared: no git", never a verified pass. The runner (T-later)
  runs the same command.
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
  *As built (branch `t33-mapping-assistant`):* charter `agents/charters/mapper.md`, prompt `mapper@v1`, schema `agents/schemas/mapper@v1.json`,
  runner `ledger/mapper.py` + `ledger mapper <TICKER> [--dry-run]` (headless `claude -p`, step `mapper` in `runs`), proposals appended
  to `decisions/mapping_proposals.jsonl` (`proposed`, `rejected`, `approved` lines); Reconcile group "asset types" (cause
  `asset_types`, any `?scope=<ticker>` the database holds) with Approve / Edit / Reject; `POST /api/mapping` is the one writer of
  `taxonomy/asset_types.yaml` (member must be on the header's list, one entry per ticker + name, `by` the signer box, `at` today);
  `POST /api/mapping/reject` logs the member so the next run proposes another. Measured on MU: 5 unmapped categories, 5 proposals
  in one call (7.3 s, 7,724 in / 717 out tokens, 1 attempt), 4 high and 1 medium (Equipment, the note's footnote is not in the
  parsed table); a person's part is five Approve clicks. MU stays out of `SCOPE` and its yaml entries unwritten until T35.
- **T34 Second reviewer.** A resolution has `by` and `confirmed_by`; a release's checklist counts items confirmed by a second
  person; `SCOPE` companies need one confirmer per company. The read-only copy stays read-only. Done when the Release page
  shows "confirmed by" per company.
- **T35 Company seven, measured.** Micron added to `SCOPE` through every stage with a stopwatch on each: agent minutes, person
  minutes, open items at each stage, rules fired, mapping proposals accepted. Written to `reports/company-cost.md`. The number
  decides whether a hundred is a week or a quarter. Done when the report exists and `PROVEN` has seven.
- **T36 Resolve-by-rule.** *Done 2 Nov 2026 (`ledger/judgement.py`, `POST /api/judgement`, the `explains` check, `tests/test_judgement.py` on a synthetic database: company seven/eight not yet in scope).* When a person explains a difference, Reconcile offers "make this a definition" or "make this a
  rule" with the text prefilled from the reason; the definition file or rule yaml is written, versioned, and the next run closes
  the same cause everywhere. Done when one explanation on company seven closes the same cause on an eighth without a person.
- **T37 Bulk by cause with preview.** Select-all-by-cause shows what each decision does to the dataset (rows that change
  `check`, rows that leave the packet) before it is applied. Done when the preview counts equal the counts after.
- **T38 Cost and time per stage on Proof.** Agent calls, tokens, wall time and person minutes per company per stage, from
  `ledger/cost.py`, on the company trail. Done when the trail shows them for the six.

- **T52 A hundred companies in scope, each with its honest state.** `SCOPE` widens in batches (7, 10, 25, 50, 100), each batch
  through every stage (the 94 are already ingested, extracted, read and stated; what each lacks is mapping, reconcile and
  gates), golden expanded to freeze and check every company in scope, the Proof board showing each company proven or "N open"
  with the causes, the packet carrying every company in scope with `proven` true only where it is. The proven count is pushed as
  high as T33, T36 and T37 allow; nothing is labelled proven that is not. Each batch gets T35's stopwatch, and the curve across
  batches is the report. Batch runs are planned around the session limit. Done when `SCOPE` has 100, golden is green on all
  100, the Proof board is honest for each, and `reports/company-cost.md` shows the curve.

**Estimate against the calendar (2 Nov, nine days to the call).** Fits: C and B (two days), T33 + T36 + T37 (three days,
parallel with the source and agents tracks), T48 (one day), T49 (one to two days if `faults` and `status` give the numbers;
they do), T52 to 100 in scope with honest states (the data is there; mapping and reconcile are the cost: with T33 at fifteen
person-minutes per company that is a day of Kenny's time across the batches, plus agent runs around the session limit).
Critical path: C → B → T33 → batches. Breaks: (1) T45 ASML to the full bar: a non-EDGAR PDF, an ESEF package reader, a new
reader agent with a charter, schema v12, ties, golden; five to seven days of one builder with nothing else; it fits only if it
starts the day B merges and nothing in the PDF or the ESEF package fights back; the T44 spike on day one tells us by day two.
(2) The proven count at 100: honest expectation is 25 to 40 proven by the call, the rest open with named causes; a hundred
proven is not a nine-day number. (3) Kenny's minutes: T52 and the 7 confirmations are his, not an agent's. (4) The session
limit: batch runs of 25+ companies take more than one window.

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
- **Charter before code (T50).** A new source or agent starts with its charter file under `agents/charters/`; the reviewer
  refuses a reader diff without one.
- **Headless only.** Agents that read filings run through `LEDGER_CLAUDE="$CLAUDE_CODE_EXECPATH"`; no API key, no paid calls.
- **One signer, one place.** Only the Release page signs; agents never run `signoff` or `publish`.
- **Phases.** 1: T0 (worktree) and A (main checkout) in parallel, merge, screenshots equal. 2: C on `schema-v11`, one builder,
  one reviewer, merge. 3: B. 4: D per page in parallel, E alongside. 5: F, starting with T35, which decides the scale plan.
  Production rails after phase 3.

## H. Answer keys and sources

XBRL is one kind of answer key. There are four: a structured twin, a second source, an arithmetic tie, a later truth. Each
extends `by` in `status.py` and `check_method` (T13); none is a redesign. A new source reaches the bar only when it is frozen
in golden. Arctal's own products (Green & Transition CapEx, Labelled Bonds) are the targets of T44–T46.

- **T40 Answer-key vocabulary.** `status.state` and `check_method` gain `esef:<tag>`, `source:<doc>`, `rule:<tie_id>`,
  `actual:<period>` next to xbrl / quote / located / mapping / rule / definition / label / resolution; `docs/PROOF.md` lists the
  four kinds and what each proves. Done when tests assert each kind on a fixture row and Proof and Reconcile count it the same.
  *As built (T56, 1 Nov, night):* the four keys are graded by independence, `status.KEY_GRADE`; see T56 in group J.
- **T41 Quarters tie.** From the cached companyfacts 10-Q facts, rule `quarters_tie`: Q1 + Q2 + Q3 + derived Q4 = FY within
  tolerance for revenue, capex and opex on the six; a negative derived Q4 or a missing quarter is an open item, not a pass. Done
  when the six carry `rule:quarters_tie` and golden is re-frozen in its own commit saying why.
- **T42 8-K second source.** Revenue and capex read from each fiscal year's earnings release (Ex 99.1, already in `texts` as
  earnings_release), compared with the 10-K value by rule `second_source`; a disagreement opens an item citing both documents.
  Done when the six carry `source:<accession>` where a release states the figure, and golden is green.
- **T43 Later truth.** Rule `actual_vs_planned`: every planned row (guidance, verbatim) whose period has passed is compared with
  the spent row for that period and the gap recorded; the planned row never changes. Done when every past-period planned row on
  the six carries `actual:<period>` and its gap.
- **T44 ESEF spike (before the call; spike, not proven).** ASML: annual report PDF plus the ESEF package from filings.xbrl.org
  (free API). Read the EU Taxonomy capex KPI table (total / eligible / aligned) and cash-flow capex. Ties: aligned ≤ eligible ≤
  total; KPI total = cash-flow capex; the ESEF tag as twin where tagged. Outside `SCOPE`, outside the packet. Done when
  `reports/spikes/asml-esef.md` shows every number with its PDF page, each tie's result, and what the full source would need.
  *As built (1 Nov):* `reports/spikes/asml-esef.md` on ASML's FY2025 ESEF filing (filings.xbrl.org, published 2026-02-25, package
  sha256 recorded); reader `ledger/spikes/esef.py` (stdlib, not wired in; a spike reader is exempt from T50's charter-before-code,
  no precedent for a reader that lands in the pipeline) with `tests/test_esef_spike.py`. Ties: aligned ≤ eligible
  ≤ total passes (6.7 ≤ 2,445.8 ≤ 2,811.3, p.199); KPI total ≠ cash-flow PP&E purchases 1,573.6 (p.275) as expected, and the
  reconciliation to the notes closes two of three parts (PP&E additions 1,596.2 p.290, intangibles 1,137.8 p.288) with 77.3 of
  right-of-use additions implied, not disclosed; the ESEF twin equals every tagged statement number read; the KPI table itself is
  untagged. The PDF was not obtained (asml.com bot check, stopped); pages are the ESEF report's own printed numbers, expected to
  equal the PDF's, unverified; the PDF-page part of the done-when stays open until a person supplies the PDF link
  (`sources/ir.yaml`). T45 needs a
  page-table reader on the xhtml, an `esef` document kind with `fxo_id` in place of accession, EUR in `unit`/`currency`, v12 KPI
  columns and four tie rules with a rounding tolerance; estimate 6.5 builder-days.
- **T45 ESEF source (after the call).** New document kind (non-EDGAR PDF plus ESEF), schema v12 columns for the KPI (aligned /
  eligible / total under the Delegated Act annex), a PDF-table reader agent with a versioned prompt and a charter (T50), tie
  rules, golden frozen. Done when ASML is in `PROVEN` as company eight and golden is green.
- **T46 Labelled-bond allocation reports (later).** The instrument as an entity, allocated-by-use as a measure, ties: allocated ≤
  issued (issued from the prospectus or 8-K) and allocation against capex. Candidates: Alphabet, Amazon, Equinix, Digital Realty.
  Done when one issuer's report is at the bar.
- **T47 Format backlog.** 20-F (TSMC, ASML; TSMC's monthly revenue on MOPS sums to the quarter), investor-day slides (vision,
  against the release figure), call audio (local Whisper against the official transcript), state data-center incentive filings
  (planned, against the announcement), sustainability MWh and PUE (against CDP). Each becomes its own ticket when picked; none
  starts before T45.

## I. Agents: one owner per method, shown

Arctal hires a "super-IC managing a fleet of AI agents". The proof is legible: every agent has a charter, a prompt history with
who changed it, a run ledger, and, after the call, a score.

- **T48 Charters and the Agents section (absorbs T23).** `agents/charters/<id>.md` for each live reader (extract, notes,
  statements, aispend, projects): what it owns, what it never touches, its input task file and output file, model, tools, prompt
  versions, and the checks that judge it. The attribution agents are marked retired in `agents.json`, not deleted. The Agents
  section moves to the top of Rules and shows per agent: the charter, the prompt history with `by`, and the runs table per
  company (calls, input and output tokens, seconds, attempts, failures). Done when every live reader shows all three for the six,
  screenshotted at 1600px.
- **T49 Per-agent score (after the call).** For each reader: the share of its outputs checked, explained and open (status.py),
  agreement with the twin where one exists, and the planted-fault catch rate of the checks behind it (`faults`), each with its
  denominator. Done when the Agents section shows a score per live reader. *As built (1 Nov 2026):* `ledger/score.py` `score(con, agent_id, tickers)`,
  carried as `score` in `cost.by_agent` and so in `/api/agents/<id>/runs` and `/api/agents`: counts and denominators only (outputs,
  checked, explained, open, blocked; `twin: {agree, of}` or null; `faults: {caught, planted, no_effect, escaped}` or null with the
  reason in `note`). The states come from `proof.company` (so from `status.state`): the reader's outputs are the Values stage's value
  rows, the AI spend reader's the Statements stage, the notes reader's the Facts stage, the projects reader's the Planned stage's
  project rows. A twin exists only for values and facts XBRL tags; a fault test exists only for the extract step (ledger/faults.py),
  read from the report of the latest `faults` run in the `runs` table that covered each company; the other readers show "not
  measured" with the reason, never a number. The Rules page shows the block under each live reader (ledger/pages/rules.js
  `scoreBlock`); each charter's Score paragraph says what the three numbers mean. Tests: tests/test_score.py. Known difference: the
  Proof board's "Fault test" line (ledger/hq.py `snapshot`) counts caught = planted − escaped, so a fault that reached no released
  value counts as caught there (1,283 of 1,283), while the score counts only a rule or the XBRL comparison firing (1,275 of 1,283,
  8 no_effect, 0 escaped); reconciling hq.py to the score's definition is a follow-up, not done here. The faults report is a file
  keyed by its name, rewritten by `ledger faults` without a runs row, so `faults_note` carries the file's written time next to the
  run's date and says when the file is newer.
- **T50 Charter before code.** The rule under G: a new source or agent starts with its charter file; the reviewer refuses a reader
  diff without one.
- **T51 The name (Kenny decides).** After T48. Council advice given to Kenny: for this audience a name for the method beats a
  personal name; his call. Change the page title, nav, README, HANDOFF and the hosted service label; redeploy the read-only copy.
  Done when the name appears everywhere and the hosted copy shows it.

## J. Measured rigor and the judgement ledger (council round 2, 1 Nov; Kenny: yes)

*Where this comes from.* Arctal's infra engineer role is filled; the data scientist runs the pipeline on new data and owns the
judgement ("last line of defense", "validation logic that encodes your judgement"). Definitions belong to a domain expert; the
data scientist builds the system that surfaces each question, routes it to the right stakeholder, records the answer and keeps
it alive as new filings arrive. What the demo must show: (1) how wrong the data is, measured with denominators, and (2) the
economics of human judgement (expert minutes per thousand data points). The weak spots today: 10-K data that is already XBRL
("you checked easy data"), the retired 993/1,218 headline with no per-agent denominator, and a UI that pitches the filled role.
The demo leads with measurement, not pages. Kenny accepted the trade (1 Nov): T45 ASML to the full bar moves after the call;
the T44 spike plus a measured unkeyed error rate on it (T53) is the ASML deliverable before the call. Group D (pages) stays in
the file and off the calendar.

- **T53 Measured error rate, keyed and unkeyed.** Keyed: per reader and per field, agreement with the twin as a share with a
  Wilson 95% interval and its denominator, computed on the page from the counts T49 already serves (`score.twin`); rules.js.
  Unkeyed: a stratified random sample of cells from a source with no key, the ASML FY2025 ESEF report first (the KPI table, the
  note roll-forwards, long tables oversampled), written to `reports/samples/asml-esef.json` with the page and the cell text; a
  Reconcile group "audit" where a person records a verdict per cell (right / wrong / cannot say, with a note) to
  `decisions/audit.jsonl`; the error rate with n and the interval on the Agents section, labelled "unkeyed, Kenny's verdicts".
  Owner of the verdicts: Kenny (~100–150 cells, about an hour). Touches rules.js, workbench.py, reconcile.js (after T37),
  ledger/spikes/esef.py for the sample. Done when the Agents section shows ASML's unkeyed error rate with n and the interval.
  *As built (keyed), 1 Nov:* `ledger/stats.py` (`wilson(k, n, z=1.96)`, `share(k, n)`, standard library, None when n is 0);
  `score.twin` carries `interval: [low, high]` (fractions, 4 dp) from its own `agree` / `of`, one interval on the sum over the
  companies; rules.js writes it in text under each reader ("agrees with the twin 70 of 71 (98.6%, 95% interval 92.4–99.8%)"),
  computed on the page from the counts (the API's 4-dp `interval` is informational; one display path). On the six: reader 70 of 71, 92.4–99.8%; notes reader 180 of 185,
  93.8–98.8%; the quote readers have no twin and no interval. Charters say what the interval does not cover (a twin exists
  only where the filing tags the number). Not built: per field. The trail's items carry `what`, not `field`, and `proof.py`
  belongs to another builder; when `proof.company` puts `field` on each item, `score.twin` can group the same counts by it
  (`twin_by_field: {field: {agree, of, interval}}`). The unkeyed half (the ASML sample and the audit group) is still open.
- **T54 Failure types as data.** `docs/INGESTION.md`'s 72 types (prose table rows today, no class, no catching check named)
  become `taxonomy/failures.yaml`: id, cause class (units / period / scope / locator / agent misread / document error), count
  seen, the check that catches it or `none`, agent-or-document. A Pareto chart on Proof reads the file (proof.js; Plotly as
  Explore uses it, `dataviz` skill loaded). Done when the chart reads from the file and every type has a class and a catching
  check or `none` (a `none` is itself a finding, counted on the chart). *As built (first half):* `taxonomy/failures.yaml`, all 72
  types keyed by INGESTION's number, each with class, origin (agent / document / code / reference), the catching check or `none`
  with a note saying what caught it instead, count of companies named, first-seen date and the INGESTION line it comes from;
  `ledger/failures.py` `load` refuses a class, origin or check not in the vocabulary or not in code (rule ids, `proof.GUARDS`,
  `faults.FAULTS`), `pareto` and `by_check` for the chart; `tests/test_failures.py`. A seventh class, `pipeline`, holds the
  defects in the pipeline's own bookkeeping or contracts (types 58, 59, 60, 61, 66). The numbers (from `pareto()`): by class
  scope 27, period 11, locator 10, agent misread 7, document error 6, units 6, pipeline 5; by origin document 31, code 22,
  agent 10, reference 9; 45 of 72 have check `none` (contracts, the evidence re-read, counts and eyes caught them, no rule
  did); the checks that catch most are `period_length` 4, `xbrl_reconcile` 4, `citation_resolves` 3, `coverage` 3,
  `no_10k_yet` 3. Where the check is an id the INGESTION row does not name (6, 16, 42, 68), the `check_note` says so. The
  chart (proof.js) is the second half, after T56. *As built (second half):* `GET /api/v1/failures` returns `pareto()`
  (`total`, `by_class`, `by_origin`, `by_check` largest first, `none`) plus `types` (id, name, class, origin, check, count; a
  null count stays null). Proof's "Failure types" section, under "Rows by answer key": two horizontal bar charts in one hue
  (Plotly as Explore loads it), types per cause class (7 bars) and "what catches them", types per check (15 bars, `none` its own
  bar, labelled "no check: a known way to be wrong that nothing guards"), every bar labelled `n of 72`; a bar is a NUMBER OF
  TYPES, never instances, and the title says so. Under each chart the same numbers as a table (class or check, types of 72,
  share), and a collapsed list of the 72 types (id, name, class, origin, check, companies seen or "not counted"), so it
  reads without colour or without the chart library. `tests/test_failures.py` fetches the route through the real Handler.
- **T55 Point-in-time.** `?as_of=D` on `/api/v1/values` and `/api/v1/taxonomy`: the figure the newest filing filed on or
  before D gave, from `extractions` (every filing's cells are kept) and `documents.filed`; `first_reported` / `basis` /
  `original_value` stay as they are. A PIT export in the packet (`values-asof.csv` per fiscal year end, or the API alone if the
  packet shape should not change before v1.9.0: decide in the ticket's first commit and say why). A test on the six that an
  as-of query never returns a figure filed after D (no lookahead). Why: Arctal's buyers backtest; a restated figure in history is
  lookahead bias. Touches api.py, release.py. Done when the API and the test exist on the six. *As built (1 Nov 2026, branch
  `t55-point-in-time`):* `ledger/pit.py` `as_of(con, D, tickers)` from `extractions` (ticker, field, period_start, period_end, value, scale,
  accession, extraction_id) joined to `documents` on accession for `filed`, the fiscal calendar from `values` (ticker, period, period_end);
  the values builder's own arithmetic (12-month columns, cost lines summed without a total, opex from three cells, newest by `filed`, the more
  complete one on a tie). Rows carry accession, filed, extraction_ids and `restated_later`; absent when no filing by D reports the year;
  overrides not applied. Covered: the three `values` fields for every year `values` knows, on any company in the database. Taxonomy as-of:
  `spent`/`capex` rows re-pointed through the same function (`check` = `not_checked` when the filing differs from the one checked); every
  other row kept only when its own `filed` <= D (facts holds the newest filing's note figures only, so a later note figure is dropped, not
  replaced); rows with no filing date dropped. Not covered: facts' earlier vintages, the 8-K / transcript rows' own history, overrides.
  Packet: no as-of file before v1.9.0 (the packet holds the signed dataset once; a derived file would need its own diff and dictionary);
  the packet README gained a "Point in time" paragraph naming the endpoint, so v1.9.0's hash differs from a packet built before this
  commit, by that text only. `tests/test_pit.py`: no lookahead at every filing date of the six, today equals `values`, the APLD flip
  (144,193,000 → 228,569,000 on 2026-07-29), 400 on a bad date through the Handler, a synthetic pair. Review fixes (same night): `as_of`
  with `release=` is 400; every field of a year comes from the one newest filing by the day, as `values_for` does. *Vintage check (from the
  vendor-methodology audit):* only the newest vintage is reconciled against XBRL. AT&T revenue FY2022: `values` 120,741,000,000,
  `first_reported` 120,741,000, `basis` restated; the first 10-K's cell `120,741` was read against a `(000s)` unit line (scale 1,000) where the
  later 10-Ks say `(000,000)`: a 1000× misread, not a restatement, and `as_of=2023-06-30` would serve $120.7m as truth. Tonight: every PIT row
  carries `vintage_check` (the `values` label for the accession it checked; `unchecked` for every older vintage), `api.AS_OF_NOTE` is the
  response note (added by the Handler at the merge), and the no-lookahead test asserts every row
  carries it and no row reads checked unless it is the newest filing's figure. No per-vintage reconciliation was invented tonight.
- **T55b Per-vintage reconciliation.** Each older extraction checked against the XBRL facts of its own accession (companyfacts holds every
  filing's tags under `accn`): `restated` only when both vintages agree with their own filing's tags; a vintage that disagrees with its own tags
  is `misread`, an open item on Reconcile with the cell and the tag, and `basis` / `first_reported` on `values` follow (a misread first vintage
  is not a restatement; the AT&T FY2022 revenue row above is the canonical case, and 45 `values` rows read `restated` today without this check).
  PIT rows then carry the per-vintage outcome in `vintage_check` instead of `unchecked`. Touches reconcile.py (the reference per accession),
  reference/, pit.py, the restated rule, status.py's keys (T56). Golden run required. Done when AT&T FY2022 reads `misread` on its first vintage
  and no `values` row says restated on an unchecked older vintage.
- **T56 Answer-key independence (folds into T40).** The four keys in `status.ANSWER_KEYS` get a grade: independent twin
  (XBRL / ESEF instance) > same-issuer second source (8-K: the same finance team can share the error) > arithmetic tie > later
  truth. `status` names the strongest key per row; Proof counts rows by key strength for the scope. Touches status.py, proof.py,
  proof.js. Done when Proof shows the count per key grade and a row's strongest key is on its trail.
  *As built (1 Nov, night, branch `t56-key-grades`):* `status.KEY_GRADE = ("twin", "second_source", "tie", "later_truth")`
  with `KEY_WHY` (one line each on why it ranks there), `KEY_LABEL`, `grade(key)` and `strongest(keys)`; `status.state()` (and
  `of_value`, `of_fact`, `of_exception`) returns `keys` and `key` beside state / reason / by: a checked row's answer keys and the
  strongest; a row carries one `by` today so `keys` holds at most one, and the shape takes several when T41–T43 write them. A
  failed tie carries none. `proof._item` carries `key` and `keys`; `proof.keys_of(items)` counts rows once by strongest key
  with `none` and `rows` (the denominator); each stage, each company and the board carry `keys`, the board also `key_grade`.
  proof.js: "Rows by answer key" table (dtable, kit only, no colours) under the board, per company and All, the why in a line
  beneath; trail.js: a collapsed "N checked (N twin)" list per stage with the key word beside `by`, and the stage header names
  the keyed count. Skills loaded before the page work: emil-design-eng, web-design-guidelines, dataviz. Tests in
  `tests/test_status.py` (grade order, strongest, key per `by` kind, board grades sum to the denominator on the fixtures) and
  `tests/test_proof.py` (`keys_of`). On the six: twin 260 of 875 rows, no key 615. Golden not run: taxonomy.py reads nothing
  from status.py. Review (MERGE, one WARN) fixed in a follow-up commit: "no key" explained in text under the table; the
  key words read from `key_grade`, which `proof.KEY_GRADE` ships on the board and on a trail.
- **T57 Judgement ledger.** A question is grouped by cause, not by cell (workbench groups by cause already). *T57a:* a
  resolution carries `owner_role` (data / expert / client) and `scope` (this company / this class / all companies); coverage =
  the cells and companies the cause governs, shown on the group; Reconcile groups by owner role; Kenny plays each role,
  labelled honestly ("Kenny as the expert"). Touches resolutions.py, workbench.py, reconcile.js (after T37). *T57b:* evidence[]
  on a resolution, each item supports / contradicts with its source; new supporting evidence attaches quietly; contradicting
  evidence re-opens the question and routes it to its owner role; out-of-scope evidence asks "extend?". Builds on the input-hash
  expiry, T34, T36, T37. T57b needs a second source that does not exist yet: T42 (8-K Ex 99.1) first; ships only if T42 lands by
  day 6. Done (a) when Reconcile groups by owner role with coverage per group; (b) when one decision on the six re-opens from
  an 8-K figure with the evidence attached and the ranking of decisions by coverage is visible.
- **T58 Series consistency (after the call unless a day frees).** A rule for scope drift across years: each year right on its
  own, wrong as a series (the AMD class found in the replication run; the attribution layer that found it was removed in
  2ee2e6f, so first check whether the fixtures still hold the case; if not, the ticket records that and builds the fixture
  first). Done when the rule catches the archived AMD case from fixtures.
- **T59 Week-one memo (no code).** `reports/arctal-week-one.md`: how Kenny would audit Arctal's Green & Transition CapEx on day
  one: the sampling plan (T53's method), the failure classes to expect (T54's), key independence (T56), point-in-time (T55),
  expert minutes per thousand data points (T35/T38). An agent drafts from the repo's own numbers; Kenny edits and owns it. Done
  when Kenny has edited it.

- **T60 Reader consistency (pass^k).** For a stratified sample of tasks per live reader (not every company: each run is a
  subscription call), the same task runs k = 3 times at the production settings. Per reader and field: pass@k (at least one
  run checked) and pass^k (every run agrees and is checked), each with n and k; a cell whose runs disagree is a finding in its
  own right (an unstable cell), listed. Lands on the Agents section beside the T49 score; runs metered in `runs`. Sample sized
  to one session window (~10 tasks per reader, ~120 calls), run around the 1:30am ET reset. Touches a new `ledger/consistency.py`,
  `ledger/cli/`, score.py, rules.js (after T53). Done when every live reader shows pass^k with n and k and the unstable cells
  are listed.
- **T61 Prompt-change gate (paired).** When `save_prompt` creates a new version, `ledger eval-prompt <id> vN vM` runs both
  versions on the same golden cells and reports a per-field paired comparison (McNemar, or a paired bootstrap interval on the
  checked rate, from score.py's states); `use_prompt` refuses the promotion when any field regresses beyond its interval. The
  result is written next to the prompt, `agents/evals/<id>@vN-vM.json`, and `agents.json`'s history line names it. Done when
  promoting a prompt without a passing paired run is refused, shown on one real version pair (notes@v2 → v3 or aispend@v3 → v4).
  Placed after T53 keyed (day 2, late). (Both from Kenny's evals checklist, 1 Nov: the other thirteen points are covered by
  T54, golden, faults, the deterministic checks, the runs table, T53, T30, the watch, T38 and the failures-to-fixtures loop.)

**Fixes found by the overnight audits (1 Nov night; verified in the code or the database by the planning session, confirmed by
the builder before fixing). Not new scope: each is a defect in approved work, fixed before v1.9.0.**

- **T62 One key per finding (was LB1).** `app.flow` builds the `finding_unconfirmed` key as kind|ticker|where, and `where` is
  the display string "field period", so two findings on the same field and year share a key; `resolutions.latest()` keeps one
  line per key, so resolving the second silently un-resolves the first. None on the six today; 21 unconfirmed findings share a
  key across the tracked companies (HUT capex FY2023, RIOT opex FY2025, CEG cost_of_revenue_part), so it bites in the first T52
  batch. Fix: the key for finding_unconfirmed and blocked items carries the rule id and is built from fields (ticker, field,
  period, dimension, rule_id), not from `where`, in app.flow and resolutions._parse; live resolutions migrate to the new keys,
  the unmappable ones go to decisions/archive/ with a note, never rewritten. Test: two findings on one field and year, both
  resolved, both stay resolved. Workbench lane, before T57a. Done when that test passes and the stage-3 queue has no duplicate keys.

  *As built (1 Nov):* confirmed first over all 100 tracked companies: 21 duplicate keys, 151 of 2,833 queue items sharing one,
  all `finding_unconfirmed`, 0 on the six; most pairs were the same rule on two filings (`unit_from_document`, `row_label_switch`
  on CEG), the rest two rules on one field and year (HUT capex FY2023 jump + capex_intensity, RIOT opex FY2025 jump +
  opex_over_revenue). One key function, `resolutions.key_for(kind, ticker, field, period, dimension, rule_id, subject)`
  → `kind|ticker|field|period|dimension|rule_id|subject` ('' for what the item lacks; a `|` inside a part, as in XOM's
  "Chemical Products | Non-U.S." or a rule's subject, is escaped `%7C`, and `%` `%25`), used by `app.flow` for all five kinds; `hq.py`'s
  findings and questions now carry `rule` (the exception's rule id; `restated` and `opex_over_revenue` for the two findings
  that are not exceptions) and `subject` (the exception id's tail: the filing, the column), and `app.flow`'s `content_hash`
  leaves out only what T62 added per kind (a finding's rule and subject; a question's subject, questions carried `rule`
  before), so every hash equals its pre-T62 value and no resolution expired. `resolutions.parse_key` / `_parse` read the shape; a legacy
  key (two pipes) is not live: not shown, not counted, not a G6 failure. Migration `ledger resolutions migrate-keys [--dry-run]`
  (`ledger/cli/resolutions.py`, logic in `resolutions.migrate_keys` / `write_migration`): the log is append-only (its
  docstring), so each legacy line that matches exactly one queue item's legacy key is appended again under the new key with
  `migrated_from` and `migrated_at` (hash kept, not recomputed, so an expired one stays expired; the CLI prints whether it is
  current), id, hash, state, reason, by, at untouched; lines matching none or several are copied to
  `decisions/archive/resolutions-keys-<date>.jsonl` behind a note and left in the log; nothing removed; a second run reads the
  archive files too and is a no-op. `by_row` gives a row the worst of its items' latest resolutions (blocks > fix > explain >
  accept) and, given the queue (Reconcile does), leaves a row open while one of its findings has no current resolution.
  `resolve()` refuses a key that is not a live kind in the key_for shape (400 from `/api/resolve`). Run on 1 Nov: migrated 3, archived 0, untouched 0
  (the three LITE operating_income lines → `finding_unconfirmed|LITE|operating_income|||row_label_switch|`, Kenny Geiler's
  accept the latest, hash current). `unconfirmed()` on the six before and after: []; G6 all empty; LITE's item shows explained
  by Kenny Geiler. After: 0 duplicate keys over the 100 companies and on `/api/v1/reconcile?scope=all|HUT|RIOT|T|LITE`. Tests
  in `tests/test_resolutions.py` (round trip and escaping, two findings on one field and year both resolved, the queue over
  every company has no duplicate key, the migration plan and write on a temp log: one mappable, one ambiguous, one orphan, one
  already new, idempotent); the T3 and gate tests moved to the new shape. Fast suite 274 OK, golden equal. Reconcile's "to
  confirm" rows now print `field period (rule)` from the parsed key. The `asset_types|ticker|name` rows (T33) keep their own
  two-pipe key: not a queue item, not read by resolutions.
- **T63 Mappings are proposals until a person confirms them.** *Done 1 Nov 2026 (branch `t63-mappings-proposals`): `status.confirmed` (a field check on `confirmed_by`) and `status.of_mapping` decide the Mapping stage; the 47 entries are open as to confirm and fail G6 until Kenny confirms them on Reconcile, asset types; proven on the six went from 6 to 0 for that reason alone. The filer's tagged member is shown and a us-gaap mismatch flagged (6 of 47: AMZN 2, APLD 4; the audit's claim holds); storing it on the row is T74.* All 47 entries in taxonomy/asset_types.yaml are `by: Claude
  Fable 5.1` and nobody confirmed them; Proof counts an entry as checked, so the six's Mapping stage is proven on model
  judgement alone, against the thesis. Fix, inside T33's design: an entry without `confirmed_by` is a proposal; the Reconcile
  "asset types" group shows it with Approve / Edit / Reject (Approve writes `confirmed_by`, `confirmed_at`); the
  asset_type_mapping guard and `status` count a mapping as checked only when confirmed, and as "to confirm" (G6, like a
  decision) until then; the mapper's own proposals confirm the same way. If cheap: store and show the filer's own tagged member
  (reference/dimensions.instance_facts reads it and discards it) beside each proposal and flag a mismatch (the audit reports
  AMZN FY2025 EquipmentMember / OtherCapitalizedPropertyPlantAndEquipmentMember and APLD BuildingMember /
  SoftwareAndSoftwareDevelopmentCostsMember differing from the yaml: verify against the instances first). The six's proven
  count drops until Kenny confirms (~15 minutes, 47 clicks, on the morning list); the README says so. Workbench lane, after T62.
- **T64 The packet says what ships, and one restatement threshold.** The packet README documents `first_reported` and
  `citations` on values.csv, which v1.6.0–v1.8.0's values.csv does not carry (checklist.py's C7 loop writes api.fetch("values"),
  which drops them and the null not_reported rows). Fix before v1.9.0: either api.fetch("values") gains first_reported, filed,
  accession and citations, or the README generator describes the columns that ship (prefer the first: the columns exist and a
  reader wants them); a test compares the README's column table with every CSV header in the packet. One restatement threshold
  in config (store.py says 1%, reconcile half a rounding unit, normalize 0.1% today), named in the dictionary. Folded in from
  the audits: DIFF.md's headline counts missing values as added (DC6): count only rows with a value; QUALITY.md's G5 wording
  "by a person where it can't" promises a human check that did not happen for v1.8.0 (no stage3-handcheck.json): say what was
  checked and by what. v1.8.0 untouched;
  v1.9.0's DIFF.md names the fix. After T55 (api.py) and T66 (checklist.py).
- **T65 A missing field with an XBRL value is open, not "not reported" (AMZN).** documents.income_tables ==
  cash_flow_tables for every AMZN 10-K (the 2026 income statement is t0035, recorded t0034), so AMZN revenue and opex FY2022–25
  are blank; reconcile.values_for labels them not_reported without asking XBRL, status calls them explained, rules._coverage
  counts null rows as present, and the gates passed; v1.8.0's values.csv has no AMZN revenue/opex rows and QUALITY.md says "10
  blank because the company reports no such line" (AMD revenue/opex FY2022 too). Database-wide 131 of 142 not_reported cells
  have an XBRL value. Fix: (a) a missing field whose XBRL reference exists gets the label `not_extracted` = open, and
  `_coverage` stops counting null rows as present; (b) a locator rule that blocks when income_tables == cash_flow_tables or
  the income table has no revenue-like row; (c) the failure type in INGESTION.md and failures.yaml; (d) AMZN re-located and
  re-extracted (headless agents); (e) a golden fixture for the AMZN case, re-frozen in its own commit. Done when the 10 cells
  read filled or open and QUALITY.md's count is true. The six's proven count moves; the README says so. v1.9.0's DIFF.md names it.

  *As built (1 Nov, branch `t65-not-extracted`):* Confirmed first: all four AMZN 10-Ks had `income_tables == cash_flow_tables`
  (t0035, t0036, t0036, t0034); AMZN revenue and opex FY2022–25 were null `not_reported` with XBRL values for every one;
  database-wide 131 of 142 not_reported cells had an XBRL value. The cause: the locator's snapshot test (`_summary`) took
  "Equity-method investment activity, net of tax" for a balance-sheet equity line, rejected every Amazon income statement as
  a highlights table, and the cash-flow table (net income, deferred taxes: score 3) won once no unflagged table scored 4.
  (a) `values.label` and the taxonomy `check` vocabulary gain `not_extracted`; `reconcile.values_for` writes it when the
  newest 10-K has no cell for a field but the XBRL reference has a value (`not_reported` only when the reference is empty
  too); `status.of_value` makes it open, by `label:not_extracted`, reason "the filing tags a value the reader did not
  extract"; `rules._coverage` counts a null row as present only with a stated reason (`not_reported`), so a not_extracted
  row is a missing value whose finding takes the row's open state; `taxonomy._checked` maps it to `check = not_extracted`,
  open like `unmapped` (no taxonomy row carries it today: revenue and opex are not taxonomy rows). (b) block rule
  `statement_tables_distinct` (`rules/statement_tables_distinct.yaml`, `rules.Context.documents` filled by `cli/rules`):
  income_tables ≠ cash_flow_tables and the located income statement has a revenue or sales row; a 10-K/A with no
  cash-flow table is the amendment guard's case. `BALANCE` excludes "equity-method". (c) type 73 in `docs/INGESTION.md`;
  the failures.yaml entry follows on T54's branch. (d) `ledger ingest --ticker AMZN` relocated the four (income t0036 /
  t0037 / t0037 / t0035), the reader re-read them headless (12 values each, 11–14 s), `extract --load`, `reconcile`:
  the 8 cells filled, every one agree with XBRL (revenue 513,983 / 574,785 / 637,959 / 716,924 M; opex 212,904 /
  233,194 / 243,078 / 280,535 M); `rules`: 0 findings for AMZN; the locator change relocates no other filing in the
  database (checked over every documents row). (e) golden re-frozen in its own commit: values (AMZN 8 filled, AMD
  revenue/opex FY2022 → not_extracted: XBRL tags 23,601 M and 9,339 M while AMD's FY2022–24 10-Ks' located income
  statement is the Xilinx pro forma pair the reader refused, a second locator case left for its own ticket), exceptions
  (+2 coverage warn on AMD FY2022), extractions (+36 AMZN income cells), facts (AMZN input_hash only); `--check` equal.
  Proven count 6 of 6 → 5 of 6 (AMD open 7: the 2 values, their 2 coverage findings, 3 row_label_switch findings on
  those fields). The v1.9.0 packet's QUALITY.md, built in memory: "81 values · 79 from agents · 2 missing · 78 agree with
  XBRL · 0 blank because the company reports no such line" (was 10); `release.py` is T64's lane, so not_extracted has no
  line of its own there yet (the 2 are the "missing"). Not done: the other 95 companies' values were not re-reconciled
  (121 not_reported cells with an XBRL value remain outside the six until the next `reconcile --stage 3`); AMZN's notes
  tasks changed sha (the income statement left the note candidates) and the notes reader was not re-asked, only reloaded;
  `ledger run --ticker AMZN` re-asks it. Tests: reconcile, status, coverage, taxonomy, the rule on synthetic documents
  rows, the Amazon layout in `test_tables`; `docs/DATA_DICTIONARY.md` regenerated. One test red on purpose, outside this
  lane: `test_status.ProofAgreesWithReconcile` (Proof counts AMD open 7, Reconcile 5): Reconcile's queue (`app.flow`) lists
  a value only when its label is `unresolved`, so the two `not_extracted` value rows have no queue item while Proof lists
  them; the fix is one condition in `app.flow` (queue `not_extracted` values the way `unresolved` ones are queued), in
  app.py's lane. Also pending: AMZN fails gate G5 ("no hand-check file") because its 8 new values have not been re-read
  on the rendered 10-K (`ledger evidence --ticker AMZN`, Chrome) nor hand-checked; `ledger run --ticker AMZN` does both.
  *Follow-up commit:* `app.flow` queues one `value_missing` item per `not_extracted` value (state from `status.of_value`,
  key built like the other kinds, `value_missing|<ticker>|<field> <period>`); Reconcile shows it open with the cause "Not
  extracted"; Proof 7 == Reconcile 7 on AMD. `value_missing` is not in `resolutions.LIVE_KINDS`: a person cannot resolve
  it, the fix is an extraction (`docs/PROOF.md`).
- **T101 AMD's located income statement is the Xilinx pro forma pair.** *Done 2 Nov 2026 (b6027ca, 332a32b): the T65 review fix to the balance-sheet marker locates AMD's statement of operations (t0012); re-read headless, all 12 values agree with XBRL, AMD proven again.* AMD's FY2022–FY2024 10-Ks (0000002488-23-000047
  t0032,t0033; -24-000012 t0031,t0032; -25-000012 t0028,t0029) have as their located income statement a two-table pair
  from the Xilinx acquisition note: a one-column partial table (Net revenue 4,612) and the unaudited pro forma results
  (Net revenue 24,117 / 20,150, Net income 2,311 / 8). The reader refused it in all three outputs ("not the consolidated
  statement of operations") and read only capex from them, so FY2023 and FY2024 come from the FY2025 10-K and FY2022
  revenue and opex have no cell: `not_extracted` since T65 (XBRL tags 23,601 M and 9,339 M), AMD open 7, proven 5 of 6.
  `statement_tables_distinct` does not catch it (the pair has revenue rows). Fix: a locator rule (a pro forma or
  acquisition caption, a one-column table, a pair whose net income does not tie to the cash-flow statement's), or a
  second candidate pass that re-scores when the reader refuses the statement; re-read AMD headless; golden re-frozen in
  its own commit. Done when AMD FY2022 revenue and opex are filled and agree with XBRL and the six read 6 of 6. Not built
  tonight (found by T65).
- **T66 The manifest states what produced the rows.** checklist.py writes the current prompt_version(), PARSER_VERSION and
  model(), not what produced the shipped rows: v1.8.0 claims statements@v2 / tables@15 / claude-opus-5-5, while 84 shipped
  statement cells were read under statements@v1 and 379 of 393 filings were parsed with tables@12; 13 statement outputs have no
  `_run`. Fix: the manifest lists the distinct prompt_version per reader and the distinct models over the shipped rows, the
  distinct parser_version over the documents in scope, git HEAD plus a dirty flag, and sha256 of definitions/companies.yaml,
  taxonomy/*.yaml and decisions/resolutions.jsonl; a test with a packet that mixes prompt versions. v1.8.0 never edited;
  v1.9.0's DIFF.md notes the correction. checklist.py lane.
  *As built (T66, 1 Nov):* `manifest.json` carries `provenance` `{prompts: {reader: [...]}, models, parser_versions, unrecorded:
  {reader: n}, git: {head, dirty}, inputs: {path: sha256}}` (`checklist.provenance`), computed over the rows the packet writes: the
  statement cells values.csv cites, the note cells facts.csv cites, every ai_statement and project in scope, the documents of the
  companies in scope; a row's model is the `versions.model` of the run that wrote it (runs by run_id, step, subject); a row whose
  prompt_version or model is not on record counts once under `unrecorded`, never guessed. Inputs: definitions/companies.yaml,
  every taxonomy/*.yaml, decisions/resolutions.jsonl (null when absent). The manifest is not among the hashed files, so git and the
  input hashes never move the packet's hash and the page's hash stays the CLI's (DryRun). The top-level `prompt`, `parser`, `model`
  stay for compatibility; the release README says `provenance` is the record. In scope for v1.9.0 (the six): reader
  statements@v1 + statements@v2 (96 distinct cited cells: 50 citations under v1 across 118; 72 of 258 in-scope extraction rows under v1,
  against 84 of 4,346 database-wide), 59 of the 96 cited cells with no model on record (their extract run wrote `model: null`; 9 of 28
  in-scope output files have no `_run.model`), notes@v3 (552 cited cells, all recorded), aispend@v4 (227), projects@v1 (182);
  parser tables@12 on all 28 documents in scope (database-wide 379 of 393 tables@12, 14 tables@15); models: claude-opus-5-5 only.
  DIFF.md says "Provenance: v1.8.0's manifest named the versions in use at build time; from v1.9.0 the manifest names the versions
  that produced the rows" when the previous manifest lacks `provenance`. Tests: `tests/test_checklist.py` `Provenance` (a packet
  mixing statements@v1 and @v2, an unrecorded row, the file hashes, git mocked away → null; the real `packet` over mocked rows into a temp releases folder: the DIFF note once
  against a previous manifest without `provenance`, never with). The reader's rows are the value-not-null set `values.csv` ships (api.fetch, C7). No golden change: no row moved.
- **T55b Older vintages reconciled against their own filing.** Only the newest vintage is checked against XBRL. AT&T revenue
  FY2022: value 120,741,000,000, first_reported 120,741,000, basis "restated": a 1000x misread, not a restatement, which an
  as_of=2023 query would serve as truth. T55 ships with every as-of row flagged `vintage_check` (unchecked unless it is the
  checked newest figure) and a response note; T55b reconciles each older extraction against the XBRL facts of its own
  accession (companyfacts lists facts by accn): "restated" only when both vintages agree with their own filing's tags, else
  "misread" = open item; the no-lookahead test also asserts no as-of answer serves an unchecked vintage. Golden re-freeze in
  its own commit. Folded in: `misread` vs `restated` is the vocabulary (VP2); 45 `values` rows read restated today without this check.

**Rollout to the call (agreed 1 Nov, both sessions; Kenny: yes).** One builder per file at a time: workbench.py + reconcile.js
go T33 → T36 → T37 → T57a → T53 audit, strictly sequential; status.py T56 → T57a; proof.py/proof.js T56 → T54; rules.js T49 →
T53; api.py/release.py T55 alone; resolutions.py T57a alone. Parallel lanes: the workbench lane, T55, T54, T42, the T52 batch runs.
- Night 1 (1→2 Nov): merge T49, T30, T44, T33 after review; T56; T54; T55. Kenny in the morning: approve MU's asset-type
  proposals (T35's stopwatch starts).
- Day 2 (2 Nov): T36, T37, T53 keyed interval, T61 prompt gate, T35 Micron → PROVEN 7, `reports/company-cost.md` first row.
- Day 3 (3 Nov): T57a, T42, T52 batch to 10.
- Day 4 (4 Nov): T53 unkeyed audit view + ASML sample; Kenny audits (~1 h); batch 25 (runs around the 1:30am ET limit).
- Day 5 (5 Nov): T57b if T42 landed; T60 pass^k sample (one session window); T41 if slack.
- Days 6–7 (6–7 Nov): batches 50 and 100 with honest states; cost curve in the report. Kenny: bulk approvals by cause, 2–3 h in
  total with T37's preview.
- Day 8 (8 Nov): T59 draft; T58 only if a day is free; feature freeze.
- Day 9 (9 Nov): v1.9.0 built; Kenny confirms what is his and signs from the Release page; hosted redeploy; T59 edited.
- Day 10 (10 Nov): rehearsal, buffer. Nothing new after day 9. Call 11/12 Nov.
Kenny's minutes: MU mappings ~15 min, audit ~1 h, batch approvals 2–3 h spread over days 3–7, confirmations ~30 min, memo ~2 h,
sign 5 min: about seven hours over nine days. What breaks: T57b depends on T42; batch runs over 25 need more than one session
window; the proven count at 100 is 25–40 honest-proven with the rest open under named causes; the 993/1,218 headline is retired.
Overnight rules: never sign v1.9.0, never publish, no paid API, no decision confirmed in Kenny's name (a "Kenny in the morning"
list in the README status instead), two builders never hold one file.

## K. The discipline audits' tickets (Kenny, 2 Nov: "fold everything we need to change into tickets")

*Copied from `docs/DISCIPLINES.md` (the audits and their root cause live there; this is the ticket list).*

Every finding above is a ticket below, with its audit source in brackets. Overlaps across audits are merged. Order:
**K1, before the call** (the root cause and what a reviewer would find first); **K2, before the call if a slot frees**;
**K3, after the call**. Already raised and building: T62–T66, T55b. A few small items fold into existing tickets and
are listed at the end.

### K1: before the call

- **T80 A label never counts as a check.** [root cause] *Done 2 Nov 2026 (branch `t80-label-never-a-check`): every proof item carries `ref`, the record its check rests on; `status.evidence_gap` says why a checked or explained item is not backed, `proof.unevidenced` walks the proven set; `tests/test_status.py` walks the six on the golden fixtures (0 gaps over 828 checked or explained rows of 875) and plants a `not_reported` with an XBRL value, a mapping with no `confirmed_by` forced to checked, and a resolution id not on file, each red. Review fixes the same day: a lookup marker (`ref.looked_up`) so an empty answer counts only when XBRL was asked; answer keys check only, each on its own value; `config.PEOPLE` and `status.is_person` (fail closed) for `confirmed_by` and resolutions; the gate only on the release stage; duplicate rule ids refused; loader failures (`proof.FAILURES`) kept off the values and release stages; planted tests for each. One real mislabel fixed: the release stage's gate item said `by: located` with no filing behind it, now `by: gate`. Resolution authorship reads `author_kind` when present, else the `mapper.NOT_A_PERSON` name check and "to confirm" (T69 makes it a field).* Every row whose state is checked or explained points at the
  evidence that makes it so: an answer key value, a quote verified against its text, a person-confirmed mapping, a
  definition or rule by id, a resolution by id with `author_kind` person. A test walks every row of the six through
  `status.state` and fails on any checked or explained row whose `by` names no evidence record, or names one that does
  not exist. Done when the test is green on the six after T63 and T65, and planting a bare label (`not_reported` with an
  XBRL value present, a mapping with no `confirmed_by`) turns it red. About ½ day.
- **T102 Negative computed opex gets its own label, shown open; a person decides it.** [root cause, type 65]
  `reconcile.values_for` labels an opex row `not_reported` when revenue − cost of revenue − operating income is negative
  (operating income holding fair-value gains, a bitcoin miner), whether or not XBRL tags an opex value. That is a label
  over an answer key. Negative computed opex gets its own label (e.g. `negative_opex`), shown open; a person decides it
  in Reconcile (a definition or an explain). Never not_reported, never explained by a rule alone (T81 keeps a blank
  accounted for only by an open item or a person's decision). Since T81 `status.of_value` already shows HUT and RIOT
  opex FY2024 open (`label:not_reported` over an XBRL value); T102 gives them their own label. None on the six. About 2
  hours.
- **T81 Completeness against the answer key.** [root cause, DQ1] *Done 2 Nov 2026 (branch `t81-completeness`, with review fixes): `proof.missing_from_dataset(con, tickers, ds)` lists the silent blanks: a release field (`config.RELEASE_FIELDS`, which `coverage` now reads too) and year from the company's first `values` row (`rules.first_periods`, shared with `coverage` and `no_10k_yet`) where reference_values holds a value and the released value (after review decisions) is blank, with no open value row, no undecided open finding on the cell, no person's resolution and no person's review decision (`proof.person_wrote`); a ticker with no reference rows is one entry, "no XBRL answer loaded". The checklist's required line `complete` counts it and must read 0. `status.of_value` explains `not_reported` only when XBRL was looked up and is empty, else open, so the line, `coverage` and Proof give one verdict per cell. 0 on the six; a one-off stage-3 reading gave 4, all "no XBRL answer loaded" (SPCX, NBIS, BTDR, ARM: no 10-K read). `tests/test_completeness.py` (unit cases and the six on the golden fixtures, which it requires). Facts not covered, decided in docs/PROOF.md: 76 of 113 instance members on the six have no fact row, nearly all scope choices; counting them needs a per-company axis and member map a person would confirm.* For every company in scope, every field and year
  where XBRL holds a value is either in the dataset or an open item; a silent blank is a release failure. A required
  checklist line counts "answer-key values missing from the dataset" and must read 0, open items aside. Builds on T65.
  Done when the line reads 0 on the six, and deleting one extracted value in a test turns it red. About ½ day.
- **T82 A gold set separate from golden.** [root cause, LB4] *Done 2 Nov 2026, infrastructure; verdicts pending (branch `t82-gold-set`): `ledger/gold.py`, `ledger gold --draw | --status`, `gold/<TICKER>.json` for the six (10 values + 10 facts each, 6 facts untagged, seed GOLDEN_SEED|v1.9.0|ticker), the Gold set section on Proof with Right / Wrong / Can’t say and a note (`POST /api/gold/verdict`, `by` on config.PEOPLE, lock + temp file + os.replace), `ledger golden --check` compares every verdict with the run's tables and reports the rest as unverified, error rate with n and a Wilson interval. `tests/test_gold.py`: a planted change fails, the frozen Amazon blank fails, the route refuses a non-person. Kenny's ~1 hour of verdicts is still to do.* Golden stays the regression snapshot ("nothing changed").
  `gold/` holds a hand-verified sample per proven company: about 10 values and 10 facts per company, stratified across
  fields, years and the untagged notes, each verified by Kenny against the filing with right / wrong / can't say and a
  note. `ledger golden --check` also compares the live tables with `gold/` and fails on any disagreement, so a frozen
  error cannot pass twice. The spot-check seed includes the release version, so the sample moves. Done when `gold/`
  covers the six, the check fails on a planted change to a gold value, and the frozen Amazon blank (before T65) would
  have failed it. About ½ day of build plus about an hour of Kenny's verdicts.
- **T67 Faults that matter: omissions, wrong tables, systematic errors, XBRL off.** [MR1, root cause] Add fault kinds:
  the reader returns nothing for a field; the locator picks the wrong table (income ↔ cash flow); the same wrong row,
  column or scale in every year of a company. Run the full set twice, with `xbrl_reconcile` counted and with it
  removed, and report catch rate per kind with denominators on the Agents section. Done when the report shows how
  much of the catch rate depends on XBRL, every escape with XBRL off is a row in `taxonomy/limitations.yaml` (T68), and
  the omission and wrong-table kinds are caught (by T81 and the T65 locator rule). About 1 day.
- **T68 Limitations and methodology in every release.** [MR2, VP7, DQ6] *Done 2 Nov 2026 (branch `t68-limitations`): `taxonomy/limitations.yaml` holds 11 entries (id, weakness, rows, mitigation, closes; `ledger/limitations.py` refuses one missing a field), 8 of them with counts computed at build time from the fault reports, failures.yaml, asset_types.yaml, config and the packet's own CSVs; `release.build` and `checklist.packet` write `LIMITATIONS.md` (intended use and not for use, the table, cadence, corrections, support = the signer in SIGNOFF.json); the README lists it; the checklist's informational line "Limitations with no mitigation" reads 2 (survivor bias, monitoring). QUALITY.md's wording was already right after T64; the `to_check` docstring and the README's QUALITY.md line were fixed. v1.9.0 is not built here: it carries the file when Kenny signs.* `taxonomy/limitations.yaml`: id, the weakness,
  rows affected (count), mitigation, the ticket that would close it. Seed: T67's escapes, "the answer key comes from the
  same filer", "one person builds, decides and signs", "N companies not proven", "the universe is today's AI-relevant
  names, survivor-biased for backtests", "45 failure types have no catching check" (T54), "interpretive fields of
  statements are unmeasured". `release.build` writes `LIMITATIONS.md` with intended use and not for use, plus cadence,
  correction policy and support contact. QUALITY.md says "re-read by machine" where no person checked and "independent
  reading" instead of "independent sources". Done when v1.9.0 carries `LIMITATIONS.md` and a checklist line counts
  entries with no mitigation. About ½ day.
- **T69 Who made a decision, as a field.** [MR4] *Done 2 Nov 2026 (branch `t69-t100-authors-late-writers`): `author_kind` on every new line, set by the writer (`resolutions.resolve(..., author_kind=)` required; the person routes refuse a `by` not on `config.PEOPLE`); `unconfirmed()` and `proof.person_wrote` read the field, the phrase only on lines without it; no migration needed (legacy lines read by the old rule, none rewritten); `tests/test_resolutions.py`, class Authors.* Every resolution has `author_kind` ∈ person / run, set by the route
  (`/api/resolve` gives person; agent writers give run). `unconfirmed()` reads the field; the "to confirm" phrase is read
  only for lines written before the field existed (one append-only migration). Done when a test shows a run-written
  resolution without the phrase still fails G6. 2–3 hours.
- **T70 Row-level provenance, and derived rows cite every input.** [LN1, LN2, MR6] Taxonomy rows (schema v12) carry
  `prompt_version`, `model`, `parser_version`, `document_sha256`, `cell_text`, `column_label`, `input_hash`; a column
  empty only with a stated reason ("output predates _run"). Derived rows add `source_prior` and `formula`, their `check`
  is the worse of the two balances', and a change across a gap year or a restated prior balance is flagged, never
  silently computed. Statements, facts and projects rows carry `prompt_version`. The proven companies' statement
  filings with no `_run` are rerun or labelled (Kenny decides; a rerun costs subscription time). Done when the MSFT
  "Buildings and improvements" FY2025 change can be followed from the CSV alone and a test plants a gap year. About 1 day.
- **T71 One key per list, enforced.** [DQ2, DC4, DC3] A stable `row_id` (hash of the row's identity plus source and
  quote) on taxonomy and ai_spend; `statement_id` and `project_id` from content, not position; `release.ROW_KEYS`,
  `store` keys and the dictionary agree; the diff pairs by `row_id`; a required checklist line "duplicate keys: 0 per
  list"; a key on `(release, key…)` in `publish.ddl`. Done when every list has 0 repeats on the six, a test fails on an
  injected duplicate, and a rebuild keeps every `row_id`. About 1 day.
- **T72 A versioning rule with a required bump.** [DC1] Written in API.md and the packet README: major = a column or file
  removed, renamed or retyped, a meaning changed, a key changed or scope narrowed; minor = additions; patch = corrected
  values in the same shape. The checklist computes the required bump from the diff (plus a declared meaning-change list)
  and refuses a lower one. `schema_version` in the manifest and `ledger_releases`. v1.7.0 and v1.8.0 stay as signed;
  v1.9.0's DIFF names them as breaking. Done when a test shows a packet that drops a column cannot sign as minor.
  About ½ day.

- **T100 A late writer never overwrites a newer state.** [memory checklist's deletion test; Kenny: "Sure send it"] *Done 2 Nov 2026 (branch `t69-t100-authors-late-writers`): (1) the three loaders refuse an output whose task_sha is not the current task's (`agent.stale`), logged as their failure class, and `ledger rules` keeps those failures; (2) `mapper.by_name` never makes a re-proposed rejected member current (`reproposed`, shown on Reconcile) and ignores proposals after an approval (`late`); (3) `resolutions.latest` keeps a person line over a later run line on the same key and hash; tests in `tests/test_late_writers.py` and test_resolutions Authors. The check refused 7 stale AMZN/AMD notes outputs (INGESTION.md 74): golden red until `ledger notes --run --ticker AMZN AMD` and a re-freeze.* Three
  places, from reading the code: (1) `extract`/`notes`/`aispend --load` never compare an output's `_run.task_sha` with the
  current task file, so an answer to a repacked task (T65 re-pointed AMZN's income table) still loads, guarded only by
  citation re-resolution; (2) `mapper.by_name`: the latest `proposed` line wins and a rejection clears a proposal only if it
  came before it, so a delayed proposal of a member Kenny rejected becomes current again; (3) resolutions: the latest line per
  key wins, so a run-written "to confirm" line after Kenny's decision supersedes it. Fix: every agent write carries the
  fingerprint of what it was built from (task_sha; the asset-type entry's hash; the item hash plus the latest resolution id);
  the loader refuses or routes to review on a mismatch and logs it; a proposal of a rejected member is never current and shows
  as "re-proposed after rejection"; a run line never supersedes a person line (T69 author_kind; fold together if they share
  files). Done when three tests pass: repack a task then load the old output → refused; reject a mapping then append a delayed
  proposal of the same member → not current; Kenny decides a key then a run writes "to confirm" → Kenny's decision stands.
  About half a day. Lanes: (1) ingest; (2) and (3) workbench after T63. Before Kenny approves and rejects during the batches.

### K2: before the call if a slot frees

- **T73 The taxonomy file is the dataset's taxonomy.** [TX1, TX4] `taxonomy/taxonomy@v2.yaml` (a new file, as v1 says)
  matching what rows emit (`derived`, `ppe_gross_by_type`, the `ai_*` ids; no `group`), `includes` / `excludes` per
  category, defined-but-not-emitted categories marked. A test: every emitted (measure, category) is in the yaml and every
  yaml id is emitted or marked. The manifest records the taxonomy version and sha256 of `taxonomy/*.yaml`; DIFF.md gets
  a "reclassified" section; `taxonomy/CHANGELOG.md`. Fix `LandAndBuildingsMember` in TAXONOMY.md and the stale header of
  `stated_figures.yaml`. Done when the test is green and the next release names its taxonomy. About ½ day.
- **T74 The filer's tag decides the mapping.** [TX2, TX3] Store the filer's member on `facts` and the row
  (`reported_member`). Where the filer tagged a us-gaap member, `standard_type` equals it (`check_method =
  mapping:filer_tag`) or `asset_types.yaml` says why not. Each mapping gains `relation` (exact / broader / narrower /
  partial), `confidence` and the note's quoted words; pin a us-gaap element list and test every `standard_type` exists
  in it; warn rule `standard_type_switch` (fires on Amazon's FY2025 split). Done when every mapped type on the six
  matches its filer tag or explains why, and the rule fires and is explained on AMZN FY2025. About 1 day, with T63.
- **T75 Timeliness measured.** [DQ3] Store `accepted_at` (EDGAR acceptance time) on documents and `first_released` per
  value key. QUALITY.md: newest filing in scope, median and max days from acceptance to signing for values new in the
  release, when watch last ran. A required checklist line: watch ran in the last 24 hours with 0 unread 10-Ks in scope.
  Done when v1.9.0 shows the numbers and the line goes green only after a fresh `ledger watch`. About ½ day.
- **T76 Series breaks as data.** [VP3] Info rule `series_break` with a cause on the row (`break` column):
  `discontinued_ops`, `carve_out`, `fiscal_year_change`, `transition`. The Dataset grid marks the break. Coordinate with
  T58. Done when WDC FY2022→23, GEV FY2022–23 and HUT FY2023→24 carry their cause on fixtures. About 1 day.
- **T77 Reviewer guide.** [LB6] `docs/REVIEW.md`: what each state means with two real examples each, when an explanation
  should become a definition or rule (T36), which causes go to data, expert or client (T57a), the edge cases met so far.
  Linked next to the Reconcile buttons. Done when every cause and state has a line and an example. About 2 hours.
- **T78 Agreement, and an error rate from every hand-check.** [LB3, LB4] Resolutions gain `pass` (primary / overlap); a
  blind second-pass mode hides earlier decisions; `ledger/agreement.py` reports percent agreement and Cohen's kappa
  with n. Before the call: a blind re-label of 25 cells of the T53 audit a few days later, labelled intra-rater. Hand-
  checks record right / wrong / can't say; about 10% of bulk-applied resolutions are queued for blind re-check. Error
  rate with n and a Wilson interval, separately for machine labels and person decisions. Done when the Agents section
  shows the intra-rater kappa with n and both error rates. About 1 day; folds into T53.
- **T79 Benchmark against XBRL alone.** [MR3] For the six, build the same values and facts from companyfacts only;
  report cells both give, cells only the pipeline gives (untagged), cells where they differ and who was right.
  `reports/benchmark-xbrl-only.md`; the release README cites the "only the pipeline" count. About 1 day.
- **T83 No mixed sums.** [VP5, first half] `api.apply` refuses a `group=period` sum across companies whose fiscal years
  end more than a set number of days apart, and any sum across currencies, unless `calendarize=` or `fx=` is passed.
  Done when summing FY2025 capex across MSFT and AMZN without the flag returns an error naming the calendars. About
  2 hours.
- **T84 Source documents are immutable.** [LN6] `_cached` compares a refetched document's sha256 with the recorded one
  and refuses on a mismatch (a logged failure type, never a silent overwrite); `documents` and `texts` gain
  `fetched_at`; the exhibit-swap path records its real fetch time. Done when a test refetches a modified body and the
  run refuses. 1–2 hours.

### K3: after the call

- **T85 Monitoring floors and a model-change gate.** [MR5] `rules/limits.yaml`: a floor per reader for twin agreement
  and fault catch rate, a ceiling on unstable cells (T60); required checklist lines with the previous release's value
  beside each. `set_model` saves the model as pending; switching needs the T61 paired run. A contingency note in
  HANDOFF (stored outputs rebuild every release; what happens if the model id is retired; the fallback and how to
  re-validate). About 1½ days.
- **T86 Interpretive fields sampled.** [MR7] About 60 AI-spend and projects rows from the six join the T53 audit:
  `kind`, `scope`, `fiscal_year`, amount vs share against the quote; error rate per field with n and interval. About
  ½ day plus 45 minutes of Kenny's verdicts.
- **T87 Validation pack.** [MR8] `docs/VALIDATION.md` laid out like an SR 11-7 validation report, from T67–T86 and
  EVALS, stated as a self-validation, with the commands an independent validator would re-run. About 1 day.
- **T88 Company master.** [VP4] `companies.csv` gains `cik`, `lei`, `fiscal_year_end` with history,
  `reporting_currency`, `accounting_standard`, `annual_form`, `former_names`, `predecessor_ciks`, `covered_since`; every
  list joins on `cik` as well as ticker. About ½ day.
- **T89 Calendar and currency policy.** [VP5 second half, VP6] A `calendar_year` column with its method; `docs/
  METHODOLOGY.md` currency section (values as reported; translated views derived and labelled, average rate for flows,
  period-end for balances, ECB as source, rate date on the row); `taxonomy/ifrs_map.yaml` with non-equivalences
  (IFRS 16 leases, expenses by nature). With T45. About 1½ days.
- **T90 Decision provenance and queue age.** [LB2, LB5] Resolutions record `commit`, `supersedes` and the rule or
  definition version; a decision whose rule changed after it was made reads "decided under an older rule". First-seen
  time per item; queue age per cause on Proof. Folds into T57a and T38. About 1 day.
- **T91 Scorecard by dimension and one rule catalogue.** [DQ4, DQ5] QUALITY.md and the checklist get one table per
  dimension (accuracy, completeness, validity, uniqueness, integrity, consistency, timeliness) with value, denominator,
  threshold, pass. Every check (yaml rules, store contracts, guards, gates, checklist lines) gets a dimension and owner
  in a generated `docs/DQ_RULES.md`. About 1½ days.
- **T92 Cross-table ties.** [DQ7] `capex_segments_tie` (values capex against segment capex, APLD's accrual case
  explained by a definition) and `ppe_total_tie` (PP&E categories against the reported total). With T40/T41. About 1 day.
- **T93 IFRS crosswalk.** [TX5] `taxonomy/crosswalk_ifrs.yaml` pairing every category and us-gaap member with its
  ifrs-full counterpart, relation and note, known non-pairs stated; T45 reads it for ASML. About 1 day.
- **T94 EU Taxonomy eligibility candidates.** [TX6] The Annex I 1.1.2 additions concepts (PP&E, intangibles, ROU) as
  spent categories; `taxonomy/crosswalk_eu.yaml` to candidate activity codes with ICMA and Climate Bonds categories
  alongside; rows say "eligibility candidate", never alignment; scored against ASML's own activity-level figures with
  n and interval. About 3–5 days.
- **T95 Who may change the taxonomy.** [TX7] An owner per file under `taxonomy/`; a change needs a second confirmer
  before a release can sign (extends T34). About ½ day.
- **T96 Contracts as files, and loud failure in production.** [DC2, DC5, DC6] A declared shape for every released list;
  `contract.json` in every packet with README tables generated from it; `current_*` views rebuilt with explicit columns
  so a removed column errors instead of returning NULL; stale views dropped and recorded in `ledger_changes`; one minor
  release of deprecation before a major removal; reader-role grants in `publish.py`; per-file sha256 and the hash recipe
  in the README; format guarantees (UTF-8 explicit, LF, empty = null, booleans, ISO dates). About 2 days.
- **T97 `ledger impact`.** [LN5] Given a changed accession, rule, prompt, mapping or definition, list the published rows
  that depend on it. A strong live demo; pull forward if a slot frees. About ½ day.
- **T98 Note cells re-read on the rendered page, with dated evidence.** [LN7] Evidence for `note_extractions`; every
  entry carries `document_sha256`, `at` and code versions; G5 trusts an entry only while the document hash matches.
  About 1 day.
- **T99 Stable lineage export.** [LN8] `lineage.jsonl` per release, one PROV-style record per row keyed by `row_id`
  (T71). About 1 day.

### Folded into existing tickets

- DIFF.md headline counts missing values as added (DC6) → T64.
- QUALITY.md G5 wording (MR) → T64 (and T68).
- Fixed spot-check seed (LB4) → T82.
- Older vintages checked against their own XBRL; `misread` vs `restated` (VP2) → T55b.
- Charter Score section and "16 rules" → done (8672cc8, agents.json).

## Order

T0 and A first, then C (the schema, one series), then B (the page that signs), then F, then H and I as the calendar above
says, with D per page in parallel and E alongside. Production rails (auth, decisions in Postgres, the self-hosted runner, the hosted copy reading Postgres)
come after T6 signs v1.8.0.
