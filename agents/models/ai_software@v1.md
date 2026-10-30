# Money-flow model: AI software and data platform (ai_software@v1)

Who: Salesforce, ServiceNow, Adobe, Snowflake, Palantir, Datadog. They run their products on hyperscaler clouds, so AI shows up as cloud purchase commitments and cost of revenue, not as capex. Capex is offices and some data-center equipment.

## Where the AI money shows up

1. **Purchase commitments** (`facts.purchase_commitments`): multi-year cloud commitments with AWS, Azure, Google Cloud; the step-up since 2023 is AI compute. Committed, not spent.
2. **Cost of revenue and R&D** (`ai_spend`, MD&A): "increased hosting costs for AI features", "AI model training costs in R&D". Opex, rarely quantified.
3. **Capex** (`values.capex`): small, usually offices and equipment; AI only when the company states it buys its own GPUs.

## How to attribute

- Capex: `stated_amount` / `stated_share` only when the company states an AI part; otherwise `none`.
- Opex: `stated_amount` when a release or MD&A gives an AI hosting or compute figure; `qualitative` with confidence ≤ 0.4 when cost of revenue growth is attributed to AI in words; `none` otherwise.
- Record the cloud purchase commitments in `basis` as the committed AI compute, never in `ai_amount` (they are not spend in the year).

## Traps

- A cloud commitment is committed spend across several years, not capex and not this year's opex.
- "AI revenue" (AI product ARR) is the sales side, not spend.
