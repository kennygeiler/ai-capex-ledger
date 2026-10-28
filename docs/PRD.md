# PRD: an agent-read dataset someone stands behind

**Owner:** Kenny Geiler · **Updated:** 28 Oct 2026 · **Target:** stage 2 released before the 11/12 Nov call

## Goal

AI agents read SEC 10-K filings and extract revenue, capex and opex, citing the exact cell for every number. Code checks every citation, rules encode judgement, XBRL serves as an answer key, and a person reviews and signs each release. This is the job the Arctal role describes: the agents do the reading, and a person stands behind the data.

## Scope

- **Data:**
  - **Source:** 10-K filings only. Each value is one cell (or, for opex, three cells of the same column). No quarterly arithmetic.
  - **Fields:** revenue, capex, opex. Definitions in [FIELDS.md](FIELDS.md).
  - **Years:** FY2022–FY2026, each company's own fiscal year.
- **Companies:** staged. A stage starts only when the previous release is signed.

| Stage | Companies | Prompt | Release |
|---|---|---|---|
| 1 | NVDA | tuned here | `v0.1.0` |
| 2 | + MSFT, CRWV (tuning); ORCL, APLD (held out, run once with the prompt frozen) | `statements@v1`; ORCL and APLD re-read with `v2` to classify cost lines (a definition change, not tuning) | `v0.2.0` |
| 3 | all 19 | frozen | `v1.0.0` |

**Not doing:**
- quarterly data
- a hosted service

## Principles

1. **An agent never has the last word.** A value ships only when it passes the rules or a person decides it.
2. **No citation, no value.**
3. **Judgement is written down.** Every rule and every decision has a reason a stranger can read.
4. **Disagreement is a signal.** If the agent and XBRL disagree, it is never averaged. Code labels a disagreement whose cause it can name; a person decides the rest.
5. **Same inputs, same output.** The release hash is reproducible.
6. **Measured, not claimed.**
7. **Every finding changes the pipeline.** It ends as a definition, a rule, a code or prompt change, or a recorded decision, logged in [INGESTION.md](INGESTION.md). A decision made twice becomes code.

## Release gates (the release command refuses otherwise)

| Gate | Requirement |
|---|---|
| G1 | Every filing ended in valid agent output or a logged failure, and no failure is open. |
| G4 | No blocking exception without a current decision (reviewer, reason, input hash). This covers citations and XBRL disagreements, because both are blocking rules. |
| G5 | Every released value hand-checked against its filing, at the value being released. |

These hold by construction:
- A rerun gives the same hash.
- A decision re-applies only while its inputs are unchanged.
- `DIFF.md` lists every change since the last release.

## Metrics

| Metric | Target | Source of target | Measured by |
|---|---|---|---|
| Cells read correctly (vs the XBRL fact for the same filing and period) | report, with 95% bound | baseline | `scripts/score_cells.py` |
| Injected misreads that escape every rule | 0 | definition | `ledger faults` |
| Released values hand-checked, errors found | 0 | definition (G5) | `golden/stage<N>-handcheck.json` |
| Fresh-agent rerun identical | 100% | definition | `scripts/compare_outputs.py` |

## Risks

- **A misread with a valid citation.** For example, the right row in last year's column, or a neighbouring line. Rules catch it by comparing columns and filings. On a company's first filing, `row_label_switch` has nothing to compare against.
- **XBRL is not truth.** Filers mis-tag, and APLD's XBRL reflects an older presentation than its newest 10-K. A disagreement is labelled and decided, never auto-resolved.
- **Definitions differ by company.** NVDA's capex line includes intangibles, and Oracle has no cost-of-revenue line, so its cost lines are classified and added, as standard tools do. `definition_note` and `cost_lines_summed` put these in front of a person, once per company.
- **Review fatigue.** If a person sees items code could have explained, they start approving without looking. Only surprises and judgement calls reach a person ([INGESTION.md](INGESTION.md)).
- **Agent cost.** Extraction runs as Claude Code subagents inside the session, with no paid API. Headless runs need `claude login`.

## History

The quarterly design (10-Q plus 10-K) and its signed `v0.1.0` live in tag `quarterly-v0.1`. On 28 Oct 2026 the project changed to 10-K only, because building quarters needs year-to-date arithmetic that mixes bases across restatements.
