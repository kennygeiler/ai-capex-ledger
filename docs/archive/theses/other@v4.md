# Thesis: adopters, physical AI and commodities (other@v4)

## Thesis

This layer holds the companies that fit no other model: adopters that buy AI as a cost line, physical AI (robots, vehicles, rockets) and the commodity and network end of the chain. There is no industry pattern to lean on, so only what the company states counts. Capex allocation matters where stated: SpaceX states AI capex by segment ($15.8 billion in Q2 2026), Tesla guides total capex and names AI as a use without an AI amount. Project-level investment matters where a company names a cluster, plant or investment program (Tesla's Cortex, Apple's Houston server plant, ExxonMobil's data-center gas plant); revenue exposure matters only for the physical-AI sellers and is qualitative; plans versus reality applies only where the company guides AI spend (Tesla's 2026 capex cut from over $25 billion to about $20 billion). The signal to watch is a stated AI amount, and its absence: for most companies here the honest answer is `none`.

## Companies

Apple (AAPL), Tesla (TSLA), IBM (IBM), Walmart (WMT), ExxonMobil (XOM), JPMorgan (JPM), Compass (COMP), SpaceX (SPCX), Uber (UBER), Symbotic (SYM), Verizon (VZ), AT&T (T), T-Mobile (TMUS) and Freeport-McMoRan (FCX), and any company added without an industry. What each states, as of 29 October 2026:

Tesla (TSLA). No AI segment. Q2 2026 capex $5.79 billion, a record; 2026 capex guidance was "more than $25 billion" in July, cut to about $20 billion on the Q3 call (22 October 2026) after Q3 capex of $4.7 billion; the cut is not broken out by program. The Q2 2026 shareholder update lists Cortex 1 (over 90 MW) and Cortex 2 (over 115 MW) training compute in production and a ramp toward about 400 MW at Giga Texas by end 2026. The uses named are AI training compute, robotaxi fleet, Optimus production and chip fabrication. Not disclosed as of 29 October 2026: an AI-related capex amount for 2026 (the earlier "AI-related capex" line in Tesla releases was not found in the 2026 coverage read).

SpaceX (SPCX). The one company here with an AI segment: the division "previously known as xAI" reported Q2 2026 (4 August 2026) revenue of $2.56 billion, up 247%, operating loss $1.25 billion, and AI capex of $15.8 billion in the quarter (Q1 2026 AI capex $7.72 billion); 2025 AI segment revenue $3.2 billion and operating loss $6.36 billion per the IPO prospectus. Revenue comes mainly from cloud services agreements, including Anthropic at $1.25 billion a month through May 2029 for about 325,000 Nvidia GPUs across the Colossus data centers. SpaceX's AI segment is a neocloud inside a rocket company; its AI capex is `segment`.

Apple (AAPL). No AI capex stated. The $600 billion US investment commitment (raised from $500 billion in August 2025) covers suppliers, data centers, facilities and content; the Houston 250,000 square foot facility makes servers for Apple Intelligence and began shipping in 2025; Apple has not disclosed a standalone cost for the plant. Not disclosed: AI capex, AI share of the $600 billion.

IBM (IBM). Segments: Software, Consulting, Infrastructure, Financing. Q2 2026 (22 July 2026): revenue $17.2 billion; capex $359 million in the quarter. The release read gives no generative-AI book of business; coverage of the call puts it at $12.5 billion cumulative since inception (bookings, not revenue). Not disclosed: AI revenue, AI capex.

Walmart (WMT). Fiscal 2026 capex $26.64 billion (from $23.78 billion), to supply-chain automation, technology and customer-facing work; fiscal 2027 guidance $25 to 27 billion. Not disclosed: an AI amount.

ExxonMobil (XOM). Announced in December 2024 a natural-gas power plant with carbon capture (over 90% of CO2) dedicated to data centers, in early development, not grid-connected; size, site and cost not disclosed as of the articles read. Not disclosed: an AI or data-center capex amount.

JPMorgan (JPM). About $18 billion of technology spend for 2026, up $1 billion, per the May 2025 investor day as reported; AI named among the strategic investments driving expense growth. Not disclosed: an AI amount within the $18 billion.

Compass (COMP). Q2 2026 (4 August 2026): revenue $4.31 billion after the Anywhere acquisition closed 9 January 2026; technology and development expense $109 million in the quarter; capex $11 million; an AI Assistant used by about 15,000 agents. Not disclosed: an AI amount.

Uber (UBER). Press coverage says Uber used its 2026 AI coding-tools budget within four months and that it pledged capital to autonomous-vehicle partners (Waabi's $1 billion raise included Uber); no AI or AV dollar amount was stated in the pieces read. Not disclosed: an AI amount.

Symbotic (SYM). Fiscal Q3 2026 (5 August 2026): revenue $721 million, up 22%; systems revenue $671 million; 77 systems in deployment; capex $17.3 million in the quarter; Q4 guidance $760 to 780 million. Sells warehouse robots, so its revenue is physical AI with no AI line of its own; the dependency on Walmart is in the risk factors.

Verizon (VZ), AT&T (T), T-Mobile (TMUS). 2026 capex guidance: Verizon about $16.0 to 16.5 billion; AT&T about $23 to 24 billion a year for 2026 to 2028; T-Mobile around $10 billion. None states a data-center or AI amount. Network capex, not AI.

Freeport-McMoRan (FCX). Segments by region (United States, South America, Indonesia). 2026 capex guidance about $4.3 billion ($3.0 billion major projects, $1.3 billion other); 2025 copper sales about 3.6 billion pounds. Its Q4 2025 call deck cites an S&P Global study (January 2026) projecting copper demand from about 27.6 million tonnes in 2024 to about 42.3 million in 2040 with AI and data centers one of four drivers. No AI share of revenue stated.

At the edge: Symbotic sells warehouse robots; Freeport sells the copper the buildout uses; the carriers build fiber and spectrum; ExxonMobil's data-center power plant is a project once it has a size, a site and an amount.

## Where the AI money shows up

1. **What the company says** (`ai_spend`): a stated AI capex amount or segment (SpaceX's AI segment capex), a stated AI investment program (Apple's US plan when it names AI servers), a technology budget with an AI part named (JPMorgan), a capex guide with AI named as a use (Tesla).
2. **Capex** (`values.capex`): the whole, which for these companies is stores, plants, networks, mines, rockets or vehicles; AI only when stated.
3. **Segment capex** (`facts.segment_capex`): SpaceX's AI segment is the one AI segment in the layer.
4. **Revenue** (`values.revenue`, `facts.segment_revenue`): physical AI (Symbotic), copper (Freeport) and AI cloud (SpaceX's AI segment) are the sales side, with Symbotic and Freeport having no AI line of their own.

## How to attribute

Capex and opex:

- `segment`: SpaceX's AI segment capex ($15.8 billion in Q2 2026), with `basis` naming the segment and that it is a cloud and model business, not Tesla-style adoption.
- `stated_amount` / `stated_share`: only what the company states as the AI part (`scope: ai`) for the whole fiscal year. A figure for a quarter, a half or a number of months is not the year's actual: answer `qualitative` and name the part-year figures in `basis` (Tesla's Q1 2024 release: "AI infrastructure capex of $1.0B in Q1", Q2: $0.6B; the year is not stated). Tesla states a year figure only when a release or the 10-K gives one for the full year; use it then, and record "not disclosed" otherwise.
- `qualitative` when spend is linked to AI in words only (Tesla's 2026 guidance, Walmart's technology capex, JPMorgan's technology budget); `none` otherwise.
- Never estimate from PP&E categories or segments here: there is no industry pattern to lean on, and a guess would be a number with nothing behind it.

Revenue, in order of hardness:

- `segment`: SpaceX's AI segment revenue ($2.56 billion in Q2 2026), confidence ≤ 0.7, `basis` "AI cloud and model revenue, segment as reported". Not allowed for anyone else: IBM's Software and Consulting, the carriers' wireless, Freeport's regions and Compass's brokerage are not AI lines.
- `stated_amount` / `stated_share`: only when the company states AI revenue or AI's share of revenue; confidence ≤ 0.8. Rare; IBM's $12.5 billion gen-AI book of business is cumulative bookings, not revenue, ≤ 0.4 and only when a release or filing states it.
- `qualitative`: revenue linked to AI or data-center demand in words only, confidence ≤ 0.3. Symbotic (warehouse automation is the product), Freeport (copper demand from data centers when the company says so, as in its January 2026 deck), the carriers (fiber to data centers when stated).
- `none`: the common answer for adopters.
- `whole_business`: never.

## Projects

A project is a stated, sized AI investment with a site or a program: Tesla's Cortex training clusters (over 90 MW and over 115 MW, ramping to about 400 MW at Giga Texas) and the plants it ties to AI and robotics, SpaceX's Colossus data centers and the Anthropic cloud agreement ($1.25 billion a month through May 2029), Apple's Houston server plant and $600 billion US program, an ExxonMobil power project once it has a size, a bank's or retailer's named AI data center when stated with an amount. Words that name one: "cluster", "GPUs", "training compute", "megawatts", "data center", "cloud services agreement", "invest $" with a term, "facility" with a location and an AI use. Not a project: a product launch (a phone, a robot, a model), a technology budget total, a fiber or spectrum build, a mine expansion with no AI link, an acquisition, a hire.

## Traps

- "Technology" or "software" capex is not AI capex (Walmart, JPMorgan, Compass).
- Opex: AI headcount, token or model costs are rarely quantified (Uber's AI budget has no public number); `none` is the common, honest answer.
- A carrier's fiber build serves data centers among many customers; it is network capex, not AI, unless the company states an AI part.
- Copper or robot revenue is physical-end exposure in words only; never make it a share without a statement.
- A guidance cut (Tesla, over $25 billion to about $20 billion) with no program breakdown says nothing about the AI part; record the total and the absence.
- A national investment pledge (Apple's $600 billion over four years) is a program total across many uses, not AI capex; only the named AI server plant is a project, and its cost is not disclosed.
- SpaceX's AI segment is the exception that proves the rule: when a company here reports an AI segment, use `segment`; when it does not, do not build one.

## Sources

- Tesla Q2 2026 capex $5.79B, guidance over $25B, Cortex 1 over 90 MW and Cortex 2 over 115 MW, about 400 MW by end 2026; cites Tesla's Q2 2026 Update. EVwire, 23 Jul 2026. https://evwire.com/p/tesla-record-capex-q2-2026-ai-compute-fab-solar
- Tesla cuts 2026 capex guidance to $20B from $25B, Q3 capex $4.7B, uses named as robotaxi, robotics, AI chips, fabs; CFO Vaibhav Taneja on the Q3 call. CFO Dive, 22 Oct 2026. https://www.cfodive.com/news/tesla-cuts-2026-capex-20b-tech-transformation-plans/833775/
- SpaceX Q2 2026: AI division (formerly xAI) revenue $2.56B, operating loss $1.25B, AI capex $15.8B, Anthropic $1.25B a month through May 2029. Engadget (Igor Bonifacic), 4 Aug 2026. https://engadget.com/2230455/spacex-s-first-public-earnings-statement-shows-the-financials-of-an-ai-company-in-2026
- SpaceX Q1 2026 AI capex $7.72B, 2025 AI segment revenue $3.2B and loss $6.36B per prospectus, Anthropic deal terms. eWeek, 3 Aug 2026. https://www.eweek.com/news/spacex-ai-spending-earnings/
- Apple Houston 250,000 sq ft server facility for Apple Intelligence, part of a $600B national investment. Greater Houston Partnership, 7 Aug 2025. https://houston.org/news/apples-major-investment-cements-houston-leading-us-manufacturing-and-tech-hub
- IBM Q2 2026 results: revenue $17.2B, segments, capex $359M, no gen-AI figure in the release. SEC EDGAR 8-K, 22 Jul 2026. https://www.sec.gov/Archives/edgar/data/0000051143/000005114326000077/ibm-20260722xex991.htm
- IBM $12.5B cumulative generative-AI bookings, guidance cut to 4 to 5%. AI Weekly (on CNBC), 22 Jul 2026. https://aiweekly.co/alerts/ibm-cuts-2026-outlook-as-q2-mainframe-revenue-falls-42
- Walmart FY26 capex $26.64B, FY27 guidance $25 to 27B, no AI amount. Retail Insight Network, 27 Apr 2026. https://www.retail-insight-network.com/news/walmart-fy26-revenue-rises-4-7/
- ExxonMobil data-center gas plant with carbon capture, Darren Woods, no size or cost. Semafor (Tim McDonnell), 13 Dec 2024. https://www.semafor.com/article/12/13/2024/exxonmobil-wants-to-make-bespoke-carbon-capture-power-plants-for-data-centers
- ExxonMobil plant to capture over 90% of CO2, early development, not grid-connected. Power Engineering, 12 Dec 2024. https://www.power-eng.com/environmental-emissions/carbon-capture-storage/exxonmobil-plans-large-gas-plant-with-ccs-for-data-center-power/
- JPMorgan about $18B of technology spend in 2026, AI among strategic investments. Stocktwits (Ananya Mariam Rajesh), 5 Mar 2026. https://stocktwits.com/news-articles/markets/equity/jpmorgan-is-pouring-billions-into-tech-to-rewire-the-bank-for-the-ai-age/cLIuDSVRENq
- Compass Q2 2026: revenue $4.31B, tech and development expense $109M, capex $11M, AI Assistant usage. SEC EDGAR 8-K, 4 Aug 2026. https://www.sec.gov/Archives/edgar/data/0001563190/000156319026000135/exhibit9918-k2q26pr.htm
- Uber 2026 AI tools budget used in four months, no dollar figure. Fortune, 26 May 2026. https://www.fortune.com/2026/05/26/uber-coo-ai-spending-tokens-claude-code/
- Symbotic fiscal Q3 2026: revenue $721M, 77 systems in deployment, capex $17.3M. SEC EDGAR 8-K, 5 Aug 2026. https://www.sec.gov/Archives/edgar/data/0001837240/000183724026000042/q3268-k_ex991.htm
- Carrier 2026 capex: AT&T $23 to 24B a year 2026 to 2028, Verizon $16 to 16.5B, T-Mobile around $10B, no AI amounts. TelecomLead, 14 Sep 2026. https://telecomlead.com/telecom-equipment/telecom-capex-2026-operators-shift-billions-from-coverage-to-spectrum-fiber-and-ai-networks-127716
- Freeport Q4 2025 call deck: 2026 capex about $4.3B, S&P copper study with AI and data centers as a driver, 2025 copper sales 3.6B lbs. SEC EDGAR 8-K exhibit, 22 Jan 2026. https://www.sec.gov/Archives/edgar/data/831259/000083125926000006/fcx4q25cc_final.htm
