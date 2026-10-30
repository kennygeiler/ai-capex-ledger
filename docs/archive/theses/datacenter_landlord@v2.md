# Thesis: data-center landlord (datacenter_landlord@v2)

## Thesis

Landlords build shells and lease power and space to hyperscalers, neoclouds and enterprises. Their capex is data-center capacity, which is broader than AI, so capex allocation matters but is capped: development capex is the number, and AI's part of it is rarely stated. Project-level investment matters most: campuses, megawatts under construction, joint ventures and hyperscale leases are where the AI link is visible. Plans versus reality matters for development capex guidance. Revenue exposure matters least: rent is rent, and no segment is the AI one. The signal to watch is megawatts under construction and pre-leased, and the share of development funded off balance sheet through joint ventures.

## Companies

Equinix (EQIX), Digital Realty (DLR) and Iron Mountain (IRM). Equinix and Digital Realty are data-center REITs through and through; Digital Realty's hyperscale development is the closer to AI, Equinix's retail colocation the further. Iron Mountain sits at the edge: records storage is the bulk of the company and the data-center business is one reported segment with its own capex, which makes it the one landlord with a segment to read. Miners converting sites into leased shells (Applied Digital, Core Scientific) do the same thing from the other side; they sit in `miner_to_hpc`.

## Where the AI money shows up

1. **Capex by type** (`facts`, MD&A): "expansion capex" or "development capex" versus "recurring" or "maintenance". Expansion capex is new capacity, which since 2023 is overwhelmingly AI-driven, but the company rarely says how much is AI.
2. **What the company says** (`ai_spend`): megawatts under construction, hyperscale leasing, "AI" in releases; Iron Mountain reports a "Data Center" segment with its own capex.
3. **Segment capex** (`facts.segment_capex`): Iron Mountain's data-center segment; Equinix xScale.

## How to attribute

Capex, in order of hardness:

- `segment`: Iron Mountain's data-center segment capex, with `basis` saying that this is data-center capacity, not AI specifically.
- `stated_amount` / `stated_share`: when the company states an AI or hyperscale part of development capex.
- `whole_business` is not allowed: a data-center REIT's capex is data-center capex, but data-center is not AI. Use `qualitative` with confidence ≤ 0.5 when the company links the development pipeline to AI demand.
- `none` otherwise.

Opex: `none`.

Revenue, in order of hardness:

- `stated_share` / `stated_amount`: only when the company states AI's or hyperscale's part of revenue or of new leasing; confidence ≤ 0.6, and new leasing is not revenue in the year (say so).
- `segment`: Iron Mountain's data-center segment revenue, confidence ≤ 0.5, with `basis` "data-center rent, not AI". For Equinix and Digital Realty the data-center segment is the whole business, so it says nothing about AI; do not use it.
- `qualitative`: leasing demand attributed to AI in words only, confidence ≤ 0.3. The usual answer for Equinix and Digital Realty.
- `none`: when nothing links rent to AI.
- `whole_business`: never.

## Projects

A project is a campus or building with a location and megawatts or an amount, a joint venture with capital raised for named development, or a hyperscale lease with a size: a named campus under construction, an xScale or hyperscale JV, a land purchase with planned megawatts, a pre-lease to a hyperscaler. Words that name one: "campus", "megawatts", "under construction", "pre-leased", "joint venture", "land", "phase", "development pipeline" when sites are named. Not a project: an interconnection or cloud-exchange product, a new market entry with no site, a rate increase, a hire.

## Traps

- Expansion capex equals data-center capex, which is broader than AI. Never equate the two without a statement.
- Joint ventures (xScale, DLR's hyperscale JVs) carry capex off balance sheet. Note it in `basis`.
- Leasing signed in the year is backlog, not revenue; a record leasing quarter is a project signal, not a revenue row.
- Iron Mountain's segment revenue is data-center rent; its ceiling is capped for the same reason as its capex.
