# Proof: the pipeline proves its own numbers (31 Oct 2026)

Kenny, after the replication run: fifty changes to the screens, and the biggest findings were still errors in
ingestion and attribution. "The entire point of this pipeline is to manage those issues and fix them." So the
frame changes. Not a dataset across 100 companies with a review screen on top; a pipeline that proves every number
it produces, shown first on five companies, widened only when the five are proven.

## What proven means: the one definition of open (`ledger/status.py`)

For a company, every row of the dataset is in exactly one of four states, and one function, `status.state`, says
which; Proof, Reconcile, the trail and the Release gates all read it, so no two pages count the same row differently:

- **checked**: it agrees with an independent check. A value or a fact matches the SEC's XBRL. A statement or a
  planned row is a verbatim quote verified against its text. A filing's statement tables are located. A reported
  asset type is mapped to a us-gaap member with the note's words (`taxonomy/asset_types.yaml`).
- **explained**: it does not match, and something on file says why, by name: a definition
  (`definitions/companies.yaml`), an info-severity rule or a guard (`rules/*.yaml`, `proof.GUARDS`), a label reconcile
  wrote because the filing has no such line or XBRL no such tag (`not_reported`, `no_reference`), or a person's
  resolution that says accept or explain (`decisions/resolutions.jsonl`).
- **blocked**: a block-severity rule fired on it, or a person's resolution says blocks. Blocked is open that also
  refuses the release; every count of open includes it.
- **open**: none of the above, or a person's resolution says fix. The only thing a person looks at.

Precedence when more than one applies: blocked, then checked, then a person's fix (open), then explained, then open. A
warn-severity finding (a jump, a renamed line, an outlier) has no state of its own: it takes the worst state of the
rows it fired on, so a jump on a value XBRL confirms is checked, on a value a definition covers is explained, on an
unresolved value is open. Every item carries `by`: `xbrl`, `quote`, `located`, `mapping:<member>`, `rule:<id>`,
`definition:<name>`, `label:<label>` or `resolution:<id>`.

Proven = zero open (blocked included), for every stage, for that company. A person's judgement enters as a definition
or a rule, never as a click on a row; once written it applies every run and the item never comes back. A resolution is
the exception for what nothing on file covers yet, and it holds only while the item's content is unchanged.
`tests/test_status.py` asserts, on the frozen fixtures, that the Proof board's open count equals Reconcile's for every
company in the proven set.

## The stages, and what proven means at each

| Stage | Item | Checked by | Explained by | Open when |
|---|---|---|---|---|
| Ingest | a filing | every statement and note table located, units from the document | a unit rule (type 48, 50, 56, 62) | a table or a unit is missing |
| Values | a value per field and year | the SEC's XBRL | a definition (cost lines, revenue line), a restatement rule | `unresolved` |
| Facts | a fact per segment or category and year | the filing's instance (concept and member named) | a restatement between filings, an untagged line | `unresolved` with no explanation |
| Statements | a quote | the text it came from, verbatim | scope, period and part-year tags set by rule | a part-year or program statement without its tag |
| Mapping | a reported asset type | the us-gaap member it maps to, with the note's words (`taxonomy/asset_types.yaml`) | the mapping is the explanation | a reported category with no mapping |
| Planned | a guidance statement, a project | the text, verbatim | part-year and program tags (types 68, 69) | never: a verbatim row is what it is |
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
and compares every table with the expectation. Any change to a parser, a rule, a loader or the taxonomy has to leave
the comparison equal or change the expectation on purpose (`--freeze`, then a commit that says why).

The agents' answers are inputs here, on purpose. Whether they are good answers is the reference set's job
(`ledger eval`), kept apart from whether the code does the right thing with them.

What the first run found, before any screen was built: the loaders check quotes against task files that are
rebuilt from the texts (so the harness packs before it loads); three of the five companies' attribution rows had
been produced under the previous thesis after the switch (the proof requires every proven company rerun under
the thesis in use); and the order of a value's cost-line extraction ids was not deterministic.

## The measures (docs/TAXONOMY.md)

| Measure | What | Standard |
|---|---|---|
| spent | capex, segment capex, segment revenue | us-gaap concepts, ASC 280 |
| committed | purchase obligations, finance lease liabilities | ASC 440, ASC 842 |
| derived | the reported gross PP&E balance per asset type, mapped to a us-gaap member, and its change | us-gaap PropertyPlantAndEquipmentByTypeAxis |
| planned | guidance and projects, verbatim, forward-looking | Regulation S-K |
| company_stated_ai | a figure the company itself stated about AI, verbatim, in its own scope words | none: the company's words |

Nothing is inferred. The attribution methods that estimated an AI share, and the theses that drove them, are archived under `docs/archive/theses/` (1 Nov 2026, "invent nothing").

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
- The releases table and the golden test's last run sit on Proof; the guards, the asset-type mappings and the readers on Rules; the dataset on Dataset, as a grid by year or as the raw rows of every list. Six pages, one file, `ledger/app.html`.
