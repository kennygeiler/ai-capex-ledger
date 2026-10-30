# Thesis: power producer (power@v3)

## Thesis

Independent power producers sell electrons, and their AI story is data-center load: nuclear restarts and uprates, gas plants co-located with data centers, long-term PPAs with hyperscalers. Project-level investment is the measure that matters: the AI link lives in a named plant with a named counterparty. Capex allocation matters only for growth capex the company itself ties to such a project; the rest is generation, transmission and fuel. Plans versus reality matters for growth capex guidance. Revenue exposure does not matter: power sold under a hyperscaler PPA is still power, and no segment is the AI one. The signal to watch is contracted data-center megawatts with a counterparty and a date, and whether the capex that serves them has started.

The backdrop is real load growth. LBNL's report for the DOE (December 2024) put US data-center use at 176 TWh in 2023 (4.4% of US electricity) and projected 325 to 580 TWh by 2028 (6.7% to 12%). That is why the PPAs below exist; it is not evidence that any one producer's capex is AI.

## Companies

Vistra (VST), Constellation (CEG), NRG (NRG) and Talen (TLN). None of the four reports an AI or data-center segment. Vistra reports Retail, Texas, East, West and Asset Closure; Talen reports PJM and All Other; no segment is by customer. What each has stated:

Constellation (CEG). Two named nuclear PPAs. Crane Clean Energy Center (the former Three Mile Island Unit 1, 835 MW) under a 20-year PPA with Microsoft signed September 2024; restart target 2027, about $1.6 billion of restart investment, backed by a $1 billion DOE Loan Programs Office loan closed November 2025. Clinton Clean Energy Center under a 20-year PPA with Meta for 1,121 MW starting June 2027, with a 30 MW uprate (release of 3 June 2025; the release does not use the words data center, but Meta's quote ties it to "our AI ambitions"). The Q2 2026 release (6 August 2026) adds 920 MW of new 15 to 20 year nuclear PPAs starting 2029 to 2032 with unnamed investment-grade customers, plus 176 MW to Walmart; it gives no data-center capex figure and no capex guidance. Not disclosed as of 29 October 2026: any AI or data-center share of capex or revenue.

Talen (TLN). One named project. The FY2025 10-K (Item 1) states a fixed-price PPA to supply AWS up to 1,920 MW from Susquehanna through 2042, ramping to full volume no later than 2032. Utility Dive (11 June 2025) reports the ramp as 840 to 1,200 MW in 2029 and 1,680 to 1,920 MW in 2032, an estimated $18 billion of revenue over the contract life per Talen's investor deck, and the shift of the 300 MW co-located arrangement to a front-of-the-meter structure. The 2024 sale of the adjacent data campus to AWS is the origin of the arrangement. Not disclosed as of 29 October 2026 in the filing text read: a data-center capex amount.

Vistra (VST). The Q4 2025 release (26 February 2026) states a 20-year PPA with AWS for up to 1,200 MW at Comanche Peak (power delivery from 2027 per Utility Dive, 10 August 2026, which also reports Amazon's $5 billion data center next to the plant), 20-year PPAs with Meta for more than 2,600 MW of energy, capacity and uprates across its PJM nuclear fleet, and a 200 MW solar PPA with AWS at Oak Hill. 2025 capex was $2,752 million including nuclear fuel and LTSA prepayments, with $1,348 million maintenance and $1,126 million growth and development; 2026 guidance is $1,536 million total. The release does not split growth capex by customer or project. Not disclosed: any AI or data-center share of capex or revenue.

NRG (NRG). No nuclear. Its data-center story is a 295 MW long-term power agreement for new data centers on two company-owned Texas sites (first power second half 2026, full by 2030, per Power Engineering, 6 August 2025, counterparty not named), a stated 445 MW of contracted data-center capacity and 4 GW of letters of intent (Utility Dive, 17 November 2025), the GE Vernova and Kiewit development agreement for about 5.4 GW of gas plants (1.2 GW by 2029, 1.2 GW by 2030, 3 GW 2030 to 2032) with 2.4 GW of turbine slots reserved, and the roughly $12 billion LS Power acquisition of about 13 GW of gas. Management said in November 2025 that a data-center agreement tied to the gas build would come in 2026; none was found by 29 October 2026. Not disclosed: a capex amount for the gas plants or an AI share of anything.

Regulated utilities that serve data centers are not in the set; neither are the fuel-cell and turbine makers, who sit in `datacenter_build`.

## Where the AI money shows up

1. **What the company says** (`ai_spend`): named projects with a data-center counterparty ("Crane Clean Energy Center restart for Microsoft", "Susquehanna campus for Amazon", "Comanche Peak PPA with AWS"), growth capex guidance tied to data-center demand.
2. **Capex by category** (`facts`, MD&A): "growth" versus "maintenance" or "nuclear fuel". Vistra reports this split; growth capex tied to a named data-center project is attributable.
3. **Segment capex** (`facts.segment_capex`): by generation fleet or market, never by customer.

## How to attribute

Capex, in order of hardness:

- `stated_amount`: a capex amount the company ties to a data-center project or PPA (`scope: ai` or `scope: datacenter`). Crane's $1.6 billion restart is the one such amount in the set, and it is a restart cost spread over 2024 to 2027, not a year's capex; take the year's share only when the filing gives it.
- `qualitative` with confidence ≤ 0.4 when growth capex is linked to data-center demand in words only (Vistra's growth and development capex, NRG's gas build).
- `none` otherwise, which is the common answer.

Opex: `none`.

Revenue, in order of hardness:

- `stated_amount` / `stated_share`: only when the company states revenue under data-center PPAs for the year; confidence ≤ 0.5, with `basis` "contracted power to a data-center customer, not AI revenue". A contract's total value (Talen's $18 billion over the life of the AWS PPA) is not revenue in the year. None of the four had stated such a figure as of 29 October 2026.
- `segment`: not available. Generation and market segments (Vistra's Texas and East, Talen's PJM) are not data-center lines; never sum them.
- `qualitative`: load growth or pricing attributed to data-center demand in words only, confidence ≤ 0.3.
- `none`: the common and honest answer.
- `whole_business`: never.

## Projects

A project is a plant with a counterparty, a size and a date: a nuclear restart or uprate under a hyperscaler PPA, a gas plant built or co-located for a named data-center customer, a PPA with megawatts and a term, a data-center campus on company land with a development partner. Words that name one: "power purchase agreement", "restart", "uprate", "co-located", "behind the meter", "front of the meter", "megawatts", "gigawatts", "20-year", "campus", "slot reservation", "letter of intent" with a counterparty. Not a project: a fuel contract, a rate case, a hedging statement, a share buyback, a hire.

Named projects as of 29 October 2026: Crane (CEG, Microsoft, 835 MW, 2027), Clinton (CEG, Meta, 1,121 MW plus 30 MW uprate, June 2027), Susquehanna (TLN, AWS, up to 1,920 MW through 2042), Comanche Peak (VST, AWS, up to 1,200 MW, from 2027), Vistra PJM nuclear (Meta, more than 2,600 MW), NRG Texas sites (295 MW, counterparty not named) and the NRG gas build (5.4 GW with GE Vernova and Kiewit, no data-center customer named yet).

## Traps

- A restart or uprate serving the grid is not AI capex because a hyperscaler signed a PPA; only capex the company itself ties to the counterparty counts.
- Nuclear fuel purchases are not growth capex. Vistra's capex totals include nuclear fuel and LTSA prepayments; strip them before reading growth.
- A PPA's contract value over twenty years is a project amount, not revenue in the year.
- Megawatts in a release can be a contract ceiling ("up to 1,200 MW"), a ramp step, or an aggregate across plants ("more than 2,600 MW"); record which.
- A letter of intent (NRG's 4 GW) with no megawatts contracted or site is a plan, not a project; record it as `qualitative` in the project's status, not as a row with an amount.
- A PPA release that never says "data center" (Constellation's Clinton and Q2 2026 PPAs) is still a data-center link only when the counterparty is a hyperscaler; for unnamed investment-grade customers it is `none`.

## Sources

- Vistra Q4 and FY2025 results: AWS Comanche Peak PPA up to 1,200 MW, Meta PJM PPAs more than 2,600 MW, 2025 capex $2,752M (maintenance $1,348M, growth $1,126M), 2026 capex guidance $1,536M. Vistra, 26 Feb 2026. https://investor.vistracorp.com/2026-02-26-Vistra-Reports-Fourth-Quarter-and-Full-Year-2025-Results
- Vistra Q2 2026 call: Comanche deal 1.2 GW, 20 years, delivery 2027, Amazon's $5B data center; Texas data-center pause. Utility Dive (Diana DiGangi), 10 Aug 2026. https://www.utilitydive.com/news/vistra-texas-data-center-pause-comanche-amazon-earnings/827434/
- Constellation and Meta 20-year PPA for 1,121 MW at Clinton from June 2027, 30 MW uprate. Constellation, 3 Jun 2025. https://www.constellationenergy.com/news/2025/constellation-meta-sign-20-year-deal-for-clean-reliable-nuclear-energy-in-illinois.html
- Constellation Q2 2026 results: 920 MW of new nuclear PPAs, Crane NRC fuel license and FERC CIR waiver, restart 2027. Constellation, 6 Aug 2026. https://www.constellationenergy.com/news/2026/08/constellation-reports-second-quarter-2026-results.html
- Crane restart: $1.6B investment, $1B DOE loan, 20-year Microsoft PPA, restart as early as 2027. World Nuclear News, 19 Nov 2025. https://world-nuclear-news.org/articles/constellation-secures-usd1-billion-loan-for-reactor-restart
- Crane is an 835 MWe unit; 20-year Microsoft PPA signed 2024; 2027 start reaffirmed. ANS Nuclear Newswire, 3 Apr 2026. https://www.ans.org/news/2026-04-03/article-7905/constellation-seeks-ferc-help-with-crane-restart/
- Talen FY2025 10-K, Item 1: AWS PPA up to 1,920 MW through 2042, full volume no later than 2032; segments PJM and All Other. Talen Energy, filed Feb 2026. https://www.sec.gov/Archives/edgar/data/1622536/000162253626000017/tln-20251231.htm
- Talen and AWS PPA: ramp 840 to 1,200 MW in 2029 and 1,680 to 1,920 MW in 2032, about $18B lifetime revenue per Talen deck, front-of-meter shift. Utility Dive (Ethan Howland), 11 Jun 2025. https://www.utilitydive.com/news/talen-amazon-aws-susquehanna-nuclear-data-center-t/750440/
- NRG: 295 MW data-center agreement on two Texas sites, 4 GW of LOIs, 2.4 GW of turbines reserved, 5.4 GW gas plan with GE Vernova and Kiewit. Power Engineering (Kevin Clark), 6 Aug 2025. https://www.power-eng.com/gas/nrg-caps-busy-second-quarter-with-295-mw-data-center-power-deal/
- NRG Q3 2025: 445 MW contracted, data-center deal on the gas build expected in 2026, LS Power about $12B, gas timeline 2029 to 2032. Utility Dive (Diana DiGangi), 17 Nov 2025. https://www.utilitydive.com/news/nrg-aims-for-2026-next-step-in-54-gw-gas-deal-with-ge-vernova-kiewit/805692/
- US data-center electricity 176 TWh in 2023 (4.4%), 325 to 580 TWh by 2028 (6.7% to 12%). DOE on the LBNL report, 20 Dec 2024. https://www.energy.gov/articles/doe-releases-new-report-evaluating-increase-electricity-demand-data-centers
