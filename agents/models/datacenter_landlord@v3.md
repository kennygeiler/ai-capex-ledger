# Thesis: data-center landlord (datacenter_landlord@v3)

## Thesis

Landlords build shells and lease power and space to hyperscalers, neoclouds and enterprises. Their capex is data-center capacity, which is broader than AI, so capex allocation matters but is capped: development capex is the number, and AI's part of it is rarely stated. Project-level investment matters most: campuses, megawatts under construction, joint ventures and hyperscale leases are where the AI link is visible. Plans versus reality matters for development capex guidance, and in 2026 the guidance moved a lot: Equinix raised 2026 capex from $3.655 to 4.155 billion (February) to $5.0 to 6.0 billion (July); Digital Realty raised 2026 development capex from $3.5 to 4.0 billion (April) to $4.25 to 4.75 billion (July). Revenue exposure matters least: rent is rent, and no segment is the AI one. The signal to watch is megawatts under construction and pre-leased, the backlog of signed-but-not-commenced rent, and the share of development funded off balance sheet through joint ventures.

## Companies

Equinix (EQIX), Digital Realty (DLR) and Iron Mountain (IRM). Equinix and Digital Realty are data-center REITs through and through; Digital Realty's hyperscale development is the closer to AI, Equinix's retail colocation the further. Iron Mountain sits at the edge: records storage is the bulk of the company and the data-center business is one reported segment with its own revenue and EBITDA, which makes it the one landlord with a segment to read. Miners converting sites into leased shells (Applied Digital, Core Scientific) do the same thing from the other side; they sit in `miner_to_hpc`.

Equinix (EQIX). Segments are Americas, EMEA and Asia-Pacific (Q2 2026: $1,251M, $845M, $529M revenue); no AI or hyperscale segment. 2025 revenue $9.217 billion; 2025 purchases of PP&E $4,311 million plus $994 million of real estate. 2026 capex guidance as of 29 July 2026: total $5.000 to 6.000 billion, recurring $290 to 310 million, non-recurring $4.710 to 5.690 billion, the non-recurring line excluding xScale and real estate. The xScale hyperscale program sits in joint ventures: the February 2026 release says Equinix plans to deploy $15 billion of capital with its JV partners and delivered more than 90 MW of xScale capacity in 2025; Q2 2026 revenue and AFFO benefited from one-time xScale fees (amount not given). 52 major projects underway across 33 markets as of July 2026. The only stated AI share is qualitative: about 60% of the largest Q4 2025 deals were "driven by AI workloads". Not disclosed as of 29 October 2026: AI or hyperscale share of capex or revenue, xScale megawatts leased in the quarter (the 134 MW figure in search summaries is not in the release).

Digital Realty (DLR). No AI segment. Q2 2026 (release 23 July 2026): revenue $1.924 billion; bookings $307 million of annualized GAAP base rent at 100% share ($208 million at DLR share, of which $108 million is the 0 to 1 MW and interconnection category); record backlog of signed-but-not-commenced leases $1.9 billion at 100% share, $1.4 billion at DLR share; two hyperscale leases signed in July for $410 million of annualized rent at 100% share ($205 million DLR share), not in the Q2 backlog; 2026 development capex guidance $4.25 to 4.75 billion net of partner contributions, excluding land. Off balance sheet: a 64% partner stake in three Northern Virginia data centers (288 MW, about $7.8 billion gross value) with partners' equity of about $3.5 billion, and $188 million of net promote income in the quarter from the development JV. Land bought in the Kansas City metro for about $475 million for hyperscale development. AI appears only in the company boilerplate. Not disclosed: AI share of leasing, capex or revenue; megawatts under construction were not in the release text read.

Iron Mountain (IRM). The one landlord with a reportable data-center line: the FY2025 10-K lists Global Data Center Business as a reportable segment (36 facilities) and says expanding it "requires significant capital". The segment's 2025 revenue and Adjusted EBITDA (about $803 million and $416 million per a search summary of the filing) were not verified by reading the filing text, which cut off before the segment tables; read them from the 10-K's segment note before use. FY2025 revenue $6,901.7 million. Q2 2026 (release 5 August 2026): total revenue $2,029 million; 13 MW leased in the quarter and 75 MW in July, 110 MW year to date through July; recurring capex $38.0 million in the quarter; management says about 325 MW will be energized over the next 24 months (the February 2026 release said 400 MW). Q2 data-center revenue of $263 million (up 39%) appears in call coverage, not in the release. Not disclosed as of 29 October 2026: segment capex for the data-center business in the releases read; an AI share of anything.

## Where the AI money shows up

1. **Capex by type** (`facts`, MD&A): "expansion" or "non-recurring" or "development" capex versus "recurring" or "maintenance". Expansion capex is new capacity, which since 2023 is overwhelmingly AI-driven, but the company rarely says how much is AI.
2. **What the company says** (`ai_spend`): megawatts under construction and pre-leased, hyperscale leasing, signed-not-commenced backlog, "AI" in releases; Iron Mountain reports a Global Data Center segment with its own revenue and EBITDA.
3. **Segment capex** (`facts.segment_capex`): Iron Mountain's data-center segment where the filing gives it; Equinix xScale only through JV capital statements.
4. **Joint-venture capital** (`ai_spend`): Equinix's $15 billion JV program; Digital Realty's partner equity ($3.5 billion in the Northern Virginia deal) and promote income. This is capacity built for hyperscalers that never appears in the landlord's capex.

## How to attribute

Capex, in order of hardness:

- `segment`: Iron Mountain's data-center segment capex when the filing gives it, with `basis` saying that this is data-center capacity, not AI specifically.
- `stated_amount` / `stated_share`: when the company states an AI or hyperscale part of development capex. None of the three had done so as of 29 October 2026.
- `whole_business` is not allowed: a data-center REIT's capex is data-center capex, but data-center is not AI. Use `qualitative` with confidence ≤ 0.5 when the company links the development pipeline to AI demand (Equinix's "60% of largest deals driven by AI workloads" is the kind of statement that earns it).
- `none` otherwise.

Opex: `none`.

Revenue, in order of hardness:

- `stated_share` / `stated_amount`: only when the company states AI's or hyperscale's part of revenue or of new leasing; confidence ≤ 0.6, and new leasing is not revenue in the year (say so). Digital Realty's hyperscale lease dollars ($410 million annualized in July 2026) are leasing, not revenue.
- `segment`: Iron Mountain's Global Data Center segment revenue (read it from the 10-K segment note), confidence ≤ 0.5, with `basis` "data-center rent, not AI". For Equinix and Digital Realty the data-center business is the whole company, so a segment says nothing about AI; do not use it.
- `qualitative`: leasing demand attributed to AI in words only, confidence ≤ 0.3. The usual answer for Equinix and Digital Realty.
- `none`: when nothing links rent to AI.
- `whole_business`: never.

## Projects

A project is a campus or building with a location and megawatts or an amount, a joint venture with capital raised for named development, or a hyperscale lease with a size: a named campus under construction, an xScale or hyperscale JV, a land purchase with planned megawatts, a pre-lease to a hyperscaler. Words that name one: "campus", "megawatts", "under construction", "pre-leased", "joint venture", "promote", "land", "phase", "development pipeline" when sites are named. Not a project: an interconnection or cloud-exchange product, a new market entry with no site, a rate increase, a hire.

Named projects as of 29 October 2026: Equinix's xScale JV program ($15 billion of JV capital, Hampton, Georgia contributed in January 2026; new projects in Chicago, Istanbul and Johor in Q2 2026); Digital Realty's three Northern Virginia buildings (288 MW, about $7.8 billion gross) and Kansas City land (about $475 million); Iron Mountain's 325 MW energization program and the 10 MW Amsterdam lease.

## Traps

- Expansion capex equals data-center capex, which is broader than AI. Never equate the two without a statement.
- Joint ventures (xScale, DLR's hyperscale JVs) carry capex off balance sheet; "net of partner contributions" in guidance means the gross build is larger. Note it in `basis`.
- Promote income (DLR's $188 million in Q2 2026) is a development fee, not rent and not AI revenue.
- Leasing signed in the year is backlog, not revenue; a record leasing quarter is a project signal, not a revenue row. Backlog at 100% share and at the company's share are different numbers; record which.
- Iron Mountain's segment revenue is data-center rent; its ceiling is capped for the same reason as its capex.
- Guidance raised twice in a year (both Equinix and Digital Realty in 2026) is the plans-versus-reality signal; record each revision with its date.

## Sources

- Equinix Q2 2026 results: revenue $2.625B, 2026 capex guidance $5.0 to 6.0B (recurring $290 to 310M, non-recurring $4.71 to 5.69B excluding xScale), 52 projects in 33 markets, one-time xScale fees, AI workloads cited. Equinix, 29 Jul 2026. https://newsroom.equinix.com/2026-07-29-Equinix-Reports-Second-Quarter-Results,-Raises-2026-Guidance-and-Long-Term-Outlook
- Equinix Q2 2026 8-K exhibit: same guidance, six-month PP&E purchases $2,834M, Q2 recurring capex $49M. SEC EDGAR, filed 29 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001101239/000110123926000145/a991eqix-q226xpr.htm
- Equinix Q4 2025 results: 2025 revenue $9.217B, PP&E purchases $4,311M, initial 2026 capex guidance $3.655 to 4.155B, $15B of JV capital planned, 90+ MW xScale delivered, about 60% of largest Q4 deals driven by AI workloads. SEC EDGAR 8-K, 11 Feb 2026. https://www.sec.gov/Archives/edgar/data/1101239/000110123926000030/february112026pressrelease-.htm
- Digital Realty Q2 2026 results: revenue $1.924B, bookings $307M, backlog $1.9B (100%) and $1.4B (DLR share), July hyperscale leases $410M, 2026 development capex $4.25 to 4.75B net of partners, Northern Virginia 288 MW JV, Kansas City land. SEC EDGAR 8-K, 23 Jul 2026. https://www.sec.gov/Archives/edgar/data/0001297996/000110465926086270/dlr-20260723xex99d1.htm
- Iron Mountain Q2 2026 results: revenue $2,029M, 13 MW leased in Q2 and 75 MW in July (110 MW YTD), 325 MW to be energized in 24 months, recurring capex $38.0M. SEC EDGAR 8-K, 5 Aug 2026. https://www.sec.gov/Archives/edgar/data/0001020569/000102056926000068/final-q22026earningspres.htm
- Iron Mountain Q4 and FY2025 results: 2025 revenue $6,901.7M, growth businesses up more than 30%, 400 MW to be energized over 24 months, 2026 revenue guidance $7,625 to 7,775M. Business Wire via 01net, 12 Feb 2026. https://www.01net.it/iron-mountain-reports-fourth-quarter-and-full-year-2025-results/
- Iron Mountain FY2025 10-K: Global Data Center Business is a reportable segment with 36 facilities; expansion "requires significant capital"; segment tables not reached in the text read. SEC EDGAR, filed Feb 2026. https://www.sec.gov/Archives/edgar/data/1020569/000102056926000013/irm-20251231.htm
- Independent estimate: McKinsey puts data-center capex through 2030 at $6.7T ($5.2T AI, $1.5T traditional), $3.7T to $7.9T across scenarios. IT Brew (on McKinsey's April 2025 report), 9 May 2025. https://www.itbrew.com/stories/2025/05/09/is-usd7-trillion-really-the-magic-number-to-get-ai-data-centers-up-to-speed-by-2030
