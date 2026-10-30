# Thesis: power producer (power@v2)

## Thesis

Independent power producers sell electrons, and their AI story is data-center load: nuclear restarts and uprates, gas plants co-located with data centers, long-term PPAs with hyperscalers. Project-level investment is the measure that matters: the AI link lives in a named plant with a named counterparty. Capex allocation matters only for growth capex the company itself ties to such a project; the rest is generation, transmission and fuel. Plans versus reality matters for growth capex guidance. Revenue exposure does not matter: power sold under a hyperscaler PPA is still power, and no segment is the AI one. The signal to watch is contracted data-center megawatts with a counterparty and a date, and whether the capex that serves them has started.

## Companies

Vistra (VST), Constellation (CEG), NRG (NRG) and Talen (TLN). Constellation and Talen have the clearest named projects: Constellation's Crane Clean Energy Center restart under a Microsoft PPA and its Clinton PPA with Meta, Talen's Susquehanna campus arrangement with Amazon. Vistra and NRG sit at the edge: Vistra's nuclear and gas fleet is contracted to data-center customers when stated, and NRG's data-center story is gas development agreements and retail load. Regulated utilities that serve data centers are not in the set; neither are the fuel-cell and turbine makers, who sit in `datacenter_build`.

## Where the AI money shows up

1. **What the company says** (`ai_spend`): named projects with a data-center counterparty ("Crane Clean Energy Center restart for Microsoft", "Susquehanna campus for Amazon"), growth capex guidance tied to data-center demand.
2. **Capex by category** (`facts`, MD&A): "growth" versus "maintenance" or "nuclear fuel". Growth capex tied to a named data-center project is attributable.
3. **Segment capex** (`facts.segment_capex`): by generation fleet, rarely by customer.

## How to attribute

Capex, in order of hardness:

- `stated_amount`: a capex amount the company ties to a data-center project or PPA (`scope: ai` or `scope: datacenter`).
- `qualitative` with confidence ≤ 0.4 when growth capex is linked to data-center demand in words only.
- `none` otherwise, which is the common answer.

Opex: `none`.

Revenue, in order of hardness:

- `stated_amount` / `stated_share`: only when the company states revenue under data-center PPAs for the year; confidence ≤ 0.5, with `basis` "contracted power to a data-center customer, not AI revenue". A contract's total value is not revenue in the year.
- `segment`: not available. Generation segments (nuclear, gas, retail) are not data-center lines; never sum them.
- `qualitative`: load growth or pricing attributed to data-center demand in words only, confidence ≤ 0.3.
- `none`: the common and honest answer.
- `whole_business`: never.

## Projects

A project is a plant with a counterparty, a size and a date: a nuclear restart or uprate under a hyperscaler PPA, a gas plant built or co-located for a named data-center customer, a PPA with megawatts and a term, a data-center campus on company land with a development partner. Words that name one: "power purchase agreement", "restart", "uprate", "co-located", "behind the meter", "megawatts", "gigawatts", "20-year", "campus", "letter of intent" with a counterparty. Not a project: a fuel contract, a rate case, a hedging statement, a share buyback, a hire.

## Traps

- A restart or uprate serving the grid is not AI capex because a hyperscaler signed a PPA; only capex the company itself ties to the counterparty counts.
- Nuclear fuel purchases are not growth capex.
- A PPA's contract value over twenty years is a project amount, not revenue in the year.
- A letter of intent with a developer and no megawatts or site is a plan, not a project; record it as `qualitative` in the project's status, not as a row with an amount.
