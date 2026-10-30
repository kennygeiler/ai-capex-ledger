# Thesis: data-center build suppliers (datacenter_build@v3)

## Thesis

These companies turn a hyperscaler's capex into a building: power distribution, cooling, switchgear, turbines, fuel cells and the construction labour. They are paid by the buildout, so revenue exposure (data-center revenue and backlog) is the measure that matters. Capex allocation rarely matters: their capex is factories and fleets, attributable only when an expansion is tied to data-center demand with a number. Project-level investment matters for those plant expansions and for named construction contracts; plans versus reality does not. The signal to watch is the data-center share of orders and backlog, which runs a year or more ahead of revenue. In mid-2026 that signal was loud: GE Vernova's data-center orders passed $5 billion year to date by July, more than double all of 2025; Eaton's Electrical Americas backlog was up 33%; Powell booked a single data-center order above $400 million; Modine signed a $4 billion chiller agreement with one hyperscaler.

## Companies

Vertiv (VRT), Eaton (ETN), nVent (NVT), Modine (MOD), Johnson Controls (JCI), Quanta (PWR), Comfort Systems (FIX), EMCOR (EME), GE Vernova (GEV), Powell (POWL) and Bloom Energy (BE). What each states, as of 29 October 2026:

Vertiv (VRT). Segments are by region (AMER $2,070.8M, APAC $719.9M, EMEA $483.6M in Q2 2026), so no segment is the data-center one. Q2 2026 net sales $3,274.3M, up 24.1% (17.8% organic); 2026 guidance $13.8 to 14.2 billion, organic growth 30 to 32%; Q2 capex $173.3M, full-year about 4% of revenue. The release says demand "for AI and general compute continues to intensify" and gives no figure. Not disclosed in the Q2 2026 release: a data-center share of revenue, trailing orders growth, backlog or book-to-bill. Vertiv is the core of the layer because nearly all its products are data-center infrastructure, but the share itself is not stated in the release.

Eaton (ETN). Segments: Electrical Americas, Electrical Global, Aerospace, Mobility. Q2 2026 (31 July 2026): sales $8.5 billion; Electrical Americas $4.0 billion, up 18% organic, twelve-month rolling orders up 41% organic, backlog up 33%; Electrical sector backlog up 43%. Data centers are "a key growth driver" with no revenue share or orders figure in the release. Call coverage cites about 65% data-center revenue growth in Electrical Americas, but that is not in the release.

nVent (NVT). Segments: Systems Protection and Electrical Connections. Q2 2026 (31 July 2026): sales $1.5 billion, up 53% (47% organic); 2026 organic growth guidance raised to 32 to 34%; another liquid-cooling manufacturing expansion announced without an amount; new products "contributed more than 30 points to sales growth". Not disclosed in the release: a data-center sales figure (the "more than $2 billion of data-center sales in 2026" and $2.5 billion backlog figures come from call coverage, not the release).

Modine (MOD). Fiscal 2026 (year to 31 March 2026, release 26 May 2026): net sales $3,181.1M, up 23%; Q4 Climate Solutions sales $665.9M, up 87%; Q4 Data Centers sales up 158%; "a landmark $4 billion long-term agreement for chiller sales with a major hyperscale customer"; fiscal 2027 net sales growth 20 to 35%; free cash flow down on capex "tied to Data Centers growth", amount not given. Data Centers is a product group inside Climate Solutions, not yet a reported segment in the fiscal 2026 release.

Johnson Controls (JCI). Segments: Americas, EMEA, APAC. Fiscal Q3 2026 (29 July 2026): sales $6.6 billion; orders up 27% organic; backlog $21.0 billion, up 32%; Americas backlog $15.9 billion, up 40%; growth "supported by sustained demand from data centers and other mission-critical environments". No data-center dollar figure or share in the release. Call coverage gives data centers as a high-teens share of fiscal 2026 sales; not in the release.

Quanta (PWR). Segments: Electric; Underground and Infrastructure. Q2 2026 (30 July 2026): revenue $9.56 billion; backlog $53.4 billion (Electric $43.8 billion); RPO $33.6 billion; 2026 revenue guidance $39.3 to 39.7 billion; 2026 net capex about $900 million. The release discusses data-center and technology markets with no quantified figure. Call coverage puts technology-related work at 15 to 20% of the business; not in the release.

Comfort Systems (FIX). No reportable segments named in the release. Q2 2026 (23 July 2026): revenue $3.27 billion; backlog $14.06 billion, up from $8.12 billion a year earlier (same-store $13.70 billion). The release does not mention data centers or technology; call coverage attributes bookings strength to the technology sector and modular work.

EMCOR (EME). Segments: US electrical construction, US mechanical construction, US building services, US industrial services. Q2 2026 (30 July 2026): revenue $5.15 billion; RPOs $17.14 billion, up 43.9%, with Network and Communications among the sectors with the most growth; 2026 revenue guidance $20.0 to 20.5 billion. No data-center figure in the release; call coverage puts network and communications revenue (which holds the data-center work) up 45% in electrical construction.

GE Vernova (GEV). Segments: Power, Electrification, Wind. Q2 2026 (22 July 2026): orders $24.2 billion, backlog $176 billion; gas equipment backlog plus slot reservations 116 GW, up from 100 GW, with at least 125 GW under contract expected by year end 2026; data-center orders over $5 billion year to date, more than double the 2025 total; capex program $6 billion for 2025 to 2028. The one company in the layer that states a data-center orders amount.

Powell (POWL). Markets, not segments: Electric Utility, Commercial and Other Industrial, Petrochemical, Oil and Gas, LNG. Fiscal Q3 2026 (3 August 2026): revenue $312M; new orders $934M, up 158%; backlog $2.4 billion, up 69%; one data-center order above $400 million tied to behind-the-meter on-site generation; capex $6.5M in the quarter; Jacintoport yard expansion finishing by fiscal year end. Data-center share of backlog not in the release (a prior call put it near 15%).

Bloom Energy (BE). No segments by end market. Q2 2026 (28 July 2026): revenue $1,065M, up 165.5%; 2026 revenue guidance $3.9 to 4.2 billion; PP&E purchases $51.6M in the quarter; "over a dozen US neoclouds, AI labs, and colocation data center operators" cited with no figure. The Oracle and Brookfield agreements are not in the release.

At the edge: Quanta, Comfort Systems and EMCOR are contractors whose AI exposure is the share of work in data centers, which none of the three states in its release; Bloom sells fuel cells to data centers among other customers.

## Where the AI money shows up

1. **Segment revenue and backlog** (`facts.segment_revenue`, `ai_spend`): "Data center" as an end market or vertical; backlog or orders tied to data centers ("data center orders", "mega order", "slot reservation"); "hyperscale" in releases.
2. **What the company says** (`ai_spend`): capacity expansions explicitly for data-center demand ("liquid-cooling manufacturing expansion", "capex tied to Data Centers growth", "Jacintoport fabrication yard expansion").
3. **Capex** (`values.capex`): factory capacity. AI spend only when the company ties an expansion to data-center demand and gives a number; in 2026 none of the eleven did in a release.

## How to attribute

Capex and opex:

- `stated_amount` / `stated_share` when the company states a capex amount or share for data-center capacity (`scope: ai` or `scope: datacenter`).
- `qualitative` with confidence ≤ 0.4 when capex is linked to data-center demand in words only (Modine, nVent, Powell in 2026).
- `none` otherwise. Data-center revenue or backlog goes in `basis`, never in `ai_amount`; the revenue field below is where it becomes a row.

Revenue, in order of hardness:

- `stated_share`: the company states the data-center share of revenue. As of 29 October 2026 none of the eleven stated one in a release; shares in call coverage (JCI high teens, Quanta 15 to 20%, Powell about 15% of backlog) are call statements, confidence ≤ 0.5, and `basis` must say "call, not release or filing". Data center is broader than AI: confidence ≤ 0.7 at best and say "data center, not AI" in `basis`.
- `stated_amount`: the company states data-center revenue or orders for the period (GE Vernova's $5 billion of data-center orders, Modine's $4 billion chiller agreement, Powell's $400 million order); confidence ≤ 0.7 for revenue. An orders, agreement or backlog figure is not revenue: ≤ 0.4.
- `segment`: only where a reported segment is the data-center line. Modine's Data Centers group once it reports as a segment; nVent's Systems Protection is data-center heavy but not a data-center segment. Vertiv's regions, Eaton's Electrical Americas, JCI's regions, Quanta's Electric, EMCOR's electrical construction and GE Vernova's Power are not data-center lines; do not sum them. Confidence ≤ 0.6.
- `qualitative`: data-center demand named as a driver with no figure, confidence ≤ 0.3. The 2026 answer for Vertiv, Eaton, JCI, Quanta, EMCOR, Comfort and Bloom from their releases.
- `none`: no link stated (Comfort Systems' Q2 2026 release).
- `whole_business`: never, even for Vertiv; use a stated share when one appears.

## Projects

A project is a plant or capacity expansion the company ties to data-center demand with a location and an amount, or a named data-center construction, equipment or turbine contract with a size: a new switchgear or cooling plant, added turbine capacity, a contracted campus build with megawatts, a multi-year supply agreement with a hyperscaler. Words that name one: "facility", "plant", "expansion", "capacity", "investment of", "contract", "agreement", "mega order", "slot reservation", "megawatts", "gigawatts" with a site or a customer. Not a project: a new product (a cooling unit, a turbine model), an order-growth statement, backlog totals, a hire.

Named as of 29 October 2026: Modine's $4 billion hyperscale chiller agreement; Powell's $400 million-plus behind-the-meter data-center order and Jacintoport expansion; nVent's liquid-cooling plant expansion; GE Vernova's 116 GW of gas backlog and slot reservations and $6 billion 2025 to 2028 capex program (not data-center specific).

## Traps

- Data-center revenue is the customer's spend, not this company's.
- Construction firms (Quanta, Comfort Systems, EMCOR) have small capex; their AI exposure is revenue mix. Expect `none` with a strong `basis`.
- Data center is not AI; every revenue ceiling here is capped for that reason.
- Orders, agreements, slot reservations and backlog run ahead of revenue; never sum them into a revenue row. GE Vernova's slot reservations are not even firm orders.
- A turbine or switchgear plant built for all customers is a project only when the company ties it to data-center demand.
- Numbers in call summaries (Vertiv backlog, nVent data-center sales, Eaton data-center growth, JCI share) are not in the releases; cite the call or leave the field at the release's ceiling.

## Sources

- Vertiv Q2 2026 results: net sales $3,274.3M, 2026 guidance $13.8 to 14.2B, capex $173.3M, regional segments, AI demand stated without figures. SEC EDGAR 8-K, 29 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001674101/000162828026050323/q22026exhibit991vrt07292026.htm
- Eaton Q2 2026 results: sales $8.5B, Electrical Americas $4.0B with orders up 41% and backlog up 33%, data centers a key growth driver without a figure. SEC EDGAR 8-K, 31 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001551182/000155118226000027/etn06302026exhibit99.htm
- nVent Q2 2026 results: sales $1.5B up 53%, organic guidance 32 to 34%, liquid-cooling expansion. Data Center Frontier press release, 31 Jul 2026. https://www.datacenterfrontier.com/press-releases/article/55397178/nvent-delivers-record-sales-and-eps-in-q2-2026
- Modine Q4 fiscal 2026 results: net sales $3,181.1M, Q4 Data Centers sales up 158%, $4B hyperscale chiller agreement, fiscal 2027 growth 20 to 35%. Placera (Avanza) copy of release, 26 May 2026. https://www.placera.se/telegram/avanza/39_bb020953-b8ee-471d-9c85-e3f54cdecdbe.html
- Johnson Controls fiscal Q3 2026 results: sales $6.6B, backlog $21.0B up 32%, Americas backlog $15.9B up 40%, data centers cited. SEC EDGAR 8-K, 29 Jul 2026. https://www.sec.gov/Archives/edgar/data/0000833444/000083344426000083/q3ex991xq3fy26earningsrele.htm
- Quanta Q2 2026 results: revenue $9.56B, backlog $53.4B, RPO $33.6B, 2026 capex about $900M. SEC EDGAR 8-K, 30 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001050915/000119312526324855/d56853dex991.htm
- Comfort Systems Q2 2026 results: revenue $3.27B, backlog $14.06B, no data-center mention. SEC EDGAR 8-K, 23 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001035983/000110465926086255/fix-20260723xex99d1.htm
- EMCOR Q2 2026 results: revenue $5.15B, RPOs $17.14B up 43.9%, Network and Communications among largest growth. SEC EDGAR 8-K, 30 Jul 2026. https://www.sec.gov/Archives/edgar/data/0000105634/000010563426000112/eme-ex991_2026630xq2.htm
- GE Vernova Q2 2026 results: orders $24.2B, backlog $176B, gas backlog plus slots 116 GW, data-center orders over $5B YTD, $6B capex 2025 to 2028. SEC EDGAR 8-K, 22 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001996810/000199681026000147/gevpressrelease2q26.htm
- Powell fiscal Q3 2026 results: orders $934M, backlog $2.4B, data-center order over $400M, Jacintoport expansion. SEC EDGAR 8-K, 3 Aug 2026. https://www.sec.gov/Archives/edgar/data/0000080420/000008042026000103/ex991-powlq3xfy2026earning.htm
- Bloom Energy Q2 2026 results: revenue $1,065M, 2026 guidance $3.9 to 4.2B, neocloud and colocation customers cited without figures. SEC EDGAR 8-K, 28 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001664703/000162828026050150/ex991_q226financialresults.htm
- Independent estimate: McKinsey's $6.7T of data-center capex through 2030 ($5.2T AI), $3.7T to $7.9T across scenarios. IT Brew, 9 May 2025. https://www.itbrew.com/stories/2025/05/09/is-usd7-trillion-really-the-magic-number-to-get-ai-data-centers-up-to-speed-by-2030
