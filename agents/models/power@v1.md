# Money-flow model: power producer (power@v1)

Who: Vistra, Constellation, NRG, Talen. Independent power producers whose growth story is data-center load: nuclear restarts, gas plants co-located with data centers, long-term PPAs with hyperscalers. Their capex is generation and transmission, which is AI-linked only when a project is contracted to a data-center customer.

## Where the AI money shows up

1. **What the company says** (`ai_spend`): named projects with a data-center counterparty ("Crane Clean Energy Center restart for Microsoft", "Susquehanna campus for Amazon"), growth capex guidance tied to data-center demand.
2. **Capex by category** (`facts`, MD&A): "growth" versus "maintenance" or "nuclear fuel". Growth capex tied to a named data-center project is attributable.
3. **Segment capex** (`facts.segment_capex`): by generation fleet, rarely by customer.

## How to attribute

- `stated_amount`: a capex amount the company ties to a data-center project or PPA (`scope: ai` or `scope: datacenter`).
- `qualitative` with confidence ≤ 0.4 when growth capex is linked to data-center demand in words only.
- `none` otherwise, which is the common answer. Opex: `none`.

## Traps

- A restart or uprate serving the grid is not AI capex because a hyperscaler signed a PPA; only capex the company itself ties to the counterparty counts.
- Nuclear fuel purchases are not growth capex.
