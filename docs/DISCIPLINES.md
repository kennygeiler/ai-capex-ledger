# Disciplines: the ledger audited the way each field would audit it

Written 2 Nov 2026 from seven read-only audits of the code, one per discipline, run with the `discipline-audit`
skill (`~/.claude/skills/discipline-audit/`). Evals were done first and live in [EVALS.md](EVALS.md). Every "built"
below was checked in the code; the claims repeated here that matter most were checked a second time by hand (marked
✓). Tickets already raised from this work are T62–T66 and T55b; the rest are group K below (T67–T99), approved by Kenny on 2 Nov.

## Why do this

Each layer of the system has a field that already decided what "good" looks like, with a checklist practitioners
agree on. Mapping the ledger against those checklists finds what the builder would not think to look for, and the
items marked "not relevant, on purpose" show the checklist was read, not skimmed. For Arctal it shows range: the
dataset judged by a bank's model-risk team, an asset manager's data team, a data-quality office, a lineage reviewer,
a taxonomy body, a labelling-ops lead and a data-product consumer.

## The map

| Layer | Discipline | Strongest here | Most important gap |
|---|---|---|---|
| Agents | Evals ([EVALS.md](EVALS.md)) | Deterministic checks only, golden test, planted faults | No run-to-run consistency (T60); prompt changes ungated (T61) |
| Whole system, as a bank sees it | Model risk management (SR 11-7, PRA SS1/23) | Change control on prompts, golden rebuild, sign-off refused while a gate is red | Fault test plants only one-cell errors; no limitations disclosure; one person builds, decides and signs |
| Companies over time | Financial data vendor methodology | Fiscal-year labelling, 52/53-week years, units, restatement kept as `first_reported` | Old filings never checked (AT&T 1000× read as a restatement ✓); series break silently; no company ID master |
| Human decisions | Labelling operations | Append-only decisions keyed to content, keyboard flow, bulk by cause | Queue keys collide ✓ (T62); agreement between reviewers not measurable |
| The dataset | Data quality | Accuracy (70 of 71 values agree with XBRL), validity contracts, rules with owners | Amazon revenue and opex missing from v1.8.0, labelled "no such line" ✓ (T65); taxonomy rows have no unique key ✓ |
| Categories | Taxonomy governance | Every category tied to a published standard; release refuses unmapped rows | All 47 asset-type mappings written by a model and counted as checked ✓ (T63); the yaml and the rows disagree |
| Releases and API | Data contracts | Releases rebuild byte-identical (v1.8.0 re-verified) | No versioning rule: v1.7.0 and v1.8.0 broke consumers as minor versions; removed columns return NULL silently |
| Citations | Lineage and provenance | Cell-level citations, hashed documents, rendered re-read of statement cells | Manifest names versions that did not produce the rows ✓ (T66); derived rows cite one of their two inputs |

## The root cause

The audits found one pattern under most of the bugs: **a label, or the existence of a record, stood in for a check.**
Missing evidence counted as evidence.

- A blank labelled `not_reported` counted as explained; nothing asked XBRL whether the company really reports no such
  line. Amazon's revenue and opex were missing for that reason.
- A mapping counted as checked because an entry existed; a model wrote all 47 and no person confirmed one.
- `restated` was set whenever two filings disagreed, without asking whether the older one had been read right.
- A decision counted as a person's unless its text said "to confirm".
- The manifest stated the versions in force at build time, not the ones that produced the rows.

The values that exist were checked well (XBRL twin, citations, the rendered re-read). What was never tested was the
negative space (blanks, labels, coverage) and the truth of the golden expectation itself. **The golden test is a
regression test, not a correctness test: it froze the Amazon blanks as expected.** The planted faults changed one
existing cell at a time and never planted an omission, a wrong table, or the same mistake in every year.

The rule from here: a label never counts as a check. T80–T82 make that a guard instead of five patches.

## Fixed or being fixed tonight

These were bugs in approved work, so they went straight to the builders:

- **T62 Stable queue keys.** Two findings on the same field and year shared one key, so deciding one reopened the
  other. None on the six; 21 waiting in the wider set.
- **T63 Mappings are proposals until a person confirms them.** The six companies' mapping stage was "proven" on model
  judgement alone. The proven count drops until Kenny confirms (about 15 minutes, on the morning list).
- **T64 The packet README matches the files.** v1.6.0–v1.8.0 README lists `first_reported` and `citations`; values.csv
  has neither ✓. One restatement threshold instead of three.
- **T65 A blank the SEC data contradicts is open, not explained.** The income-statement locator picked the cash-flow
  table for every Amazon 10-K ✓. 131 of 142 "not reported" cells in the database have an XBRL value ✓.
- **T66 The manifest records what produced the rows.** v1.8.0 claims `statements@v2` and `tables@15`; most rows came
  from `statements@v1` and `tables@12`.
- **T55b Every vintage checked before point-in-time serves it.** T55 ships tonight with older vintages flagged.

v1.8.0 stays as signed. Each fix lands in v1.9.0 and its DIFF.md says what changed.

## Model risk management

The lens a bank's vendor-risk team applies. The design is sound and documented (PROOF.md says what each answer key
can and cannot prove), change control on prompts is real, and every release can be rebuilt without the model. What a
validator would write up:

- The planted-fault test changes one cell at a time. An agent that picks the same wrong line in every year passes the
  label-switch and period rules and is caught only by XBRL, which 142 of 327 note facts and ASML's KPI table do not
  have. The 99% catch rate does not cover the error a bank fears most.
- Nothing compares the pipeline with the obvious alternative, XBRL alone. The value the agents add (untagged facts,
  MD&A statements) is claimed, not measured.
- The packet has no limitations section. QUALITY.md says values were confirmed "by a person where it can't"; for
  v1.8.0 no person checked one ✓. "Two independent sources" is an independent reading of two documents from the same
  filer.
- Whether a decision came from a person or a run is told apart by the phrase "to confirm" in free text. A run that
  writes a resolution without the phrase passes G6.
- No metric has a floor or alert, and a model can be swapped (`agents.set_model`) with no re-run. One model id on one
  subscription, with no written fallback.

## Financial data vendor methodology

How Compustat, FactSet and LSEG document the time and entity dimensions. Fiscal years, 52/53-week years, units and
consolidation are handled. The gaps an asset manager would hit:

- Older filings are never checked against their own XBRL, so a misread becomes a "restatement" and a point-in-time
  view would serve it (AT&T FY2022 ✓; T55b).
- Series break without a marker: Western Digital's spin-off (a fake −67%), GE Vernova's pre-spin carve-out years,
  Hut 8's fiscal-year change (six months missing).
- Totals mix fiscal calendars (Nvidia's year ends in January, Microsoft's in June) and, once ASML lands, euros with
  dollars. No currency policy is written.
- Ticker is the key; CIK appears only on documents. No LEI, fiscal-year end, reporting currency or former names in
  `companies.csv`.
- The company list was chosen for today's AI relevance, so any backtest is survivor-biased. Fine for a prototype if
  stated; it isn't.

## Labelling operations

Human review as ML data teams and data-operations QA run it. The schema is strict, decisions are append-only and
expire when their item changes, and propagation works through definitions. Missing:

- Agreement between two reviewers cannot be measured: one answer per key, the earlier reason is shown and prefilled,
  and nothing marks a blind second label. With one person, the honest measure is a blind re-label of part of the T53
  audit a few days later.
- The hand-check records only "verified", so no error rate comes out of it, and person decisions are never sampled.
  The spot-check seed is fixed, so stable data re-samples the same ten values every release.
- A decision does not record the rule or definition version it relied on, so narrowing a definition leaves earlier
  "explain" decisions green.
- No first-seen time per item, so no queue age or time to decision. No reviewer guide.

## Data quality

The standard dimensions applied to the published dataset. Accuracy and validity are strong; referential integrity
holds today, though nothing checks it.

- Completeness is mismeasured: blanks were counted as present (T65).
- `taxonomy.csv` repeats its own documented key: 25 keys, 43 extra rows ✓. Statement and project ids depend on position,
  so a rerun can renumber them.
- Timeliness is not measured. Day-level latency can be computed from stored data; acceptance time is not stored, and
  `ledger watch` last ran 28 Oct with nothing scheduled.
- QUALITY.md covers accuracy and completeness, never uniqueness, integrity or timeliness. The rule catalogue covers the
  yaml rules only, not the contracts, guards and gates that hold most of the logic.

## Taxonomy governance

As XBRL, EU Taxonomy and ICMA bodies maintain classifications. Every category names a standard and unmapped rows
refuse the release. Missing:

- The published `taxonomy.yaml` and the emitted rows disagree under the same version (the `derived` measure and the
  `ai_*` categories are missing from the yaml; two defined categories are never emitted).
- Mappings carry no relation (exact, broader, partial), no confidence, no check against a pinned us-gaap release; mixed
  labels ("computer equipment and software") are forced to one member. The filer's own tagged member is read and
  thrown away; the audit reports Amazon and Applied Digital tags that differ from the yaml (to be checked in T63).
- Releases don't name their taxonomy version, and there is no changelog.
- No crosswalk to IFRS or to EU Taxonomy activities. An honest EU crosswalk yields eligibility candidates only, needs
  additions-based capex concepts the taxonomy lacks, and can be tested against ASML's own activity-level figures.

## Data contracts

What a bank integrating the files would expect. Reproducibility is excellent. Missing:

- No versioning rule; `next_version()` always bumps minor. v1.7.0 removed files and a column; v1.8.0 removed and
  reordered columns, changed what `value_high` means and narrowed scope from 100 companies to 6.
- In Postgres, removed lists leave empty `current_*` views and removed columns return NULL: a consumer's pipeline loads
  nulls without failing.
- One of seven files has a declared schema, and none ships as a file. DIFF.md's headline counts missing values as added
  in every release.
- No owner or support contact, cadence, format guarantees (encoding, booleans, nulls), or a hash recipe a consumer can
  run without the code.

## Lineage and provenance

W3C PROV and column-level lineage. Documents are hashed (re-verified for the MSFT FY2026 10-K), every value cites its
cell, statement cells are re-read on the rendered filing. Missing:

- A derived row (`change_from_prior`) names only the current year's cells; the prior-year input and the formula are
  off the row. 1,431 of 1,992 changes subtract a balance from a different filing.
- Agent identity is the load run, not the agent call. 13 statement outputs (173 cells, including MSFT, NVDA and APLD)
  have no recorded model or task hash.
- Consumers get the document but not the cell text, prompt, model, parser version or input hash.
- No impact analysis ("if this filing or rule changes, which rows move?"). A refetch overwrites a cached document
  without comparing hashes. Note cells are never re-read on the rendered page.

## Tickets (group K): what resolves each finding

Every finding above is a ticket below, with its audit source in brackets. Overlaps across audits are merged. Order:
**K1, before the call** (the root cause and what a reviewer would find first); **K2, before the call if a slot frees**;
**K3, after the call**. Already raised and building: T62–T66, T55b. A few small items fold into existing tickets and
are listed at the end.

### K1: before the call

- **T80 A label never counts as a check.** [root cause] Every row whose state is checked or explained points at the
  evidence that makes it so: an answer key value, a quote verified against its text, a person-confirmed mapping, a
  definition or rule by id, a resolution by id with `author_kind` person. A test walks every row of the six through
  `status.state` and fails on any checked or explained row whose `by` names no evidence record, or names one that does
  not exist. Done when the test is green on the six after T63 and T65, and planting a bare label (`not_reported` with an
  XBRL value present, a mapping with no `confirmed_by`) turns it red. About ½ day.
- **T81 Completeness against the answer key.** [root cause, DQ1] For every company in scope, every field and year
  where XBRL holds a value is either in the dataset or an open item; a silent blank is a release failure. A required
  checklist line counts "answer-key values missing from the dataset" and must read 0, open items aside. Builds on T65.
  Done when the line reads 0 on the six, and deleting one extracted value in a test turns it red. About ½ day.
- **T82 A gold set separate from golden.** [root cause, LB4] Golden stays the regression snapshot ("nothing changed").
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
- **T68 Limitations and methodology in every release.** [MR2, VP7, DQ6] `taxonomy/limitations.yaml`: id, the weakness,
  rows affected (count), mitigation, the ticket that would close it. Seed: T67's escapes, "the answer key comes from the
  same filer", "one person builds, decides and signs", "N companies not proven", "the universe is today's AI-relevant
  names, survivor-biased for backtests", "45 failure types have no catching check" (T54), "interpretive fields of
  statements are unmeasured". `release.build` writes `LIMITATIONS.md` with intended use and not for use, plus cadence,
  correction policy and support contact. QUALITY.md says "re-read by machine" where no person checked and "independent
  reading" instead of "independent sources". Done when v1.9.0 carries `LIMITATIONS.md` and a checklist line counts
  entries with no mitigation. About ½ day.
- **T69 Who made a decision, as a field.** [MR4] Every resolution has `author_kind` ∈ person / run, set by the route
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

## Not relevant, on purpose

Collected from the audits: retrieval scoring and simulated users (no search step, no conversation); model judges (every
check is code); risk tiering (the bank tiers, the vendor supplies inputs); sensitivity on estimates (the pipeline makes
none since 2ee2e6f); pro forma figures and imputation ("invent nothing"); security-level corporate actions and ISINs
(company-level dollar flows); active learning (no model is trained on the decisions); calibration sessions and Fleiss'
kappa (one reviewer today); an OpenLineage server or SQL-parsing lineage (one process, Python transforms); streaming
delivery and schema registries (annual data, signed batches); EU Taxonomy alignment for US filers (screening criteria
are not in a 10-K).
