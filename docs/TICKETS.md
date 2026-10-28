# Tickets: from today's pipeline to the PRD MVP

This is the build plan for [PRD.md](PRD.md): every ticket from where the project stands to all release gates (G1–G9) and delivery checks (D1–D5) being met.

- **Owner of every ticket:** Kenny Geiler. He is accountable, resolves disputes over what a ticket means, and signs off.
- **Executor:** Claude Code, unless the status is `human`, in which case Kenny does the work himself.
- **Last reviewed:** 2026-10-27, against the 18 requirement-quality characteristics in the `make-requirements-great` skill (MIT, from prodmgmt.world's free sample). The defect log from that review is at the end.

## How to read a ticket

- **Requirement:** what must be true when the ticket is done. It is one sentence where possible, and written at solution level: naming components such as DuckDB or the CLI is intended.
- **Traces to:** the PRD item it serves. Rn = requirement, Gn = release gate, Dn = delivery check, NFR = non-functional (section 13 below).
- **Verified by:** the test or check that decides done. "Test:" means an automated test in `tests/`. "Check:" means a recorded manual check, with its result logged in the Log at the end.
- **Status:**
  - `todo`: not started
  - `doing`: in progress
  - `done`: verified
  - `blocked`: the reason is in the Log
  - `human`: Kenny does the work
- **Size:** S is under 1 hour, M is 1–3 hours, L is more than 3 hours of executor time.

## Glossary

One name per concept, used everywhere below and in the code.

| Term | Meaning |
|---|---|
| Filing | One 10-Q or 10-K, identified by its accession number. |
| Primary document | The filing's main HTML file (`primaryDocument` in the SEC `submissions` API). |
| Statement | The income statement or cash-flow statement inside a primary document. One statement can span two tables at a page break. |
| Table, row, column, cell | Parsed from the primary document's HTML. A **cell's text** is exactly what a reader sees ("(1,234)"). |
| Field | One of the 4 MVP line items: revenue, cost of revenue, operating income, capex. |
| As-stated value | A field's value for the period a column covers (three months, year to date, or a full year), in USD. |
| Quarterly value | A field's value for one calendar quarter, derived from as-stated values. |
| Reference value | The XBRL value for the same field and period, from today's pipeline. It is evidence, not truth. |
| Extraction | One agent run on one filing, producing as-stated values with citations. |
| Citation | Document, table ID, row label, column header, and cell text for one value. |
| Rule | A named check in `rules/*.yaml` with a severity: block, warn or info. |
| Exception | One rule firing on one value. (The old word "issue" is retired.) |
| Decision | A person's recorded resolution of an exception: accept, override, reject, or fix_rule. |
| Release | A versioned, signed set of quarterly values plus the reports on them. |
| Dev split / hold-out | NVDA, MSFT, CRWV are used for prompt tuning; the other 16 companies are never shown during tuning. |
| Golden set | 300 hold-out values hand-checked by Kenny. |

## Stages

Delivery is staged (PRD section 5, decided 2026-10-27): **one company, then 5, then 19.** Each stage ends in a signed release that passes every gate at that stage's size. Most tickets are built once, during stage 1, and reused. Only the hand-check and release tickets repeat.

| Stage | Companies | Built in this stage | Exit (all must hold) |
|---|---|---|---|
| **1: `v0.1.0`** | NVDA | Epics 0–7, 9, 10 at minimum size: T12, T14, T20–T23, T30–T33, T40–T45, T50–T52, T60–T61, T70–T72, T80, **T81-1**, T82, T90–T94, T100. T73, T101 and T110 are deferred. | G1–G9 pass on NVDA's 32 values. All 32 hand-checked, zero errors. Signed by Kenny. |
| **2: `v0.2.0`** | + MSFT, CRWV (dev), ORCL, APLD (held out) | T53 (prompt tuned on 3 dev companies), **T81-2**, T110 (client view), T120–T122 | G1–G9 pass on 160 values. All 64 hold-out values hand-checked, zero errors. Signed. **Must be done before the 11/12 Nov call.** |
| **3: `v1.0.0`** | All 19 | **T81-3** (300-value golden set), T73, T101, T123 | G1–G9 at full size. Stretch goal. |

## Epic 0: Foundation

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T00 | Today's pipeline code shall live in the `ledger/` package, with `python3 -m pipeline.run` still working and producing the same data. | Appendix (refactor map) | – | M | done | Check (2026-10-27): after a cache rerun, `facts.csv`, `quarterly_wide.csv`, `annual_wide.csv`, `companies.csv` and `quality.json` are byte-identical, and `dataset.json` is identical apart from pull timing. Test: the 7 existing tests pass. |
| T01 | The project shall install from `pyproject.toml` with `uv` and expose `python -m ledger <command>` for: reference, ingest, extract, reconcile, rules, review, score, release, signoff. | NFR-4 | – | S | done | Check: `uv run python -m ledger --help` lists all 9; an unbuilt command exits with code 2 and names this file. |
| T02 | `ledger/config.py` shall define the MVP universe: 19 tickers, quarters 2024Q3–2026Q2, 4 fields, the dev split (NVDA, MSFT, CRWV) and the hold-out (the other 16). | R9 | T01 | S | done | Test: `tests/test_config.py` (the splits are disjoint and cover all 19; 8 consecutive quarters). |

## Epic 1: Filing documents (R1)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T10 | The ingest step shall list every 10-Q and 10-K for the MVP companies whose report period ends from 2024-01-01 to 2026-08-31. The extra year is needed to turn year-to-date values into single quarters. | R1 | T02 | S | done | Check (2026-10-27): 177 filings (136 10-Q, 41 10-K). Low counts explained: IREN files 10-Q/10-K only since FY2025, CRWV listed March 2025, SPCX has one 10-Q. |
| T11 | Each primary document shall be fetched once, cached with its SHA-256, and never refetched while the cache exists. | R1, NFR-1 | T10 | S | done | Check (2026-10-27): 177 documents, 381.6 MB, 0 errors; a rerun made 0 network calls. |
| T12 | The table parser shall output, for each table: a stable table ID, the text above it, the stated unit and scale, column labels, row labels, and every number cell's text and parsed value. Parentheses are negative, a dash is zero, and inline-XBRL tags are unwrapped to visible text. | R1 | T11 | L | done | Test (to write): fixtures from 3 documents (NVDA 10-Q 2026-07-26, ORCL 10-K 2026-05-31, IREN 10-K 2026-06-30, which has shifted headers and a note column) assert named cells' text, value and column label. Check: no XBRL tag names appear in parser output. |
| T13 | The statement locator shall return, for each primary document, the table or tables that make up the income statement and the cash-flow statement. | R1 | T12 | M | done | Check: located in 354/354 (100%) on 2026-10-27. Still open: **correctly** located means the located income statement has a cell equal to the reference revenue for that filing's period, in at least 95% of filings. Every miss is listed in the Log. |
| T14 | Each parsed document shall be stored as `data/docs/<cik>/<accession>.tables.json` with a `documents` row (hash, parser version, table count). | R1, G7 | T12, T20 | S | done | Test: reparsing an unchanged document produces a byte-identical file. |

## Epic 2: Storage and contracts (R7)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T20 | `ledger.store.init()` shall create a DuckDB database with these tables: documents, reference_values, extractions (which carry the citations), values, exceptions, decisions, rules, runs. USD is stored unscaled. | R7 | T01 | M | done | Test: init on an empty path creates all 8 tables with the declared keys. |
| T21 | Every write to the store shall pass its table's contract: types, non-null keys, allowed values (form, label, severity, decision kind), and a unique `(ticker, field, period)` in values. | R7 | T20 | M | done | Test: one bad row per contract is rejected, and the error names the row and the broken contract. |
| T22 | The reference values for the 19 MVP companies shall be loaded from today's pipeline output, with lineage. | R4 | T00, T20 | S | done | Test: row count equals the matching rows in `facts.csv`. |
| T23 | `docs/DATA_DICTIONARY.md` shall be generated from the schema and contracts. | R7 | T21 | S | done | Test: every table and column in the schema appears in the dictionary. |

## Epic 3: Rule registry (R3)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T30 | The rule engine shall load `rules/*.yaml`, where each rule has id, description, rationale, severity, scope, and check (a named function plus parameters). It runs the rules over values and writes exceptions. | R3 | T20 | M | done | Test: two runs on the same values give the same exceptions; a rule naming an unknown check fails at load. |
| T31 | Today's 8 checks shall run as registry rules on agent values: sign, period length, jump, coverage and restated carry over; tag switch becomes row_label_switch (the agent-world equivalent); tiling becomes quarters_sum_to_ytd (independent, not circular); basis conflict is handled by the shared derivation. | R3, D1 | T30 | M | done | Test: every migrated rule passes and fails its fixtures. (Revised 2026-10-28: `validate.py` stays for the XBRL reference pipeline, which still feeds the explorer and reconciliation; the agent pipeline's checks all live in the registry.) |
| T32 | New rules shall run: citation_resolves (covers unit and scale), statement_tie, quarters_sum_to_ytd, xbrl_reconcile (tolerance: the coarser rounding of the two sources), outlier_vs_own_history, unit_from_document (warn), magnitude, and definition_note (info; added from the QA pass). Each has its rationale written in its YAML. | R3, G2, G3 | T30, T44 | M | done | Test: covered by T33. |
| T33 | Every rule shall have one fixture that passes and one that fails. | D1 | T31, T32 | M | done | Test: `tests/test_rules.py`, 14 rules × 2 fixtures + loader and engine tests (32 tests) pass. |

## Epic 4: Agent extraction (R2)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T40 | The extraction output shall follow a JSON Schema with these fields: value, unit as stated, scale, period start and end, citation, confidence, notes. Prompt v1 is stored as `agents/prompts/statements@v1.md`. | R2 | T12 | S | done | Test: the schema accepts a hand-written valid example and rejects 3 invalid ones. |
| T41 | Each filing shall get one task file holding only its located statement tables, the field list and the prompt version. It must contain no reference value and no XBRL tag name. | R2 | T13, T40 | M | done | Test: no task file contains any reference value string, or the text "us-gaap". |
| T42 | The runner shall give tasks to Claude Code subagents in batches, inside the session (no paid API). It writes outputs to `data/extract/<run_id>/` and logs one runs row per task. Finished tasks are skipped on rerun. | R2, R8 | T41, T20 | M | done | Check: one batch of 5 filings completes; rerunning the batch starts 0 new tasks. |
| T43 | An output that fails the schema shall be retried once; if it still fails, it becomes an extraction_failed exception with its cause. | G1 | T42 | S | doing | Test: injected bad outputs produce exactly one retry, then one exception each. |
| T44 | The citation resolver shall confirm that the cited table, row and column exist, the cell text matches, and the cell's value × scale = the extracted value. | G2 | T14, T40 | M | done | Test: one valid citation and 4 broken ones (bad table, bad row, text mismatch, scale mismatch). |
| T46 | Each agent run shall record the model, tokens, wall-clock time and the tool calls it made, and keep its transcript as evidence. | R2, R8 | T42 | S | todo | Check: a run's `runs` row has a non-null model and tokens; its transcript is saved under `data/extract/runs/`. |
| T47 | Prompt v2 shall require a judgement note for every row choice. Confidence is not used to route review until it has been calibrated on stage 2. | R2 | T53 | S | todo | Check: every capex value in a v2 output has a note; the review queue ignores confidence. |
| T48 | Every prompt version shall pass a repeatability test: a fresh agent on the same tasks returns identical values and citations. Run it on a sample of held-out filings at each stage too. | R9 | T42 | S | doing | Check (2026-10-28): NVDA batch C rerun by a fresh agent reading value by value: 34/34 identical. |
| T45 | As-stated values shall be turned into quarterly values with the reference logic: year-to-date differencing, Q4 = full year minus nine months, and calendar mapping by most days. | R2 | T00, T43 | M | doing | Test: the existing calendar, YTD, Q4, Costco and Nvidia tests pass when run on agent-shaped input. |

## Epic 5: Baseline and calibration

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T50 | The scorer shall report counts, rates and 95% Wilson intervals by field, company and reconciliation label. | R9 | T45, T22 | S | todo | Test: the Wilson interval matches published values for (0/300), (3/96) and (50/100). |
| T51 | A baseline run on the dev split (24 company-quarters × 4 fields) shall record: agent accuracy, review minutes per exception, exceptions per rule, pipeline time per filing, and cost per filing. | PRD §7 | T42–T45, T32, T50 | M | todo | Check: `docs/BASELINE.md` gives every number with its count and interval. |
| T52 | Every "Baseline" target in PRD section 9 shall be filled in using its stated rule, with a changelog entry. | D5 | T51 | S | todo | Check: no PRD row still reads "measured" or "set on 5 Nov". |
| T53 | Prompt v2 shall fix failures seen on the dev split only. | R9 | T51 | M | todo | Check: the dev-split rescore is equal or better; a test confirms no hold-out document is in the tuning log. |

## Epic 6: Reconciliation (R4)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T60 | Each (ticker, field, quarter) shall get one label from the agent, reference and derived values: agree, agent_wrong, xbrl_wrong, definition_gap, or unresolved. Unresolved items go to review. | R4, G3 | T45, T22 | M | doing | Test: one fixture per label. |
| T61 | Each released value shall record its source: agent, override, or missing. The agent value is used unless a decision overrides it. | R4 | T60, T72 | S | doing | Test: every row in values has a non-null source; an override decision changes the source. |

## Epic 7: Review (R5)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T70 | The review queue shall order open exceptions: severity block first, then the latest quarter, then ticker. | R5 | T30, T60 | S | todo | Test: a fixed input gives a fixed order. |
| T71 | `python -m ledger review` shall show each exception with: the cited table around the cell, the agent value, the reference value, the rule and the company's history for that field. It records a decision with reviewer, reason, timestamp and input hashes in `decisions/*.jsonl`. | R5, G4 | T70, T44 | M | todo | Check: one recorded session of at least 10 decisions. The minutes per decision feed T51. |
| T72 | A decision shall be re-applied on rerun only when its input hashes match. A later decision on the same item supersedes the earlier one, and both are kept. | R5, G8 | T71 | M | todo | Test: changing one input reopens only that item; a superseding decision wins and the history shows both. |
| T73 | The explorer shall have a Review tab listing open and decided exceptions from the release database. **This is the first ticket cut if time runs short.** | R5 | T71, T110 | M | todo | Check: the tab's counts of open and decided exceptions equal the database's counts. |

## Epic 8: Golden set (R9)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T80 | The golden sampler shall produce each stage's checking sheet (for stages 1 and 2, the T83 validation page is the sheet): stage 1 is all 32 NVDA values; stage 2 is all 64 values of the 2 hold-out companies; stage 3 picks 75 hold-out company-quarters with a fixed seed. It must include the hard cases: Oracle's mistag quarter, Applied Digital's restated quarter, CoreWeave, Tesla, and a 13-week-calendar company. The output is a checking sheet with document links and empty truth columns. | R9, G5 | T02, T10 | S | doing | Test: 300 value slots; no dev-split company; every named hard case present. |
| T81-1 | Kenny shall hand-check all 32 NVDA values (about 30 minutes), recording each value's truth and where in the filing he read it. An agent may prepare the sheet but never fills in truth. | G5 | T80 | S | human | Check: 32 rows filled and initialled. |
| T81-2 | Kenny shall hand-check all 64 values of ORCL and APLD (about 1 hour), under the same rules. | G5 | T80, T53 | M | human | Check: 64 rows filled and initialled. |
| T81-3 | Kenny shall hand-check the 300-value stage-3 golden set (about 5 hours), under the same rules. | G5 | T80 | L | human | Check: 300 rows filled and initialled. |
| T83 | `python -m ledger report --stage N` shall write `reports/stage<N>-validation.html`. For every quarterly value it shows: the agent value next to the reference, the arithmetic from the cited cells, each cited cell highlighted in its parsed table, and a link that opens the SEC filing at the cited row. It also gives a hand-check checkbox and note per value, kept in the browser and exportable as JSON. | G5, R5 | T60, T44 | M | done | Check (2026-10-28): stage 1 page: 32 rows, arithmetic ✓ on every derived value, no horizontal scroll at 375 px, ticking a value updates the count. |
| T82 | The scorer shall report the golden-set error count (G5) and, for each agent error, whether any rule flagged it (G6). | G5, G6 | T81, T32, T50 | S | todo | Test: a fixture with one flagged error and one unflagged error reports 1 escape. |

## Epic 9: Release (R6)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T90 | `python -m ledger release vYYYY.MM.N` shall write `releases/<version>/`: the DuckDB file, Parquet and CSV exports, `QUALITY.md`, `DIFF.md`, `SIGNOFF.json` and a content hash. | R6 | T61, T23 | M | todo | Test: a release builds from a fixture database with every listed file present. |
| T91 | The release shall refuse to build while any of G1–G6 fails, naming each failing item. | G1–G6 | T90, T82 | M | todo | Test: one test per gate shows the refusal and the named item. |
| T92 | Two releases built from the same inputs, prompt versions and decisions shall have the same content hash. | G7 | T90 | S | todo | Test: build twice, compare hashes. |
| T93 | `DIFF.md` shall list every value that changed since the previous release, with its cause: new filing, restatement, rule change, or decision. | G9 | T90 | S | todo | Test: a seeded change appears in the diff with its cause. |
| T94 | Kenny shall sign each stage's release (`v0.1.0`, `v0.2.0`, `v1.0.0`) with `python -m ledger signoff`, which records the signer, the time and the release hash. | R6 | T91 | S | human | Check: `SIGNOFF.json` hash equals the release hash. |
| T95 | A published release shall be correctable: a new patch version (for example `v0.1.1`) with a correction notice in `DIFF.md` naming each corrected value. The old release is kept, never edited in place. | R6, principle 6 | T93 | S | todo | Test: correcting one value produces a new version; the old directory's hash is unchanged. |

## Epic 10: Observability (R8)

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T100 | The ingest, parse, extract, rules and release steps shall each write a runs row: inputs, versions, wall-clock, outcome. | R8 | T20 | S | todo | Test: a one-company end-to-end run writes at least one row per step. |
| T101 | The Admin tab shall show agent steps, failures by cause, and time and cost per filing from the release database. | R8 | T100, T110 | M | todo | Check: the tab's totals equal SQL counts on the runs table. |

## Epic 11: Client view

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T110 | The explorer shall show only released values. Each cell shows its release version, its source (agent, override or missing) and a link to its cited document location. | D2 | T90 | M | todo | Check: on 10 random cells, the version, source and link match the database; an override cell and a missing cell are visibly marked. |

## Epic 12: Known defects and handoff

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T120 | Honeywell 2025Q3 and Intuit 2025Q2 negative capex shall each have a recorded decision with the reason found in the filings. | D3 | T71 | S | todo | Check: 2 decisions in `decisions/`. |
| T121 | The S&P 100 list shall match a dated primary source for current membership. | D3 | – | S | todo | Check: the source URL and date are recorded in `ledger/config.py`. |
| T122 | Each Nasdaq-list company shall be confirmed as outside the S&P 500 as of the check date. | D3 | – | S | todo | Check: the source and date are recorded. |
| T123 | Someone with only the README shall be able to run ingest, extract, review and release for one company. | D4 | T91 | S | todo | Check: a fresh agent dry run with only the README; any gaps it hits are fixed and logged. |

## Epic 13: Non-functional requirements

| ID | Requirement | Traces to | Deps | Size | Status | Verified by |
|---|---|---|---|---|---|---|
| T130 | NFR-1: every SEC request shall carry a contact User-Agent and be spaced at least 0.15 s apart (under SEC's limit of 10 per second). | NFR-1 | – | S | todo | Test: a mocked clock confirms no two requests are closer than 0.15 s; a missing User-Agent stops the run. |
| T131 | NFR-2: no file outside `.env` shall contain the SEC contact email, or any credential. | NFR-2 | – | S | todo | Test: scan the repo, `data/clean`, `releases/` and the built explorer for the email and for key patterns. |
| T132 | NFR-3: parsing all 177 MVP documents shall take under 60 s on Kenny's laptop. Today it takes about 20 s. | NFR-3 | T12 | S | todo | Check: timed run logged. |
| T133 | NFR-4: the environment shall be reproducible from the lock file (`uv.lock`), with pinned dependency versions. | NFR-4 | T01 | S | todo | Check: `uv sync --frozen` succeeds in a fresh clone. |

## Critical path (stage 1)

T12 → T14 → T20 → T21 → T22 → T40 → T41 → T42 → T43 → T44 → T45 → T30 → T31 → T32 → T60 → T70 → T71 → T81-1 (human, about 30 minutes) → T82 → T90 → T91 → T94 (human)

The release machinery (T90–T93) can be built in parallel with extraction, against a fixture database.

## Open questions

These block correctness, so each needs an answer from Kenny.

1. ~~**IREN's units.**~~ **Decided 2026-10-27 (Kenny):** an agent may cite a unit stated elsewhere in the same filing, and it is flagged as a warning. The parser marks these `unit_source: document` and keeps the context where the unit was found; a `unit_from_document` warning rule (part of T32) raises the exception.
2. **Second reviewer.** Does anyone second-check a sample of the golden set? Without that, there is no agreement-between-people figure. (T81.)
3. **SpaceX.** It has one 10-Q in the window. Should its prior-period comparative columns count as extractable values, given they come from a filing made after the period? (T10, T45.)

## Review log (make-requirements-great, 2026-10-27)

Defects found in the first draft of this file, and how each was fixed:

| Characteristic | Defect | Fix |
|---|---|---|
| Owned | No ticket named an owner. | Named Kenny Geiler as owner of every ticket; executor named; `human` status for his own work. |
| Traceable | Tickets had no link back to the PRD or forward to a test. | Added "Traces to" (R, G, D, NFR) and "Verified by" (test or check) to every ticket. |
| Correct | T00 promised byte-identical outputs, but four outputs carry run timestamps. T12 named a Costco fixture, but Costco is not in the MVP. | T00 states exactly which files are identical. T12's fixtures are NVDA, ORCL and IREN. |
| Unambiguous / Testable | T13 counted a statement as "found" without checking it was the right one. T73, T101 and T110 were verified by "renders". | T13 must match the reference revenue. The UI tickets compare their counts and values against SQL. |
| Consistent | "Issue", "alert" and "exception" were used for the same thing. | Added a glossary; "exception" is the one term. |
| Categorised | No non-functional requirements. | Epic 13: SEC fair access, no credentials in outputs, a parse-time budget, a reproducible environment. |
| Complete | Decisions couldn't be superseded, and a release couldn't be corrected once shipped. | T72 now covers superseding decisions; T95 adds patch releases with a correction notice. |
| Cohesive | (Reviewed.) T12, T71 and T90 each bundle several steps, but each serves one intent. | Kept as one ticket each, per the skill's rule to default to not decomposing. |
| Feasible | T81 is 5 hours of Kenny's time on the critical path. | Flagged in the critical path; it starts as soon as T80 exists. |

## Log

- **2026-10-27:** Breakdown written from PRD rev 2.
- **2026-10-27:** T00, T01, T02, T10, T11 done.
  - T12: parser built; the version history shows the bugs found and fixed:
    - tables@2: currency units and year header rows
    - tables@3–5: shifted header spans
    - tables@6: group headers
  - T13: locator finds 354/354 statements, including 5 split across two tables (IREN, TeraWulf); the correctness check is still open.
- **2026-10-27:** Tickets reviewed against `make-requirements-great` and rewritten (see the review log).
- **2026-10-27:** T13 correctness check: 170/177 = 96.0% of located income statements contain the reference revenue for their period (bar: 95%), so T13 is done. The 7 misses are follow-ups for T12, to be confirmed before extraction:
  - APLD 10-K 2024-05-31 and 10-Qs 2024-08-31, 2024-11-30, 2025-08-31: probably restatement, since the reference holds restated revenue while the original filing shows the old figure. Not a locator error, but unconfirmed.
  - CRWV 10-Qs 2025-03-31 and 2025-06-30: the parser read the scale as thousands. Suspected unit-detection error.
  - IREN 10-K 2025-06-30: no unit found (open question 1).
- **2026-10-27:** Decisions from Kenny: (1) units stated elsewhere in the filing are allowed, with a warning; (2) delivery is staged: 1 company (NVDA), then 5, then 19.
- **2026-10-27:** T13 recheck with `scripts/check_locator.py` (parser tables@7): 176/177 = 99.4%.
  - The CRWV and APLD "misses" were not locator errors. The reference holds a later 10-Q's comparative, rounded to millions (CRWV), or a restated value (APLD). So the match tolerance is now the coarser rounding of the two sources, and restated references also match on their original value. The same tolerance goes into the `xbrl_reconcile` rule.
  - Remaining miss: IREN 10-K 2025-06-30, where the locator picks an MD&A quarterly-results table over the real statement. IREN is a stage-3 company; fix before stage 3.
  - 3 IREN statements take their unit from elsewhere in the document (`unit_source: document`).
- **2026-10-28: Stage 1 (NVDA) data path runs end to end.**
  - T12 done: 9 parser tests on committed fixtures from real NVDA, ORCL and IREN filings.
  - T20–T23 done: one schema in `ledger/store.py` drives the DDL, the write contracts (12 tests) and `docs/DATA_DICTIONARY.md`. The citations table was folded into extractions, so there are 8 tables.
  - T14 and T22 done: `python -m ledger ingest --stage 1` parses 11 NVDA filings (a rerun is byte-identical) and loads 32 reference values.
  - T40–T42 and T44 done: 11 tasks run by 3 Claude Code subagents in about 30 s each, giving 130 values. Every citation resolved: table, row, column, cell text, unit and sign.
  - T45 and T60 working: `python -m ledger reconcile --stage 1` produces **32/32 quarterly values that agree with XBRL**.
  - Still open:
    - T43: the automatic retry-once is not built; today the runner (me) re-dispatches by hand.
    - T45: needs its own test on agent-shaped input.
    - T60: the agent_wrong / xbrl_wrong / definition_gap labels only arise in review, and NVDA produced none.
  - **Finding for prompt v2 (T53):** all 3 agents wrote a small script to copy cells from the task tables instead of reading value by value. This is fine for exactness (no typing errors), but "which row is capex" was decided once per agent in code. On cleaner filings like NVDA that's invisible; on messy ones it could repeat one wrong choice across every value. Stage 2 should measure this; options are per-filing judgement notes, or a second agent that checks row choices.
  - **Agent accuracy so far:** 32 agree out of 32, on the tuning company. That is not a generalization claim (PRD section 5, stage 1).
- **2026-10-28:** T83 added and done. Kenny asked for a visual way to validate the data, so `reports/stage1-validation.html` now exists:
  - charts of agent vs XBRL for each field
  - all 32 values with their arithmetic and highlighted source cells
  - deep links into the SEC filings
  - the hand-check checkboxes for T81-1, exported as `stage1-handcheck.json`

  The links use Chrome text fragments to jump to the cited row. They were not tested against sec.gov from here; if a fragment misses, the filing still opens at the top.
- **2026-10-28: QA pass with the newly installed plugins** (see `docs/QA-stage1.md`).
  - The Data plugin's `validate-data` checklist was applied to NVDA. Everything is correct; the verdict is "share with caveats": capex includes intangibles, and stage 1 is the tuning company. It also found that a quarters-sum-to-year check is circular, so the independent check is now three-month cells vs. the filing's nine-month cell (12/12 pass), plus an income-statement tie from the parsed tables (35/35).
  - The Agent Evaluation acceptance review passed coverage (130/130), citations, notes and repeatability (34/34 identical on a fresh rerun). It failed on evidence (no model, tokens or transcript kept) and on calibrated confidence; T46–T48 were added.
  - Neither plugin was callable in this already-running session (plugins load at session start). The Data plugin's skill text was applied directly; Agent Evaluation was applied from its description.
- **2026-10-28: T30–T33 done.** 14 rules in `rules/*.yaml`, each with a rationale and owner; engine in `ledger/rules.py`; `python -m ledger rules --stage 1` gives 0 block, 0 warn, 1 info (the capex definition note). `reconcile` no longer writes exceptions; the registry is their single source. 71 tests pass.
