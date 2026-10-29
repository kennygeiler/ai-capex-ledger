# Evaluation: the attribution against the reference set

6 reference entries (gold/ai_capex.yaml), each a sourced figure or bound for AI's part of capex. We have a number for 5: 2 agree, 3 disagree; 1 have no estimate from us. Only 1 entries state a figure rather than a bound, so the error band is a first measurement, not a statistic.

| Company | Year | Reference | Ours | Method | Outcome | What the reference measures |
|---|---|---|---|---|---|---|
| GOOGL | FY2025 | 60% | 68% | ppe_category | disagree | Servers' share of 2025 capital expenditures (the rest data centers and networking), as stated by the CFO on the Q4 2025 call. Servers include CPUs, not only AI accelerators. |
| GOOGL | FY2024 | ≥ 90% | 56% | ppe_category | disagree | Share of 2024 capex going to technical infrastructure (servers, data centers, networking), a planning statement on the Q4 2023 call. Wider than servers; a floor on the infrastructure share, not on AI. |
| MSFT | FY2025 | ≤ 50% | 60% | ppe_category | disagree | Short-lived assets (servers, CPUs and GPUs) were at most about half of cloud and AI spend through fiscal 2025; the CFO said "roughly half" long-lived in Q1 and "more than half" long-lived in Q2 and Q4. So the server share of the year is at most about 0.5. |
| AMZN | FY2025 | ≥ 50% | 45% | ppe_category | agree | The CEO said the vast majority of 2025 capex is AI for AWS; a floor of half on the AI share of total capex, which includes fulfillment and transportation. |
| TSLA | FY2024 | ≥ $5.0B | — | qualitative | no estimate | AI-related capex including infrastructure, as stated by the CFO on the Q4 2024 call; the wording leaves open whether it is the year or cumulative, so a floor. |
| ORCL | FY2026 | ≥ 50% | 53% | ppe_category | agree | The vast majority of fiscal 2026 capex is revenue-generating data center equipment, per the company's plan; a floor of half on the data-center share. |

## Error band by method

| Method | n | agree | median abs error (eq entries) |
|---|---|---|---|
| ppe_category | 5 | 2 | 13% (n=1) |

Sources, one per entry:

- GOOGL FY2025: 60 per cent of Alphabet's capex in 2025 was spent on servers (https://nasdaq.com/articles/alphabet-spends-about-60-cents-every-technical-infrastructure-dollar-servers-nvidias, 2026-02-05)
- GOOGL FY2024: at least 90% of 2024 spending would focus on technical infrastructure (https://accelerationeconomy.com/?p=64061, 2024-01-30)
- MSFT FY2025: more than half of cloud and AI-related spending at the firm was directed toward long-lived assets ... the remaining spend was primarily for servers, both CPUs and GPUs (https://itpro.com/business/business-strategy/microsoft-promises-more-ai-spending-despite-cloud-cost-stumble, 2025-01-29)
- AMZN FY2025: The vast majority of that capex spend is on AI for AWS (https://www.rcrwireless.com/20250207/business/amazon-100-billion-ai-infrastructure-spend-2025, 2025-02-06)
- TSLA FY2024: total AI-related capex, including infrastructure, is now more than $5 billion (https://www.tomshardware.com/tech-industry/artificial-intelligence/elon-musk-spent-roughly-usd10-billion-on-ai-training-hardware-in-2024, 2025-01-29)
- ORCL FY2026: vast majority of it dedicated to revenue-generating data center equipment (https://datacentremagazine.com/news/oracles-data-centre-strategy-cloud-ai-and-more-capacity, 2025-09-10)
