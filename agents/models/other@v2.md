# Thesis: adopters, physical AI and commodities (other@v2)

## Thesis

This layer holds the companies that fit no other model: adopters that buy AI as a cost line, physical AI (robots, vehicles) and the commodity and network end of the chain. There is no industry pattern to lean on, so only what the company states counts. Capex allocation matters where stated (Tesla's AI capex); project-level investment matters where a company names a cluster, plant or investment program; revenue exposure matters only for the physical-AI sellers and is qualitative; plans versus reality applies only where the company guides AI spend. The signal to watch is a stated AI amount, and its absence: for most companies here the honest answer is `none`.

## Companies

Apple (AAPL), Tesla (TSLA), IBM (IBM), Walmart (WMT), ExxonMobil (XOM), JPMorgan (JPM), Compass (COMP), SpaceX (SPCX), Uber (UBER), Symbotic (SYM), Verizon (VZ), AT&T (T), T-Mobile (TMUS) and Freeport-McMoRan (FCX), and any company added without an industry. Tesla is the one adopter that states AI capex. Apple, IBM, Walmart, JPMorgan, Compass, Uber and SpaceX buy or build AI as part of a technology budget. At the edge: Symbotic sells warehouse robots, so its revenue is physical AI; Freeport sells the copper the buildout uses; the carriers (Verizon, AT&T, T-Mobile) build fiber and spectrum, which is network capex, not AI, whatever the AI demand for it; ExxonMobil's data-center power plans are a project when stated.

## Where the AI money shows up

1. **What the company says** (`ai_spend`): a stated AI capex amount (Tesla), a stated AI investment program (Apple's US investment plan when it names AI servers), a technology budget with an AI part named (JPMorgan).
2. **Capex** (`values.capex`): the whole, which for these companies is stores, plants, networks, mines or vehicles; AI only when stated.
3. **Revenue** (`values.revenue`, `facts.segment_revenue`): physical AI (Symbotic) and copper (Freeport) are the sales side of the buildout's physical end, with no AI line of their own.

## How to attribute

Capex and opex:

- `stated_amount` / `stated_share`: only what the company states as the AI part (`scope: ai`). Tesla states AI-related capex in its releases; use it.
- `qualitative` when spend is linked to AI in words only; `none` otherwise.
- Never estimate from PP&E categories or segments here: there is no industry pattern to lean on, and a guess would be a number with nothing behind it.

Revenue, in order of hardness:

- `stated_amount` / `stated_share`: only when the company states AI revenue or AI's share of revenue; confidence ≤ 0.8. Rare.
- `segment`: not allowed. No company here reports an AI segment; IBM's software and consulting segments, the carriers' wireless segments and Freeport's copper segments are not AI lines.
- `qualitative`: revenue linked to AI or data-center demand in words only, confidence ≤ 0.3. Symbotic (warehouse automation is the product), Freeport (copper demand from data centers when the company says so), the carriers (fiber to data centers when stated).
- `none`: the common answer for adopters.
- `whole_business`: never.

## Projects

A project is a stated, sized AI investment with a site or a program: Tesla's training clusters and the plants it ties to AI and robotics, Apple's named server plant or AI investment program, an ExxonMobil or other power project stated as serving data centers, a bank's or retailer's named AI data center when stated with an amount. Words that name one: "cluster", "GPUs", "training compute", "data center", "invest $" with a term, "facility" with a location and an AI use. Not a project: a product launch (a phone, a robot, a model), a technology budget total, a fiber or spectrum build, a mine expansion with no AI link, an acquisition, a hire.

## Traps

- "Technology" or "software" capex is not AI capex.
- Opex: AI headcount or model costs are rarely quantified; `none` is the common, honest answer.
- A carrier's fiber build serves data centers among many customers; it is network capex, not AI, unless the company states an AI part.
- Copper or robot revenue is physical-end exposure in words only; never make it a share without a statement.
