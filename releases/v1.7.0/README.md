# Capex Ledger v1.7.0

Revenue, capex and opex for 96 companies, fiscal years FY2022–FY2026, read from their 10-K filings. Every value points at the exact cell of the filing it came from, was re-read on the filing as rendered, and was compared with the company's own XBRL data. A person reviewed what code could not settle and signed this release.

Nothing here is estimated. `taxonomy.csv` is the dataset in one shape: each row an instance of a published standard concept (us-gaap for spent, committed and derived; Regulation S-K for planned), the company's own label beside it, and for AI only what the company itself stated, quoted. See docs/TAXONOMY.md in the repository.

## Files

- `taxonomy.csv`: one row per company, fiscal year, measure (spent, committed, derived, planned, company_stated_ai) and category; `standard_concept` names the standard, `reported_name` the company's label, `check` how the number was verified, `proven` whether the company is in the proven set.
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

Companies: AAOI, AAPL, ACLS, ADBE, AEIS, ALAB, AMAT, AMD, AMZN, ANET, APLD, AVGO, BE, BTBT, CDNS, CEG, CIEN, CIFR, CLS, CLSK, COHR, COMP, CORZ, CRDO, CRM, CRWV, CSCO, DDOG, DELL, DLR, EME, ENTG, EQIX, ETN, FCX, FIX, FLEX, FN, GEV, GLXY, GOOGL, HPE, HUT, IBM, INTC, IREN, IRM, JBL, JCI, JPM, KLAC, LITE, LRCX, MARA, META, MOD, MPWR, MRVL, MSFT, MU, NOW, NRG, NTAP, NVDA, NVT, ONTO, ORCL, PENG, PLTR, POWL, PWR, QCOM, RIOT, RMBS, SITM, SLNH, SMCI, SNDK, SNOW, SNPS, STX, SYM, T, TER, TLN, TMUS, TSLA, TXN, UBER, VRT, VST, VZ, WDC, WMT, WULF, XOM.
