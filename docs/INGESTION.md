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

## Scale run (28 Oct): 10 S&P majors added from DATAHQ, blind

Apple, Broadcom, Intel, Qualcomm, Texas Instruments, Cisco, IBM, Walmart, ExxonMobil and JPMorgan: 38 filings, 7.5 agent-minutes, no code change
before the run. Six were clean on the first pass (AAPL, AVGO, CSCO, QCOM, TXN, WMT: 78/78 values agree with XBRL, every cell confirmed). The
other four found five new types, each fixed as a type:

| # | Type | Where | Caught by | Fix |
|---|---|---|---|---|
| 16 | **Financial statements kept in an exhibit.** The primary 10-K document has 9 tables and no statements; the annual report to stockholders (Exhibit 13) has them. | IBM, all 4 years | `ingest` (statements not located); the agent then returned 0 values | `with_statements`: when the primary document lacks a statement, the filing's other HTML documents are tried, largest first, and the one that has it replaces the primary at the same cached path. |
| 17 | **A company reorganized under a new CIK.** The ticker now maps to the new holding company, whose history sits under the old CIK. | ExxonMobil (0 filings found) | `no_10k_yet`, wrongly | `list_filings` also lists the predecessor CIK's filings (`PREDECESSORS` in config, until now only used by the answer key). |
| 18 | **A line the 10-K doesn't have left a hole, not a blank.** A bank has no capex line and no operating income; the agent said so, but the year had no row at all, so `coverage` warned "no capex value". | JPMorgan (capex, opex), Intel (capex) | `coverage` (false alarm) | A field absent from a 10-K that reports the year is a `not_reported` row: blank, with the reason, and no coverage warning. |
| 19 | **The locator picked an MD&A reconciliation.** Intel's "adjusted free cash flow" table has operating, investing and PP&E rows, so it scored like the cash-flow statement. The agent refused it: "not the investing section of the cash-flow statement; the gross additions line is not in the provided tables". | Intel, all years | the agent's `not_found` reason | Tables introduced as non-GAAP, adjusted or a reconciliation never win the locator (`_mdna`). |
| 21 | **A sub-header repeated under every year.** Intel's income statement puts "Amount" under each year; the re-read matched the last "Amount" cell, so every cited cell "showed" the oldest year's value. The values still agreed with XBRL; only the second read failed. | Intel, 24 cells | `evidence` (not confirmed) | When a sub-header repeats, the re-read takes the one under the cited year (nearest by position to the year's header cell). |
| 20 | **A unit phrased the other way round.** "(millions of dollars)" instead of "(in millions)"; the parser found no unit, and the agent refused to guess: "the filing as given does not say so and the value is not guessed". | ExxonMobil, all years | the agent's `not_found` reason | `_UNIT_PAREN` accepts "(thousands/millions/billions of [U.S.] dollars)". Parser `tables@8`. |
| 22 | **The SEC's revenue tag is "total revenues and other income".** ExxonMobil tags only the total (sales + income from equity affiliates + other income) with `Revenues`; the sales line has no us-gaap tag since FY2022. The agent read "Sales and other operating revenue", which is what revenue means in this ledger. | ExxonMobil, all 4 years | `xbrl_reconcile` (block: 4% gap) | None in code: the ledger's definition is right and the SEC's tag is the wider one, so this is the "confirm a definition once per company" case. Kenny decides the 4 items with one reason. Next step (M3.1): one question per cause, not four per year. |
| 23 | **A highlights table outscored the income statement.** Inside IBM's exhibit, the "Management Discussion Snapshot" (revenue, net income, EPS, then assets, liabilities, equity) comes first and scores like the income statement; the agent read it, found two years of revenue and no cost or operating lines, and said so. | IBM, 3 filings: FY2022–23 revenue blank, opex blank | the agent's `not_found` reasons ("a financial-highlights summary rather than the full consolidated income statement") | A table introduced as a snapshot, highlights or summary, or mixing income lines with balance-sheet totals, never wins the locator (`_summary`). Parser `tables@9`. |

Three things worked exactly as designed: the agent's `not_found` reasons named type 23 in plain words before anyone looked at IBM's page; the Reader agent twice refused to produce a number it couldn't stand behind (types 19 and 20), with a
reason a person could act on; and a bank came out as revenue only, with capex and opex blank for a stated reason, which is the right answer.

## AI spend from the MD&A (29 Oct): a second agent over text

The question behind the ledger is how much of the capex is AI. Filings almost never book a line for it, so the
answer is a graded statement, not a number: `ledger aispend` has a second agent (`ai_reader`, prompt `aispend@v2`)
read the MD&A passages that mention AI next to capital or operating spending and return every statement with a
verbatim quote. Code checks the quote is in the passage (the only citation a text can give), writes table A
(`ai_statements`) and derives table B (`ai_spend`): per company, field, fiscal year and kind, the most specific
statement from the newest filing, and an AI dollar amount only where the filing states the AI part. Item 7 text comes
through `edgartools`; our own table parser is untouched.

Blind pass on META, GOOGL, MSFT, NVDA, JPM (22 filings): 39 statements, 27 company-year rows, 0 with an AI dollar
amount; then all 31 (scorecard below): 79 statements, 54 rows, 3 AI dollar amounts, all IREN's. That is the finding, not a failure: in 10-K MD&A the hyperscalers say "primarily", "the majority", "to support
our AI efforts" and give totals; the only numbers are total-capex outlooks (Meta: $60–65B for 2025, $115–135B for
2026) which the agent correctly files as `scope: total`, not AI spend.

| # | Type | Where | Caught by | Fix |
|---|---|---|---|---|
| 24 | **No year in the sentence.** "We continue to invest…" names no fiscal year; the agent returned `fiscal_year: null` and the output contract rejected it, twice. | 6 of 22 filings (MSFT ×4, GOOGL, META) | contract (`ai_extraction_failed`) | The contract allows null; code assigns the filing's reported year (actual) or the year after (outlook) and records that it did so in `notes`. Prompt `aispend@v2` says so. 0 failures on the rerun. |
| 25 | **A definition sentence read as a statement.** Alphabet's "technical infrastructure, which consists of our investments in servers and network equipment…" describes what the line is, not spend on AI. | GOOGL FY2022 capex | nothing yet (confidence 0.8) | Open: a prompt rule against defining sentences, or a check that a `qualitative` quote contains a spend verb. |
| 26 | **Scope is loose for words-only statements.** The same kind of sentence gets `scope: ai` in one filing and `total` in the next; scope only has meaning for an amount or share. | GOOGL, META opex | by eye | Open: ignore scope for `qualitative` rows when reading them; or drop it from the contract for that class. |
| 27 | **The numbers live elsewhere.** Explicit AI amounts and shares appear in earnings-call prepared remarks and 8-K earnings releases (Exhibit 99.1), not in 10-K MD&A. | every hyperscaler | by design | Next: feed Exhibit 99.1 of the 8-K filed with each 10-K (edgartools gives it) through the same agent and contract. |

## Evaluation (29 Oct): a reference set and an error band

A number other people act on needs a measured error, not an agent's confidence. `gold/ai_capex.yaml` is a reference
set of sourced figures for AI's part of capex: what the company said on a call, or an independent estimate, each with
URL, quote, date, and a line saying what the figure measures (a server share includes CPUs; "vast majority" is a
floor). `ledger eval` scores every attribution row against it: coverage, agreement within 10%, and the error on the
entries that state a figure, by method. The report ships in every release as `EVALUATION.md` and on the Insights tab.

First set, six entries, all company statements: we have a number for three. Oracle and Amazon agree with the floors
the companies gave; Microsoft disagrees (our 61% by server-category growth against "at most about half" short-lived
assets: the category's growth includes finance-lease assets and software, so it overstates the server share, a
known limit of that method, now measured); Alphabet twice and Tesla have no estimate from us. Small, and said so;
the point is that the number is now checkable and every new sourced figure tightens it.

| # | Type | Where | Caught by | Fix |
|---|---|---|---|---|
| 45 | **A company renamed its PP&E categories.** From the FY2024 10-K Alphabet reports "Technical infrastructure", "Office space", "Corporate and other assets" and "in service / not yet in service" lines instead of land, buildings and information technology assets. None matched the candidate-table words, so the notes reader never saw the table; FY2024–25 attribution was `none`, and two reference entries had no estimate. | GOOGL FY2024–25 | the evaluation (no estimate) | The candidate words include the new names; a test keeps them. Hyperscaler model `@v2` names the rename so the attributor bridges it. |
| 46 | **Server-category growth overstates the server share.** Microsoft's gross "Servers, network equipment, and software" grew 39.1B in FY2025 against 63.6B capex (61%); the company said short-lived assets were at most about half. The category includes finance-lease assets and software, which are not cash capex. | MSFT FY2025 | the evaluation (disagree) | None yet: the method's error is now measured and stated beside the number. Open: subtract finance-lease additions from the category growth when the lease note gives them. |
| 47 | **A company files no 10-K.** The base of the chain (TSMC, ASML, SK hynix, Samsung) files 20-F or nothing with the SEC, and recent movers (Nebius, Bitdeer, Arm, Celestica) have 20-F or 40-F history before their first 10-K. The pipeline reads 10-Ks only, so those companies and years are gaps, not errors. | the 100-company set (`docs/COMPANIES.md`) | `no_10k_yet` and coverage | Open: a 20-F reader (same statements, different item numbers and often IFRS). Until then the set holds US filers and the gap is stated. |
| 48 | **A filer reports the notes in whole dollars.** Bit Digital's segment table is in dollars, not thousands; the notes reader read `27,349,798` right and the citation check multiplied by the document's declared scale (×1,000) and rejected every row, twice. Nothing wrong loaded; the company has no note facts. | BTBT FY2025 | citation check (rejected) | Open: the unit resolver must read the scale per table ("in thousands" in the table caption or the first header cell), not per document; until then a whole-dollar filer's notes are a gap. |
| 49 | **A 52/53-week fiscal year is named by the prior calendar year.** Cadence's year ended 2 January 2021 sits in the column "2020"; `column_matches_period` compared the column year with the period end's year and blocked 20 right values. | CDNS, every year | the rule (false block) | The rule accepts the prior year when the period ends in the first seven days of January. Cadence's two cost lines also went into `definitions/companies.yaml`. |
| 50 | **The unit is written "($000)".** Coherent's statements say "($000)" and "($000, except per share data)"; no unit pattern matched, the cash-flow statement got the document's majority unit (millions, from MD&A tables), and every capex citation was rejected, five filings. | COHR, every year | citation check (rejected) | `tables@10`: "($000)" is thousands, in table headers and in the document scan. |
| 51 | **An MD&A analysis table located as the income statement.** Coherent's "select items from our Consolidated Statements of Earnings" table, in millions with "% of Revenues" columns, comes before the statement and names it, so it won the locator. Values were right in dollars (the table states its unit) but cite the wrong table. | COHR | reading the located tables | `tables@10`: a table with a percent column, or introduced as "select items", is a summary and never wins. |
| 52 | **Current and non-current lease lines cited as two values for one year.** Jabil's note gives finance lease liabilities as a current and a non-current line with no total; `notes@v2` asked for "current plus non-current" but the contract takes one cell per value, so the reader cited both and the loader rejected them. | JBL FY2025, FY2026 | notes loader (two values) | `notes@v3`: cite the total line, or each portion as its own dimension (`current`, `non-current`); never two cells for one dimension. |
| 53 | **A `none_found` / `not_found` entry in the wrong shape.** The attributor (Rambus, Seagate) and the notes reader (Coherent FY2022) returned an entry the contract could not read (field not one of the allowed words, or no reason), and both attempts were rejected. The rejected text was not kept, so the exact shape is unknown. | RMBS, STX, COHR | contract (rejected) | Rejected answers are now kept in the output file; `attribution@v2` and `notes@v3` spell out the entry shape; the rerun re-asks all three. |

## Attribution (29 Oct): money-flow models and the attributor

The question, finally answered per company and year: how much of the capex and opex is AI. Six money-flow models
(`agents/models/<industry>@v1.md`: hyperscaler, neocloud, miner-to-HPC, chip seller, component supplier, other) say
where AI money shows up for that kind of business and which methods are allowed, hardest first. The attributor
(`attribution@v1`) reads the model and the company's data pack (values, facts from the notes, what the company said)
and returns one row per field, fiscal year and kind with the method, the amount, every input by id, and a basis a
reader can check. Code looks every input up in the pack and recomputes the amount by the method's arithmetic; a
mismatch is rejected and asked again. Editing a model reruns only that industry; `--load` writes a diff.

Five companies first: 47 rows, 15 with an AI amount, 0 failed, 1 attempt each. All 31: 223 rows for 29 companies, 38
with an AI amount, 0 failed, 0 retries, 9.4 agent minutes, 330k tokens. Microsoft from growth in the
server-and-network PP&E category (FY2026: 83.0B of 115.9B capex, 72%); Applied Digital from segment capex; CoreWeave
whole-business; Nvidia `none` with data-center revenue named in the basis; Tesla words only, correctly declining to add
two quarterly AI-capex figures into a year.

| # | Type | Where | Caught by | Fix |
|---|---|---|---|---|
| 41 | **Segment capex above cash capex.** Applied Digital's HPC segment capex (accrual, ASC 280) exceeds the cash-flow capex: FY2024 287M vs 142M, FY2025 977M vs 682M. The attributor said so in `basis`. | APLD | the attributor; `ai_amount_within_capex` now checks attribution rows too | None in code: the segment number is the right AI number; the warning carries the explanation. A model note could ask for a cash-basis adjustment where the note gives one. |
| 42 | **Quarterly AI figures not summed.** Tesla states AI-infrastructure capex per quarter in releases ($1.0B Q1, $0.6B Q2 2024) but never the year; the contract forbids the agent to add them. | TSLA FY2024 | by design | Open: a `stated_sum` method over statements that cover the whole year's quarters, checked by code. |
| 44 | **Alphabet stops at FY2023.** Server-category growth needs two consecutive year-end facts of the same category; Alphabet's "Information technology assets" is in the pack for FY2022–23 only, so FY2024–25 are `none`. | GOOGL | counts | Open: check the notes reader's output for Alphabet's FY2024–25 PP&E note (the category may be worded differently, or the table missed by the locator). |
| 43 | **Category renamed across years.** Microsoft's server category was "Computer equipment and software" until FY2025 and "Servers, network equipment, and software" after; the agent bridged the rename in `basis` and the arithmetic check passed because both facts are in the pack. | MSFT | none | None; worth a model sentence so every attributor does the same. |

## More sources for AI spend (29 Oct): releases, transcripts, CFO commentary

`ledger texts` gathers every text the AI spend reader reads into one registry with the fiscal period each speaks to:
10-K MD&A, 8-K earnings releases (Exhibit 99.1 of every Item 2.02 8-K since FY2022, through edgartools), and the
transcripts and CFO commentary a company's investor page offers when `sources/ir.yaml` names it. The reader then runs
over all of them; the most specific statement wins across sources, the newest text breaks ties. Meta and Nvidia first:
72 texts, 88 statements, 20 rows, 0 AI dollar amounts; transcripts gave 7 explicit totals and 24 words-only AI
statements, releases 6 totals. All 31 with `aispend@v3`: 702 texts, 244 statements, 83 rows, 8 AI dollar amounts,
0 failed, 0 retries, 65 agent minutes, 4.1M tokens.

| # | Type | Where | Caught by | Fix |
|---|---|---|---|---|
| 35 | **In-year guidance read as an actual.** "We anticipate full-year 2024 capital expenditures of $35–40 billion" in a mid-2024 release was `kind: actual` because the text's fiscal year is 2024. Spent and expected were conflated. | Meta releases, every year | by eye in `ai_spend` | Prompt `aispend@v3`: `actual` means spent; expected, anticipated, planned or guided is an `outlook` even for the current year. |
| 36 | **Investor pages sit behind a bot check.** Nvidia's and Meta's pages answer headless Chrome with "Just a moment…" and no links. A headed Chrome gets past it, and that is exactly what code must not do. | NVDA, META (Q4 Inc pages) | 0 links found; then the permission check | No page rendering in code. A person lists the PDF links in `sources/ir.yaml` from their own browser; the PDFs download directly (no challenge on the CDN). Meta: 19 transcripts, Nvidia: 2 transcripts and 2 commentaries listed so far. |
| 37 | **Only the current fiscal year is on the page.** Nvidia's page lists one year by default, so its list has 4 links, not 20. | NVDA | counts | A person lists older years' links (the page has a year selector). |
| 38 | **Second click or no match.** Alphabet's earnings page links to event pages that hold the transcript; Microsoft's page has no obvious link. | GOOGL, MSFT | not listed | Per-company work in `sources/ir.yaml`, nothing in code. |
| 40 | **Releases under the old CIK.** ExxonMobil reorganised under a new CIK in 2026; its 8-Ks before that sit under the predecessor CIK, which the release lister doesn't walk. 0 releases gathered. | XOM | counts (4 mdna, 0 releases) | Open: walk `config.PREDECESSORS` for 8-Ks as the 10-K lister does. |
| 39 | **Multiple guidance for one year.** A company guides full-year capex each quarter and narrows the range; four rows for FY2024 from four releases. | Meta | `spend_rows` | The newest text wins among equally specific statements: the latest guidance ships, earlier ones stay in `ai_statements`. |

## Facts from the notes (29 Oct): the base for attribution

AI-spend attribution needs numbers the primary statements don't carry: capex and revenue per segment (ASC 280), PP&E
by category (servers vs buildings), finance lease liabilities, purchase commitments. `ledger notes` is a third agent
(`notes_reader`, prompt `notes@v2`) over candidate note tables, same citation contract as the Reader; code resolves
every cell. Table A `note_extractions`, table B `facts` (per company, field, dimension, fiscal year, newest filing).
The answer key is the filing's own XBRL instance, read directly (`reference/dimensions.py`): segment and category
members are matched by normalised name, so a tagged fact checks the agent and an untagged one is `no_reference`.

First pass, six companies, 25 filings: 478 cells, 288 facts, 166 agree with the filing's tags, 11 differ, 111 untagged,
2 filings failed. All 31 after the fixes below: 124 filings, 2,346 cells, 1,436 facts, 522 agree, 27 differ, 887 untagged,
0 failed; 70 agent minutes, 1.88M tokens, 20 retries.

| # | Type | Where | Caught by | Fix |
|---|---|---|---|---|
| 28 | **Note tables carry no unit of their own.** The parser states a unit only for a table that has one in its context; a PP&E note says "(in millions)" in the sentence above, or nowhere. The resolver crashed on a missing key and took the run down. | every filing | crash (KeyError) | `notes.with_units`: a note table without a unit takes the primary statements' unit, `unit_source: document`, as the statements already do. |
| 29 | **The answer key came from the wrong vintage.** The fact takes the newest filing's value (Microsoft's recast segments), the reference took the oldest filing's tag: 9 "differ" rows that were right. | MSFT segment revenue FY2021–24, APLD PP&E FY2024 | `facts.label = unresolved` | The reference is built newest filing first, so a value and its check come from the same 10-K. |
| 30 | **Column label shortened.** The agent cited `"May 31, 2024"` for the column listed as `"Fiscal year ended | May 31, 2024"`, twice, retry included. | APLD FY2024 | citation check (rejected) | Prompt `notes@v2`: the column label is the whole listed string, every ` | ` part included. |
| 31 | **Text after the JSON.** One answer had a sentence after the closing brace; the extractor matched first brace to last and failed to parse. | APLD FY2026 | `_json` (rejected after retry) | `agent._json` decodes the first object and ignores what follows. |
| 33 | **Capex in parentheses in a segment note.** Applied Digital's segment table shows capital expenditures as (1,234); the resolver required the shown sign and rejected the answer twice. | APLD FY2026 | citation check | Note values resolve as the absolute cell value: a spend or a balance is positive however the table prints it. |
| 34 | **Purchase commitments are several definitions.** The agent reads the contractual-obligations total; the tags are `PurchaseObligation` (one concept among several) or company-specific: Amazon 50.4B vs 333.0B tagged, IBM 4.9B vs 0.5B. 8 of 42 differ, 29 untagged. | AMZN, IBM, COMP, CRDO, ALAB | `facts.label = unresolved` | Open: this field needs a per-company definition (which table, which total) before it feeds attribution; shown as "differs" until then. |
| 32 | **Segment capex is rarely tagged.** Applied Digital's segment capex has no us-gaap member in the instance; every `segment_capex` is `no_reference`. Expected: ASC 280 capex is often a custom concept or untagged. | APLD | by design | None. The cell citation is the check; the share of untagged facts is reported honestly in QUALITY.md. |

## No questions (29 Oct)

A person was being asked three kinds of thing: a definition (ExxonMobil's revenue line, which cost lines count), a big move or outlier the SEC's data couldn't confirm, and a renamed line. The first is now a file (`definitions/companies.yaml`, who and why on every entry) that code applies every run. The other two are findings with an "SEC data agrees / can't confirm" flag, not questions: a misread would also disagree with XBRL, so agreement rules it out, and a disagreement is already its own block. Stage 3 after the change: 0 block, 0 unresolved, 93 findings, 1 unconfirmed (one jump the SEC's data has no value for).

## Scorecard

What each company cost. `ledger run` prints this, and each validation page shows it. Code changes are counted by hand from the log above.

| Company | How it ran | Agent time | Tokens | Code changes | For a person | Values agreeing with XBRL |
|---|---|---|---|---|---|---|
| NVDA, MSFT, CRWV, ORCL, APLD | by hand (in-session agents) | n/a | n/a | many (stage 1–2 built the pipeline) | 6 decisions | 56/66 |
| AMD | `ledger run`, unattended | 0.5 min (2 filings) | 16,302 | 0 | 0 (3 warnings: FY2026 not yet ended) | 12/12 |
| AMZN, GOOGL, META, MRVL, MU, TSLA | blind run 1 | 2.5 min (13 filings) | 99,666 | 0 | 0 | 75/75 |
| ALAB, CIFR, CORZ, CRDO, IREN, WULF, SPCX | blind run 1 | 3.5 min (13 filings) | 120,630 | types 1–6 above | 15 blocks (types 2–4) | 68/70 |
| ANET (Arista Networks) | added in DATAHQ, unattended | 0.8 min (4 filings) | 31,774 | 0 | 0 (2 warnings, both confirmed by XBRL, shown as findings) | 12/12 |
| all 19 | run 2, after the fixes | 11.5 min of agent time (all headless filings) | 488,543 | 2 (types 7–8) | 0 | 224/234 (6 explained by code, 4 decided) |
| AAPL, AVGO, CSCO, QCOM, TXN, WMT | added in DATAHQ, blind | 4.9 min (26 filings) | 201,818 | 0 | 0 | 78/78 |
| COMP (Compass) | added by Kenny in DATAHQ, blind | 1.2 min (4 filings) | 42,090 | 0 | 1 (cost lines: commissions) | 8/12 (4 opex definition gaps, explained by code) |
| IBM, INTC, JPM, XOM | added in DATAHQ, blind | 3.7 min (16 filings) | 122,877 | types 16–21, 23 | 5 (XOM: 4 revenue definition, 1 cost lines) | see below |
| all 31, attribution | `attribution`, `attribution@v1`, six models @v1 | 9.4 min (29 companies) | 330,402 | 0 | 0 (3 warnings: accrual segment capex above cash capex, explained) | 223 rows: 38 AI dollar amounts by server-category growth (22), whole business (6), stated amount (6), segment (4); 67 words only, 118 none |
| all 31, texts + AI spend | `texts` + `aispend`, `aispend@v3` | 65.5 min (702 texts, 543 asked) | 4,120,870 | 1 (type 35) | 0 | 244 statements → 83 rows: 8 AI dollar amounts, 21 explicit totals, 62 words only; releases gave the most statements, transcripts the most words |
| all 31, notes | `notes`, blind, `notes@v2` | 70.1 min (124 filings) | 1,879,685 | 4 (types 28–31, 33) | 0 | 1,436 facts: 522 agree with the filing's tags, 27 differ (purchase-commitment definitions, type 34), 887 untagged |
| all 31, AI spend | `aispend`, blind, `aispend@v2` | 11.6 min (124 filings with an Item 7; 87 asked, 37 had no passage) | 643,212 | 1 (type 24) | 0 | 79 statements → 54 company-year rows: 3 AI dollar amounts (all IREN), 9 company totals with AI as driver (Meta, Tesla, Core Scientific, IREN), 42 words only; IBM, Intel, ExxonMobil, JPMorgan: no passage mentions AI next to spending |
| all 31 | full run, `tables@9` | 22.6 min (132 filings) | 907,507 | 1 (type 23) | 8 | 354/384 (26 explained by code: 16 not reported, 10 definition gaps); 1,431/1,431 cells confirmed |

## Open

- **One question per cause (M3.1):** XOM's revenue definition is one judgement shown as four items. Cost lines already ask once per company; `xbrl_reconcile` should too when every year of a field disagrees by the same kind of gap.
- **APLD opex FY2023:** restated with no explanatory sentence found by the cue list. Agrees with XBRL, so not blocking.
- **First filings:** a wrong-row misread is caught by comparing filings, so a company's first 10-K is less protected.
