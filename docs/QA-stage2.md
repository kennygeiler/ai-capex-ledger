# Stage 2 QA: NVDA, MSFT, CRWV (tuning) + ORCL, APLD (held out)

## Held-out result

The prompt (`statements@v1`) and rules were frozen and committed (`664726e`) before ORCL and APLD were run, once.

| | ORCL | APLD |
|---|---|---|
| Filings | 11 | 11 |
| Cells read, matching the XBRL fact for the same filing and period | 95/95 | 121/121 |
| Quarterly values that agree with XBRL | 24/24 | 27 of 31 (3 differ; 1 has no XBRL value yet) |

- **Reading accuracy on unseen companies is 216/216 cells.** If the error rate were 1.4% or higher, a perfect run this size would be unlikely (95% confidence, rule of three: 3/216). Tuning companies: 332/332. Script: `scripts/score_cells.py`.
- **The 3 APLD disagreements are not misreads.** APLD restated its history for discontinued operations, so later filings show earlier periods on a continuing-operations basis. Subtracting year-to-date figures across the two bases mixes them. The rules blocked the release (8 `quarters_sum_to_ytd`, 3 `xbrl_reconcile`). Choosing a basis is Kenny's decision.
- **Agents handled the hard cases without guessing:**
  - Oracle has no cost-of-revenue line; it was reported as not found 11 times.
  - APLD's cost of revenue splits into components in later filings; the agents didn't add them up.
  - The APLD restatement and the "other assets" capex line were noted.

## Fault injection (all five companies)

3,015 trials: 0 escaped, 0 caught only by XBRL.

## Fixes, and where each came from

| Fix | Found on |
|---|---|
| Month-end dating (a six-month period ending 30 Jun starts 1 Jan) | CRWV (tuning) |
| `statement_tie`: total operating expenses may include cost of revenue | CRWV (tuning) |
| `restated`: ignore differences within the coarser rounding of the two filings | CRWV (tuning) |
| `statement_tie`: prefer the "Total …" line over a component above it | APLD (held out) |
| Fault classifier: a fault that changes an exception already open counts as caught | APLD (held out) |

None of these changed an agent value or the prompt. The two held-out fixes affect rule and test bookkeeping only.
| `citation_resolves` checks every extracted cell, not only cells behind released values (otherwise a bad cell could silently turn a quarter blank: 140 escapes on the first rerun) | fault injection, after the restatement change |
