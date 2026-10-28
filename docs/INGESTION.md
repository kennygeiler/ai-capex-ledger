# Ingestion

How a 10-K becomes a released number, who looks at what, and what each stage taught us. This file is updated whenever a finding changes the pipeline.

## The flow

| Step | Done by | Output |
|---|---|---|
| 1. Fetch the company's 10-Ks; cache each with SHA-256 | code | `data/raw/` |
| 2. Parse tables; locate the income and cash-flow statements | code | `data/docs/*.tables.json` |
| 3. Read the statements: one cited cell per field and year; classify cost lines when there is no total | agent | `data/extract/outputs/` |
| 4. Check every citation against the cell | code | `extractions` |
| 5. Build fiscal-year values: newest 10-K per year, opex from one column, first-reported kept | code | `values` |
| 6. Compare with XBRL; run the rules; inject faults to prove the rules catch misreads | code | `exceptions`, `reports/` |
| 6b. Re-read every cited cell on the 10-K rendered in Chrome (row label × column header, by position); screenshot the ones a person might check, boxed | code | `reports/evidence/` |
| 7. Review what code could not explain; hand-check; sign | person | `decisions/`, `releases/` |

## Who decides what

A person's attention is the scarcest input, so it goes only where code can't name the cause.

| Kind | Example | Handled by | How often |
|---|---|---|---|
| **Policy** | opex excludes cost of revenue; the newest 10-K wins, first-reported kept | a person, once; written in [FIELDS.md](FIELDS.md) and the rules | once per project |
| **Known mismatch** | Oracle's XBRL has no cost-of-revenue tag, so its "opex" is all costs | code labels it (`definition_gap`) and shows both numbers | never a person |
| **Judgement** | is "data center rental" a cost of delivering revenue? | a person confirms the agent's classification (`cost_lines_summed`) | once per company |
| **Surprise** | APLD's FY2025 revenue moved 58% between 10-Ks | a person finds the cause (the page shows the filing's own sentence) and records it | once per surprise |

**The loop.** Every finding ends as one of: a definition in FIELDS.md, a rule, a code or prompt change, or a recorded decision. If the same decision reason comes up twice, it becomes code. Each entry below names which.

## Learnings

| Date | Found | Changed | Kind |
|---|---|---|---|
| 28 Oct | Building quarters needs year-to-date arithmetic that mixes bases across restatements. | 10-K only; quarterly work kept in tag `quarterly-v0.1`. | policy |
| 28 Oct | Opex for one year was built from two filings. | One filing per company-year (`reconcile.py`). | code |
| 28 Oct | Later 10-Ks rewrite past years (APLD, after moving a business in and out). | Newest figure used, first kept in `first_reported`, `basis` = restated (standard practice: ASC 205-20, vendor as-reported and restated series). | policy |
| 28 Oct | Oracle and APLD's newest 10-K have no total cost-of-revenue line, so opex was blank. | Agent classifies and cites each delivery-cost line (prompt `statements@v2`); code adds them; `cost_lines_summed` asks a person to confirm once per company. | policy + prompt + rule |
| 28 Oct | XBRL draws cost of revenue differently (Oracle: no tag; APLD FY2026: one of two lines). 6 blocking items, one cause. | When revenue and operating income agree, an opex gap is labelled `definition_gap`, not raised. | code |
| 28 Oct | Agents read tables only, so they can't see why a restated year changed. | The page shows the 10-K's own sentence ("recast…", "previously reported…") with a link (`ingest/notes.py`). First version matched "forecast"; fixed with word boundaries. | code |
| 28 Oct | APLD shows "—" for a cost line in years it didn't exist. | Read as 0, as in financial statements. | policy |
| 28 Oct | `row_label_switch` flagged cost lines as "different rows", which is noise, because they are several rows by design and get renamed between filings. Simply skipping them let 10 planted misreads escape (a line counted twice, or a neighbour pulled in). | For cost lines the rule checks that every year in one filing uses the same set of lines, each once. Faults: 0 of 862 escaped. Lesson: before removing a check, rerun the faults. | code |
| 28 Oct | Kenny reviewed stage 2: APLD's recast years and the ORCL and APLD cost lines. | 6 decisions recorded in `decisions/decisions.jsonl`. | decision |
| 28 Oct | Hand-checking all 66 values was too hard, and pointless where XBRL already agrees. The page also still showed decided items in red and never said what to compare. | A person checks only what XBRL can't vouch for, plus 10 random agreeing values; each is one yes/no question naming the row, column and number; decided items show who decided (`release.to_check`, G5). | policy + code |
| 28 Oct | Even 20 yes/no checks made a person hunt through a long filing for one cell. | `ledger evidence`: headless Chrome renders the real 10-K, finds the cited row and the column header above it by position (independent of our table parser), compares the text and screenshots it boxed. Stage 2: 173/173 cells confirmed; 708/708 citations moved to a neighbouring row or column noticed. A person sees only cells the machine can't confirm, with the box showing where. OCR (docling) wasn't needed: 10-Ks are born-digital HTML, so the rendered page's own text is exact. First version cut off cells past the right edge and missed a ")" in its own cell; both fixed. | code |
| 28 Oct | Headless `claude -p` failed with "token revoked": inside the desktop app it inherits the app's session variables (its own proxy and token), and `claude login` on v2.1.114 sends "login" as a chat message instead of logging in. | The agent runs with only HOME, PATH, USER and LANG, in an empty folder, with no user settings, hooks or MCP servers (so none of the user's own plugins reach the prompt). Login is `claude`, then `/login`. | code + setup |
| 28 Oct | The installed `claude` (2.1.119) can't run Opus 5.5, the model the in-session agents used. | The agent pins `claude-opus-5-5`; `LEDGER_CLAUDE` points at a newer `claude` until the installed one is upgraded. | setup |
| 28 Oct | First unattended company (AMD): no code change needed. Its only warnings are FY2026 coverage, because AMD's FY2026 hasn't ended (December year-end). | Next type to label in code (M2): a fiscal year that hasn't ended isn't missing. | finding |
| 28 Oct | The "fiscal year hasn't ended" type, fixed in code. | `coverage` skips a year after the newest 10-K until its 10-K is due (90 days after the year ends). AMD's and CRWV's FY2026 warnings are gone. | rule |
| earlier | NVDA's capex line includes intangible assets. | Used as reported; `definition_note` records it on every release. | rule |
| earlier | Some tables state their unit elsewhere in the filing. | Allowed, flagged as a warning. | policy |
| earlier | Misreads with a valid-looking citation escaped (140 in fault tests). | `citation_resolves` checks every extraction. | code |

## M2 blind run 1 (28 Oct, pipeline frozen at tag `m2-frozen`)

13 unseen companies, one command, nobody in the loop.
- **Agent:** read 26 10-Ks in about 9 agent-minutes, with 1 retry.
- **Values:** 143 of 145 agree with XBRL.
- **Faults:** 0 of 1,555 planted faults escaped.
- **Clean on the first pass:** AMZN, GOOGL, META, MRVL, MU and TSLA (no code change, nothing for a person).

Every failure, by type:

| # | Type | Where | Caught by | Fix |
|---|---|---|---|---|
| 1 | **Re-read can't see text in Workiva's positioned layout.** The browser reports the cell text as empty although it is on screen. | CORZ FY2025 10-K: 12 cells not confirmed | `evidence` | **Fixed:** read the cell's own text (`textContent`), not the browser's visible-text view. 311/311 confirmed. |
| 2 | **Locator picks a quarterly table in a 10-K.** IREN's first 10-K has a quarterly summary that looked like the income statement. | IREN FY2025 10-K: 12 quarterly values | `period_length` (block) | Proposed: in a 10-K, prefer the statement whose columns are fiscal years. |
| 3 | **The answer key picks a narrower revenue tag.** The XBRL reference chose contract revenue over the filed total `Revenues`, which leaves out lease revenue. | WULF FY2025 revenue and opex | `xbrl_reconcile` (block) | Proposed: the reference prefers the total `Revenues` tag when the company files one. |
| 4 | **Statement tie assumes a layout.** Operating lines outside "total operating expenses" (impairments, gains on sales) break revenue − cost − opex = operating income. | CORZ FY2022 | `statement_tie` (block) | Proposed: count lines between cost of revenue and operating income that sit outside the operating-expenses block. |
| 5 | **The fetch window doesn't reach the first year.** Smaller filers show 2 years, so 10-Ks from 2024 on miss FY2022. | CIFR FY2022 (also APLD, CRWV) | `coverage` (warn) | Proposed: fetch 10-Ks from 2022, and label a year before the company's first 10-K (pre-IPO, or a foreign filer before switching to 10-K, like IREN) in code. |
| 6 | **A company with no 10-K is silent.** SpaceX (SPCX) has filed an S-1 and 10-Qs but no 10-K yet. The run produced nothing and said nothing. | SPCX | nothing (the gap) | Proposed: `coverage` names every requested company with no 10-K. |

Not failures: 6 `row_label_switch` warnings are lines renamed between filings ("Revenue" → "Total revenue"), and 17 `jump` warnings are real growth. Both are working as intended.

## M2 run 2 (28 Oct, after fixing types 2–6): all 19 companies

`ledger run --stage 3`: 72 10-Ks, 59 of them read fresh by the headless agent. Results:
- 234 values: 224 agree with XBRL, 6 are labelled by code (`definition_gap`), and 4 are the APLD recast already decided.
- 857/857 cited cells confirmed on the rendered 10-K, and 3,104/3,104 moved citations noticed.
- 0 of 4,270 planted faults escaped.
- 0 items for a person. `no_10k_yet` names SpaceX and the years before CRWV's and IREN's first 10-Ks.

Two more types surfaced, both in the re-read:

| # | Type | Where | Fix |
|---|---|---|---|
| 7 | A zero-width space inside a cell's text | one FY2022 10-K | Ignored when comparing numbers. |
| 8 | A row label repeats in one table (Oracle lists "Services" under revenues and again under expenses) | ORCL FY2022 10-K | The re-read uses the row that shows the cited text. |

## Audit fixes (28 Oct): human in the loop used wisely

A Monday-morning audit of DATAHQ and the pipeline found that the answer key backing "values accounted for" was itself
wrong in places, and that a person was being asked questions code could settle. Fixed by type:

| # | Type | Where | Fix |
|---|---|---|---|
| 9 | **The answer key mixed filings within a year.** It ranked tags first and dates second, so a better-ranked tag in an older 10-K beat the newest 10-K's tag. Opex was then built from two filings (APLD FY2025 key opex: −$0.4M). | APLD FY2024–25 revenue and opex | The key takes the newest filing for the year first, then the best tag in it; opex only from one filing (`normalize.annual_series`, `derive_costs`). The 4 APLD items Kenny decided were raised by this bug; they now agree and need no decision. |
| 10 | **10-K/As were ignored.** A full amendment (CORZ FY2024: operating income −$19.2M → −$142.1M) was only covered because a later 10-K repeated it. | AMD, APLD, CORZ, CRDO, TSLA, WULF | 10-K/As are read when they carry financial statements; Part III-only amendments are skipped with the reason logged. On the same day, the more complete filing wins and both count as one vintage (AMD's partial 10-K/A). |
| 11 | **"Explained by code" had no size limit.** Opex from summed cost lines was excused whenever revenue and operating income agreed (ORCL 28–49% from the key, every year). | ORCL, APLD | `cost_lines_summed` now blocks release until a person confirms the lines, once per company, and its message shows the gap per year. |
| 12 | **Small restatements were labelled as reported.** The restated label needed a 1% change. | META FY2022–23 capex (0.8%), TSLA | Any change beyond rounding is `restated`; the size shows beside it. |
| 13 | **Capex lines narrower or broader than the definition weren't noted,** and XBRL agreed because the company tags the same line. | IREN (net of GPU prepayments), TSLA (excl. finance leases), WULF (deposits) | `definition_note` also matches "net of", "excluding", "deposit", "prepayment". |
| 14 | **Business signals were shown as chores.** 44 of 57 open warnings were capex and opex jumps and outliers: the AI buildout itself. | all | A jump, outlier or renamed line on values that agree with XBRL can't be a misread (XBRL is an independent read), so DATAHQ shows it as a finding about the company, not a question. Questions for a person went from 57 to 3. |
| 15 | **Opex can exceed revenue** because it includes impairments and other operating items. | CORZ FY2022, CIFR FY2025, 12 company-years | Stated in FIELDS.md, in Outputs, and beside each such year. |

Also: every step of `ledger run` is logged and the run saves a snapshot, so DATAHQ shows what changed since the last run;
`ledger watch` asks the SEC for filings not yet read.

## Scorecard

What each company cost. `ledger run` prints this, and each validation page shows it. Code changes are counted by hand from the log above.

| Company | How it ran | Agent time | Tokens | Code changes | For a person | Values agreeing with XBRL |
|---|---|---|---|---|---|---|
| NVDA, MSFT, CRWV, ORCL, APLD | by hand (in-session agents) | n/a | n/a | many (stage 1–2 built the pipeline) | 6 decisions | 56/66 |
| AMD | `ledger run`, unattended | 0.5 min (2 filings) | 16,302 | 0 | 0 (3 warnings: FY2026 not yet ended) | 12/12 |
| AMZN, GOOGL, META, MRVL, MU, TSLA | blind run 1 | 2.5 min (13 filings) | 99,666 | 0 | 0 | 75/75 |
| ALAB, CIFR, CORZ, CRDO, IREN, WULF, SPCX | blind run 1 | 3.5 min (13 filings) | 120,630 | types 1–6 above | 15 blocks (types 2–4) | 68/70 |
| all 19 | run 2, after the fixes | 11.5 min of agent time (all headless filings) | 488,543 | 2 (types 7–8) | 0 | 224/234 (6 explained by code, 4 decided) |

## Open

- **APLD opex FY2023:** restated with no explanatory sentence found by the cue list. Agrees with XBRL, so not blocking.
- **First filings:** a wrong-row misread is caught by comparing filings, so a company's first 10-K is less protected.
