# Thesis: neocloud (neocloud@v2)

## Thesis

A neocloud is the pure play. The whole business is renting AI compute, so the whole capex is AI capex and the whole revenue is AI revenue. All four measures matter and all four are easy to read: capex allocation and revenue exposure are the whole business; projects are the GPU clusters, sites and customer contracts that the capex serves; plans versus reality is capex guidance against the actual, which moves with GPU deliveries and financing. The signal to watch is the gap between contracted backlog (customer commitments, purchase commitments for GPUs) and the capex the company can finance, because the balance sheet, not demand, is the constraint.

## Companies

CoreWeave (CRWV) and Nebius (NBIS). CoreWeave is the model: a single-segment AI cloud financed by GPU-backed debt and finance leases. Nebius sits at the edge: its AI infrastructure business is the bulk of the company, but it has carried other businesses (education, data labelling, autonomous driving) and filed 20-F before moving to 10-K, so earlier years are gaps and whole-business attribution needs a lower ceiling. Miners that host GPUs (IREN, Applied Digital) look like neoclouds but keep a mining segment; they sit in `miner_to_hpc`.

## Where the AI money shows up

1. **Capex** (`values.capex`) is almost entirely GPUs, servers, networking and datacenter fit-out. The PP&E note's "data center equipment" category is the same thing.
2. **Finance leases** (`facts.finance_lease_liability`) and GPU-backed debt carry part of the buildout outside cash capex.
3. **Purchase commitments** (`facts.purchase_commitments`): contracted GPU deliveries and datacenter capacity.
4. **Revenue and backlog** (`values.revenue`, `ai_spend`): all revenue is AI compute; contracted backlog with named customers is the forward number.

## How to attribute

Capex:

- `stated_amount` or `stated_share` when the company gives one; otherwise:
- `whole_business`: `ai_amount = capex`, confidence 0.9, `basis` "a single-segment AI cloud: all capex is AI infrastructure". Cite `values.capex` for the year. For Nebius, confidence ≤ 0.7 while non-infrastructure businesses sit in consolidated capex, or `segment` when the company reports an AI infrastructure segment's capex.

Opex: cost of revenue is running the fleet (power, depreciation, datacenter leases); `whole_business` with confidence 0.7 for opex is defensible; say so.

Revenue, in order of hardness:

- `stated_share` / `stated_amount`: rarely needed; the company does not split what is all one thing. Confidence ≤ 0.9 when given.
- `segment`: Nebius, when it reports an AI infrastructure (or "core") segment's revenue separately from its other businesses; confidence ≤ 0.8.
- `whole_business`: CoreWeave, `ai_amount = revenue`, confidence 0.9, `basis` "a single-segment AI cloud: all revenue is AI compute". This is the one layer where `whole_business` is the normal revenue method.
- `qualitative` / `none`: only for a year before the business was an AI cloud.

## Projects

A project is a GPU cluster or site with a size and a counterparty: a data-center lease or build with megawatts and a location, a GPU delivery contract with a count or an amount, a customer contract with a named customer and amount (CoreWeave's contracts with Microsoft, OpenAI and Meta), and a financing facility tied to a named site or GPU batch. Words that name one: "megawatts", "contracted power", "site", "cluster", "delivery", "master services agreement", "delayed draw term loan" when tied to a site, "backlog". Not a project: general availability of a new GPU type, a software feature, a hire, an equity raise with no use named.

## Traps

- Do not add finance leases to capex in `ai_amount`; report capex and mention leases in `basis`.
- A share of revenue from one customer (Microsoft) is a concentration fact, not an attribution input.
- Backlog is contracted future revenue, not revenue in the year; it belongs in `basis` and in a project row, never in `ai_amount`.
- Nebius before its 10-K years is a gap, not a zero.
