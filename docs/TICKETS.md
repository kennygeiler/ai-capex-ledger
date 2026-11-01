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
  denominator. Done when the Agents section shows a score per live reader.
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
- **T54 Failure types as data.** `docs/INGESTION.md`'s 72 types (prose table rows today, no class, no catching check named)
  become `taxonomy/failures.yaml`: id, cause class (units / period / scope / locator / agent misread / document error), count
  seen, the check that catches it or `none`, agent-or-document. A Pareto chart on Proof reads the file (proof.js; Plotly as
  Explore uses it, `dataviz` skill loaded). Done when the chart reads from the file and every type has a class and a catching
  check or `none` (a `none` is itself a finding, counted on the chart). *As built (first half):* `taxonomy/failures.yaml`, all 72
  types keyed by INGESTION's number, each with class, origin (agent / document / code / reference), the catching check or `none`
  with a note saying what caught it instead, count of companies named, first-seen date and the INGESTION line it comes from;
  `ledger/failures.py` `load` refuses a class, origin or check not in the vocabulary or not in code (rule ids, `proof.GUARDS`,
  `faults.FAULTS`), `pareto` and `by_check` for the chart; `tests/test_failures.py`. The numbers: by class scope 31, period 11,
  locator 10, agent misread 7, document error 7, units 6; by origin document 31, code 22, agent 10, reference 9; 44 of 72 have
  check `none` (contracts, the evidence re-read, counts and eyes caught them, no rule did); the checks that catch most are
  `period_length` 4, `xbrl_reconcile` 4, `citation_resolves` 3, `coverage` 3, `no_10k_yet` 3. Four types (58, 60, 61, 66) are
  pipeline bookkeeping defects none of the six classes names; each carries a `class_note`. The chart (proof.js) is the second
  half, after T56.
- **T55 Point-in-time.** `?as_of=D` on `/api/v1/values` and `/api/v1/taxonomy`: the figure the newest filing filed on or
  before D gave, from `extractions` (every filing's cells are kept) and `documents.filed`; `first_reported` / `basis` /
  `original_value` stay as they are. A PIT export in the packet (`values-asof.csv` per fiscal year end, or the API alone if the
  packet shape should not change before v1.9.0: decide in the ticket's first commit and say why). A test on the six that an
  as-of query never returns a figure filed after D (no lookahead). Why: Arctal's buyers backtest; a restated figure in history is
  lookahead bias. Touches api.py, release.py. Done when the API and the test exist on the six.
- **T56 Answer-key independence (folds into T40).** The four keys in `status.ANSWER_KEYS` get a grade: independent twin
  (XBRL / ESEF instance) > same-issuer second source (8-K: the same finance team can share the error) > arithmetic tie > later
  truth. `status` names the strongest key per row; Proof counts rows by key strength for the scope. Touches status.py, proof.py,
  proof.js. Done when Proof shows the count per key grade and a row's strongest key is on its trail.
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

**Rollout to the call (agreed 1 Nov, both sessions; Kenny: yes).** One builder per file at a time: workbench.py + reconcile.js
go T33 → T36 → T37 → T57a → T53 audit, strictly sequential; status.py T56 → T57a; proof.py/proof.js T56 → T54; rules.js T49 →
T53; api.py/release.py T55 alone; resolutions.py T57a alone. Parallel lanes: the workbench lane, T55, T54, T42, the T52 batch runs.
- Night 1 (1→2 Nov): merge T49, T30, T44, T33 after review; T56; T54; T55. Kenny in the morning: approve MU's asset-type
  proposals (T35's stopwatch starts).
- Day 2 (2 Nov): T36, T37, T53 keyed interval, T35 Micron → PROVEN 7, `reports/company-cost.md` first row.
- Day 3 (3 Nov): T57a, T42, T52 batch to 10.
- Day 4 (4 Nov): T53 unkeyed audit view + ASML sample; Kenny audits (~1 h); batch 25 (runs around the 1:30am ET limit).
- Day 5 (5 Nov): T57b if T42 landed; T41 if slack.
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

## Order

T0 and A first, then C (the schema, one series), then B (the page that signs), then F, then H and I as the calendar above
says, with D per page in parallel and E alongside. Production rails (auth, decisions in Postgres, the self-hosted runner, the hosted copy reading Postgres)
come after T6 signs v1.8.0.
