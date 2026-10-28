# PRD: a pipeline that turns any company's 10-Ks into numbers someone stands behind

**Owner:** Kenny Geiler · **Updated:** 28 Oct 2026 · **Target for the 11/12 Nov call:** `v0.2.0` signed, M1 and M2 done

## Goal

Give the pipeline a ticker and it returns revenue, capex and opex for five fiscal years, each citing the exact 10-K cell it came from. Agents do the reading, code checks it, and a person spends minutes, not hours, standing behind each company.

This is the job the Arctal role describes. Success is measured by **what the next company costs**: code changes, items a person must decide, and that person's minutes. The number of companies done is not the measure. A mature pipeline adds a company with no code change, and a person sees only real surprises.

## Scope

- **Source:** 10-K filings only. Each value is one cell; opex is three cells from the same column. No quarterly arithmetic.
- **Fields:** revenue, capex, opex, as defined in [FIELDS.md](FIELDS.md).
- **Years:** FY2022–FY2026, each company's own fiscal year.
- **Companies:** the 19 in `ledger/config.py`. They are test inputs for the pipeline, not the product.
- **Not doing:** quarterly data; a hosted service.

## Milestones

Each milestone is a capability. Companies are how we test it.

| | Capability | Done when |
|---|---|---|
| **M0** ✓ | **The loop works by hand.** Agents read, code checks, a person signs. | `v0.1.0` (NVDA) signed. `v0.2.0` (5 companies) signed by Kenny, the first with the sampled hand-check. |
| **M1** | **It runs unattended.** One command takes a ticker from fetch to validation page, with agents run headless on the subscription (no paid API). | `ledger run --ticker X` on a company it has never seen produces its page with no manual step, and logs model, tokens and seconds per filing. |
| **M2** | **A new company needs no code.** The 14 unseen companies run blind with the pipeline frozen. Each failure is recorded by type, fixed as that type (never as a company), and the whole batch reruns. | A full rerun of all 19 needs no code change. The first-pass rate and every fix are in [INGESTION.md](INGESTION.md). |
| **M3** | **Review scales.** A person sees only items code can't explain, grouped by cause, and hand-checks a sample, not every value. | One decision covers every item with the same cause. `v1.0.0` (19 companies) is signed. (The sampled hand-check, G5, was pulled forward to `v0.2.0`.) |

## Principles

1. **An agent never has the last word.** A value ships only when it passes the rules or a person decides it.
2. **No citation, no value.**
3. **Judgement is written down.** Every rule and decision has a reason a stranger can read.
4. **Disagreement is a signal.** It is never averaged. Code labels a disagreement whose cause it can name; a person decides the rest.
5. **Same inputs, same output.** The release hash is reproducible.
6. **Measured, not claimed.**
7. **Fix the type, never the company.** Every finding ends as a definition, rule, code or prompt change, or a recorded decision, logged in [INGESTION.md](INGESTION.md). A decision made twice becomes code.

## Release gates (the release command refuses otherwise)

| Gate | Requirement |
|---|---|
| G1 | Every filing ended in valid agent output or a logged failure, and no failure is open. |
| G4 | No blocking exception without a current decision (reviewer, reason, input hash). |
| G5 | Confirmed on the filing, at the value being released: every value XBRL can't vouch for (it disagrees, or defines the field differently), plus 10 random values it agrees with. Confirmed means the re-read of the 10-K rendered in Chrome finds the cited text in the cited row and column (`ledger evidence`), or, where it can't, a person looks at the boxed screenshot and answers yes. A value where the 10-K cell and XBRL agree is verified by two independent sources. `QUALITY.md` states the split. |

These hold by construction: a rerun gives the same hash; a decision re-applies only while its inputs are unchanged; `DIFF.md` lists every change since the last release.

## Metrics

**Pipeline (the headline).** Measured per company, logged by `ledger run`.

| Metric | Target | Why that target |
|---|---|---|
| Code changes needed to add the company | 0 by the end of M2 | definition of M2 |
| Items reaching a person | report; each has a cause code couldn't name | definition (principle 4) |
| Person minutes to sign it off | report the trend | no baseline yet; M1 sets one |
| Agent tokens and seconds | report | cost evidence |

**Data.**

| Metric | Target | Measured by |
|---|---|---|
| Cells read correctly, vs the XBRL fact for the same filing and period | report, with a 95% bound | `scripts/score_cells.py` |
| Injected misreads that escape every rule | 0 | `ledger faults` |
| Citations moved to a neighbouring row or column that the rendered-10-K re-read misses | 0 | `ledger evidence --faults` |
| Hand-check errors | 0 found | G5 |
| Fresh-agent rerun identical | 100% | `scripts/compare_outputs.py` |

## Risks

- **Overfitting to the companies we've seen.** Rules and prompts tuned on 5 companies may break on the next 14. M2 runs them blind with the pipeline frozen, and fixes count only when the whole batch reruns.
- **A misread with a valid citation,** such as the right row in last year's column. Rules catch it by comparing columns and filings, so a company's first filing is less protected.
- **XBRL is not truth.** Filers mis-tag and use different definitions. Disagreements are labelled, and decided if code can't explain them, never auto-resolved.
- **Review fatigue.** A person shown items code could explain starts approving without looking. Only surprises and judgement calls reach a person ([INGESTION.md](INGESTION.md)).
- **Agent access.** Headless runs use `claude -p` on Kenny's subscription and need a one-time `claude login`. There is no paid API.

## History

- **Quarterly design:** the 10-Q plus 10-K version and its signed `v0.1.0` are in tag `quarterly-v0.1`. On 28 Oct 2026 the project moved to 10-K only, because quarters need year-to-date arithmetic that mixes bases across restatements.
- **Pipeline-first reframe:** also on 28 Oct, the plan moved from company stages (1 → 5 → 19) to pipeline milestones.
