# Disciplines: the ledger audited the way each field would audit it

Written 2 Nov 2026 from seven read-only audits of the code, one per discipline, run with the `discipline-audit`
skill (`~/.claude/skills/discipline-audit/`). Evals were done first and live in [EVALS.md](EVALS.md). Every "built"
below was checked in the code; the claims repeated here that matter most were checked a second time by hand (marked
✓). Tickets already raised from this work are T62–T66 and T55b; the rest are proposals for Kenny to approve.

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

## Proposed tickets for Kenny

Overlaps across audits are merged. Numbers start at T67. "Before" means before the 11/12 Nov call.

**Tier A, before the call (about 3 builder-days):**

| Ticket | From | What | Effort |
|---|---|---|---|
| T67 Systematic faults and the XBRL-off run | MR1 | Faults that repeat one wrong choice across every year; catch rate per kind with and without `xbrl_reconcile`; escapes listed as known weaknesses | 1 day |
| T68 Limitations and methodology in every release | MR2, VP7, DQ6 | `LIMITATIONS.md` in the packet from `taxonomy/limitations.yaml` (intended use, not-for-use, survivorship, same-filer answer key, one signer, unproven companies); QUALITY.md wording fixed | ½ day |
| T69 Who made a decision, as a field | MR4 | `author_kind` person or run on every resolution; G6 reads the field, not a phrase | 2–3 hours |
| T70 Row-level provenance and derived inputs | LN1, LN2, MR6 | Every row carries prompt, model, parser, document hash, cell text, input hash; derived rows cite the prior-year input and the formula | 1 day |
| T71 One key per list, enforced | DQ2, DC4, DC3 | A stable `row_id` on taxonomy and ai_spend; content-based statement and project ids; release refuses a duplicate key | 1 day |
| T72 Versioning rule with a required bump | DC1 | Major, minor, patch written down; the checklist computes the required bump and refuses a lower one; schema version in the manifest | ½ day |

**Tier B, before the call if a slot frees:**

| Ticket | From | What | Effort |
|---|---|---|---|
| T73 The taxonomy file is the dataset's taxonomy | TX1, TX4 | `taxonomy@v2.yaml` matching what rows emit, includes and excludes per category; the release names its taxonomy hash | ½ day |
| T74 The filer's tag decides | TX2, TX3 | Store the filer's member; a mapping matches it or says why not; relation and confidence on each mapping | 1 day (with T63) |
| T75 Timeliness measured | DQ3 | Acceptance time stored; latency in QUALITY.md; checklist line that watch ran in the last 24 hours | ½ day |
| T76 Series breaks as data | VP3 | A `break` cause (discontinued ops, carve-out, fiscal-year change, transition) on rows; WDC, GEV, HUT on fixtures | 1 day |
| T77 Reviewer guide | LB6 | `docs/REVIEW.md`: each state with real examples, when an explanation becomes a rule, which causes go to which owner | 2 hours |
| T78 Agreement and an error rate from QA | LB3, LB4 | Blind re-label of 25 cells of the T53 audit (intra-rater kappa, labelled as such); right/wrong/can't-say on hand-checks; moving spot-check seed | Folds into T53 |
| T79 Benchmark against XBRL alone | MR3 | Cells both give, cells only the pipeline gives, cells where they differ and who was right | 1 day |

**After the call:** monitoring floors and a model-change gate (MR5); interpretive-field sample (MR7); validation pack
(MR8); security master (VP4); calendar alignment and currency policy (VP5, VP6); reviewer provenance and queue age
(LB2, LB5, fold into T57a and T38); scorecard by dimension and full rule catalogue (DQ4, DQ5); cross-table ties (DQ7);
IFRS and EU Taxonomy crosswalks (TX5, TX6); taxonomy ownership (TX7); per-list contracts as files, loud failure in
production views, consumer contract page (DC2, DC5, DC6); `ledger impact`, enforced source hashes, dated note evidence,
PROV export (LN5–LN8).

## Not relevant, on purpose

Collected from the audits: retrieval scoring and simulated users (no search step, no conversation); model judges (every
check is code); risk tiering (the bank tiers, the vendor supplies inputs); sensitivity on estimates (the pipeline makes
none since 2ee2e6f); pro forma figures and imputation ("invent nothing"); security-level corporate actions and ISINs
(company-level dollar flows); active learning (no model is trained on the decisions); calibration sessions and Fleiss'
kappa (one reviewer today); an OpenLineage server or SQL-parsing lineage (one process, Python transforms); streaming
delivery and schema registries (annual data, signed batches); EU Taxonomy alignment for US filers (screening criteria
are not in a 10-K).
