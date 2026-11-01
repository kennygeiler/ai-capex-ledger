# v1.8.0

81 values · 71 from agents · 0 overridden · 10 missing · 70 agree with XBRL · 6 on a restated basis · 10 blank because the company reports no such line

AI spend (ai_spend.csv): 71 statements for 6 companies on what the 10-K's MD&A says about AI's part of capex and opex; 25 give a stated AI amount or share, 8 give the company's total with AI as a driver, 38 are words only. Every row quotes its sentence.

Facts from the notes (facts.csv): 327 values for 6 companies: 10 segment_capex, 124 segment_revenue, 171 ppe_category, 10 finance_lease_liability, 12 purchase_commitments. 180 agree with the filing's own XBRL, 5 differ, 142 have no tagged counterpart. Every value cites its cell.

Verified: 60 values by two independent sources (the 10-K cell and XBRL agree). 11 more confirmed on the filing (1 that XBRL can't vouch for, 10 random spot-checks of the agreeing ones): by re-reading the rendered 10-K where it confirms the cited cell, by a person where it can't. Re-read confirmed 118 of 118 cited cells.

All gates passed: G1 Every filing ended in a valid output or a logged failure, and no failure is open; G4 No block exception without a current decision; G5 Every value XBRL can't vouch for, plus a random sample of those it can, confirmed on the filing at the value being released: by the re-read of the rendered 10-K, or by a person where it can't; G6 No decision left by a run for a person to confirm (decisions/resolutions.jsonl, 'to confirm').

## Notes

- APLD capex: capex is read from 'Purchases of property and equipment and other assets' (10 values), which differs from the field definition; note it when comparing companies
- NVDA capex: capex is read from 'Purchases related to property and equipment and intangible assets' (15 values), which differs from the field definition; note it when comparing companies
- AMD cost_of_revenue: cost_of_revenue FY2024 2023-12-31..2024-12-28 differs between filings: 13,060,000,000 (0000002488-26-000018), 12,114,000,000 (0000002488-26-000021)
- AMD cost_of_revenue: cost_of_revenue FY2025 2024-12-29..2025-12-27 differs between filings: 17,487,000,000 (0000002488-26-000018), 16,456,000,000 (0000002488-26-000021)
- APLD capex: capex FY2022 2021-06-01..2022-05-31 differs between filings: 54,974,000 (0001144879-23-000176), 58,251,000 (0001628280-22-023816)
- APLD capex: capex FY2023 2022-06-01..2023-05-31 differs between filings: 128,721,000 (0001144879-23-000176), 131,278,000 (0001144879-24-000216), 131,278,000 (0001144879-25-000021)
- APLD cost_of_revenue: cost_of_revenue FY2024 2023-06-01..2024-05-31 differs between filings: 148,340,000 (0001144879-24-000216), 106,653,000 (0001144879-25-000021)
- APLD operating_income: operating_income FY2023 2022-06-01..2023-05-31 differs between filings: -44,055,000 (0001144879-23-000176), -44,055,000 (0001144879-24-000216), -42,911,000 (0001144879-25-000021)
- APLD operating_income: operating_income FY2024 2023-06-01..2024-05-31 differs between filings: -99,023,000 (0001144879-24-000216), -32,852,000 (0001144879-25-000021), -98,338,000 (0001144879-26-000048)
- APLD operating_income: operating_income FY2025 2024-06-01..2025-05-31 differs between filings: -16,845,000 (0001144879-25-000021), -72,175,000 (0001144879-26-000048)
- APLD revenue: revenue FY2024 2023-06-01..2024-05-31 differs between filings: 165,575,000 (0001144879-24-000216), 136,618,000 (0001144879-25-000021), 165,575,000 (0001144879-26-000048)
- APLD revenue: revenue FY2025 2024-06-01..2025-05-31 differs between filings: 144,193,000 (0001144879-25-000021), 228,569,000 (0001144879-26-000048)
