# Taxonomy: standardize and sanitize, invent nothing (draft, 1 Nov 2026)

Kenny: "a full taxonomy iteration that focuses on standardizing and sanitizing, rather than coming up with our own
concept of AI spend. Let's not invent anything." So every category below is taken from a published standard, named,
and the pipeline's job is to map what a company reports onto it with the evidence beside it. Where no standard
exists, the dataset carries what the company itself said, verbatim, and nothing more.

## The standards used, and for what

| Standard | What it gives us | Where it is used |
|---|---|---|
| US GAAP / XBRL (FASB taxonomy, `us-gaap`) | the accounting definitions of capex, PP&E, asset types, segments, commitments, leases; the concept names the SEC checks | every spent and committed measure is a `us-gaap` concept or a member of one of its axes |
| ASC 280 (segment reporting) | what a reportable segment is and that segment capex and revenue are disclosed | segment-level spent and revenue |
| ASC 440 and ASC 842 (commitments; leases) | unconditional purchase obligations; finance and operating lease liabilities | committed |
| SEC Regulation S-K Item 303 and forward-looking statement rules | what management guidance is, that it is forward-looking and must be quoted as such | planned, verbatim |
| SEC SIC codes (EDGAR `submissions`) | the entity's industry, assigned by the SEC | entity classification |
| EU Taxonomy, Climate Delegated Act, activity 8.1 "Data processing, hosting and related activities" (NACE J63.11) | the one published taxonomy activity that is a data center, with its reporting shape (capex, opex, turnover aligned to the activity) | the shape of the three measures and the precedent for reporting capex "aligned to an activity" |
| ICMA Green Bond Principles | the structure of a use-of-proceeds taxonomy: category, eligibility definition, evidence, reporting metric | the structure of `taxonomy/taxonomy.yaml`; none of its categories, which are climate categories |

What is not a standard, and therefore not in the taxonomy: "AI capex". No accounting standard, regulator or industry
body defines it. Companies state figures about it in their own words. The dataset carries those statements as
`company_stated`, scoped by the company's own words, and never a figure the pipeline inferred.

## The three measures (EU Taxonomy shape)

- **spent**: cash paid or assets added in the fiscal year, by `us-gaap` concept.
- **committed**: obligations the company has signed and disclosed but not yet paid, by `us-gaap` concept.
- **planned**: what management said it expects to spend, quoted verbatim with the period it names, flagged
  forward-looking; and projects the company named, quoted verbatim.

A fourth, **company_stated_ai**: a figure or share the company itself stated about AI, verbatim, with scope words and
period as stated. Not a measure of ours. A label on a quote.

## Categories

### Entity

- `sic`: the SEC's SIC code and description for the filer (from EDGAR `submissions`). Standard.
- `layer` (non-standard, a reading aid): the supply-chain layer we used to pick companies (hyperscaler, neocloud,
  ...), added to every row by the API and the packet. A grouping for reading the dataset, not a definition of
  anything; never shown as `industry`. Schema v11 (T9) dropped `group`, which was the same value under a second name.

### Spent (every one a `us-gaap` concept)

| id | concept | what it is |
|---|---|---|
| `capex` | `PaymentsToAcquirePropertyPlantAndEquipment` (or `PaymentsToAcquireProductiveAssets` where that is the reported line) | cash capex, the company's own line |
| `ppe_additions_by_type` | `PropertyPlantAndEquipmentGross` by `PropertyPlantAndEquipmentByTypeAxis` member, year-over-year change | the gross balance per asset type, reported, and its change; the change is arithmetic, not an estimate |
| `segment_capex` | capex by `StatementBusinessSegmentsAxis` member (ASC 280) | the company's own segment split |
| `segment_revenue` | revenue by segment (ASC 280) | the company's own segment split |

Asset types: the member the company tags. Where the company tags its own extension (`goog:TechnicalInfrastructureMember`,
`amzn:ServersAndNetworkingEquipmentMember`), the dataset carries the company's member name and its description from
the note, and maps it to the nearest standard `us-gaap` member (`TechnologyEquipmentMember`, `ComputerEquipmentMember`,
`LandAndBuildingsMember`, `ConstructionInProgressMember`, ...) as a second column, `standard_type`, with the mapping
written in `taxonomy/asset_types.yaml` and the note's own words as the evidence. A mapping is a classification
against a published list, recorded; it is never a number.

### Committed (every one a `us-gaap` concept)

| id | concept |
|---|---|
| `purchase_obligations` | `UnrecordedUnconditionalPurchaseObligationBalanceSheetAmount` / `PurchaseObligation` (ASC 440) |
| `finance_lease_liability` | `FinanceLeaseLiability` (ASC 842) |
| `operating_lease_liability` | `OperatingLeaseLiability` (ASC 842) |
| `contractual_obligations_total` | `ContractualObligation`, the total, kept apart from the above, never a stand-in for them (type 71) |

### Planned (verbatim, forward-looking)

| id | what |
|---|---|
| `guidance` | a management statement of expected spend for a named period, quoted, with the period and the range as stated; a statement that covers part of a year or a multi-year program carries that tag (types 68, 69) |
| `project` | a named project with the size, stage and date the company gave, quoted |

### Company-stated AI (verbatim, labelled, never computed)

| id | what |
|---|---|
| `company_stated_ai` | any figure or share the company stated about AI spend or AI revenue, quoted, with the scope words the company used ("AI infrastructure", "servers", "technical infrastructure", "AI-optimized servers"), the period as stated, and whether it is spent, committed or planned |

## What is removed as conjecture

- The attribution methods that infer an AI share: `ppe_category` (growth in a category as AI capex), `segment` (a
  segment as AI), `whole_business`, `commitment` as AI. They produced "61% of Microsoft's capex is AI". That is a
  view. Gone from the dataset.
- `ai_amount` and `ai_share` as columns. Replaced by `company_stated_ai` rows, which carry the company's figure, and
  by standard asset-type rows, which carry what the company reported under the name it used.
- The money-flow theses as attribution instructions. What survives of them is the mapping of each company's reported
  categories and segments onto the standard lists, which moves into `taxonomy/asset_types.yaml` and
  `definitions/`, with evidence. The "traps" sections become rules or failure types where they are rules.
- "AI capex by layer" and every chart or export that summed inferred AI amounts.
- The reference set as a scorer of inferred shares. It survives as a list of company-stated figures, which is what
  it mostly was, and becomes `company_stated_ai` rows with their sources.

## What stays

- Every reader: values, notes, statements, projects. They extract; they do not estimate.
- Every check: XBRL agreement, the rendered-cell re-read, verbatim quotes, the rules, the golden test, the proof
  board. Proof reads the same on the new shape; the attribution stage becomes the mapping stage (every reported
  category mapped to a standard type, or open).
- Spent, committed, planned as the three columns a buyer sees, each by standard concept, each cited.

## What a row looks like (schema v11, T9–T17)

One shape for all five measures, 37 columns, declared once in `ledger/store.py` (`TAXONOMY`) and described column by
column in `docs/DATA_DICTIONARY.md`; the API and the packet add `layer` and `proven`. One meaning per column:

```
ticker, fiscal_year, period_end, period_kind (reported|planned),
measure (spent|committed|derived|planned|company_stated_ai), category (taxonomy id),
reported_name (the company's own label), standard_concept (us-gaap, Reg S-K, or none), standard_type (member, when an asset type), mapped,
value, value_high (a range high only), change_from_prior (the derived change only), share, relation (eq|ge|le, gathered figures), has_value,
unit (USD|share, empty without a figure), scale (1), currency (USD),
period_as_stated, quote, kind (actual|outlook), project_kind, status, location, capacity_mw, forward_looking, part_year, program   (verbatim rows; empty elsewhere)
source (internal id), source_kind (10-K table|10-K note|10-K MD&A|8-K release|transcript|cfo commentary|gathered), accession, filed, source_table, source_url,
check (agree|explained|differs|no_reference|unmapped|verbatim), check_method (<kind>[:<id>], kinds in status.METHOD_KINDS)
```

`check` says whether the figure was verified and how it stands; `check_method` says what established that, in the
words `ledger/status.py` uses for `by`: `xbrl`, `quote`, `gathered`, `rule:<id>`, `definition:<name>`,
`resolution:<id>`, `label:<label>`, `none`, and the answer keys T40 named for later sources, `esef:<tag>`,
`source:<doc>`, `actual:<period>` and a tie rule `rule:<id>_tie` (`status.ANSWER_KEYS`, docs/PROOF.md; no row carries
the three new ones yet). `period_kind` is reported only when the company's fiscal calendar (the
10-K that reports the year) knows the year's end and the source was written on or after it; otherwise planned.
`source_url` opens the source: for a 10-K cell the filing with a text fragment of the row label and number (the first
place the filing shows those words; sec.gov has no table anchors), for a statement or project the text at its quote,
for a gathered figure its page; `source_table` is the parser's id of the table the cell came from, the one DATAHQ shows. No column holds a number the pipeline made up: `change_from_prior` is
this year's reported balance minus last year's, and says so.

One restatement threshold (T64): a figure is `restated` (values and facts `basis`, the rows' `rule:restated_between_filings`
explanation, `reference_values.restated`) when a later filing moved the first-reported one by more than
`config.RESTATEMENT_TOLERANCE`, half a rounding unit of the figure: the 10-K cell's stated scale, or for an XBRL fact the
coarser unit the two vintages are rounded to. Half a unit is the most rounding alone can move a figure, so anything
beyond it is a change the filer made (Meta's 0.8% capex change counts; a same-day amendment that re-rounds does not).
Nothing else holds a threshold; `docs/DATA_DICTIONARY.md` names the constant on every `basis` and `restated` column.

## Open questions for Kenny

1. ~~Keep `group` as a non-standard reading aid, or drop it?~~ Dropped in schema v11 (T9); `layer` stays as the reading aid.
2. `ppe_additions_by_type` reports the change in a gross balance. It is arithmetic on reported figures, not an estimate,
   but it is one step from a reported number. Keep as spent, or move to a `derived` measure?
3. Projects: keep as planned rows (verbatim), or park until something verifies them?
