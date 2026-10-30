# Thesis: data-center build suppliers (datacenter_build@v2)

## Thesis

These companies turn a hyperscaler's capex into a building: power distribution, cooling, switchgear, turbines, fuel cells and the construction labour. They are paid by the buildout, so revenue exposure (data-center revenue and backlog) is the measure that matters. Capex allocation rarely matters: their capex is factories and fleets, attributable only when an expansion is tied to data-center demand with a number. Project-level investment matters for those plant expansions and for named construction contracts; plans versus reality does not. The signal to watch is the data-center share of orders and backlog, which runs a year or more ahead of revenue.

## Companies

Vertiv (VRT), Eaton (ETN), nVent (NVT), Modine (MOD), Johnson Controls (JCI), Quanta (PWR), Comfort Systems (FIX), EMCOR (EME), GE Vernova (GEV), Powell (POWL) and Bloom Energy (BE). Vertiv is the core: nearly all of it is data-center infrastructure. Eaton, nVent, Modine, Johnson Controls and Powell sell electrical and thermal equipment with data centers as one end market, and most state the data-center share. GE Vernova sells gas turbines whose data-center orders it states. At the edge: Quanta, Comfort Systems and EMCOR are contractors whose AI exposure is the share of work in data centers, stated when they choose; Bloom Energy sells fuel cells to data centers among other customers.

## Where the AI money shows up

1. **Segment revenue and backlog** (`facts.segment_revenue`, `ai_spend`): "Data center" as an end market or vertical; backlog or orders tied to data centers; "hyperscale" in releases.
2. **What the company says** (`ai_spend`): capacity expansions explicitly for data-center demand ("expanding liquid-cooling capacity", "new switchgear plant for data-center orders").
3. **Capex** (`values.capex`): factory capacity. AI spend only when the company ties an expansion to data-center demand and gives a number.

## How to attribute

Capex and opex:

- `stated_amount` / `stated_share` when the company states a capex amount or share for data-center capacity (`scope: ai` or `scope: datacenter`).
- `qualitative` with confidence ≤ 0.4 when capex is linked to data-center demand in words only.
- `none` otherwise. Data-center revenue or backlog goes in `basis`, never in `ai_amount`; the revenue field below is where it becomes a row.

Revenue, in order of hardness:

- `stated_share`: the company states the data-center share of revenue (Vertiv, Eaton, Comfort Systems, EMCOR, Modine and Powell do so when they choose). Data center is broader than AI: confidence ≤ 0.7 and say "data center, not AI" in `basis`.
- `stated_amount`: the company states data-center revenue for the year; confidence ≤ 0.7 for the same reason. An orders or backlog figure is not revenue: ≤ 0.4.
- `segment`: only where a reported segment is the data-center line. nVent's data solutions segment and Modine's data-center product line when reported as segments; Vertiv reports by region, so no segment is the AI one. Eaton's Electrical Americas, Johnson Controls' regional segments, Quanta's Electric Power segment and GE Vernova's Power segment are not data-center lines; do not sum them. Confidence ≤ 0.6.
- `qualitative`: data-center demand named as a driver with no figure, confidence ≤ 0.3. Common for Bloom Energy and the contractors.
- `none`: no link stated.
- `whole_business`: never, even for Vertiv; use its stated share.

## Projects

A project is a plant or capacity expansion the company ties to data-center demand with a location and an amount, or a named data-center construction or turbine contract with a size: a new switchgear or cooling plant, added turbine capacity, a contracted campus build with megawatts. Words that name one: "facility", "plant", "expansion", "capacity", "investment of", "contract", "megawatts", "gigawatts" with a site or a customer. Not a project: a new product (a cooling unit, a turbine model), an order-growth statement, backlog totals, a hire.

## Traps

- Data-center revenue is the customer's spend, not this company's.
- Construction firms (Quanta, Comfort Systems, EMCOR) have small capex; their AI exposure is revenue mix. Expect `none` with a strong `basis`.
- Data center is not AI; every revenue ceiling here is capped for that reason.
- Orders and backlog run ahead of revenue; never sum them into a revenue row.
- A turbine or switchgear plant built for all customers is a project only when the company ties it to data-center demand.
