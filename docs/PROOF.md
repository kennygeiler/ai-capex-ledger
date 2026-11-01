# Proof: the pipeline proves its own numbers (31 Oct 2026)

Kenny, after the replication run: fifty changes to the screens, and the biggest findings were still errors in
ingestion and attribution. "The entire point of this pipeline is to manage those issues and fix them." So the
frame changes. Not a dataset across 100 companies with a review screen on top; a pipeline that proves every number
it produces, shown first on five companies, widened only when the five are proven.

## What proven means: the one definition of open (`ledger/status.py`)

For a company, every row of the dataset is in exactly one of four states, and one function, `status.state`, says
which; Proof, Reconcile, the trail and the Release gates all read it, so no two pages count the same row differently:

- **checked**: it agrees with an independent check. A value or a fact matches the SEC's XBRL. A statement or a
  planned row is a verbatim quote verified against its text. A filing's statement tables are located. A reported
  asset type is mapped to a us-gaap member with the note's words (`taxonomy/asset_types.yaml`) and a person's
  `confirmed_by` on the entry (T63, `status.confirmed`, a field check). An entry without it is a proposal: open, by
  `label:to_confirm`, and a G6 failure, until a person approves, edits or rejects it on Reconcile.
- **explained**: it does not match, and something on file says why, by name: a definition
  (`definitions/companies.yaml`), an info-severity rule or a guard (`rules/*.yaml`, `proof.GUARDS`), a label reconcile
  wrote because the filing has no such line or XBRL no such tag (`not_reported`, `no_reference`), or a person's
  resolution that says accept or explain (`decisions/resolutions.jsonl`).
- **blocked**: a block-severity rule fired on it, or a person's resolution says blocks. Blocked is open that also
  refuses the release; every count of open includes it.
- **open**: none of the above, or a person's resolution says fix. The only thing a person looks at. A missing field whose
  XBRL reference has a value (`not_extracted`, T65, type 73) is open: the label names the cause (the filing tags a value
  the reader did not extract), it explains nothing; `not_reported` explains a blank only when XBRL tags nothing either.

**A label never counts as a check (T80, `status.evidence_gap`, `proof.unevidenced`).** A checked or explained row must
point at the record that makes it so; each Proof item carries `ref`, that record, and the walk fails on any item whose
`by` names nothing, or names something not on file:

| `by` | the record it must point at |
|---|---|
| `xbrl` (checked only) | an XBRL value on the row and the lookup marker (`ref.looked_up`) |
| `esef:`, `source:`, `actual:`, `rule:<id>_tie` (checked only) | that key's own value on the row (`ref.esef`, `ref.source`, `ref.actual`, `ref.tie`), never the XBRL one; an answer key never explains |
| `quote` | the quote on file for the row (the statement by its id, the planned row by ticker, text, category, year and name; the item carries ids, not the quote) found, normalised as the loaders do (curly quotes, no-break spaces, case), in the text its `text_id` names |
| `located` | the filing's income and cash-flow tables both named |
| `gate` | on the release stage only (`ref.stage`), with no block item; the stage's one item when nothing blocks (it said `located` before T80) |
| `mapping:<member>` | the entry in `taxonomy/asset_types.yaml` with that member and a `confirmed_by` that is a person (`status.is_person`) |
| `definition:<name>` | an entry by that name under the ticker in `definitions/companies.yaml` |
| `rule:<id>` (explained) | a rule in `rules/*.yaml` of info severity, or a guard in `proof.GUARDS` (a guard fills an id no rule has; a rule id on file twice is an error) |
| `resolution:<id>` | a line with that id in `decisions/resolutions.jsonl` that a person wrote: `author_kind` person when the line has the field (T69), else a `by` on `config.PEOPLE` and no "to confirm" |
| `label:not_reported`, `label:no_reference` | XBRL looked up for that row and holding no value |

**Who is a person (`status.is_person`).** Fail closed: a name on `config.PEOPLE` (the signers, today Kenny Geiler) that
names no model, agent or run (`status.NOT_A_PERSON`). `status.confirmed` uses it, so a hand edit `confirmed_by: Claude`
confirms nothing, and `mapper.person` refuses any other name on the write. T69 replaces the name with a field for
resolutions.

**The lookup marker (`ref.looked_up`).** An empty answer is only an answer when the question was asked. A value's
marker is true only when `reference_values` holds rows for its ticker (reconcile reads the same table, and with none
it writes `not_reported` over every blank); a fact's only when its filing's XBRL instance is on disk
(`proof.instance_on_file`: `data/raw/<cik>/filings/<accession>.facts.json` or `.xml`, never fetched). No marker, no
evidence: a blank whose lookup never ran is a gap, and so is an `xbrl` check.

Which labels explain, decided: only `not_reported` and `no_reference`, and only with XBRL looked up and empty. That is
reconcile's own definition (`ledger/reconcile.py`): `not_reported` means the 10-K has no line and XBRL tags no value
either, `no_reference` means XBRL has no value to compare. A label with an XBRL value behind it is a check that did not
happen, so it is a gap; a label whose row never asked XBRL is a gap too. Every other label (`not_extracted`,
`to_confirm`, anything new) names a cause and explains nothing. One known way reconcile can still write `not_reported`
over an XBRL value: a negative computed opex (operating income holding fair-value gains, type 65; T102 gives it its own
label, shown open, for a person to decide). No row of the six has it today. Since T81 `status.of_value` itself opens a
`not_reported` row unless its `ref` says XBRL was looked up and is empty, so such a row is open, not a gap; the walk
still fails any explained state over it that bypasses `of_value`.

**Failures are never explanations.** The exceptions a loader writes when a stage failed (`extraction_failed`,
`note_extraction_failed`, `ai_extraction_failed`, `projects_failed`, `proof.FAILURES`) name no rule on file. They sit
on the ingest stage, blocked or open by their severity, and never take the state of other rows (before T80 a warn
`projects_failed` with no field would have taken the worst state of every value on the values stage). None is on the
six today.

On the six today the walk finds no gap (`tests/test_status.py`, on the golden fixtures, which the test requires to
exist; the 47 mappings are open since T63, so none is checked).

**Completeness against the answer key (T81, `proof.missing_from_dataset`).** The walk above judges the rows that exist;
this asks about the ones that might not. A cell is a release field (`config.RELEASE_FIELDS`, the one list the
`coverage` rule also reads) and fiscal year in the window, not before the company's first `values` row
(`rules.first_periods`, which `coverage` and `no_10k_yet` read too), where XBRL (`reference_values`) holds a value. Its
released value is the `values` row after the review decisions (an override fills it, a reject empties it). A cell with
no released value is accounted for only when:

- the value row is open or blocked (`not_extracted`; `not_reported` over an XBRL value; a person's fix), or an undecided
  open finding names the cell (a `coverage` finding on a missing row). Both are on the Open line, so nothing is
  counted twice;
- a person's resolution on the value row explains it, or a person's review decision (accept, or a reject that emptied
  it) on a finding for the cell decided it. "A person" is `proof.person_wrote`, the one test: `author_kind` person when
  the line carries it (T69), else a `by` / `reviewer` on `config.PEOPLE` naming no model and no "to confirm".

Anything else is a silent blank: no row at all with no finding on it, a checked label with no value, a run's
resolution or decision. A ticker with no reference rows, or no `reference_values` table, is one entry, "no XBRL answer
loaded": an absent answer key is no answer (T80's lookup marker). The Release checklist's required line "Answer-key
values missing from the dataset" counts them and must read 0 to sign.

One verdict per cell: since T81 `status.of_value` explains `not_reported` only when the row's `ref` says XBRL was looked
up and holds nothing; over an XBRL value, or with no lookup, the row is open by `label:not_reported`, and the `coverage`
finding on it is open with it. `coverage` fires on every cell the line counts: the same fields, from the same first year
(a year before the company's first `values` row is left out by both; `no_10k_yet` names it). A year after the newest
10-K that is not yet due is outside both too: XBRL holds no value for a 10-K not filed.

Residual risk, authorship: resolutions and decisions written before T69 carry no `author_kind`, so a legacy line counts
as a person's when its `by` (or `reviewer`) is a name on `config.PEOPLE`. Anyone who can write that name into the log can
clear a blank; the log is in git and the name is checked against the list, never guessed.

Where it runs: on `config.SCOPE` (the six). On the six it reads 0 (golden fixtures and the live database). A one-off
reading on stage 3 (2 Nov 2026, this branch's database copy) gave 4, all "no XBRL answer loaded": SPCX, NBIS, BTDR and
ARM, companies with no 10-K read and no values rows (foreign filers or not yet public). HUT and RIOT opex FY2024 (the
negative computed opex) are no longer on the line: they are open by `label:not_reported` until T102. No test asserts
the stage-3 figure: the fixtures hold the six only.

Facts are not covered, decided. A fact's answer key is the filing's own instance, matched to the note's line by member
name; the instance tags every member on every axis for the same concepts (geography, related party, product line,
equity-method investees, corporate and eliminations). On the six, 76 of the 113 members tagged for the dimensioned
fields have no fact row, nearly all of them scope choices (country revenue, related-party splits), not omissions.
Counting them would need an axis filter and a member-to-line map per company, a classification a person would have to
confirm, so the count would be noise, not a guard. A missing fact row is caught where it is caught today: the notes
reader's `not_found` list and the mapping stage.

Precedence when more than one applies: blocked, then checked, then a person's fix (open), then explained, then open. A
warn-severity finding (a jump, a renamed line, an outlier) has no state of its own: it takes the worst state of the
rows it fired on, so a jump on a value XBRL confirms is checked, on a value a definition covers is explained, on an
unresolved value is open. Every item carries `by`: `xbrl`, `esef:<tag>`, `source:<doc>`, `actual:<period>`, `quote`,
`located`, `gate`, `mapping:<member>`, `rule:<id>`, `definition:<name>`, `label:<label>` or `resolution:<id>`.

### The four answer keys (`status.ANSWER_KEYS`, `status.answer_key(by)`)

XBRL is one kind of answer key. There are four, and `answer_key(by)` names which one a `by` (or a taxonomy row's
`check_method`) is; a quote, a located table, a mapping and every explanation are not answer keys. One function,
`status.state`, turns each into checked, so Proof and Reconcile count a row an ESEF tag confirms exactly as they count
one XBRL confirms. No row carries `esef:`, `source:` or `actual:` today (2 Nov 2026); T41–T45 write them.

- **A structured twin** (`xbrl`, `esef:<tag>`): the filer's own tagged number for the same concept and period, read
  from the instance the filer signed (the SEC's XBRL, an ESEF package). It proves the number the pipeline read from the
  document is the number the filer declared, to the unit and the sign. It cannot prove the filer is right.
- **A second source** (`source:<doc>`): the same figure stated in another document by the same filer, cited by its
  accession or id (an 8-K earnings release against the 10-K, a 20-F against the annual report). It proves the number
  is not an artefact of one document's parsing or one agent's reading; a disagreement opens an item citing both.
- **An arithmetic tie** (`rule:<id>_tie`): numbers that must sum or bound each other (quarters to the year, a
  statement's lines to its total, aligned ≤ eligible ≤ total). A tie rule is a rule, written and versioned under
  `rules/`, with an id ending in `_tie`; when it holds it is the check (`by` = `rule:quarters_tie`), when it fails it
  is the rule's finding, open or blocked until something on file explains it, never checked. It proves the parts and
  the whole were read consistently; it cannot say which one is wrong.
- **A later truth** (`actual:<period>`): the actual for a period, against what the company planned for it. The planned
  row never changes; the gap is recorded beside it. It proves what the plan was worth, not whether the plan was read
  right (the quote does that).

**The keys are graded by independence (T56, `status.KEY_GRADE`, `status.grade`, `status.strongest`).** They do not vouch
equally, because each shares a different amount of its pedigree with the number it checks. Strongest first:

1. **twin**: a separate preparer's machine-readable instance. The filer tagged the number for a different reader (the
   SEC's or ESMA's machines), by a different process, from the text the pipeline read; the two agree only when both
   read the same figure.
2. **second source**: the same issuer's other document. An 8-K release and a 10-K are written by the same finance team
   from the same ledger, so an error upstream of both documents is shared; it rules out one document's parsing or one
   agent's reading, not the issuer's own mistake.
3. **tie**: arithmetic inside the same document. Parts that sum to the whole show the pipeline read them consistently;
   a wrong figure read consistently still ties.
4. **later truth**: a later period's actual against the plan. The actual can itself be restated, and it proves what
   the plan was worth, not that the plan was read right.

`status.state` carries `keys` (every answer key that vouches for a checked row) and `key` (the strongest of them); a
row carries one `by` today, so `keys` holds at most one, and T41–T43 add ties, second sources and later truths beside
the twin without a change of shape. A failed tie carries no key: it is a finding. `proof.board()` counts the scope's
rows by their strongest key (`keys`, with `none` for every row no key vouches for and `rows` the denominator, so the
grades always sum to rows), per company and in total; Proof shows it as "Rows by answer key", and a company trail names
the key in one word beside `by`. On the six today: twin 260 of 875 rows, no key 615, the other three grades 0 until
T41–T43 write them.

Under it, "Failure types" (T54): the 72 types `docs/INGESTION.md` logged, as `taxonomy/failures.yaml` codes them, two bar charts
from `/api/v1/failures` (types per cause class; types per catching check, `none` its own bar: a known way to be wrong that nothing
guards, 45 of 72 today) with the same numbers as tables; a bar counts types, never instances, and a null count seen stays null.

Proven = zero open (blocked included), for every stage, for that company. A person's judgement enters as a definition
or a rule, never as a click on a row; once written it applies every run and the item never comes back. A resolution is
the exception for what nothing on file covers yet, and it holds only while the item's content is unchanged. It is keyed
by the item (`resolutions.key_for`: `kind|ticker|field|period|dimension|rule_id|subject`, built from the item's fields,
`%` escaped `%25` and `|` `%7C` inside a part, T62), so two findings on one field and year (two rules, or one rule on two filings) are two items with two resolutions; the
hash is the item's content without those key parts.
A `not_extracted` value (Reconcile kind `value_missing`) takes no resolution at all: it is not in `resolutions.LIVE_KINDS`,
because the fix is an extraction, not a decision; the row closes when the filing is re-read and the cell is found.
`tests/test_status.py` asserts, on the frozen fixtures, that the Proof board's open count equals Reconcile's for every
company in the proven set.

## The stages, and what proven means at each

| Stage | Item | Checked by | Explained by | Open when |
|---|---|---|---|---|
| Ingest | a filing | every statement and note table located, units from the document | a unit rule (type 48, 50, 56, 62) | a table or a unit is missing |
| Values | a value per field and year | the SEC's XBRL | a definition (cost lines, revenue line), a restatement rule, `not_reported` (no line, no tag) | `unresolved`, or `not_extracted` (no cell read while XBRL tags a value) |
| Facts | a fact per segment or category and year | the filing's instance (concept and member named) | a restatement between filings, an untagged line | `unresolved` with no explanation |
| Statements | a quote | the text it came from, verbatim | scope, period and part-year tags set by rule | a part-year or program statement without its tag |
| Mapping | a reported asset type | the us-gaap member it maps to, with the note's words and a person's `confirmed_by` (`taxonomy/asset_types.yaml`, T63) | nothing: a mapping is checked or open | a reported category with no mapping, or an entry no person confirmed (`label:to_confirm`, also a G6 failure) |
| Planned | a guidance statement, a project | the text, verbatim | part-year and program tags (types 68, 69) | never: a verbatim row is what it is |
| Release | the company's rows | the gates, per company (`release.gates`: G1 failures, G4 blocks, G5 hand-check, G6 decisions a run left to confirm and asset-type mappings no person confirmed) | resolutions written as definitions | any `blocks`, any gate row failing |

## The five

| Company | Layer | Why this one |
|---|---|---|
| Microsoft | hyperscaler | PP&E growth method; a stated ceiling (at most 50%); software and finance leases inside the category |
| Alphabet | hyperscaler | a category rename; a restatement between filings; a planning floor against a point figure |
| Amazon | hyperscaler | a category split with no restated comparative |
| Nvidia | chip seller | the seller side: stated AI revenue against a segment; no AI capex |
| Applied Digital | miner to HPC | segment accrual capex above cash capex |

`config.PROVEN` holds the list and `PROVEN_WHY` the reasons. Nothing runs across 100 until the five are proven.
The other 95 stay in the dataset as they are, marked not yet proven.

## The golden test

`fixtures/` holds, for the five, what the code stages read: the parsed tables, the texts, the distilled XBRL
instances, the documents and texts rows, and the agents' answers. `fixtures/expected/` holds the tables the code
makes from them. `ledger golden --check` rebuilds a repo layout in a temporary root (`LEDGER_ROOT`), seeds a fresh
database, runs pack and load for every stage, reconcile and the rules, with nothing fetched and no agent asked,
and compares every table with the expectation. Any change to a parser, a rule, a loader or the taxonomy has to leave
the comparison equal or change the expectation on purpose (`--freeze`, then a commit that says why).

The agents' answers are inputs here, on purpose. Whether they are good answers is the reference set's job
(`ledger eval`), kept apart from whether the code does the right thing with them.

What the first run found, before any screen was built: the loaders check quotes against task files that are
rebuilt from the texts (so the harness packs before it loads); three of the five companies' attribution rows had
been produced under the previous thesis after the switch (the proof requires every proven company rerun under
the thesis in use); and the order of a value's cost-line extraction ids was not deterministic.

## The measures (docs/TAXONOMY.md)

| Measure | What | Standard |
|---|---|---|
| spent | capex, segment capex, segment revenue | us-gaap concepts, ASC 280 |
| committed | purchase obligations, finance lease liabilities | ASC 440, ASC 842 |
| derived | the reported gross PP&E balance per asset type, mapped to a us-gaap member, and its change | us-gaap PropertyPlantAndEquipmentByTypeAxis |
| planned | guidance and projects, verbatim, forward-looking | Regulation S-K |
| company_stated_ai | a figure the company itself stated about AI, verbatim, in its own scope words | none: the company's words |

Nothing is inferred. The attribution methods that estimated an AI share, and the theses that drove them, are archived under `docs/archive/theses/` (1 Nov 2026, "invent nothing").

**Point in time, no lookahead (T55).** `values` ships the newest 10-K's figure per fiscal year and keeps the first 10-K's as `first_reported`;
a buyer who backtests on day D must see only what was filed by D, or a restated figure leaks the future into history (APLD's FY2025 revenue
moved 58% between its 10-Ks). `?as_of=D` on `/api/v1/values` and `/api/v1/taxonomy` (`ledger/pit.py`, `docs/API.md`) answers from the cells
every filing left in `extractions` and `documents.filed`, with the values builder's own arithmetic, and names the accession and filing date it
used; a year no filing by D reports is absent, never filled. `tests/test_pit.py` proves on the six that at every filing date the answer's
`filed <= D` and that today's answer equals `values`. The packet carries no as-of file: the signed dataset is shipped once, and the as-of
answer is derived from the same cells.

## DATAHQ

- **Proof** (home): the five companies down, the stages across. Each cell: checked, explained, open, as counts.
  Proven companies read as one line. Below, the other 95 in one collapsed row with their counts.
- **Company**: the proof trail. Each stage's items with their check, and for every non-match the rule or
  definition that explains it, or "open". The cited cell, the tag's concept and member, the quote, the inputs.
- **Rules**: every rule and definition, what it explains, how many items it closed in the latest run, and the
  failure type it came from. The open items of the five, grouped by what rule is missing. This is the work list.
- **Reconcile**: judgement on open items, which should be nearly empty; a judgement that would be made twice becomes a definition.
  The mapping stage's open items sit here too (the "asset types" group, T33): each unmapped reported PP&E category with the mapper
  agent's proposed us-gaap member, the note's words and a confidence; a person's Approve or Edit writes `taxonomy/asset_types.yaml`
  under their name, Reject logs the member. The stage's states do not change: a proposal is not a mapping, and the row stays open
  until the entry is written. T63: an entry already in the file without `confirmed_by` is a proposal too and sits in the same group
  ("to confirm", with the entry's member and who wrote it): Approve adds `confirmed_by` and `confirmed_at` to its line, Edit replaces
  it with the person's member (confirmed), Reject removes the line and logs the member. Each row shows the member the filer itself
  tagged for the category in its XBRL instance (`mapper.filer_members`) and flags a us-gaap member that differs from the proposal.
- **Dataset**: the grid for a consumer, marks per cell (✓ traced, ≠ differs from SEC data, ✗ disagrees with a stated figure, ! above the total, a decision as a badge), CSV export.
- **Explore**: charts on the API lists, share as a value, saved views as queries.
- **Release** (`#release`, the last page; `ledger/checklist.py`, T5–T8): the checklist a person signs from. One line per thing
  that could make the signature wrong, each green or red with its count and a link to the page that fixes it: the four
  gates per company (G1 G4 G5 G6, `release.gates`), open and blocked items in the scope (the Proof board's counts, the one
  definition of open), answer-key values missing from the dataset (T81, 0 required: an XBRL value with no released
  value, nothing open and no person's decision; a company with no XBRL answer loaded counts once), decisions a run left to confirm, unmapped asset types (0 required), rows with no value by measure
  (informs), the rows added / removed / changed per list against the previous release (informs; `DIFF.md` carries the same
  table), the golden test (`reports/golden.json`, required equal) and the last test run (`reports/tests.json`, written
  by `ledger test`: count, failures, golden, commit; absent reads "not run" and does not block; failing is red; passed on
  another commit or a dirty tree reads "stale" and informs until `ledger test` runs again), the previous
  release folders readable (a folder before this version without a manifest of the right shape or a `values.csv` is a red
  line, "previous release vX is broken: delete and rebuild", and the diff runs against the last readable one; a folder whose
  name is not a version is not a release), and the packet as
  `ledger release` would write it, built in memory with its files and hash. The version checked is the lowest unsigned
  release folder newer than the last signed one (a packet the CLI built and nobody signed is signed, not skipped; an
  unsigned folder older than a signed release was superseded and stays), else the minor bump of the last folder, or
  `?version=`. A folder that exists with a different hash reads "unsigned, built before this release's checks; delete and
  rebuild", one without `manifest.json` "unsigned, broken; delete and rebuild"; "a shipped release is never edited" is said
  only of a signed one. The Sign button enables only when every required line is green; it writes `releases/<version>/`
  whole (a temporary folder renamed into place), builds the checklist again on the folder as written and refuses if anything
  went red, signs as the name in the header's signer box (recorded as given; who may press it is a later ticket, auth),
  stores the checklist as it was in `SIGNOFF.json` under `checklist`, and publishes; a publish that fails after the signature
  is recorded there (`published: false`, `publish_error`) and stays on screen, and Proof says "signed, not published" until
  `ledger publish` succeeds. One signature at a time; a signature is never replaced. Refused with 403 on the read-only copy
  and 400 while any required line is red. `ledger release` refuses on the same checklist, so the CLI never writes a folder
  the page cannot sign. Proof's releases table reads the stored checklist back: open, unmapped and the companies in scope at
  signing; a release signed before the checklist says so.
  A release's `manifest.json` names what produced its rows (T66, `provenance`: the prompt versions per reader and the models over
  the shipped rows, the parser versions over the filings in scope, rows whose run is unrecorded, the commit built on and whether
  the tree was dirty, the sha256 of the definitions, taxonomy and resolutions files); v1.8.0 and earlier name the versions in use at
  build time, and v1.9.0's DIFF.md says so. A shipped release is never edited.
- The releases table and the golden test's last run sit on Proof; the guards, the asset-type mappings and the readers on Rules; the dataset on Dataset, as a grid by year or as the raw rows of every list. Seven pages, one file each under `ledger/pages/`, the shell in `ledger/app.html`.
