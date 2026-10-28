# Stage 1 QA: NVDA (28 Oct 2026)

Two reviews of the stage 1 release candidate (NVDA, 32 quarterly values) before sign-off:

1. **Data review.** Follows the `validate-data` checklist from Anthropic's Data plugin (knowledge-work-plugins). The plugin is enabled on the account, but it was not callable in this already-running session, so its skill text was applied directly. The numbers come from `scripts/stage1_qa.py`.
2. **Agent acceptance review.** Follows the Agent Evaluation plugin's published scope: an acceptance plan, then checking agent outputs against requirements and saved evidence. The plugin's skill files were not available in this session, so this was applied from its description.

## Data review: validation report

### Overall assessment: Share with noted caveats

The numbers are right on every check we can run. The caveats below are about what the numbers mean and how far the result generalizes, not about errors.

### Methodology review

- **Question and population:** NVDA revenue, cost of revenue, operating income and capex, for calendar quarters 2024Q3–2026Q2. All 32 cells are present, with no nulls and no duplicate extractions.
- **Source:** the agents read only the statement tables of 11 primary 10-Q/10-K documents. XBRL is used only to check them.
- **Time alignment:** NVDA's fiscal quarters end in late January, April, July and October. Each is placed in the calendar quarter that holds most of its days. For example, "2026Q2" is the quarter ended 26 Jul 2026, which NVDA calls Q2 FY2027.

### Issues found

1. **[Medium] Capex definition.** NVDA has a single cash-flow line, "Purchases related to property and equipment *and intangible assets*." Most companies report property and equipment only.
   - **Impact:** NVDA's capex is not like-for-like with peers from stage 2 on.
   - **Status:** the `definition_note` rule now records it on every release.
2. **[Medium] The result does not generalize.** The prompt was written against NVDA, so 32/32 agreeing shows the machinery works, not that the agents are accurate on unseen companies. Stage 2's held-out companies (ORCL, APLD) are the first test of that.
3. **[Low] Circular check avoided.** A "quarters add up to the full year" check is circular here, because Q4 is derived as the full year minus nine months.
   - **Fix:** the independent check compares the three-month cells with the filing's own six- and nine-month cells (rule `quarters_sum_to_ytd`).

### Calculation spot-checks

| Check | Result |
|---|---|
| Q1 + Q2 + Q3 three-month cells = nine-month cell (both read from filings) | 12/12 match |
| Revenue − cost of revenue − total operating expenses = operating income, every income-statement column, read straight from the parsed tables | 35/35 tie, within 1 table unit |
| Derived quarters (year-to-date difference, full year minus 9 months) re-add correctly | 32/32 (validation page) |
| Agent vs XBRL | 32/32 agree. Wilson 95% interval for the agreement rate: 89.3%–100% |

### Reasonableness

- **Magnitude:** every quarter has revenue, cost and capex above zero, cost below revenue, and operating income no higher than gross profit.
- **Operating margin:** ranges from 49.1% to 66.2%. The low point is the quarter ended Apr 2025, which is plausible (H20 inventory charge).
- **Capex ÷ revenue:** 1.9%–4.1%.
- **Trend continuity:** no field moves more than 2× quarter to quarter.

### Statistics (from the statistical-analysis guidance)

- 32 values is a small sample. Zero errors in your 32-value hand-check would bound the error rate at about 9.4% with 95% confidence (rule of three: 3/32). That claim is weak on purpose: stage 1 proves the pipeline, not a rate.
- Stage 2 (64 held-out values, bound 4.7%) and stage 3 (300 values, bound 1%) carry the real accuracy claims.
- **Multiple comparisons:** 14 rules run on every value. A warning or info result from one rule is a prompt to look, not proof of an error.

### Required caveats for stakeholders

- NVDA capex includes intangible assets.
- Quarters are calendar quarters mapped from NVDA's fiscal calendar.
- Stage 1 agreement is measured on the tuning company.

## Agent acceptance review

### Acceptance plan (what "accepted" means for the extraction agents)

| Requirement (source) | Evidence checked | Result |
|---|---|---|
| Every filing returns a valid output or a logged failure (PRD G1) | 11 outputs, schema check | **Pass:** 11/11 valid, 0 failures |
| Every column of each statement extracted for all four fields (prompt rule) | Expected cells from the parsed tables vs. values returned | **Pass:** 130 expected, 130 returned, 0 gaps |
| Every value cites a cell that exists, and cell × unit = value (PRD G2) | Citation resolver + rule `citation_resolves` | **Pass:** 130/130 |
| No guessing: missing lines go in `not_found` (prompt rule) | `not_found` lists | **Pass:** empty everywhere, and no field is actually missing in NVDA's statements |
| Judgement calls are explained (prompt rule) | `notes` on capex values | **Pass:** 25/25 capex values explain the intangible-assets line |
| **Repeatable:** a fresh agent on the same tasks gives the same answer | Batch C rerun by a new agent told to read value by value (no script), compared with the original scripted run | **Pass:** 34/34 values and citations identical |
| Confidence is meaningful | Confidence on identical choices across agents | **Fail (minor):** the same capex row got 0.9 from one agent and 0.95 from two others. Don't route review on confidence until it's calibrated. |
| Run evidence kept: model, tokens, time per filing, what the agent read (PRD R2, R8) | `runs` rows, outputs | **Fail:** model recorded as null; no tokens or time per filing; the agents' statement that they read only the task files can't be verified from saved evidence |

### Observed behaviour

- All three original agents wrote small scripts to copy cells instead of choosing value by value. The rerun agent read by judgement and also documented a decision the scripted runs never surfaced: it excluded a $13.0B "Groq, Inc." investing line from capex. Same numbers, but better evidence of judgement.

### Follow-ups (added to docs/TICKETS.md)

- **T46:** record model, tokens, time and the tool calls each run made; keep agent transcripts as evidence.
- **T47:** prompt v2 requires per-value judgement notes on any row choice. Confidence stays out of review routing until it's calibrated on stage 2.
- **T48:** run the repeatability test on every prompt version, and on a sample of held-out filings at each stage.

## Fault injection (`python -m ledger faults --stage 1`)

Each of the 130 real extractions was corrupted one at a time, then derivation and every rule were rerun.

| Fault | Trials | Caught by a rule | Escaped |
|---|---|---|---|
| Wrong column (a different period length) | 60 | 60 | 0 |
| Stale column (same length, a year earlier) | 130 | 130 | 0 |
| Wrong row (a neighbouring line) | 130 | 130 | 0 |
| Wrong scale (thousands vs millions) | 130 | 87 (43 have no effect on a released value) | 0 |
| Sign flip | 130 | 87 (43 no effect) | 0 |
| Misread digits | 130 | 87 (43 no effect) | 0 |

**The first run found a gap.** 8 stale-column faults were caught only by XBRL: a valid citation to a plausible prior-year number. With no answer key, those would ship. The new `column_matches_period` rule closed the gap, and nothing now depends on XBRL alone.

**Known limit:** 47 wrong-row faults are caught only by `row_label_switch`, which compares a company's filings with each other. On a company's first filing it can't fire.

## No-locator test (`extract --pack --find`)

One agent got every table in three NVDA filings (45 in the latest 10-Q) and had to find the statements itself.
- It picked the same income and cash-flow tables as the locator in 3 of 3 filings.
- It named the decoys it skipped: MD&A summaries and segment tables.
- Its 34 values and citations were identical to the original run.
