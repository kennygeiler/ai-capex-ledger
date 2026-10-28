# PRD: From "a pipeline that runs" to "a dataset someone stands behind"

**Status:** draft for review · **Owner:** Kenny Geiler · **Date:** 2026-10-27 · **Target:** stage 2 (5 companies) before the 11/12 Nov call; stage 3 (19) stretch

## 1. Summary

Capex Ledger today pulls already-structured XBRL from SEC EDGAR, cleans it well, and shows every number's source. That is good data engineering. It is not yet what Arctal sells, for three reasons:

1. **The hard part is skipped.** XBRL is machine-readable already. Arctal's documents (fund reports, regulatory filings, investor letters) were never meant to be machine-read, so agents have to read them.
2. **Nobody stands behind it.** The pipeline raised 390 issues on the last run (2 errors, 77 warnings, 311 info). None has a decision recorded against it. There is no release, no sign-off, and no record of who accepted what.
3. **Judgement lives in code branches,** not in rules a reviewer can read, change and audit.

This overhaul turns the project into an **agent-led extraction pipeline with a data owner in the loop**:

- AI agents read the filing documents themselves (the 10-Q/10-K HTML, then PDFs) and extract revenue, capex and opex, with a citation to the exact table cell.
- Validation rules encode judgement.
- Exceptions go to a review queue.
- Data ships as a versioned, signed-off release.

EDGAR gives this project an advantage most extraction teams don't have: **XBRL is a free answer key.** Every number the agents read from a document can be scored against the XBRL value the company filed for the same number. That makes extraction accuracy measured, not claimed.

## 2. Where we are vs. where this needs to be

| Dimension | Today | Arctal-grade |
|---|---|---|
| Source | XBRL facts from `companyfacts` (pre-structured) | Agents read the filing document. XBRL is used only to score them. |
| Extraction | Deterministic tag lookup and arithmetic | Agent extraction to a fixed schema. Each value carries a citation (document, page or section, table, row, column, quoted text), the unit and scale as stated, and a confidence. |
| Validation | 8 checks hard-coded in `validate.py` | A rule registry: each rule has an ID, severity, rationale, owner, and whether it blocks a release. Rules are versioned and tested. |
| Exceptions | Listed in a table; never resolved | A review queue. Every blocking exception gets a decision (accept, override with value, reject) with a reason and a reviewer. Decisions are kept and re-applied on reruns. |
| Release | Whatever the last run produced | Versioned releases (`v2026.11.0`) with a diff against the previous release, a quality report, and a named sign-off. Nothing ships with an unresolved blocking issue. |
| Storage | JSON and CSV files | DuckDB with schema contracts (types, units, keys, allowed values), queryable in SQL. CSV and Parquet are exports. |
| Proof of quality | Spot checks against known figures | A hand-verified golden set, plus scoring against XBRL on every run, with field-level accuracy per release. |
| Observability | HTTP request log | Per-agent-step log: input document, prompt version, output, tokens, latency, retries, cost, validator results. |
| UI | Explorer for analysts | A **review console** for the data owner, plus the explorer as the client view, which shows only released data. |

What stays: the EDGAR ingest, caching with SHA-256, the calendar-alignment rules, the restatement handling, the lineage model, and the explorer. These become the reconciliation layer and the client view.

## 3. Users and jobs

- **Data owner (Kenny / the role).** Decides whether the data is right. Needs to see what the agents extracted, why a rule fired, and what changed since last release, then make a recorded decision fast.
- **Client analyst (asset manager, bank, data firm).** Needs a number they can trust, its source in one click, and a clear note when something is estimated, restated or missing.
- **Agent operator (also the role).** Runs and debugs the fleet. Needs to know which prompt version produced which value, where agents fail, and what a run costs.

## 4. Principles

1. **An agent never has the last word.** An agent's value ships only when it passes the rules or a person decides it.
2. **No citation, no value.** A number without a document location is dropped, not shipped.
3. **Judgement is written down.** Every rule and every override has a reason a stranger can read.
4. **Disagreement is a signal.** If the agent, XBRL and arithmetic disagree, the item goes to review. It is never averaged or silently resolved.
5. **Same inputs, same output.** A rerun on the same documents, prompts and decisions gives the same release, byte for byte.
6. **Measured, not claimed.** Every quality statement in the release notes comes from a number the pipeline computed.

## 5. Scope

### Delivery stages (decision, 2026-10-27)

The MVP is built one company first, then 5, then all 19. Each stage is a full release that passes every gate in section 8, with the gate sizes scaled to the stage. A stage starts only when the previous stage's release is signed.

| Stage | Companies | Values (8 quarters × 4 fields) | Hand-checked | What the release can claim | Release | Target date |
|---|---|---|---|---|---|---|
| **1** | NVDA | 32 | **All 32** (about 30 minutes) | "Every released value was checked against the filing." Proves the machinery end to end. It says nothing about other companies, because the prompt was tuned on this one. | `v0.1.0` | 2 Nov |
| **2** | + MSFT, CRWV (dev); ORCL, APLD (held out) | 160 | All 64 hold-out values, plus the 32 from stage 1 | First generalization test: prompts tuned on NVDA, MSFT and CRWV only, then run once on ORCL (May year-end, mistagged XBRL) and APLD (restated history). Zero errors in 64 hold-out values puts the 95% upper bound at 3/64 ≈ 4.7%. | `v0.2.0` | 6 Nov |
| **3** | All 19 | ~590 | 300-value hold-out golden set | "Released error rate under 1%, with 95% confidence" (rule of three). | `v1.0.0` | 10 Nov (stretch) |

**Why NVDA first:**
- It has a January fiscal year, so calendar mapping is exercised from day one.
- It is the reference company in the summary.
- Its statements parse cleanly.

The goal of stage 1 is to prove every part of the pipeline works once, not to find hard cases. **Stage 2 must be done before the 11/12 Nov call.** Stage 3 is a stretch goal; if it isn't done, the call presents the 5-company release and the plan for 19.

### MVP (stage 3 end state)

- **Universe:** the 19-company AI set.
- **Periods:** 8 quarters (Q3 2024 to Q2 2026), about 150 filings.
- **Fields extracted by agents from the primary 10-Q/10-K document:**
  - revenue, cost of revenue and operating income (income statement)
  - capex (cash-flow statement)
  - the statement's stated unit (thousands or millions) and the period column
- **Agent step:**
  - Claude Code subagents run within the subscription (no paid API calls; see risks).
  - Output is fixed JSON with a citation and the verbatim cell text.
  - A prompt version is recorded on every value.
- **Reconciliation:**
  - Each agent value is compared with the XBRL value for the same concept and period.
  - A match within the stated rounding passes.
  - A mismatch goes to review, labelled as agent error, XBRL error, or definition difference.
- **Rule registry:** move today's 8 checks into `rules/*.yaml` and add 6 new rules (listed in R3).
- **Review queue:** a CLI first (`python -m ledger.review`), plus a review tab in the explorer.
- **Decisions:** stored in `decisions/*.jsonl` in git.
- **Release:**
  - `python -m ledger.release` builds `v2026.11.0`: a DuckDB file, Parquet and CSV exports, a quality report, a diff, and a sign-off record.
  - It refuses to build while any blocking issue is unresolved.
- **Golden set:** 75 company-quarters × 4 fields (300 values), held out from prompt tuning and hand-checked against the filing documents, in `golden/`. The size comes from the claim it has to support (section 7). Estimated effort is about 5 hours at about 1 minute per value.
- **Client view:** the explorer reads only the latest release and shows release version, review status and citation on every cell.

### Phase 2

- The S&P 100 (all 113 companies).
- A truly unstructured source with no XBRL answer key:
  - capex guidance from earnings press releases (8-K exhibit 99.1)
  - then fund shareholder reports (N-CSR), which are the closest EDGAR match to Arctal's fund-report work
- Two-agent extraction with disagreement routing, for fields that have no answer key.
- Segment and data-centre revenue (dimensional facts).
- Finance-lease capex: new right-of-use assets under finance leases.
- A scheduled refresh after each earnings season, with an automatic release diff.

### Not doing

- A production service, auth, or multi-tenant hosting (engineers' job).
- Manual extraction. People review and decide; they do not type in numbers, except as a recorded override.

## 6. Requirements

**R1. Document ingestion**
- Fetch the primary document for each 10-Q/10-K from the `submissions` API's `primaryDocument` field. Cache it with SHA-256, as the XBRL is today.
- Turn it into page-addressable text plus tables, keeping each table's caption and its unit line ("in millions, except per share").
- Record the parser version.

**R2. Agent extraction**
- One task per filing and field family. The input is the parsed statement tables plus a fixed instruction set. The output follows this JSON schema:
  - `value`
  - `unit_stated`
  - `scale`
  - `period_start`
  - `period_end`
  - `citation`: document, table ID, row label, column header, and the verbatim cell text
  - `confidence`
  - `notes`
- Instructions are versioned files (`agents/prompts/<field>@vN.md`).
- Every run logs the prompt version, model, tokens, latency and retries.
- A schema-invalid output is retried once, then becomes an `extraction_failed` exception. It never becomes a guess.

**R3. Validation rule registry**
- Each rule declares: ID, description, rationale, severity (block, warn or info), scope, and a test fixture.
- Today's 8 checks move over unchanged.
- New rules for the MVP:
  1. **unit_scale:** the agent's value equals the verbatim cell text × the stated scale.
  2. **statement_tie:** revenue − cost of revenue − operating expenses = operating income, within rounding.
  3. **ytd_consistency:** Q1 + Q2 + Q3 + Q4 = the 10-K full year (today's tiling check, now blocking).
  4. **xbrl_reconcile:** the agent's value matches XBRL within the stated rounding.
  5. **peer_outlier:** capex ÷ revenue is outside the company's own 8-quarter range by more than 2×.
  6. **citation_present:** every value has a citation that resolves to a cell that exists.
- Each rule has a unit test with a passing and a failing fixture.

**R4. Reconciliation**
- For each (company, field, period): line up the agent value, the XBRL value and the derived value (YTD difference or Q4 as full year minus nine months).
- Classify the result: `agree`, `agent_wrong`, `xbrl_wrong` (for example the Oracle full-year mistag), `definition_gap` (for example extension tags or finance leases), or `unresolved`.
- The release value comes from the agent unless a decision says otherwise. XBRL is evidence, not the default.

**R5. Review queue**
- A queue of exceptions ordered by severity, then client impact (the AI set first, latest quarter first).
- Each item shows:
  - the cited table cell (as an image crop or the rendered table)
  - the agent output and the XBRL value
  - the rule that fired and the history for that company
- Each decision is one of:
  - `accept`
  - `override(value, reason)`
  - `reject(reason)`, which ships the value as missing, with a reason
  - `fix_rule`, which links to a rule change
- A decision records the reviewer, the time, and the input hashes, so it is re-applied only if the inputs haven't changed.

**R6. Release and sign-off**
- A release includes:
  - the DuckDB file with tables `facts`, `citations`, `exceptions`, `decisions`, `rules` and `runs`
  - Parquet and CSV exports
  - `QUALITY.md`: coverage, accuracy against XBRL and the golden set, open warnings, and every override
  - `DIFF.md`: changed values, with old value, new value and reason
  - `SIGNOFF.json`: who signed, when, and the release hash
- The release fails if any blocking exception has no decision, if citation coverage is below 100%, or if any release gate in section 8 is false.

**R7. Storage and contracts**
- DuckDB schema with types, units (USD, not scaled), keys `(ticker, field, period)`, and enum checks.
- `ledger.contracts` validates every table before writing.
- A data dictionary is generated from the schema.

**R8. Observability**
- A `runs` table records every pipeline and agent step: inputs, versions, cost, tokens, latency, outcome.
- The Admin tab gains views for agent steps, failures by cause, and cost per filing.

**R9. Evaluation**
- **Golden set:** 75 company-quarters (300 values) from the 16 companies outside the dev split. It deliberately includes the known hard cases: Costco's 16-week quarter, Oracle's mistag, Applied Digital's restatement, Nvidia's January year-end, CoreWeave, Tesla.
- **Dev split:** the 3 baseline companies (24 company-quarters), the only data used to tune prompts.
- **On every run:** score against the golden set and XBRL, per field and per company, with 95% confidence intervals. A regression on the golden set fails CI.

## 7. How the targets are set

A target with no reason behind it invites gaming, or gets ignored. Every number below comes from one of four sources, and each row says which:

- **Definition.** The target follows from a principle in section 4, so anything short of it is a defect. Example: a value without a citation breaks principle 2, so citation coverage must be 100%.
- **Statistics.** The target is the sample size or result needed to support a stated claim. Example: to say "released error rate is under 1%" with 95% confidence after finding zero errors, you must check at least 300 values. This uses the rule of three: zero errors in *n* values puts the 95% upper bound at about 3/*n*.
- **Budget.** The target follows from a stated constraint, such as reviewer hours. The assumptions are written out so they can be argued with.
- **Baseline.** There is no honest way to pick the number in advance. It is measured on a baseline run (milestone 4 Nov). The target is then frozen by a stated rule on 5 Nov and recorded in this document's changelog. Until then, the PRD says "measured," not a made-up number.

**Sizes these rest on.** The MVP has 147 company-quarters: 18 companies × 8 quarters, plus SpaceX's 3. At 4 fields that is about **590 values**. Any accuracy number on a sample this small is reported with a 95% confidence interval (Wilson), not as a bare percentage.

**Hold-out.** Prompts are tuned only on a *dev split*: the 3 baseline companies. The golden set is drawn from the other 16 and is never shown to the agents or used during tuning. Otherwise the golden-set score measures memorization, not accuracy.

## 8. Acceptance criteria

### Release gates (binary; the release command fails if any is false)

| # | Gate | Source of the target |
|---|---|---|
| G1 | Every MVP filing × field ends in schema-valid output or a logged `extraction_failed` exception. Zero silent gaps. | Definition (principle 1: no unexplained output) |
| G2 | 100% of released values cite a cell in the cached document, and the cited verbatim text × the stated scale = the value. | Definition (principle 2: no citation, no value) |
| G3 | 100% of agent-vs-XBRL comparisons carry a reconciliation label (`agree`, `agent_wrong`, `xbrl_wrong`, `definition_gap`). Zero `unresolved` in the release. | Definition (principle 4: disagreement is surfaced, not averaged) |
| G4 | Zero blocking exceptions without a decision (reviewer, reason, input hashes). A test proves the release command refuses otherwise. | Definition (principle 1) |
| G5 | **Zero errors in released values on a golden set of at least 300 values** (75 company-quarters × 4 fields), hand-checked against the filing. This supports "released error rate under 1%, with 95% confidence." | Statistics (rule of three: 3/300 = 1%) |
| G6 | **Zero escapes on the golden set:** every agent error in the golden set was flagged by at least one rule before review. An unflagged error is one that would reach a client. | Definition. Measured against the golden set because XBRL can be wrong too. |
| G7 | Two reruns on the same cached inputs, prompt versions and decisions produce the same release hash. | Definition (principle 5) |
| G8 | Deleting outputs and rerunning re-applies every decision whose input hashes are unchanged. Changing one input reopens only that item. | Definition (principle 5) |
| G9 | `DIFF.md` lists every value that changed since the previous release, with its cause. Checked by a test that seeds a known change. | Definition (principle 3: changes are explained) |

### Delivery criteria (checked once at MVP sign-off)

- **D1. Rules are in the registry.** All 14 rules are YAML, each with a passing and a failing fixture test, and the hard-coded checks are deleted.
- **D2. The client view is honest.** The explorer shows only released data. Every cell shows its release version and links to the cited document location. Overridden or missing values are visibly marked.
- **D3. Known defects are closed:**
  - Honeywell 2025Q3 and Intuit 2025Q2 negative capex: decided and documented.
  - Current S&P 100 membership verified, with a source and date.
  - The Nasdaq list checked for 2026 S&P 500 additions.
- **D4. Someone else can run it.** Someone with only the README runs ingest, extract, review and release on one company.
- **D5. Calibrated targets are frozen.** Every "Baseline" row in section 9 has a number, the rule that produced it, and the baseline data behind it, recorded by 5 Nov.

## 9. Success metrics

| Metric | Definition | MVP target | Source of the target |
|---|---|---|---|
| Released error rate | Wrong values ÷ checked values on the held-out golden set | 0 of ≥ 300 (95% upper bound < 1%) | Statistics, see G5 |
| Escape rate | Agent errors no rule flagged ÷ agent errors, on the golden set | 0 | Definition, see G6 |
| Agent accuracy before review | Values matching the checked truth ÷ all values, reported with a 95% CI | **No target.** Reported, and must not fall from baseline across prompt versions (a regression check, not a goal). | Baseline. Review catches agent errors, so a high pre-review number isn't the goal; what matters is that misses are caught (escape rate) and cheap to fix (exception rate). |
| Agent–XBRL agreement | `agree` labels ÷ all comparisons, with a 95% CI | **No target.** Reported, broken down by label. | A pass/fail threshold would punish the agent when XBRL is the one that's wrong (e.g. Oracle). The release gate is G3 instead. |
| Review minutes per exception | Median time from opening an item to recording a decision | **Measured** on the baseline run | Baseline. It feeds the exception-rate budget below. |
| Exception rate | Values sent to a person ÷ all values | **Set on 5 Nov** = review budget ÷ (minutes per exception × 590 values) | Budget. Assumption: 3 reviewer-hours for the MVP release. Example: at 2 min per exception, 180 min ÷ (2 × 590) ≈ **15%**. |
| Exception rate at Arctal scale (projection) | Same formula at 100k documents | Reported as a projection, not a target | Budget. Assumptions to confirm with Arctal: ~20 values per document, one reviewer at ~1,500 hours a year. At 2 min per exception, one reviewer can clear ~45,000 exceptions a year ≈ **2.3%** of 2M values. This shows why per-rule precision matters at scale. |
| Rule precision | For each rule: alerts that were real problems ÷ all alerts | **Reported per rule. No % target in the MVP.** Demotion rule: a blocking rule with zero true positives across baseline and golden set is demoted to `warn`. | Baseline. With ~590 values, most rules fire only a handful of times, so a % threshold would be noise. |
| Citation coverage | Released values with a resolvable cell citation ÷ released values | 100% | Definition, see G2 |
| Reproducibility | Identical release hash on rerun | 100% | Definition, see G7 |
| Pipeline time, filing to release candidate | Wall-clock from fetching a new filing to a release candidate, excluding time waiting for review | **Measured** | Baseline. The freshness clients need is an open question for Arctal; no target until it is answered. |
| Agent cost per filing | Tokens and $ (or subscription minutes) per filing | **Measured** | Baseline. Needed for unit economics at 100k documents. |

## 10. Risks and mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Agents misread scale (thousands vs millions) or take the wrong column (three months vs year to date) | Plausible-looking numbers that are wrong by 1,000× or ~3× | `unit_scale` and `xbrl_reconcile` rules block release; the verbatim cell text is required; golden set includes YTD-only cash-flow statements |
| XBRL treated as truth when it is wrong (Oracle files a full year as a quarter) | The answer key penalizes a correct agent | XBRL is evidence, not truth: mismatches get a label; `xbrl_wrong` is a valid outcome with a recorded decision |
| Overfitting to SEC filings, which are cleaner than Arctal's documents | MVP looks better than the real job | Phase 2 adds press releases and N-CSR fund reports, which have no answer key; report accuracy separately for documents with and without an answer key |
| Rules are too noisy and reviewers start rubber-stamping | The person in the loop stops adding value | Track precision per rule; demote blocking rules with zero true positives; the exception-rate budget caps queue size per release |
| Review becomes the bottleneck at scale | Can't get from 150 filings to 100k | Route by risk: auto-accept when agent, XBRL and arithmetic all agree; people see only disagreements; measure review time from day one |
| Non-determinism from model updates | Same document, different value, no reason | Pin the model per release, record it on every value, keep cached agent outputs, rerun only on purpose |
| Cost: no paid API credits (project constraint) | Agent extraction can't run in an automated pipeline | MVP runs extraction as Claude Code subagents in-session; batch by filing; a paid API run needs a cost estimate and Kenny's OK first |
| Scope vs the 11/12 Nov call | Half-built overhaul shown at the call | MVP is 19 companies, 4 fields, CLI review; anything else is Phase 2; cut the review tab before cutting the release gate |
| Small samples make numbers look more precise than they are | A reported "98.6%" from 96 values gets over-trusted | Report every rate with a 95% Wilson interval and its count; no % targets on rules that fire only a few times |
| Prompts tuned on the golden set | The golden-set score measures memorization, and accuracy is overstated | A hold-out split: prompts are tuned only on the 3 dev companies; the golden set is never shown during tuning |
| Primary documents vary (inline-XBRL HTML, older formats, exhibits) | Parser misses tables | Record parser version; `extraction_failed` is a first-class outcome with a count per cause |

## 11. Milestones

| By | Milestone |
|---|---|
| 28 Oct | Foundation, document ingest, table parser and statement locator for all 19 (done or nearly done; shared by every stage). |
| 30 Oct | Store and contracts (R7), rule registry with today's checks (R3). |
| 31 Oct | Stage 1, NVDA: agent extraction (R2), reconciliation (R4), all 32 values hand-checked. |
| 1 Nov | Stage 1 baseline numbers recorded; calibrated targets frozen from them (D5). |
| 2 Nov | **Release `v0.1.0` (NVDA) signed**: every gate passes at stage-1 size. |
| 4 Nov | Stage 2: MSFT and CRWV added to the dev split; prompt tuned on the three dev companies. |
| 6 Nov | **Release `v0.2.0` (5 companies) signed**: ORCL and APLD run once, held out; 64 hold-out values hand-checked. |
| 10 Nov | Stretch: release `v1.0.0` (19 companies) with the 300-value golden set. |

## 12. Open questions

1. Golden set: is it hand-checked by Kenny alone, or a second reviewer for a sample? (Two reviewers lets us report agreement between people.)
2. Should the release value be the agent's or XBRL's when they agree within rounding? The draft says the agent's, so the citation points to the document a client can read.
3. Which unstructured source in Phase 2 best mirrors Arctal's work: earnings press releases (high value, messy) or N-CSR fund reports (closest document type)?
4. Is there budget for a paid API run at the Phase 2 scale? It is needed to measure cost per document honestly.
5. For Arctal: how fresh do clients need data after a filing, how many values does a typical document yield, and how many reviewer-hours a year back a dataset? These replace the assumptions in the scale projection in section 9.

## Changelog

- **2026-10-27:** First draft.
- **2026-10-27, rev 2:** Every target now names its source (definition, statistics, budget or baseline). Removed the unsupported thresholds (97% agent accuracy, 99% XBRL match, ≤5% exceptions, ≥50% rule precision, ≤24h freshness, 10 min per 100 values). The golden set grew from 160 to 300 values so that it supports a "<1% error" claim. Added a dev/hold-out split and a baseline-then-freeze step.
- **2026-10-27, rev 3:** Delivery staged: 1 company (NVDA), then 5, then 19, each a full release. Hand-check sizes and claims scaled per stage (section 5).

## Appendix: refactor map

| Today | After |
|---|---|
| `pipeline/edgar.py` | `ledger/ingest/edgar.py` (unchanged logic) + `ledger/ingest/documents.py` (R1) |
| `pipeline/xbrl_instance.py`, `normalize.py` | `ledger/reference/xbrl.py`: XBRL becomes the reference set used in R4 |
| `pipeline/validate.py` | `rules/*.yaml` + `ledger/rules/engine.py` (R3) |
| `pipeline/run.py` export | `ledger/release.py` (R6) + `ledger/store.py` (DuckDB, R7) |
| (new) | `agents/prompts/`, `ledger/extract.py` (R2), `ledger/reconcile.py` (R4), `ledger/review.py` (R5), `golden/` (R9) |
| `web/` explorer | Client view on released data + Review tab; Admin gains agent-run views |
| `tests/test_normalize.py` | Kept; plus rule fixtures, a determinism test, a release-gate test |
