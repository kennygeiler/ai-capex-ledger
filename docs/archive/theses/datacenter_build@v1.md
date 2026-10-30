# Money-flow model: data-center build suppliers (datacenter_build@v1)

Who: Vertiv, Eaton, nVent, Modine, Johnson Controls, Quanta, Comfort Systems, EMCOR, GE Vernova, Powell, Bloom Energy. They sell the power, cooling, switchgear, turbines, fuel cells and construction labour that turn a hyperscaler's capex into a building. Paid by the AI buildout; their own capex is factories and fleets.

## Where the AI money shows up

1. **Segment revenue and backlog** (`facts.segment_revenue`, `ai_spend`): "Data center" as an end market or vertical; backlog or orders tied to data centers; "hyperscale" in releases.
2. **What the company says** (`ai_spend`): capacity expansions explicitly for data-center demand ("expanding liquid-cooling capacity", "new switchgear plant for data-center orders").
3. **Capex** (`values.capex`): factory capacity. AI spend only when the company ties an expansion to data-center demand and gives a number.

## How to attribute

- `stated_amount` / `stated_share` when the company states a capex amount or share for data-center capacity (`scope: ai` or `scope: datacenter`).
- `qualitative` with confidence ≤ 0.4 when capex is linked to data-center demand in words only.
- `none` otherwise. Data-center revenue or backlog goes in `basis`, never in `ai_amount`.

## Traps

- Data-center revenue is the customer's spend, not this company's.
- Construction firms (Quanta, Comfort Systems, EMCOR) have small capex; their AI exposure is revenue mix. Expect `none` with a strong `basis`.
