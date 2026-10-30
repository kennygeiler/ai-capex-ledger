# Money-flow model: data-center landlord (datacenter_landlord@v1)

Who: Equinix, Digital Realty, Iron Mountain. REITs that build shells and lease power and space to hyperscalers, neoclouds and enterprises. Their capex is the data centers themselves: land, shell, power, cooling. The tenant's GPUs are not on this balance sheet.

## Where the AI money shows up

1. **Capex by type** (`facts`, MD&A): "expansion capex" or "development capex" versus "recurring" or "maintenance". Expansion capex is new capacity, which since 2023 is overwhelmingly AI-driven, but the company rarely says how much is AI.
2. **What the company says** (`ai_spend`): megawatts under construction, hyperscale leasing, "AI" in releases; Iron Mountain reports a "Data Center" segment with its own capex.
3. **Segment capex** (`facts.segment_capex`): Iron Mountain's data-center segment; Equinix xScale.

## How to attribute

- `segment`: Iron Mountain's data-center segment capex, with `basis` saying that this is data-center capacity, not AI specifically.
- `stated_amount` / `stated_share`: when the company states an AI or hyperscale part of development capex.
- `whole_business` is *not* allowed: a data-center REIT's capex is data-center capex, but data-center is not AI. Use `qualitative` with confidence ≤ 0.5 when the company links the development pipeline to AI demand.
- `none` otherwise. Opex: `none`.

## Traps

- Expansion capex equals data-center capex, which is broader than AI. Never equate the two without a statement.
- Joint ventures (xScale, DLR's hyperscale JVs) carry capex off balance sheet. Note it in `basis`.
