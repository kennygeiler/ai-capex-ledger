# Thesis: AI software and data platform (ai_software@v2)

## Thesis

Software and data platforms rent their compute from the hyperscalers, so AI shows up as cloud purchase commitments and hosting cost of revenue, not as capex. Capex allocation matters only when a company states it buys its own GPUs; the committed cloud spend is the real number and it sits in `basis`, not in the year's spend. Revenue exposure matters, but only through what the company states about AI products, and most state ARR or bookings rather than revenue. Project-level investment is the cloud commitments themselves; plans versus reality rarely applies. The signal to watch is the step-up in purchase commitments year on year, which is the committed AI compute, read against stated AI product revenue or ARR.

## Companies

Salesforce (CRM), ServiceNow (NOW), Adobe (ADBE), Snowflake (SNOW), Palantir (PLTR) and Datadog (DDOG). Salesforce, ServiceNow and Adobe sell AI features inside large application suites and state AI ARR or AI-influenced ARR when they choose. Snowflake and Datadog are consumption platforms whose AI workloads run on hyperscaler clouds under commitments. Palantir sits at the edge: its growth is attributed to its AI platform, but it reports no AI revenue line and its segments are government and commercial, neither of which is AI. The hyperscalers that sell these companies their compute sit in `hyperscaler`.

## Where the AI money shows up

1. **Purchase commitments** (`facts.purchase_commitments`): multi-year cloud commitments with AWS, Azure, Google Cloud; the step-up since 2023 is AI compute. Committed, not spent.
2. **Cost of revenue and R&D** (`ai_spend`, MD&A): "increased hosting costs for AI features", "AI model training costs in R&D". Opex, rarely quantified.
3. **Capex** (`values.capex`): small, usually offices and equipment; AI only when the company states it buys its own GPUs.
4. **Stated AI product figures** (`ai_spend`): AI ARR, AI bookings, "AI-influenced" ARR, customer counts for an AI product.

## How to attribute

Capex: `stated_amount` / `stated_share` only when the company states an AI part; otherwise `none`.

Opex: `stated_amount` when a release or MD&A gives an AI hosting or compute figure; `qualitative` with confidence ≤ 0.4 when cost of revenue growth is attributed to AI in words; `none` otherwise.

Record the cloud purchase commitments in `basis` as the committed AI compute, never in `ai_amount` (they are not spend in the year).

Revenue, in order of hardness:

- `stated_amount`: the company states AI product revenue for the year; confidence ≤ 0.8. An ARR or bookings figure (Salesforce's Agentforce ARR, ServiceNow's Now Assist ACV) is not fiscal-year revenue: confidence ≤ 0.5 and name the measure in `basis`. "AI-influenced" ARR (Adobe) counts deals that include AI, not AI revenue: ≤ 0.3.
- `stated_share`: the company states AI's share of revenue, ARR or bookings; same ceilings as above by measure.
- `segment`: not available. Palantir's government and commercial segments are not AI lines; Salesforce's, ServiceNow's and Adobe's product clouds are not AI lines. Never sum one as the AI revenue.
- `qualitative`: growth attributed to AI products in words only, confidence ≤ 0.3. The usual answer for Palantir, Snowflake and Datadog.
- `none`: nothing stated.
- `whole_business`: never.

## Projects

A project is a committed, sized spend on AI compute: a multi-year cloud commitment with a named hyperscaler and amount, a stated purchase of the company's own GPUs or a data center, a sized investment program the company names ("$N billion over five years" for AI infrastructure). Words that name one: "commitment", "non-cancelable", "agreement with" a cloud provider, "GPUs", "data center", "invest $" with a term. Not a project: a product launch (an agent, a copilot, a model), an AI feature release, a partnership with no amount, an acquisition, a hire.

## Traps

- A cloud commitment is committed spend across several years, not capex and not this year's opex.
- "AI revenue" (AI product ARR) is the sales side, not spend; it belongs in the revenue field, with the ARR ceiling.
- ARR, ACV, bookings and "AI-influenced" are each a different thing from revenue; name which one was stated and cap the confidence.
- A customer-count or "deals including AI" statement is qualitative, not a share.
