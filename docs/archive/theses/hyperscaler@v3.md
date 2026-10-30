# Thesis: hyperscaler (hyperscaler@v3)

## Thesis

The hyperscalers are the buyers. Their capex is the AI buildout, and the server and network category of PP&E is where the GPUs land. Capex allocation is the measure that matters most here; project-level investment (named campuses, power deals, cloud commitments to neoclouds) and plans versus reality (capex guidance against the actual) matter next. Revenue exposure matters least: these companies sell ads, software and cloud, and no reported segment is the AI one. The signal to watch is the year-on-year growth in the gross value of the server and network category, read against the company's own capex guidance and against purchase commitments, which run a year ahead.

## Companies

Microsoft (MSFT), Alphabet (GOOGL), Amazon (AMZN), Meta (META) and Oracle (ORCL). The first four are the model: huge capex, a server category in the PP&E note, guidance "to support AI". Oracle sits at the edge: it is a hyperscaler by spend (OCI capex, finance leases) but its buildout is contracted to one customer class and its remaining performance obligations are the forward number; a reader should treat it as a buyer with a seller's backlog. Apple and Tesla also buy compute but do not report like this; they sit in `other`.

## Where the AI money shows up

1. **Capex** (`values.capex`, cash paid for property and equipment) is the main line, but it understates the buildout: finance leases (`facts.finance_lease_liability`, growing fast at Microsoft and Meta) and third-party-funded datacenters (Meta's Hyperion joint venture) sit outside it.
2. **PP&E by category** (`facts.ppe_category`): the "servers and network equipment" category (Microsoft: "Servers, network equipment, and software"; Meta: "Servers and network assets"; Alphabet: "Technical infrastructure" from the FY2024 10-K, "Information technology assets" before, the same category renamed; Amazon: "Equipment") is where GPUs land. Its year-on-year growth in gross value is the hard number closest to compute capex. Buildings and land are the shell, not AI as such.
3. **What the company says** (`ai_spend`): these companies give total-capex guidance "to support AI" (`scope: total`) and, on calls, sometimes a split ("roughly half short-lived assets"). An explicit AI share from the company (`scope: ai`, `explicit_share`) beats any estimate.
4. **Purchase commitments** (`facts.purchase_commitments`) are forward: contracted GPUs and cloud capacity. A jump in commitments precedes capex by a year.

## How to attribute

Capex, in order of hardness:

- `stated_share`: the company states the AI (or GPU/server) share of capex → `ai_amount = share × capex`.
- `stated_amount`: the company states an AI dollar amount for the year (`scope: ai`, `explicit_amount`).
- `ppe_category`: growth in the server/network category: `ai_amount = category gross(t) − category gross(t−1)`, when both years are in `facts`. Name the category. This counts all server growth, not only AI; say so in `basis` and set confidence ≤ 0.6.
- `qualitative`: the company says "primarily AI" but gives nothing to compute from: no amount, confidence ≤ 0.3.
- `none`: nothing links spend to AI.

Opex: AI shows up as depreciation of the fleet and as R&D headcount; no hyperscaler quantifies it. Expect `qualitative` or `none` for opex.

Revenue, in order of hardness:

- `stated_amount`: the company states an AI revenue figure for the year (Microsoft has stated an AI business run-rate on calls). A run-rate is not a fiscal-year figure; confidence ≤ 0.5 and say so in `basis`.
- `stated_share`: the company states AI's share of revenue, or of a segment's growth. A growth contribution ("AI contributed N points to Azure growth") is not a share of revenue; record it in `basis`, not as a share. Confidence ≤ 0.8 for a true share.
- `segment`: not available. Microsoft Intelligent Cloud is not AI; Google Cloud is not AI; AWS is not AI; Oracle's cloud infrastructure line is not AI. Never sum a cloud segment as the AI line.
- `qualitative`: cloud growth or backlog attributed to AI in words only, confidence ≤ 0.3.
- `none`: the common answer, and the honest one for Meta.
- `whole_business`: never.

## Projects

A project is a named, located, sized capital commitment: a data-center campus with a site and a megawatt or gigawatt figure (Meta's Hyperion and Prometheus, Oracle's Abilene site, Microsoft's Fairwater), a power deal with a named plant or counterparty (Microsoft's Crane Clean Energy Center PPA), a joint venture or third-party financing for a named site, or a multi-year capacity commitment to a neocloud with an amount. Words that name one in releases and MD&A: "campus", "site", "broke ground", "gigawatt", "megawatts", "joint venture", "lease agreement", "commitment", "power purchase agreement". Not a project: a model or product launch (Copilot, Gemini), a new chip generation, a hire, total-capex guidance with no site, a partnership with no amount.

## Traps

- A total-capex figure "to support our AI efforts" is the whole, never the AI part. Never copy it into `ai_amount`.
- Gross PP&E categories are cumulative balances; the flow is the difference between year-ends, and a disposal or reclassification can make it negative (then `none`).
- Opex: AI shows up as depreciation of the fleet and as R&D headcount; no hyperscaler quantifies it. Expect `qualitative` or `none` for opex.
- A cloud segment (Intelligent Cloud, Google Cloud, AWS) is not AI revenue. An AI growth contribution in points is not a share of revenue.
- Oracle's remaining performance obligations are contracted future revenue, not a project and not revenue in the year.
- A capacity deal where the hyperscaler is the customer (Microsoft buying from CoreWeave) is a project for the hyperscaler and revenue for the seller; record who pays.
