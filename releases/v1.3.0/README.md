# Capex Ledger v1.3.0

Revenue, capex and opex for 30 companies, fiscal years FY2022–FY2026, read from their 10-K filings. Every value points at the exact cell of the filing it came from, was re-read on the filing as rendered, and was compared with the company's own XBRL data. A person reviewed what code could not settle and signed this release.

## Files

- `values.csv`: one row per company, field and fiscal year.
- `facts.csv`: facts from the notes: capex and revenue per segment, property and equipment by category, finance lease liabilities, purchase commitments; `xbrl` says whether the filing's own tagged fact agrees.
- `attribution.csv`: AI's part of capex and opex per company and fiscal year, with the method (a stated share or amount, segment capex, growth in the server category, the whole business, or words only), the inputs behind the number and the money-flow model version.
- `ai_spend.csv`: what each 10-K's MD&A says about AI's part of capex and opex, one row per company, field, fiscal year and kind, with the sentence quoted.
- `QUALITY.md`: how many values agree with XBRL, what a person checked, and every note on definitions and restatements.
- `DIFF.md`: what changed since the previous release.
- `manifest.json`: the content hash, the prompt, parser and rule versions, and the number of decisions applied.
- `SIGNOFF.json`: who signed, when, and the hash they signed.

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

## Columns of attribution.csv

| Column | Meaning |
|---|---|
| `method` | `stated_share` / `stated_amount`: the company said so. `segment`: the AI segment's capex (ASC 280). `ppe_category`: year-on-year growth in the server and network category (all server growth, not only AI). `whole_business`: a single-segment AI business. `qualitative`: words only, no number. `none`: nothing links the spend to AI. |
| `ai_amount`, `ai_share` | AI dollars and their share of the company's capex or opex; blank for `qualitative` and `none`. |
| `confidence` | 0 to 1, within the model's ceiling for the method. |
| `model`, `inputs`, `basis` | The money-flow model version, the ids of the values, facts and statements the number rests on, and the arithmetic in words. |

## Columns of ai_spend.csv

| Column | Meaning |
|---|---|
| `kind` | `actual`: the fiscal year the filing reports. `outlook`: a later year the filing speaks to. |
| `scope` | `ai`: the figure is the AI part. `total`: the company's whole capex or opex, with AI named as a driver; **not** AI spend. |
| `class` | `explicit_amount` (dollars in `amount_low`, `amount_high`), `explicit_share` (`share`, 0 to 1), or `qualitative` (words only). |
| `ai_amount` | AI dollars only where the filing supports one: the midpoint of an explicit AI amount, or an explicit AI share × the released value. Blank otherwise. |
| `source` | `mdna` (10-K Item 7), `earnings_release` (8-K Exhibit 99.1), `transcript` or `cfo_commentary` (the company's investor page). |
| `quote` | The sentence, verbatim from the source. |

## Verify it yourself

The hash in `manifest.json` is SHA-256 over the files it lists, so the packet can be checked against the signature. Each citation names a public filing on sec.gov; open the accession number, find the row and column, and the cell text should match.

Companies: AAPL, ALAB, AMD, AMZN, ANET, APLD, AVGO, CIFR, COMP, CORZ, CRDO, CRWV, CSCO, GOOGL, IBM, INTC, IREN, JPM, META, MRVL, MSFT, MU, NVDA, ORCL, QCOM, TSLA, TXN, WMT, WULF, XOM.
