# Capex Ledger v1.8.0

Revenue, capex and opex for 6 companies, fiscal years FY2022–FY2026, read from their 10-K filings. Every value points at the exact cell of the filing it came from, was re-read on the filing as rendered, and was compared with the company's own XBRL data. A person reviewed what code could not settle and signed this release.

Nothing here is estimated. `taxonomy.csv` is the dataset in one shape: each row an instance of a published standard concept (us-gaap for spent, committed and derived; Regulation S-K for planned), the company's own label beside it, and for AI only what the company itself stated, quoted. See docs/TAXONOMY.md in the repository.

## Files

- `taxonomy.csv`: one row per company, fiscal year, measure (spent, committed, derived, planned, company_stated_ai) and category; `standard_concept` names the standard, `reported_name` the company's label, `check` and `check_method` how the number was verified, `source_url` the filing at the cited row's words, `source_table` the parsed table, `proven` whether the company is in the proven set. Columns below.
- `companies.csv`: the tracked companies with layer, role and the SEC's SIC code.
- `statements.csv`: guidance and AI statements, quoted, with the source document and date.
- `projects.csv`: named projects the filings and releases mention, verbatim.
- `values.csv`: one row per company, field and fiscal year.
- `facts.csv`: facts from the notes: capex and revenue per segment, property and equipment by category, finance lease liabilities, purchase commitments; `xbrl` says whether the filing's own tagged fact agrees.
- `ai_spend.csv`: what each 10-K's MD&A says about AI's part of capex and opex, one row per company, field, fiscal year and kind, with the sentence quoted.
- `QUALITY.md`: how many values agree with XBRL, what a person checked, and every note on definitions and restatements.
- `DIFF.md`: what changed since the previous release.
- `manifest.json`: the content hash, the prompt, parser and rule versions, and the number of decisions applied.
- `SIGNOFF.json`: who signed, when, and the hash they signed.

## Columns of taxonomy.csv

One meaning per column (schema v11). Every amount is in whole units (`scale` 1) of US dollars (`currency` USD); `value_high` is only a range high, `change_from_prior` only the derived year-over-year change; a reported row carries its `period_end`, a verbatim row its `quote`; `source` is the internal id and `accession`, `filed`, `source_table`, `source_url`, `source_kind` follow it to the filing. `layer` is the supply-chain layer the company was picked under, a reading aid, not a standard.

| Column | Allowed values | Meaning |
|---|---|---|
| `ticker` |  | Company ticker, e.g. NVDA. |
| `fiscal_year` |  | The company's fiscal year label, e.g. FY2025. |
| `period_end` |  | The fiscal period's last day, from the company's own fiscal calendar (the 10-K that reports that year), on every row whose period_kind is reported; empty on a planned row. |
| `period_kind` | `reported`, `planned` | reported: the figure is for a fiscal period that had ended when the source was written. planned: the period's end is after the source's date, or the calendar does not know it yet. |
| `measure` | `spent`, `committed`, `derived`, `planned`, `company_stated_ai` | spent, committed, derived (a reported balance and its arithmetic change), planned (verbatim) or company_stated_ai (verbatim). |
| `category` |  | The taxonomy id (taxonomy/taxonomy.yaml): capex, segment_capex, segment_revenue, purchase_obligations, finance_lease_liability, ppe_gross_by_type, guidance, project, ai_capex, ai_opex, ai_revenue. |
| `reported_name` |  | The company's own label: the line, segment, asset type, project or statement as written. |
| `standard_concept` |  | The us-gaap concept (and axis) the row is an instance of; 'forward-looking statement (Reg S-K)' for guidance; 'none: ...' for a verbatim row with no standard. |
| `standard_type` |  | For an asset type: the us-gaap PropertyPlantAndEquipmentByTypeAxis member it maps to (taxonomy/asset_types.yaml). Empty elsewhere, and on an unmapped asset type. |
| `mapped` |  | False exactly when check is unmapped: a reported asset type with no entry in taxonomy/asset_types.yaml. True on every other row. |
| `value` |  | The figure as reported or quoted, in `unit`: a dollar amount, or the low end of a stated range. Empty when the company gave no figure (has_value false) or stated a share instead. |
| `value_high` |  | The high end of a stated range, on planned and company_stated_ai rows only, and only when the range has two ends. Never anything else. |
| `change_from_prior` |  | On derived rows only: this year's reported gross balance minus the prior year's, for the same asset type. Arithmetic on two reported figures; empty on the first year. |
| `share` |  | A share the company stated, 0 to 1, on company_stated_ai rows whose unit is share. Empty elsewhere. |
| `relation` | `eq`, `ge`, `le` | On a gathered figure: how the company's words relate to value or share: eq (the figure), ge (at least), le (at most). Empty elsewhere. |
| `has_value` |  | True when the row carries a figure (value or share). False on a project or statement the company named without an amount. |
| `unit` | `USD`, `share` | USD for a dollar amount; share for a stated share. Empty when has_value is false. A project's capacity is in capacity_mw, in megawatts. |
| `scale` |  | Always 1: every amount is in whole units (whole dollars, a share of one, megawatts). |
| `currency` | `USD` | Always USD: the currency of value, value_high and change_from_prior. |
| `period_as_stated` |  | On a verbatim row: the period the company named, as the reader labelled it (the fiscal year). Empty on reported rows. |
| `quote` |  | On a verbatim row: the sentence, as written in the source. Empty on reported rows. |
| `kind` | `actual`, `outlook` | On a company_stated_ai statement read from a text: actual (the period the text reports) or outlook (a later period). Empty elsewhere. |
| `project_kind` | `data_center`, `fab`, `plant`, `power`, `gpu_cluster`, `cloud_commitment`, `network`, `other` | On a project: data_center, fab, plant, power, gpu_cluster, cloud_commitment, network or other. Empty elsewhere. |
| `status` | `announced`, `under_construction`, `in_service`, `contracted`, `cancelled` | On a project: announced, under_construction, in_service, contracted or cancelled, as stated. Empty elsewhere. |
| `location` |  | On a project: the place as stated. Empty elsewhere. |
| `capacity_mw` |  | On a project: megawatts when stated. Empty elsewhere. |
| `forward_looking` |  | On a statement read from a text: True for guidance and an outlook statement (a forward-looking statement under Regulation S-K), False for a figure the text reports as actual. Empty where the source does not say: spent, committed and derived rows, projects, gathered figures. |
| `part_year` |  | On a statement read from a text: True when its words cover part of a year (a quarter, a half), by rules/guards; the figure is never turned into a year. Empty elsewhere. |
| `program` |  | On a statement read from a text: True when its words describe a multi-year program rather than a year's figure, by rules/guards. Empty elsewhere. |
| `source` |  | The internal id of what the row was read from: extraction ids (values), the fact's extraction ids (facts), a text id (statements, projects), or taxonomy/stated_figures.yaml. |
| `source_kind` | `10-K table`, `10-K note`, `10-K MD&A`, `8-K release`, `transcript`, `cfo commentary`, `gathered` | Where the figure is written: a 10-K statement table, a 10-K note, the 10-K's MD&A, an 8-K earnings release, a transcript, CFO commentary, or gathered (a figure a person recorded with its URL and quote). |
| `accession` |  | SEC accession number of the filing the row was read from. Empty when the source is not a filing. |
| `filed` |  | The date the source was filed with the SEC (documents.filed for a 10-K, the 8-K's filing date for a release). Empty for a transcript, CFO commentary or a gathered figure, which have no filing date. |
| `source_table` |  | For a 10-K cell: the id of the parsed table the cell was read from (e.g. t0035), the table DATAHQ shows; it is the parser's id, not an anchor on sec.gov. Empty elsewhere. |
| `source_url` |  | A URL that opens the source. For a 10-K cell: the filing on sec.gov with a `#:~:text=<row label>,<number>` fragment that scrolls the browser to the first place the filing shows those words, usually the row, sometimes prose; sec.gov offers no table anchor. For a statement or project: the text with the quote's first words as the fragment. For a gathered figure: the page recorded with it. |
| `check` | `agree`, `explained`, `differs`, `no_reference`, `unmapped`, `verbatim` | agree: matches the SEC's XBRL. explained: differs and something on file says why (check_method). differs: differs and nothing on file says why. no_reference: no XBRL fact to compare. unmapped: an asset type with no standard member. verbatim: a quote verified against its text. |
| `check_method` |  | What established the check, as status.py names `by`: `<kind>` or `<kind>:<id>` with the kind one of status.METHOD_KINDS: xbrl, quote, gathered, none (nothing to compare against), rule:<id>, definition:<name>, resolution:<id>, label:<label>, mapping:<member>. An open vocabulary: a later answer key adds a kind there. |

## Columns of values.csv

| Column | Meaning |
|---|---|
| `ticker`, `period` | Company and its own fiscal year (`period_end` is the year's last day; Nvidia's FY2026 ended 25 Jan 2026). |
| `field` | `revenue`: total revenue or net sales. `capex`: cash paid for property and equipment. `opex`: revenue − cost of revenue − operating income, all from the same 10-K column; it includes impairments and other operating items, so it can exceed revenue. |
| `value` | Whole US dollars, unscaled. Blank when the 10-K has no such line (`source` = missing) or a reviewer rejected it. |
| `basis`, `first_reported` | `restated` when a later 10-K changed the figure; `first_reported` keeps the first one. |
| `source` | `agent`: read from the filing by the agent and checked. `override`: a reviewer replaced it, with a recorded reason. |
| `xbrl` | `agree`: matches the company's XBRL data. `definition_gap`: differs only in which lines count as cost of revenue, confirmed by a reviewer. `unresolved`: differs; a reviewer decided. `not_reported`: no line to read. |
| `citations` | The filing's accession number, table, row label, column label and the cell text, for every cell behind the value. |

## Columns of ai_spend.csv

| Column | Meaning |
|---|---|
| `kind` | `actual`: the fiscal year the filing reports. `outlook`: a later year the filing speaks to. |
| `scope` | `ai`: the figure is the AI part. `total`: the company's whole capex or opex, with AI named as a driver; **not** AI spend. |
| `class` | `explicit_amount` (dollars in `amount_low`, `amount_high`), `explicit_share` (`share`, 0 to 1), or `qualitative` (words only). |
| `source` | `mdna` (10-K Item 7), `earnings_release` (8-K Exhibit 99.1), `transcript` or `cfo_commentary` (the company's investor page). |
| `quote` | The sentence, verbatim from the source. |

## Verify it yourself

The hash in `manifest.json` is SHA-256 over the files it lists, so the packet can be checked against the signature. Each citation names a public filing on sec.gov; open the accession number, find the row and column, and the cell text should match.

Companies: AMD, AMZN, APLD, GOOGL, MSFT, NVDA.
