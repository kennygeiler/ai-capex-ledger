# Proof: the pipeline proves its own numbers (31 Oct 2026)

Kenny, after the replication run: fifty changes to the screens, and the biggest findings were still errors in
ingestion and attribution. "The entire point of this pipeline is to manage those issues and fix them." So the
frame changes. Not a dataset across 100 companies with a review screen on top; a pipeline that proves every number
it produces, shown first on five companies, widened only when the five are proven.

## What proven means

For a company, every figure in the dataset is one of three things, and the pipeline says which:

- **checked**: it matches an independent check. A value matches the SEC's XBRL. A cited cell matches the rendered
  10-K. An attributed amount matches what the company stated, within tolerance, same scope.
- **explained**: it does not match, and a rule or a definition on file says why, by name. A definition names the
  company's cost lines. A rule says a cell from a later 10-K against a tag from an earlier one is a restatement. A
  comparability rule says a wider measure eight points above a narrower stated one is consistent.
- **open**: neither. The only thing a person looks at.

Proven = zero open, for every stage, for that company. A person's judgement enters as a definition or a rule,
never as a click on a row; once written it applies every run and the item never comes back.

## The stages, and what proven means at each

| Stage | Item | Checked by | Explained by | Open when |
|---|---|---|---|---|
| Ingest | a filing | every statement and note table located, units from the document | a unit rule (type 48, 50, 56, 62) | a table or a unit is missing |
| Values | a value per field and year | the SEC's XBRL | a definition (cost lines, revenue line), a restatement rule | `unresolved` |
| Facts | a fact per segment or category and year | the filing's instance (concept and member named) | a restatement between filings, an untagged line | `unresolved` with no explanation |
| Statements | a quote | the text it came from, verbatim | scope, period and part-year tags set by rule | a part-year or program statement without its tag |
| Attribution | an amount per field and year | the reference set, same scope | comparability by scope and tolerance; the method's known bias | `disagree` |
| Plans, projects | a plan per year, a project per mention | code only | program words (type 69) | a program read as a plan |
| Release | the company's rows | the gates | resolutions written as definitions | any `blocks` |

## The five

| Company | Layer | Why this one |
|---|---|---|
| Microsoft | hyperscaler | PP&E growth method; a stated ceiling (at most 50%); software and finance leases inside the category |
| Alphabet | hyperscaler | a category rename; a restatement between filings; a planning floor against a point figure |
| Amazon | hyperscaler | a category split with no restated comparative |
| Nvidia | chip seller | the seller side: stated AI revenue against a segment; no AI capex |
| Applied Digital | miner to HPC | segment accrual capex above cash capex |

`config.PROVEN` holds the list and `PROVEN_WHY` the reasons. Nothing runs across 100 until the five are proven.
The other 95 stay in the dataset as they are, marked not yet proven.

## The golden test

`fixtures/` holds, for the five, what the code stages read: the parsed tables, the texts, the distilled XBRL
instances, the documents and texts rows, and the agents' answers. `fixtures/expected/` holds the tables the code
makes from them. `ledger golden --check` rebuilds a repo layout in a temporary root (`LEDGER_ROOT`), seeds a fresh
database, runs pack and load for every stage, reconcile and the rules, with nothing fetched and no agent asked,
and compares every table with the expectation. Any change to a parser, a rule, a loader or a thesis has to leave
the comparison equal or change the expectation on purpose (`--freeze`, then a commit that says why).

The agents' answers are inputs here, on purpose. Whether they are good answers is the reference set's job
(`ledger eval`), kept apart from whether the code does the right thing with them.

What the first run found, before any screen was built: the loaders check quotes against task files that are
rebuilt from the texts (so the harness packs before it loads); three of the five companies' attribution rows had
been produced under the previous thesis after the switch (the proof requires every proven company rerun under
the thesis in use); and the order of a value's cost-line extraction ids was not deterministic.

## The four measures

| Measure | Question | Table |
|---|---|---|
| Capex allocation | how much of this year's capex is AI | `attribution`, field capex |
| Revenue exposure | how much of revenue comes from AI demand | `attribution`, field revenue |
| Project-level investment | which named projects, how big, what stage | `projects` |
| Plans vs reality | what the company said it would spend, and what it spent | `plans` |

One thesis per layer of the AI supply chain (`agents/models/<layer>@vN.md`, `docs/COMPANIES.md`): what moves the needle, where the money shows up, how to attribute, what counts as a project, the traps. Versioned, never edited in place; dry-run on a company before the switch.

## DATAHQ

- **Proof** (home): the five companies down, the stages across. Each cell: checked, explained, open, as counts.
  Proven companies read as one line. Below, the other 95 in one collapsed row with their counts.
- **Company**: the proof trail. Each stage's items with their check, and for every non-match the rule or
  definition that explains it, or "open". The cited cell, the tag's concept and member, the quote, the inputs.
- **Rules**: every rule and definition, what it explains, how many items it closed in the latest run, and the
  failure type it came from. The open items of the five, grouped by what rule is missing. This is the work list.
- **Reconcile**: judgement on open items, which should be nearly empty; a judgement that would be made twice becomes a definition.
- **Dataset**: the grid for a consumer, marks per cell (✓ traced, ≠ differs from SEC data, ✗ disagrees with a stated figure, ! above the total, a decision as a badge), CSV export.
- **Explore**: charts on the API lists, share as a value, saved views as queries.
- The releases table and the golden test's last run sit on Proof; the theses and the readers on Rules. Six pages, one file, `ledger/app.html`.
