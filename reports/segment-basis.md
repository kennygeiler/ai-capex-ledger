# Segment basis by company

Written by `scripts/segment_basis.py` from the database (ledger/checks/ties.py `segment_basis`, the analysis the `segment_basis_mixed` rule runs). For each segment and fiscal year: the value the dataset ships as the filing printed it, the filing it comes from, the newest filing that prints that year for the field, and every other reading. A re-segmentation is seen only where a later 10-K prints a segment figure differently (the cutover); a segment dropped or added with no figure printed two ways is not seen by the rule and is called out in the conclusion. No value is changed.

Release years: FY2022, FY2023, FY2024, FY2025, FY2026.

## Conclusion

- **MSFT**: segment_revenue mixes definitions: FY2022 on segments from before 10-K 2025-07-30, FY2023, FY2024, FY2025, FY2026 on the restated ones (amounts moved between segments, the total unchanged (FY2023, FY2024); seen by `segment_basis_mixed`)
- **GOOGL**: every release year of every segment series comes from the newest filing printing it, and no re-segmentation shows in the readings: one basis.
- **AMZN**: every release year of every segment series comes from the newest filing printing it, and no re-segmentation shows in the readings: one basis.
- **NVDA**: segment_revenue mixes vintages: OEM & Other in FY2022, FY2023 come from a filing older than the newest one printing that year, which does not print them (a segment dropped or renamed; no figure printed two ways, so the rule does not see it); the same figure under two names: OEM & Other / OEM and Other FY2022 1,162; OEM & Other / OEM and Other FY2023 455
- **AMD**: every release year of every segment series comes from the newest filing printing it, and no re-segmentation shows in the readings: one basis.
- **APLD**: segment_capex mixes vintages: Cloud Services Business in FY2023, FY2024 come from a filing older than the newest one printing that year, which does not print them (a segment dropped or renamed; no figure printed two ways, so the rule does not see it); segment_revenue mixes vintages: Cloud Services Business in FY2024 come from a filing older than the newest one printing that year, which does not print them (a segment dropped or renamed; no figure printed two ways, so the rule does not see it)

## MSFT

### segment_revenue

Cutover (re-segmentation): 10-K 2025-07-30 (0000950170-25-100235) printed 6 segment figures differently; amounts moved between segments, the total unchanged (FY2023, FY2024). Years on an earlier basis: FY2020, FY2021, FY2022 (in release years: FY2022). Earlier re-segmentations: 10-K 2023-07-27 (amounts moved between segments, the total unchanged (FY2021, FY2022)) restated Intelligent Cloud FY2021 60,080 → 59,728, More Personal Computing FY2021 54,093 → 54,445, Intelligent Cloud FY2022 75,251 → 74,965, More Personal Computing FY2022 59,655 → 59,941.

| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |
|---|---|---|---|---|---|---|
| Intelligent Cloud | FY2020 | 48,366 | 10-K 2022-07-28 | 10-K 2022-07-28 | — | earlier basis (before cutover) |
| More Personal Computing | FY2020 | 48,251 | 10-K 2022-07-28 | 10-K 2022-07-28 | — | earlier basis (before cutover) |
| Productivity and Business Processes | FY2020 | 46,398 | 10-K 2022-07-28 | 10-K 2022-07-28 | — | earlier basis (before cutover) |
| Intelligent Cloud | FY2021 | 59,728 | 10-K 2023-07-27 | 10-K 2023-07-27 | 60,080 (10-K 2022-07-28) | earlier basis (before cutover) |
| More Personal Computing | FY2021 | 54,445 | 10-K 2023-07-27 | 10-K 2023-07-27 | 54,093 (10-K 2022-07-28) | earlier basis (before cutover) |
| Productivity and Business Processes | FY2021 | 53,915 | 10-K 2023-07-27 | 10-K 2023-07-27 | 53,915 (10-K 2022-07-28) | earlier basis (before cutover) |
| Intelligent Cloud | FY2022 | 74,965 | 10-K 2024-07-30 | 10-K 2024-07-30 | 75,251 (10-K 2022-07-28); 74,965 (10-K 2023-07-27) | earlier basis (before cutover) |
| More Personal Computing | FY2022 | 59,941 | 10-K 2024-07-30 | 10-K 2024-07-30 | 59,655 (10-K 2022-07-28); 59,941 (10-K 2023-07-27) | earlier basis (before cutover) |
| Productivity and Business Processes | FY2022 | 63,364 | 10-K 2024-07-30 | 10-K 2024-07-30 | 63,364 (10-K 2022-07-28); 63,364 (10-K 2023-07-27) | earlier basis (before cutover) |
| Intelligent Cloud | FY2023 | 72,944 | 10-K 2025-07-30 | 10-K 2025-07-30 | 87,907 (10-K 2023-07-27); 87,907 (10-K 2024-07-30) | newest |
| More Personal Computing | FY2023 | 44,820 | 10-K 2025-07-30 | 10-K 2025-07-30 | 54,734 (10-K 2023-07-27); 54,734 (10-K 2024-07-30) | newest |
| Productivity and Business Processes | FY2023 | 94,151 | 10-K 2025-07-30 | 10-K 2025-07-30 | 69,274 (10-K 2023-07-27); 69,274 (10-K 2024-07-30) | newest |
| Intelligent Cloud | FY2024 | 87,464 | 10-K 2026-07-29 | 10-K 2026-07-29 | 105,362 (10-K 2024-07-30); 87,464 (10-K 2025-07-30) | newest |
| More Personal Computing | FY2024 | 50,838 | 10-K 2026-07-29 | 10-K 2026-07-29 | 62,032 (10-K 2024-07-30); 50,838 (10-K 2025-07-30) | newest |
| Productivity and Business Processes | FY2024 | 106,820 | 10-K 2026-07-29 | 10-K 2026-07-29 | 77,728 (10-K 2024-07-30); 106,820 (10-K 2025-07-30) | newest |
| Intelligent Cloud | FY2025 | 106,265 | 10-K 2026-07-29 | 10-K 2026-07-29 | 106,265 (10-K 2025-07-30) | newest |
| More Personal Computing | FY2025 | 54,649 | 10-K 2026-07-29 | 10-K 2026-07-29 | 54,649 (10-K 2025-07-30) | newest |
| Productivity and Business Processes | FY2025 | 120,810 | 10-K 2026-07-29 | 10-K 2026-07-29 | 120,810 (10-K 2025-07-30) | newest |
| Intelligent Cloud | FY2026 | 137,791 | 10-K 2026-07-29 | 10-K 2026-07-29 | — | newest |
| More Personal Computing | FY2026 | 54,052 | 10-K 2026-07-29 | 10-K 2026-07-29 | — | newest |
| Productivity and Business Processes | FY2026 | 139,996 | 10-K 2026-07-29 | 10-K 2026-07-29 | — | newest |

## GOOGL

### segment_revenue

No re-segmentation seen in the readings.

| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |
|---|---|---|---|---|---|---|
| Google Cloud | FY2020 | 13,059 | 10-K 2023-02-03 | 10-K 2023-02-03 | — | newest |
| Google Services | FY2020 | 168,635 | 10-K 2023-02-03 | 10-K 2023-02-03 | — | newest |
| Other Bets | FY2020 | 657 | 10-K 2023-02-03 | 10-K 2023-02-03 | — | newest |
| Google Cloud | FY2021 | 19,206 | 10-K 2024-01-31 | 10-K 2024-01-31 | 19,206 (10-K 2023-02-03) | newest |
| Google Services | FY2021 | 237,529 | 10-K 2024-01-31 | 10-K 2024-01-31 | 237,529 (10-K 2023-02-03) | newest |
| Other Bets | FY2021 | 753 | 10-K 2024-01-31 | 10-K 2024-01-31 | 753 (10-K 2023-02-03) | newest |
| Google Cloud | FY2022 | 26,280 | 10-K 2025-02-05 | 10-K 2025-02-05 | 26,280 (10-K 2023-02-03); 26,280 (10-K 2024-01-31) | newest |
| Google Services | FY2022 | 253,528 | 10-K 2025-02-05 | 10-K 2025-02-05 | 253,528 (10-K 2023-02-03); 253,528 (10-K 2024-01-31) | newest |
| Other Bets | FY2022 | 1,068 | 10-K 2025-02-05 | 10-K 2025-02-05 | 1,068 (10-K 2023-02-03); 1,068 (10-K 2024-01-31) | newest |
| Google Cloud | FY2023 | 33,088 | 10-K 2026-02-05 | 10-K 2026-02-05 | 33,088 (10-K 2024-01-31); 33,088 (10-K 2025-02-05) | newest |
| Google Services | FY2023 | 272,543 | 10-K 2026-02-05 | 10-K 2026-02-05 | 272,543 (10-K 2024-01-31); 272,543 (10-K 2025-02-05) | newest |
| Other Bets | FY2023 | 1,527 | 10-K 2026-02-05 | 10-K 2026-02-05 | 1,527 (10-K 2024-01-31); 1,527 (10-K 2025-02-05) | newest |
| Google Cloud | FY2024 | 43,229 | 10-K 2026-02-05 | 10-K 2026-02-05 | 43,229 (10-K 2025-02-05) | newest |
| Google Services | FY2024 | 304,930 | 10-K 2026-02-05 | 10-K 2026-02-05 | 304,930 (10-K 2025-02-05) | newest |
| Other Bets | FY2024 | 1,648 | 10-K 2026-02-05 | 10-K 2026-02-05 | 1,648 (10-K 2025-02-05) | newest |
| Google Cloud | FY2025 | 58,705 | 10-K 2026-02-05 | 10-K 2026-02-05 | — | newest |
| Google Services | FY2025 | 342,721 | 10-K 2026-02-05 | 10-K 2026-02-05 | — | newest |
| Other Bets | FY2025 | 1,537 | 10-K 2026-02-05 | 10-K 2026-02-05 | — | newest |

## AMZN

### segment_revenue

No re-segmentation seen in the readings.

| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |
|---|---|---|---|---|---|---|
| AWS | FY2020 | 45,370 | 10-K 2023-02-03 | 10-K 2023-02-03 | — | newest |
| International | FY2020 | 104,412 | 10-K 2023-02-03 | 10-K 2023-02-03 | — | newest |
| North America | FY2020 | 236,282 | 10-K 2023-02-03 | 10-K 2023-02-03 | — | newest |
| AWS | FY2021 | 62,202 | 10-K 2024-02-02 | 10-K 2024-02-02 | 62,202 (10-K 2023-02-03) | newest |
| International | FY2021 | 127,787 | 10-K 2024-02-02 | 10-K 2024-02-02 | 127,787 (10-K 2023-02-03) | newest |
| North America | FY2021 | 279,833 | 10-K 2024-02-02 | 10-K 2024-02-02 | 279,833 (10-K 2023-02-03) | newest |
| AWS | FY2022 | 80,096 | 10-K 2025-02-07 | 10-K 2025-02-07 | 80,096 (10-K 2023-02-03); 80,096 (10-K 2024-02-02) | newest |
| International | FY2022 | 118,007 | 10-K 2025-02-07 | 10-K 2025-02-07 | 118,007 (10-K 2023-02-03); 118,007 (10-K 2024-02-02) | newest |
| North America | FY2022 | 315,880 | 10-K 2025-02-07 | 10-K 2025-02-07 | 315,880 (10-K 2023-02-03); 315,880 (10-K 2024-02-02) | newest |
| AWS | FY2023 | 90,757 | 10-K 2026-02-06 | 10-K 2026-02-06 | 90,757 (10-K 2024-02-02); 90,757 (10-K 2025-02-07) | newest |
| International | FY2023 | 131,200 | 10-K 2026-02-06 | 10-K 2026-02-06 | 131,200 (10-K 2024-02-02); 131,200 (10-K 2025-02-07) | newest |
| North America | FY2023 | 352,828 | 10-K 2026-02-06 | 10-K 2026-02-06 | 352,828 (10-K 2024-02-02); 352,828 (10-K 2025-02-07) | newest |
| AWS | FY2024 | 107,556 | 10-K 2026-02-06 | 10-K 2026-02-06 | 107,556 (10-K 2025-02-07) | newest |
| International | FY2024 | 142,906 | 10-K 2026-02-06 | 10-K 2026-02-06 | 142,906 (10-K 2025-02-07) | newest |
| North America | FY2024 | 387,497 | 10-K 2026-02-06 | 10-K 2026-02-06 | 387,497 (10-K 2025-02-07) | newest |
| AWS | FY2025 | 128,725 | 10-K 2026-02-06 | 10-K 2026-02-06 | — | newest |
| International | FY2025 | 161,894 | 10-K 2026-02-06 | 10-K 2026-02-06 | — | newest |
| North America | FY2025 | 426,305 | 10-K 2026-02-06 | 10-K 2026-02-06 | — | newest |

## NVDA

### segment_revenue

No re-segmentation seen in the readings.

| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |
|---|---|---|---|---|---|---|
| Automotive | FY2020 | 700 | 10-K 2022-03-18 | 10-K 2022-03-18 | — | newest |
| Data Center | FY2020 | 2,983 | 10-K 2022-03-18 | 10-K 2022-03-18 | — | newest |
| Gaming | FY2020 | 5,518 | 10-K 2022-03-18 | 10-K 2022-03-18 | — | newest |
| OEM & Other | FY2020 | 505 | 10-K 2022-03-18 | 10-K 2022-03-18 | — | newest |
| Professional Visualization | FY2020 | 1,212 | 10-K 2022-03-18 | 10-K 2022-03-18 | — | newest |
| Automotive | FY2021 | 536 | 10-K 2023-02-24 | 10-K 2023-02-24 | 536 (10-K 2022-03-18) | newest |
| Data Center | FY2021 | 6,696 | 10-K 2023-02-24 | 10-K 2023-02-24 | 6,696 (10-K 2022-03-18) | newest |
| Gaming | FY2021 | 7,759 | 10-K 2023-02-24 | 10-K 2023-02-24 | 7,759 (10-K 2022-03-18) | newest |
| OEM & Other | FY2021 | 631 | 10-K 2023-02-24 | 10-K 2023-02-24 | 631 (10-K 2022-03-18) | newest |
| Professional Visualization | FY2021 | 1,053 | 10-K 2023-02-24 | 10-K 2023-02-24 | 1,053 (10-K 2022-03-18) | newest |
| Automotive | FY2022 | 566 | 10-K 2024-02-21 | 10-K 2024-02-21 | 566 (10-K 2022-03-18); 566 (10-K 2023-02-24) | newest |
| Data Center | FY2022 | 10,613 | 10-K 2024-02-21 | 10-K 2024-02-21 | 10,613 (10-K 2022-03-18); 10,613 (10-K 2023-02-24) | newest |
| Gaming | FY2022 | 12,462 | 10-K 2024-02-21 | 10-K 2024-02-21 | 12,462 (10-K 2022-03-18); 12,462 (10-K 2023-02-24) | newest |
| OEM & Other | FY2022 | 1,162 | 10-K 2023-02-24 | 10-K 2024-02-21 | 1,162 (10-K 2022-03-18) | not in the newest (10-K 2024-02-21) |
| OEM and Other | FY2022 | 1,162 | 10-K 2024-02-21 | 10-K 2024-02-21 | — | newest |
| Professional Visualization | FY2022 | 2,111 | 10-K 2024-02-21 | 10-K 2024-02-21 | 2,111 (10-K 2022-03-18); 2,111 (10-K 2023-02-24) | newest |
| Automotive | FY2023 | 903 | 10-K 2025-02-26 | 10-K 2025-02-26 | 903 (10-K 2023-02-24); 903 (10-K 2024-02-21) | newest |
| Data Center | FY2023 | 15,005 | 10-K 2025-02-26 | 10-K 2025-02-26 | 15,005 (10-K 2023-02-24); 15,005 (10-K 2024-02-21) | newest |
| Gaming | FY2023 | 9,067 | 10-K 2025-02-26 | 10-K 2025-02-26 | 9,067 (10-K 2023-02-24); 9,067 (10-K 2024-02-21) | newest |
| OEM & Other | FY2023 | 455 | 10-K 2023-02-24 | 10-K 2025-02-26 | — | not in the newest (10-K 2025-02-26) |
| OEM and Other | FY2023 | 455 | 10-K 2025-02-26 | 10-K 2025-02-26 | 455 (10-K 2024-02-21) | newest |
| Professional Visualization | FY2023 | 1,544 | 10-K 2025-02-26 | 10-K 2025-02-26 | 1,544 (10-K 2023-02-24); 1,544 (10-K 2024-02-21) | newest |
| Automotive | FY2024 | 1,091 | 10-K 2026-02-25 | 10-K 2026-02-25 | 1,091 (10-K 2024-02-21); 1,091 (10-K 2025-02-26) | newest |
| Data Center | FY2024 | 47,525 | 10-K 2026-02-25 | 10-K 2026-02-25 | 47,525 (10-K 2024-02-21); 47,525 (10-K 2025-02-26) | newest |
| Gaming | FY2024 | 10,447 | 10-K 2026-02-25 | 10-K 2026-02-25 | 10,447 (10-K 2024-02-21); 10,447 (10-K 2025-02-26) | newest |
| OEM and Other | FY2024 | 306 | 10-K 2026-02-25 | 10-K 2026-02-25 | 306 (10-K 2024-02-21); 306 (10-K 2025-02-26) | newest |
| Professional Visualization | FY2024 | 1,553 | 10-K 2026-02-25 | 10-K 2026-02-25 | 1,553 (10-K 2024-02-21); 1,553 (10-K 2025-02-26) | newest |
| Automotive | FY2025 | 1,694 | 10-K 2026-02-25 | 10-K 2026-02-25 | 1,694 (10-K 2025-02-26) | newest |
| Data Center | FY2025 | 115,186 | 10-K 2026-02-25 | 10-K 2026-02-25 | 115,186 (10-K 2025-02-26) | newest |
| Gaming | FY2025 | 11,350 | 10-K 2026-02-25 | 10-K 2026-02-25 | 11,350 (10-K 2025-02-26) | newest |
| OEM and Other | FY2025 | 389 | 10-K 2026-02-25 | 10-K 2026-02-25 | 389 (10-K 2025-02-26) | newest |
| Professional Visualization | FY2025 | 1,878 | 10-K 2026-02-25 | 10-K 2026-02-25 | 1,878 (10-K 2025-02-26) | newest |
| Automotive | FY2026 | 2,349 | 10-K 2026-02-25 | 10-K 2026-02-25 | — | newest |
| Data Center | FY2026 | 193,737 | 10-K 2026-02-25 | 10-K 2026-02-25 | — | newest |
| Gaming | FY2026 | 16,042 | 10-K 2026-02-25 | 10-K 2026-02-25 | — | newest |
| OEM and Other | FY2026 | 619 | 10-K 2026-02-25 | 10-K 2026-02-25 | — | newest |
| Professional Visualization | FY2026 | 3,191 | 10-K 2026-02-25 | 10-K 2026-02-25 | — | newest |

## AMD

### segment_revenue

No re-segmentation seen in the readings.

| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |
|---|---|---|---|---|---|---|
| Client | FY2020 | 5,189 | 10-K 2023-02-27 | 10-K 2023-02-27 | — | newest |
| Data Center | FY2020 | 1,685 | 10-K 2023-02-27 | 10-K 2023-02-27 | — | newest |
| Embedded | FY2020 | 143 | 10-K 2023-02-27 | 10-K 2023-02-27 | — | newest |
| Gaming | FY2020 | 2,746 | 10-K 2023-02-27 | 10-K 2023-02-27 | — | newest |
| Client | FY2021 | 6,887 | 10-K 2024-01-31 | 10-K 2024-01-31 | 6,887 (10-K 2023-02-27) | newest |
| Data Center | FY2021 | 3,694 | 10-K 2024-01-31 | 10-K 2024-01-31 | 3,694 (10-K 2023-02-27) | newest |
| Embedded | FY2021 | 246 | 10-K 2024-01-31 | 10-K 2024-01-31 | 246 (10-K 2023-02-27) | newest |
| Gaming | FY2021 | 5,607 | 10-K 2024-01-31 | 10-K 2024-01-31 | 5,607 (10-K 2023-02-27) | newest |
| Client | FY2022 | 6,201 | 10-K 2025-02-05 | 10-K 2025-02-05 | 6,201 (10-K 2023-02-27); 6,201 (10-K 2024-01-31) | newest |
| Data Center | FY2022 | 6,043 | 10-K 2025-02-05 | 10-K 2025-02-05 | 6,043 (10-K 2023-02-27); 6,043 (10-K 2024-01-31) | newest |
| Embedded | FY2022 | 4,552 | 10-K 2025-02-05 | 10-K 2025-02-05 | 4,552 (10-K 2023-02-27); 4,552 (10-K 2024-01-31) | newest |
| Gaming | FY2022 | 6,805 | 10-K 2025-02-05 | 10-K 2025-02-05 | 6,805 (10-K 2023-02-27); 6,805 (10-K 2024-01-31) | newest |
| Client | FY2023 | 4,651 | 10-K 2026-02-04 | 10-K 2026-02-04 | 4,651 (10-K 2024-01-31); 4,651 (10-K 2025-02-05) | newest |
| Data Center | FY2023 | 6,496 | 10-K 2026-02-04 | 10-K 2026-02-04 | 6,496 (10-K 2024-01-31); 6,496 (10-K 2025-02-05) | newest |
| Embedded | FY2023 | 5,321 | 10-K 2026-02-04 | 10-K 2026-02-04 | 5,321 (10-K 2024-01-31); 5,321 (10-K 2025-02-05) | newest |
| Gaming | FY2023 | 6,212 | 10-K 2026-02-04 | 10-K 2026-02-04 | 6,212 (10-K 2024-01-31); 6,212 (10-K 2025-02-05) | newest |
| Client | FY2024 | 7,054 | 10-K 2026-02-04 | 10-K 2026-02-04 | 7,054 (10-K 2025-02-05) | newest |
| Data Center | FY2024 | 12,579 | 10-K 2026-02-04 | 10-K 2026-02-04 | 12,579 (10-K 2025-02-05) | newest |
| Embedded | FY2024 | 3,557 | 10-K 2026-02-04 | 10-K 2026-02-04 | 3,557 (10-K 2025-02-05) | newest |
| Gaming | FY2024 | 2,595 | 10-K 2026-02-04 | 10-K 2026-02-04 | 2,595 (10-K 2025-02-05) | newest |
| Client | FY2025 | 10,640 | 10-K 2026-02-04 | 10-K 2026-02-04 | — | newest |
| Data Center | FY2025 | 16,635 | 10-K 2026-02-04 | 10-K 2026-02-04 | — | newest |
| Embedded | FY2025 | 3,454 | 10-K 2026-02-04 | 10-K 2026-02-04 | — | newest |
| Gaming | FY2025 | 3,910 | 10-K 2026-02-04 | 10-K 2026-02-04 | — | newest |

## APLD

### segment_capex

No re-segmentation seen in the readings.

| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |
|---|---|---|---|---|---|---|
| Cloud Services Business | FY2023 | 390 | 10-K 2024-08-30 | 10-K 2025-07-30 | — | not in the newest (10-K 2025-07-30) |
| Data Center Hosting Business | FY2023 | 135,946 | 10-K 2025-07-30 | 10-K 2025-07-30 | 135,946 (10-K 2024-08-30) | newest |
| HPC Hosting Business | FY2023 | 9,813 | 10-K 2025-07-30 | 10-K 2025-07-30 | 9,813 (10-K 2024-08-30) | newest |
| Cloud Services Business | FY2024 | 80,082 | 10-K 2024-08-30 | 10-K 2026-07-29 | — | not in the newest (10-K 2026-07-29) |
| Data Center Hosting Business | FY2024 | 38,266 | 10-K 2026-07-29 | 10-K 2026-07-29 | 38,266 (10-K 2024-08-30); 38,266 (10-K 2025-07-30) | newest |
| HPC Hosting Business | FY2024 | 207,299 | 10-K 2026-07-29 | 10-K 2026-07-29 | 207,299 (10-K 2024-08-30); 207,299 (10-K 2025-07-30) | newest |
| Data Center Hosting Business | FY2025 | 9,320 | 10-K 2026-07-29 | 10-K 2026-07-29 | 9,320 (10-K 2025-07-30) | newest |
| HPC Hosting Business | FY2025 | 976,506 | 10-K 2026-07-29 | 10-K 2026-07-29 | 976,506 (10-K 2025-07-30) | newest |
| Data Center Hosting Business | FY2026 | (1,234) | 10-K 2026-07-29 | 10-K 2026-07-29 | — | newest |
| HPC Hosting Business | FY2026 | 2,988,712 | 10-K 2026-07-29 | 10-K 2026-07-29 | — | newest |

### segment_revenue

No re-segmentation seen in the readings.

| Segment | FY | Dataset value (as filed) | From | Newest filing printing the FY | Other readings | Basis |
|---|---|---|---|---|---|---|
| Data Center Hosting Business | FY2023 | 55,392 | 10-K 2024-08-30 | 10-K 2024-08-30 | — | newest |
| Cloud Services Business | FY2024 | 28,957 | 10-K 2024-08-30 | 10-K 2026-07-29 | — | not in the newest (10-K 2026-07-29) |
| Data Center Hosting Business | FY2024 | 136,618 | 10-K 2026-07-29 | 10-K 2026-07-29 | 136,618 (10-K 2024-08-30) | newest |
| Data Center Hosting Business | FY2025 | 144,193 | 10-K 2026-07-29 | 10-K 2026-07-29 | 144,193 (10-K 2025-07-30) | newest |
| Data Center Hosting Business | FY2026 | 154,403 | 10-K 2026-07-29 | 10-K 2026-07-29 | — | newest |
| HPC Hosting Business | FY2026 | 385,304 | 10-K 2026-07-29 | 10-K 2026-07-29 | — | newest |
