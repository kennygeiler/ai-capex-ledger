# Evaluation: the attribution against the reference set

26 reference entries (gold/ai_capex.yaml), each a sourced figure or bound for AI's part of capex. We have a number for 19: 14 agree, 5 disagree; 7 have no estimate from us. Only 11 entries state a figure rather than a bound, so the error band is a first measurement, not a statistic.

| Company | Year | Reference | Ours | Method | Outcome | What the reference measures |
|---|---|---|---|---|---|---|
| GOOGL | FY2025 | 60% | 68% | ppe_category | disagree | Servers' share of 2025 capital expenditures (the rest data centers and networking), as stated by the CFO on the Q4 2025 call. Servers include CPUs, not only AI accelerators. |
| GOOGL | FY2024 | ≥ 90% | 56% | ppe_category | disagree | Share of 2024 capex going to technical infrastructure (servers, data centers, networking), a planning statement on the Q4 2023 call. Wider than servers; a floor on the infrastructure share, not on AI. |
| MSFT | FY2025 | ≤ 50% | 60% | ppe_category | disagree | Short-lived assets (servers, CPUs and GPUs) were at most about half of cloud and AI spend through fiscal 2025; the CFO said "roughly half" long-lived in Q1 and "more than half" long-lived in Q2 and Q4. So the server share of the year is at most about 0.5. |
| AMZN | FY2025 | ≥ 50% | 45% | ppe_category | agree | The CEO said the vast majority of 2025 capex is AI for AWS; a floor of half on the AI share of total capex, which includes fulfillment and transportation. |
| TSLA | FY2024 | ≥ $5.0B | — | qualitative | no estimate | AI-related capex including infrastructure, as stated by the CFO on the Q4 2024 call; the wording leaves open whether it is the year or cumulative, so a floor. |
| ORCL | FY2026 | ≥ 50% | 53% | ppe_category | agree | The vast majority of fiscal 2026 capex is revenue-generating data center equipment, per the company's plan; a floor of half on the data-center share. |
| NVDA | FY2025 | $115.2B | $115.2B | segment | agree | Data Center segment revenue for fiscal 2025 (ended January 2025), from the earnings release. Includes networking and non-AI data-center compute, so wider than AI accelerator revenue. |
| AMD | FY2024 | $12.6B | $12.6B | segment | agree | Data Center segment revenue for 2024, from the earnings release. Includes EPYC server CPUs as well as Instinct accelerators, so wider than AI. |
| AMD | FY2024 | ≥ $5.0B | $12.6B | segment | agree | AMD Instinct accelerator revenue for 2024, the CEO's floor in the earnings release; the closest to pure AI revenue AMD states. |
| AVGO | FY2024 | $12.2B | $12.2B | stated_amount | agree | AI revenue (custom accelerators plus AI networking) for fiscal 2024 (ended November 2024), as the CEO stated it in the earnings release. A company-defined AI line within semiconductor revenue. |
| MRVL | FY2025 | ≥ $1.5B | $4.0B | stated_share | agree | AI revenue for fiscal 2025 (ended February 2025) exceeded the company's $1.5 billion target, per the Q4 call; a floor, the exact figure was not stated. Custom silicon plus optics for AI. |
| CRWV | FY2025 | $5.1B | $5.1B | whole_business | agree | Total revenue for 2025 from the earnings release's income statement; CoreWeave sells only AI cloud capacity, so total revenue is AI revenue. |
| CRWV | FY2025 | ≤ $10.3B | $10.3B | whole_business | agree | Purchases of property and equipment including capitalized software for 2025, from the cash flow statement in the earnings release. Nearly all is GPUs and the shells around them, so a ceiling on AI capex. |
| NBIS | FY2024 | $0.1B | — | — | no estimate | Group revenue for 2024 from the earnings release. Includes the smaller Toloka, TripleTen and Avride units alongside the core AI infrastructure business, so slightly wider than AI cloud. |
| NBIS | FY2024 | ≤ $0.8B | — | — | no estimate | Total capital expenditures for 2024 from the earnings release; nearly all GPU clusters and data centers, so a ceiling on AI capex. |
| IREN | FY2025 | $0.0B | $0.0B | segment | agree | AI Cloud Services revenue for fiscal 2025 (ended June 2025), the income statement line in the full-year results; the rest of revenue is bitcoin mining. |
| APLD | FY2025 | ≤ $0.7B | $1.0B | segment | disagree | Purchases of property and equipment and other assets for fiscal 2025 (ended May 2025), the cash flow line in the earnings release (in thousands). Almost all is the Ellendale (Polaris Forge) HPC campus, but the line is total, so a ceiling. |
| WULF | FY2025 | $0.0B | $0.0B | segment | agree | HPC lease revenue for 2025, the income statement line in the full-year results (in thousands); the rest of revenue is bitcoin mining. |
| WULF | FY2025 | ≤ $1.1B | — | qualitative | no estimate | Purchase of and deposits on plant and equipment for 2025, the cash flow line in the full-year results (in thousands). The build is HPC data centers for Fluidstack and Google-backed leases, but the line is total, so a ceiling. |
| CORZ | FY2025 | ≤ $0.7B | — | qualitative | no estimate | Capital expenditures for 2025 per the 10-K's liquidity discussion, driven by converting mining sites to colocation for CoreWeave; the figure is total, so a ceiling on HPC capex. |
| MU | FY2025 | $10.0B | $13.5B | segment | disagree | Combined HBM, high-capacity DIMM and LP server DRAM revenue for fiscal 2025 (ended August 2025), as stated on the Q4 call; wider than HBM alone (HBM was nearly $2 billion in Q4). Source is a call summary, not the release. |
| DELL | FY2026 | ≥ $25.0B | $24.7B | stated_amount | agree | AI-optimized server shipments in fiscal 2026 (ended January 2026), as the COO stated on the Q4 call; a floor, and shipments rather than recognized revenue. |
| COHR | FY2025 | ≤ $3.4B | $3.8B | segment | agree | Networking segment revenue for fiscal 2025 (ended June 2025), from the segment table in the earnings release. Holds the AI datacenter transceivers but also telecom, so a ceiling on AI revenue. |
| LITE | FY2025 | ≤ $1.4B | — | qualitative | no estimate | Cloud & Networking segment revenue for fiscal 2025 (ended June 2025), from the earnings release. Holds the AI datacenter lasers and transceivers but also telecom, so a ceiling on AI revenue. |
| MOD | FY2025 | $0.6B | $0.6B | segment | agree | Data center product sales for fiscal 2025 (ended March 2025), including $197 million from the Scott Springfield acquisition, per an earnings summary of the Q4 call. Cooling for all data centers, not only AI. |
| ETN | FY2025 | 17% | — | — | no estimate | Data center end market as a share of total revenue in 2025, management's planning estimate as reported; all data centers, not only AI, and a plan rather than a reported actual. |

Agreement rate 14/19, 95% Wilson interval 51%–88%. The interval is the honest width at this sample size; it narrows as the reference set grows. Error on entries that state a figure: median 0% (IQR 0%–6%) n=9.

## Error band by method

| Method | n | agree | 95% interval | abs error on eq entries (median, IQR) |
|---|---|---|---|---|
| ppe_category | 5 | 2 | 12%–77% | 13% n=1 |
| segment | 9 | 7 | 45%–94% | 0% (IQR 0%–9%) n=6 |
| stated_amount | 2 | 2 | 34%–100% | 0% n=1 |
| stated_share | 1 | 1 | 21%–100% | — |
| whole_business | 2 | 2 | 34%–100% | 0% n=1 |

## By layer

| Layer | n | agree | 95% interval | abs error on eq entries (median, IQR) |
|---|---|---|---|---|
| chip_seller | 5 | 5 | 57%–100% | 0% (IQR 0%–0%) n=3 |
| component_supplier | 3 | 2 | 21%–94% | 35% n=1 |
| datacenter_build | 1 | 1 | 21%–100% | 0% n=1 |
| hyperscaler | 5 | 2 | 12%–77% | 13% n=1 |
| miner_to_hpc | 3 | 2 | 21%–94% | 0% (IQR -0%–0%) n=2 |
| neocloud | 2 | 2 | 34%–100% | 0% n=1 |

## By field

| Field | n | agree | 95% interval | abs error on eq entries (median, IQR) |
|---|---|---|---|---|
| capex | 7 | 3 | 16%–75% | 13% n=1 |
| revenue | 12 | 11 | 65%–98% | 0% (IQR 0%–0%) n=8 |


Sources, one per entry:

- GOOGL FY2025: 60 per cent of Alphabet's capex in 2025 was spent on servers (https://nasdaq.com/articles/alphabet-spends-about-60-cents-every-technical-infrastructure-dollar-servers-nvidias, 2026-02-05)
- GOOGL FY2024: at least 90% of 2024 spending would focus on technical infrastructure (https://accelerationeconomy.com/?p=64061, 2024-01-30)
- MSFT FY2025: more than half of cloud and AI-related spending at the firm was directed toward long-lived assets ... the remaining spend was primarily for servers, both CPUs and GPUs (https://itpro.com/business/business-strategy/microsoft-promises-more-ai-spending-despite-cloud-cost-stumble, 2025-01-29)
- AMZN FY2025: The vast majority of that capex spend is on AI for AWS (https://www.rcrwireless.com/20250207/business/amazon-100-billion-ai-infrastructure-spend-2025, 2025-02-06)
- TSLA FY2024: total AI-related capex, including infrastructure, is now more than $5 billion (https://www.tomshardware.com/tech-industry/artificial-intelligence/elon-musk-spent-roughly-usd10-billion-on-ai-training-hardware-in-2024, 2025-01-29)
- ORCL FY2026: vast majority of it dedicated to revenue-generating data center equipment (https://datacentremagazine.com/news/oracles-data-centre-strategy-cloud-ai-and-more-capacity, 2025-09-10)
- NVDA FY2025: Full-year revenue rose 142% to a record $115.2 billion. (https://www.sec.gov/Archives/edgar/data/1045810/000104581025000021/q4fy25pr.htm, 2025-02-26)
- AMD FY2024: For 2024, Data Center segment revenue was a record $12.6 billion, an increase of 94% compared to the prior year (https://ir.amd.com/financial-information/sec-filings/content/0000002488-25-000009/q42024991.htm, 2025-02-04)
- AMD FY2024: delivered more than $5 billion of AMD Instinct accelerator revenue (https://ir.amd.com/financial-information/sec-filings/content/0000002488-25-000009/q42024991.htm, 2025-02-04)
- AVGO FY2024: Semiconductor revenue was a record $30.1 billion driven by AI revenue of $12.2 billion. (https://www.sec.gov/Archives/edgar/data/1730168/000173016824000125/avgo-11032024x8kxex99.htm, 2024-12-12)
- MRVL FY2025: AI revenue surpassed the FY25 $1.5B target (https://ziven.io/earnings/calls/MRVL/q4-fy2025, 2025-03-05)
- CRWV FY2025: we became the fastest cloud in history to reach $5 billion in annual revenue (https://seekingalpha.com/pr/20416642, 2026-02-26)
- CRWV FY2025: Purchase of property and equipment, including capitalized internal-use software (https://seekingalpha.com/pr/20416642, 2026-02-26)
- NBIS FY2024: For the full year 2024, the Group's revenue of $117.5 million increased 462% year-over-year. (https://www.sec.gov/Archives/edgar/data/1513845/000110465925015480/tm257185d1_ex99-1.htm, 2025-02-20)
- NBIS FY2024: Capital expenditures totaled $417.6 million and $808.1 million for the three and twelve months ended December 31, 2024 (https://www.sec.gov/Archives/edgar/data/1513845/000110465925015480/tm257185d1_ex99-1.htm, 2025-02-20)
- IREN FY2025: AI Cloud Services Revenue 16.4 3.1 (https://finviz.com/news/152716/iren-reports-full-year-fy25-results, 2025-08-28)
- APLD FY2025: Purchases of property and equipment and other assets (https://www.sec.gov/Archives/edgar/data/1144879/000114487925000019/apldq425earningsrelease.htm, 2025-07-30)
- WULF FY2025: HPC lease revenue (https://investors.terawulf.com/news-events/press-releases/detail/132, 2026-02-26)
- WULF FY2025: Purchase of and deposits on plant and equipment (https://investors.terawulf.com/news-events/press-releases/detail/132, 2026-02-26)
- CORZ FY2025: we incurred approximately 729.0 million and $95.0 million in capital expenditures, respectively (https://www.sec.gov/Archives/edgar/data/1839341/000162828026013305/core-20251231.htm, 2026-03-02)
- MU FY2025: HBM, high-capacity DIMMs, and LP server DRAM revenue reached $10 billion, over 5x the prior year. (https://ziven.io/earnings/calls/MU/q4-fy2025, 2025-09-23)
- DELL FY2026: shipped more than $25 billion throughout the year (https://www.blocksandfiles.com/flash/2026/02/27/ai-server-frenzy-fuels-record-revenues-for-dell/4092727, 2026-02-27)
- COHR FY2025: Networking $945.2 $897.3 $679.8 $3,421.3 $2,295.7 (https://www.sec.gov/Archives/edgar/data/820318/000119312525179833/d22249dex991.htm, 2025-08-13)
- LITE FY2025: Cloud & Networking $ 1,410.8 $ 1,084.9 30.0% (https://www.sec.gov/Archives/edgar/data/1633978/000162828025039896/lite_ex991xq4fy25.htm, 2025-08-12)
- MOD FY2025: Data center revenue increased 119% to $644 million for the full year (https://247wallst.com/companies/mod/earnings/2025/Q4, 2025-05-20)
- ETN FY2025: management estimating that data centers will be responsible for 17% of total revenue in 2025 (https://www.fool.com/investing/2025/10/12/should-you-buy-eaton-stock-while-its-below-400, 2025-10-12)
