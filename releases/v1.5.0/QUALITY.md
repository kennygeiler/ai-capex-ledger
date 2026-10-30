# v1.5.0

1218 values · 1076 from agents · 0 overridden · 142 missing · 993 agree with XBRL · 45 on a restated basis · 142 blank because the company reports no such line

AI spend (ai_spend.csv): 476 statements for 77 companies on what the 10-K's MD&A says about AI's part of capex and opex; 140 give an AI dollar amount, 48 give the company's total with AI as a driver, 282 are words only. Every row quotes its sentence.

Facts from the notes (facts.csv): 4635 values for 96 companies: 376 segment_capex, 1510 segment_revenue, 2575 ppe_category, 91 finance_lease_liability, 83 purchase_commitments. 1742 agree with the filing's own XBRL, 95 differ, 2798 have no tagged counterpart. Every value cites its cell.

AI attribution (attribution.csv): 676 rows for 93 companies, 161 with an AI dollar amount, by method: 262 qualitative, 253 none, 81 segment, 36 stated_amount, 23 ppe_category, 9 whole_business, 7 stated_share, 5 commitment. Each number names its inputs and the money-flow model version; code recomputed every one.

Evaluation (EVALUATION.md): against 26 sourced reference figures for AI's part of capex, we have a number for 20: 13 agree, 7 disagree; 6 have no estimate from us. The set is small and says so.

Verified: 983 values by two independent sources (the 10-K cell and XBRL agree). 93 more confirmed on the filing (83 that XBRL can't vouch for, 10 random spot-checks of the agreeing ones): by re-reading the rendered 10-K where it confirms the cited cell, by a person where it can't. Re-read confirmed 1768 of 1801 cited cells.

All gates passed: G1 Every filing ended in a valid output or a logged failure, and no failure is open; G4 No block exception without a current decision; G5 Every value XBRL can't vouch for, plus a random sample of those it can, confirmed on the filing at the value being released: by the re-read of the rendered 10-K, or by a person where it can't.

## Notes

- ACLS capex: capex is read from 'Expenditures for property, plant and equipment and capitalized software' (15 values), which differs from the field definition; note it when comparing companies
- ANET capex: capex is read from 'Purchases of property, equipment and intangible assets' (12 values), which differs from the field definition; note it when comparing companies
- APLD capex: capex is read from 'Purchases of property and equipment and other assets' (10 values), which differs from the field definition; note it when comparing companies
- BTBT capex: capex is read from 'Purchases of and deposits made for property, plant and equipment' (6 values), which differs from the field definition; note it when comparing companies
- CLSK cost_of_revenue: cost_of_revenue is read from 'Cost of revenues (exclusive of depreciation and amortization shown below)' (7 values), which differs from the field definition; note it when comparing companies
- CLS capex: capex is read from 'Purchase of computer software and property, plant and equipment' (3 values), which differs from the field definition; note it when comparing companies
- CRWV capex: capex is read from 'Purchase of property and equipment, including capitalized internal-use software' (3 values), which differs from the field definition; note it when comparing companies
- DELL capex: capex is read from 'Capital expenditures and capitalized software development costs' (15 values), which differs from the field definition; note it when comparing companies
- GEV capex: capex is read from 'Additions to property, plant, and equipment and internal-use software' (6 values), which differs from the field definition; note it when comparing companies
- GLXY capex: capex is read from 'Purchase of property, equipment and intangible assets' (3 values), which differs from the field definition; note it when comparing companies
- HPE capex: capex is read from 'Investment in property, plant and equipment and software assets' (6 values), which differs from the field definition; note it when comparing companies
- IREN capex: capex is read from 'Payments for property, plant and equipment, net of computer hardware' (3 values), which differs from the field definition; note it when comparing companies
- IRM cost_of_revenue: cost_of_revenue is read from 'Cost of sales (excluding depreciation and amortization)' (12 values), which differs from the field definition; note it when comparing companies
- LRCX capex: capex is read from 'Capital expenditures and intangible assets' (15 values), which differs from the field definition; note it when comparing companies
- NVDA capex: capex is read from 'Purchases related to property and equipment and intangible assets' (15 values), which differs from the field definition; note it when comparing companies
- PENG capex: capex is read from 'Capital expenditures and deposits on equipment' (15 values), which differs from the field definition; note it when comparing companies
- RIOT capex: capex is read from 'Purchases of property and equipment, including construction in progress' (12 values), which differs from the field definition; note it when comparing companies
- SMCI capex: capex is read from 'Purchases of property, plant, and equipment (including payments to related parties of $12,567, $17,677, and $10,625 in fiscal years 2026, 2025, and 2024, respectively)' (3 values), which differs from the field definition; note it when comparing companies
- SYM capex: capex is read from 'Purchases of property and equipment and capitalization of internal use software development costs' (3 values), which differs from the field definition; note it when comparing companies
- TER cost_of_revenue: cost_of_revenue is read from 'Total cost of revenues (exclusive of acquired intangible assets amortization shown separately below)' (6 values), which differs from the field definition; note it when comparing companies
- TMUS capex: capex is read from 'Purchases of property and equipment, including capitalized interest of $(43), $(34) and $(104)' (3 values), which differs from the field definition; note it when comparing companies
- TSLA capex: capex is read from 'Purchases of property and equipment excluding finance leases, net of sales' (12 values), which differs from the field definition; note it when comparing companies
- UBER cost_of_revenue: cost_of_revenue is read from 'Cost of revenue, exclusive of depreciation and amortization shown separately below' (11 values), which differs from the field definition; note it when comparing companies
- VST capex: capex is read from 'Capital expenditures, including nuclear fuel purchases and LTSA prepayments' (6 values), which differs from the field definition; note it when comparing companies
- VZ capex: capex is read from 'Capital expenditures (including capitalized software)' (12 values), which differs from the field definition; note it when comparing companies
- WULF capex: capex is read from 'Purchase of and deposits on plant and equipment' (9 values), which differs from the field definition; note it when comparing companies
- WULF cost_of_revenue: cost_of_revenue is read from 'Cost of revenue (exclusive of depreciation shown below)' (9 values), which differs from the field definition; note it when comparing companies
- ARM : ARM has filed no 10-K for any year from FY2022 on (it may be newly public)
- BTDR : BTDR has filed no 10-K for any year from FY2022 on (it may be newly public)
- CRWV : no 10-K shows FY2022: the company's 10-Ks start at FY2023
- GLXY : no 10-K shows FY2022: the company's 10-Ks start at FY2023
- IREN : no 10-K shows FY2022: the company's 10-Ks start at FY2023
- NBIS : NBIS has filed no 10-K for any year from FY2022 on (it may be newly public)
- SNDK : no 10-K shows FY2022: the company's 10-Ks start at FY2023
- SPCX : SPCX has filed no 10-K for any year from FY2022 on (it may be newly public)
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
- CIFR capex: capex FY2022 2022-01-01..2022-12-31 differs between filings: 39,815,000 (0000950170-23-007793), 39,219,000 (0000950170-24-025442)
- CIFR operating_income: operating_income FY2023 2023-01-01..2023-12-31 differs between filings: -20,115,000 (0000950170-24-025442), -20,115,000 (0001819989-25-000005), -25,534,000 (0001819989-26-000009)
- CIFR operating_income: operating_income FY2024 2024-01-01..2024-12-31 differs between filings: -43,699,000 (0001819989-25-000005), -44,635,000 (0001819989-26-000009)
- CLSK operating_income: operating_income FY2022 2021-10-01..2022-09-30 differs between filings: -37,864,921 (0000950170-22-026564), -37,864,000 (0000950170-23-067339), -37,864,000 (0000950170-24-132565)
- CLSK revenue: revenue FY2022 2021-10-01..2022-09-30 differs between filings: 131,524,445 (0000950170-22-026564), 131,525,000 (0000950170-23-067339), 131,525,000 (0000950170-24-132565)
- CORZ operating_income: operating_income FY2024 2024-01-01..2024-12-31 differs between filings: -19,196,000 (0001628280-25-008302), -142,065,000 (0001628280-26-013232), -142,065,000 (0001628280-26-013305)
- DELL cost_of_revenue: cost_of_revenue FY2024 2023-02-04..2024-02-02 differs between filings: 67,556,000,000 (0001571996-24-000036), 67,356,000,000 (0001571996-25-000034), 67,356,000,000 (0001571996-26-000008)
- DELL operating_income: operating_income FY2024 2023-02-04..2024-02-02 differs between filings: 5,211,000,000 (0001571996-24-000036), 5,411,000,000 (0001571996-25-000034), 5,411,000,000 (0001571996-26-000008)
- EQIX cost_of_revenue: cost_of_revenue FY2022 2022-01-01..2022-12-31 differs between filings: 3,751,501,000 (0001628280-23-004039), 3,751,501,000 (0001628280-24-005350), 3,751,000,000 (0001628280-25-005126)
- EQIX operating_income: operating_income FY2022 2022-01-01..2022-12-31 differs between filings: 1,200,528,000 (0001628280-23-004039), 1,200,528,000 (0001628280-24-005350), 1,200,000,000 (0001628280-25-005126)
- INTC capex: capex FY2022 2021-12-26..2022-12-31 differs between filings: 23,724,000,000 (0000050863-23-000006), 23,724,000,000 (0000050863-24-000010), 24,844,000,000 (0000050863-25-000009)
- INTC capex: capex FY2023 2023-01-01..2023-12-30 differs between filings: 23,228,000,000 (0000050863-24-000010), 25,750,000,000 (0000050863-25-000009), 25,750,000,000 (0000050863-26-000011)
- JCI capex: capex FY2022 2021-10-01..2022-09-30 differs between filings: 592,000,000 (0000833444-22-000043), 592,000,000 (0000833444-23-000048), 487,000,000 (0000833444-24-000064)
- JCI capex: capex FY2023 2022-10-01..2023-09-30 differs between filings: 539,000,000 (0000833444-23-000048), 446,000,000 (0000833444-24-000064), 446,000,000 (0000833444-25-000097)
- JCI cost_of_revenue: cost_of_revenue FY2022 2021-10-01..2022-09-30 differs between filings: 16,956,000,000 (0000833444-22-000043), 16,956,000,000 (0000833444-23-000048), 13,547,000,000 (0000833444-24-000064)
- JCI cost_of_revenue: cost_of_revenue FY2023 2022-10-01..2023-09-30 differs between filings: 17,822,000,000 (0000833444-23-000048), 14,527,000,000 (0000833444-24-000064), 14,527,000,000 (0000833444-25-000097)
- JCI revenue: revenue FY2022 2021-10-01..2022-09-30 differs between filings: 25,299,000,000 (0000833444-22-000043), 25,299,000,000 (0000833444-23-000048), 20,637,000,000 (0000833444-24-000064)
- JCI revenue: revenue FY2023 2022-10-01..2023-09-30 differs between filings: 26,793,000,000 (0000833444-23-000048), 22,331,000,000 (0000833444-24-000064), 22,331,000,000 (0000833444-25-000097)
- MARA cost_of_revenue: cost_of_revenue FY2022 2022-01-01..2022-12-31 differs between filings: 151,426,000 (0001493152-23-007879), 151,424,000 (0001628280-24-007680)
- MARA cost_of_revenue: cost_of_revenue 2021-01-01..2021-12-31 differs between filings: 42,395,000 (0001493152-23-007879), 42,396,000 (0001628280-24-007680)
- MARA operating_income: operating_income FY2022 2022-01-01..2022-12-31 differs between filings: -663,868,000 (0001493152-23-007879), -673,543,000 (0001628280-24-007680)
- MARA operating_income: operating_income 2021-01-01..2021-12-31 differs between filings: -12,663,000 (0001493152-23-007879), -2,988,000 (0001628280-24-007680), -2,988,000 (0001628280-24-025261)
- META capex: capex FY2022 2022-01-01..2022-12-31 differs between filings: 31,431,000,000 (0001326801-23-000013), 31,431,000,000 (0001326801-24-000012), 31,186,000,000 (0001326801-25-000017)
- META capex: capex FY2023 2023-01-01..2023-12-31 differs between filings: 27,266,000,000 (0001326801-24-000012), 27,045,000,000 (0001326801-25-000017), 27,045,000,000 (0001628280-26-003942)
- NVT capex: capex FY2022 2022-01-01..2022-12-31 differs between filings: 45,900,000 (0001720635-23-000009), 45,900,000 (0001720635-24-000012), 40,500,000 (0001720635-25-000018)
- NVT capex: capex FY2023 2023-01-01..2023-12-31 differs between filings: 65,600,000 (0001628280-26-008608), 71,000,000 (0001720635-24-000012), 65,600,000 (0001720635-25-000018)
- NVT cost_of_revenue: cost_of_revenue FY2022 2022-01-01..2022-12-31 differs between filings: 1,812,300,000 (0001720635-23-000009), 1,812,300,000 (0001720635-24-000012), 1,472,200,000 (0001720635-25-000018)
- NVT cost_of_revenue: cost_of_revenue FY2023 2023-01-01..2023-12-31 differs between filings: 1,593,700,000 (0001628280-26-008608), 1,921,500,000 (0001720635-24-000012), 1,593,700,000 (0001720635-25-000018)
- NVT operating_income: operating_income FY2022 2022-01-01..2022-12-31 differs between filings: 440,400,000 (0001720635-23-000009), 440,400,000 (0001720635-24-000012), 309,000,000 (0001720635-25-000018)
- NVT operating_income: operating_income FY2023 2023-01-01..2023-12-31 differs between filings: 462,700,000 (0001628280-26-008608), 587,400,000 (0001720635-24-000012), 462,700,000 (0001720635-25-000018)
- NVT revenue: revenue FY2022 2022-01-01..2022-12-31 differs between filings: 2,909,000,000 (0001720635-23-000009), 2,909,000,000 (0001720635-24-000012), 2,295,100,000 (0001720635-25-000018)
- NVT revenue: revenue FY2023 2023-01-01..2023-12-31 differs between filings: 2,668,900,000 (0001628280-26-008608), 3,263,600,000 (0001720635-24-000012), 2,668,900,000 (0001720635-25-000018)
- PENG capex: capex FY2022 2021-08-28..2022-08-26 differs between filings: 38,153,000 (0001628280-22-026409), 20,359,000 (0001628280-23-034807), 20,359,000 (0001628280-24-043646)
- PENG capex: capex 2020-08-29..2021-08-27 differs between filings: 47,580,000 (0001628280-22-026409), 16,669,000 (0001628280-23-034807)
- PENG cost_of_revenue: cost_of_revenue FY2022 2021-08-28..2022-08-26 differs between filings: 1,366,132,000 (0001628280-22-026409), 1,004,831,000 (0001628280-23-034807), 1,004,831,000 (0001628280-24-043646)
- PENG cost_of_revenue: cost_of_revenue 2020-08-29..2021-08-27 differs between filings: 1,192,762,000 (0001628280-22-026409), 817,556,000 (0001628280-23-034807)
- PENG operating_income: operating_income FY2022 2021-08-28..2022-08-26 differs between filings: 114,509,000 (0001628280-22-026409), 67,176,000 (0001628280-23-034807), 67,176,000 (0001628280-24-043646)
- PENG operating_income: operating_income 2020-08-29..2021-08-27 differs between filings: 55,197,000 (0001628280-22-026409), -15,706,000 (0001628280-23-034807)
- PENG revenue: revenue FY2022 2021-08-28..2022-08-26 differs between filings: 1,819,352,000 (0001628280-22-026409), 1,395,876,000 (0001628280-23-034807), 1,395,876,000 (0001628280-24-043646)
- PENG revenue: revenue 2020-08-29..2021-08-27 differs between filings: 1,501,142,000 (0001628280-22-026409), 1,055,529,000 (0001628280-23-034807)
- SLNH capex: capex FY2024 2024-01-01..2024-12-31 differs between filings: 8,853,000 (0001628280-26-021847), 9,160,000 (0001641172-25-001756)
- SNPS capex: capex FY2024 2023-11-01..2024-10-31 differs between filings: 123,161,000 (0000883241-24-000024), 139,500,000 (0000883241-25-000028)
- SNPS cost_of_revenue: cost_of_revenue FY2022 2021-11-01..2022-10-31 differs between filings: 1,063,697,000 (0000883241-22-000017), 1,063,697,000 (0000883241-23-000019), 898,013,000 (0000883241-24-000024)
- SNPS cost_of_revenue: cost_of_revenue FY2023 2022-11-01..2023-10-31 differs between filings: 1,222,193,000 (0000883241-23-000019), 1,030,843,000 (0000883241-24-000024), 1,030,843,000 (0000883241-25-000028)
- SNPS operating_income: operating_income FY2022 2021-11-01..2022-10-31 differs between filings: 1,162,038,000 (0000883241-22-000017), 1,162,038,000 (0000883241-23-000019), 1,148,714,000 (0000883241-24-000024)
- SNPS operating_income: operating_income FY2023 2022-11-01..2023-10-31 differs between filings: 1,269,259,000 (0000883241-23-000019), 1,273,239,000 (0000883241-24-000024), 1,273,239,000 (0000883241-25-000028)
- SNPS revenue: revenue FY2022 2021-11-01..2022-10-31 differs between filings: 5,081,542,000 (0000883241-22-000017), 5,081,542,000 (0000883241-23-000019), 4,615,714,000 (0000883241-24-000024)
- SNPS revenue: revenue FY2023 2022-11-01..2023-10-31 differs between filings: 5,842,619,000 (0000883241-23-000019), 5,318,014,000 (0000883241-24-000024), 5,318,014,000 (0000883241-25-000028)
- SYM capex: capex FY2023 2022-09-25..2023-09-30 differs between filings: 15,688,000 (0001837240-23-000189), 15,688,000 (0001837240-24-000232), 21,326,000 (0001837240-25-000278)
- SYM capex: capex FY2024 2023-10-01..2024-09-28 differs between filings: 42,237,000 (0001837240-24-000232), 44,374,000 (0001837240-25-000278)
- TSLA capex: capex FY2023 2023-01-01..2023-12-31 differs between filings: 8,898,000,000 (0001628280-24-002390), 8,898,000,000 (0001628280-25-003063), 8,899,000,000 (0001628280-26-003952)
- TSLA capex: capex FY2024 2024-01-01..2024-12-31 differs between filings: 11,339,000,000 (0001628280-25-003063), 11,342,000,000 (0001628280-26-003952)
- T capex: capex FY2022 2022-01-01..2022-12-31 differs between filings: 19,626,000 (0000732717-23-000011), 19,626,000,000 (0000732717-24-000009), 19,626,000,000 (0000732717-25-000013)
- T capex: capex 2021-01-01..2021-12-31 differs between filings: 15,545,000 (0000732717-23-000011), 15,545,000,000 (0000732717-24-000009)
- T cost_of_revenue_part: cost_of_revenue_part (Other cost of revenues (exclusive of depreciationand amortization shown separately below)) FY2022 2022-01-01..2022-12-31 differs between filings: 26,839,000 (0000732717-23-000011), 26,839,000,000 (0000732717-24-000009), 26,839,000,000 (0000732717-25-000013)
- T cost_of_revenue_part: cost_of_revenue_part (Other cost of revenues (exclusive of depreciationand amortization shown separately below)) 2021-01-01..2021-12-31 differs between filings: 28,616,000 (0000732717-23-000011), 28,616,000,000 (0000732717-24-000009)
- T operating_income: operating_income FY2022 2022-01-01..2022-12-31 differs between filings: -4,587,000 (0000732717-23-000011), -4,587,000,000 (0000732717-24-000009), -4,587,000,000 (0000732717-25-000013)
- T operating_income: operating_income 2021-01-01..2021-12-31 differs between filings: 25,897,000 (0000732717-23-000011), 25,897,000,000 (0000732717-24-000009)
- T revenue: revenue FY2022 2022-01-01..2022-12-31 differs between filings: 120,741,000 (0000732717-23-000011), 120,741,000,000 (0000732717-24-000009), 120,741,000,000 (0000732717-25-000013)
- T revenue: revenue 2021-01-01..2021-12-31 differs between filings: 134,038,000 (0000732717-23-000011), 134,038,000,000 (0000732717-24-000009)
- WDC cost_of_revenue: cost_of_revenue FY2023 2022-07-02..2023-06-30 differs between filings: 10,431,000,000 (0000106040-23-000024), 10,431,000,000 (0000106040-24-000031), 4,864,000,000 (0000106040-25-000038)
- WDC cost_of_revenue: cost_of_revenue FY2024 2023-07-01..2024-06-28 differs between filings: 10,058,000,000 (0000106040-24-000031), 4,544,000,000 (0000106040-25-000038), 4,544,000,000 (0001628280-26-057139)
- WDC operating_income: operating_income FY2023 2022-07-02..2023-06-30 differs between filings: -1,285,000,000 (0000106040-23-000024), -1,285,000,000 (0000106040-24-000031), -548,000,000 (0000106040-25-000038)
- WDC operating_income: operating_income FY2024 2023-07-01..2024-06-28 differs between filings: -317,000,000 (0000106040-24-000031), -403,000,000 (0000106040-25-000038), -403,000,000 (0001628280-26-057139)
- WDC revenue: revenue FY2023 2022-07-02..2023-06-30 differs between filings: 12,318,000,000 (0000106040-23-000024), 12,318,000,000 (0000106040-24-000031), 6,255,000,000 (0000106040-25-000038)
- WDC revenue: revenue FY2024 2023-07-01..2024-06-28 differs between filings: 13,003,000,000 (0000106040-24-000031), 6,317,000,000 (0000106040-25-000038), 6,317,000,000 (0001628280-26-057139)
