# Thesis: AI software and data platform (ai_software@v3)

## Thesis

Software and data platforms rent their compute from the hyperscalers, so AI shows up as cloud purchase commitments and hosting cost of revenue, not as capex. Capex allocation matters only when a company states it buys its own GPUs; the committed cloud spend is the real number and it sits in `basis`, not in the year's spend. Revenue exposure matters, but only through what the company states about AI products, and most state ARR, ACV or bookings rather than revenue. Project-level investment is the cloud commitments themselves; plans versus reality rarely applies. The signal to watch is the step-up in purchase commitments year on year, which is the committed AI compute, read against stated AI product revenue or ARR. Two numbers set the scale in 2026: Salesforce's $16.7 billion of commitments to infrastructure providers at 31 January 2026 against $594 million of capex, and Snowflake's $6 billion five-year AWS commitment (May 2026) against product revenue of about $6 billion a year.

## Companies

Salesforce (CRM), ServiceNow (NOW), Adobe (ADBE), Snowflake (SNOW), Palantir (PLTR) and Datadog (DDOG). None reports an AI segment. What each states, as of 29 October 2026:

Salesforce (CRM). Fiscal 2026 (year to 31 January 2026, release 25 February 2026): revenue $41.5 billion; Agentforce ARR $800 million, up 169%; Agentforce and Data 360 ARR over $2.9 billion, including $1.1 billion of Informatica Cloud ARR; RPO $72.4 billion, cRPO $35.1 billion; capex $594 million, guided to about 1.5% of fiscal 2027 revenue. The 10-K's contractual obligations: total commitments under enforceable agreements "including those with infrastructure service providers" of about $16.7 billion, $3.7 billion due within 12 months and $13.0 billion after, with the note that the company "may slow the pace of our investments". No AI capex figure; the 10-K says it will "continue to invest additional resources in our AI, agentic and cloud services".

ServiceNow (NOW). Q2 2026 (22 July 2026): subscription revenue $3,877 million, up 24.5%; cRPO $13.20 billion; "ServiceNow AI crossed $1 billion in annual contract value in Q2 2026"; capex $114 million in the quarter, guided at 4% of revenue; 2026 subscription revenue guidance $15.76 to 15.78 billion. ACV, not revenue. Not disclosed: AI revenue, AI hosting cost, cloud commitments in the release.

Adobe (ADBE). Q3 fiscal 2026 (10 September 2026): revenue $6.76 billion; total ARR $27.50 billion; "AI-first ARR grew more than 150% year over year" with no dollar figure; customer groups Business Professionals and Consumers ($1.91 billion subscription revenue) and Creative and Marketing Professionals ($4.65 billion). The older "AI-influenced ARR" measure is not in the release. Not disclosed: AI ARR in dollars, AI compute spend.

Snowflake (SNOW). Q2 fiscal 2027 (quarter to 31 July 2026, release 2 September 2026): product revenue $1,491.9 million, up 37%; RPO $9.00 billion; "a meaningful step-up in AI revenue" with no dollar figure; CoCo 9,100 accounts, CoWork 5,800; fiscal 2027 product revenue guidance $6,070 million; non-GAAP product gross margin 74.7% in the quarter, 74.0% guided for the year. Project: "$6 billion in Graviton compute and AI spend on AWS over five years", announced 27 May 2026, its largest commitment to date. Not disclosed: AI revenue in dollars.

Palantir (PLTR). Q2 2026 (3 August 2026): revenue $1.935 billion, up 93%; US commercial $764 million, up 149%; US government $809 million; US commercial remaining deal value $6.238 billion; TCV closed $3.373 billion; 2026 revenue guidance $8.150 to 8.158 billion; capex $14.6 million in the quarter. AIP is named once, in forward-looking statements. No AI revenue line: the breakout is US commercial and US government, neither of which is AI. Not disclosed: AI revenue, AI compute spend, cloud commitments in the release.

Datadog (DDOG). Q2 2026 (6 August 2026): revenue $1,121 million, up 36%; about 4,720 customers above $100k ARR; purchases of PP&E $9.9 million plus capitalized software $27.3 million in the quarter; 2026 revenue guidance $4.45 to 4.47 billion. The release says only "Our customers are building and deploying with AI". The AI-native cohort (more than 750 AI customers) and its share of revenue appear in call coverage, not in the release. Not disclosed: AI-native share of ARR in the release, cloud commitments in the release.

Salesforce, ServiceNow and Adobe sell AI features inside large application suites and state AI ARR or ACV. Snowflake and Datadog are consumption platforms whose AI workloads run on hyperscaler clouds under commitments. Palantir sits at the edge: its growth is attributed to its AI platform, but it reports no AI revenue line. The hyperscalers that sell these companies their compute sit in `hyperscaler`.

## Where the AI money shows up

1. **Purchase commitments** (`facts.purchase_commitments`): multi-year cloud commitments with AWS, Azure, Google Cloud; the step-up since 2023 is AI compute. Committed, not spent. Salesforce $16.7 billion total (10-K, January 2026); Snowflake $6 billion over five years with AWS (May 2026).
2. **Cost of revenue and R&D** (`ai_spend`, MD&A): "increased hosting costs for AI features", "AI model training costs in R&D". Opex, rarely quantified. Snowflake's product gross margin guide of 74.0% is the visible trace.
3. **Capex** (`values.capex`): small, usually offices and equipment (Salesforce $594 million for a year, Palantir $14.6 million for a quarter); AI only when the company states it buys its own GPUs, which none of the six did in the releases read.
4. **Stated AI product figures** (`ai_spend`): AI ARR (Salesforce $800 million Agentforce), AI ACV (ServiceNow $1 billion), AI-first ARR growth (Adobe, percent only), account counts for an AI product (Snowflake CoCo and CoWork).

## How to attribute

Capex: `stated_amount` / `stated_share` only when the company states an AI part; otherwise `none`, the 2026 answer for all six.

Opex: `stated_amount` when a release or MD&A gives an AI hosting or compute figure; `qualitative` with confidence ≤ 0.4 when cost of revenue growth or gross margin is attributed to AI in words; `none` otherwise.

Record the cloud purchase commitments in `basis` as the committed AI compute, never in `ai_amount` (they are not spend in the year). Salesforce's $16.7 billion covers all infrastructure providers, not AI alone; say so.

Revenue, in order of hardness:

- `stated_amount`: the company states AI product revenue for the year; confidence ≤ 0.8. None of the six did as of 29 October 2026. An ARR or ACV figure (Salesforce's $800 million Agentforce ARR, ServiceNow's $1 billion AI ACV) is not fiscal-year revenue: confidence ≤ 0.5 and name the measure in `basis`. A growth rate with no base (Adobe's AI-first ARR up more than 150%) is not an amount: `qualitative`. "AI-influenced" ARR, where stated, counts deals that include AI, not AI revenue: ≤ 0.3.
- `stated_share`: the company states AI's share of revenue, ARR or bookings; same ceilings as above by measure. ServiceNow's target of AI at 30% of ACV by 2030 is a plan, not a share.
- `segment`: not available. Palantir's US commercial and US government are not AI lines; Adobe's customer groups and Salesforce's clouds are not AI lines. Never sum one as the AI revenue.
- `qualitative`: growth attributed to AI products in words only, confidence ≤ 0.3. The 2026 answer for Snowflake ("meaningful step-up in AI revenue"), Palantir and Datadog.
- `none`: nothing stated.
- `whole_business`: never.

## Projects

A project is a committed, sized spend on AI compute: a multi-year cloud commitment with a named hyperscaler and amount, a stated purchase of the company's own GPUs or a data center, a sized investment program the company names ("$N billion over five years" for AI infrastructure). Words that name one: "commitment", "non-cancelable", "agreement with" a cloud provider, "GPUs", "data center", "invest $" with a term. Not a project: a product launch (an agent, a copilot, a model), an AI feature release, a partnership with no amount, an acquisition, a hire.

Named as of 29 October 2026: Snowflake's $6 billion AWS commitment over five years (27 May 2026). Salesforce's $16.7 billion of infrastructure commitments is a total across providers with no named project; record it in `basis`.

## Traps

- A cloud commitment is committed spend across several years, not capex and not this year's opex.
- "AI revenue" (AI product ARR) is the sales side, not spend; it belongs in the revenue field, with the ARR ceiling.
- ARR, ACV, bookings, RDV, TCV and "AI-influenced" are each a different thing from revenue; name which one was stated and cap the confidence. Palantir's $6.238 billion of US commercial RDV is a backlog of all deals, not AI revenue.
- A customer-count, account-count or "deals including AI" statement is qualitative, not a share.
- Call-only figures (Datadog's AI-native cohort, Snowflake's AI share of acceleration) are not in the releases; cite the call or stay at the release's ceiling.
- ARR that includes an acquisition (Salesforce's $2.9 billion includes $1.1 billion of Informatica) is not organic AI growth.

## Sources

- Salesforce Q4 fiscal 2026 results: revenue $41.5B, Agentforce ARR $800M, Agentforce and Data 360 ARR over $2.9B incl. $1.1B Informatica, RPO $72.4B, capex $594M, FY27 capex about 1.5% of revenue. SEC EDGAR 8-K, 25 Feb 2026. https://www.sec.gov/Archives/edgar/data/1108524/000110852426000056/crm-q4fy26xexhibit991.htm
- Salesforce fiscal 2026 10-K, Contractual Obligations: about $16.7B of commitments incl. infrastructure service providers, $3.7B within 12 months, $13.0B thereafter; may slow pace of investment. SEC EDGAR, filed Mar 2026. https://www.sec.gov/Archives/edgar/data/1108524/000110852426000060/crm-20260131.htm
- ServiceNow Q2 2026 results: subscription revenue $3,877M, cRPO $13.20B, ServiceNow AI crossed $1B in ACV, capex $114M. SEC EDGAR 8-K, 22 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001373715/000137371526000072/erq2fy26.htm
- Adobe Q3 fiscal 2026 results: revenue $6.76B, total ARR $27.50B, AI-first ARR up more than 150% with no dollar figure. SEC EDGAR 8-K, 10 Sep 2026. https://www.sec.gov/Archives/edgar/data/0000796343/000079634326000147/adbeex991q326.htm
- Snowflake Q2 fiscal 2027 results: product revenue $1,491.9M, RPO $9.00B, step-up in AI revenue without a figure, FY27 product revenue $6,070M, product gross margin 74.7%. 01net copy of release, 3 Sep 2026. https://www.01net.it/snowflake-reports-financial-results-for-the-second-quarter-of-fiscal-2027/
- Snowflake $6B in Graviton compute and AI spend on AWS over five years, largest commitment to date. Snowflake, 27 May 2026. https://www.snowflake.com/en/news/press-releases/snowflake-expands-aws-collaboration-with-6b-commitment-to-accelerate-enterprise-agentic-ai-adoption/
- Palantir Q2 2026 results: revenue $1.935B, US commercial $764M, US commercial RDV $6.238B, TCV $3.373B, capex $14.6M. SEC EDGAR 8-K, 3 Aug 2026. https://www.sec.gov/Archives/edgar/data/0001321655/000132165526000039/a2026q2ex991pressrelease.htm
- Datadog Q2 2026 results: revenue $1,121M, 4,720 customers over $100k ARR, PP&E $9.9M plus capitalized software $27.3M, no AI-native figures in the release. SEC EDGAR 8-K, 6 Aug 2026. https://www.sec.gov/Archives/edgar/data/0001561550/000162828026053829/ex-991x20260630x8k.htm
- Independent estimate: Gartner's May 2026 forecast of $2.59T of AI spending in 2026 (up 47%), with vendor AI infrastructure over 45% of it. CIO Dive, 19 May 2026. https://www.ciodive.com/news/global-AI-spend-2026/820656/
