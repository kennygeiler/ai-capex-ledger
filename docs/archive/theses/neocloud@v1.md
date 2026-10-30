# Money-flow model: neocloud (neocloud@v1)

Who: CoreWeave. The whole business is renting AI compute, so the whole capex is AI capex, financed largely by debt secured on the GPUs and by finance leases.

## Where the AI money shows up

1. **Capex** (`values.capex`) is almost entirely GPUs, servers, networking and datacenter fit-out. The PP&E note's "data center equipment" category is the same thing.
2. **Finance leases** (`facts.finance_lease_liability`) and GPU-backed debt carry part of the buildout outside cash capex.
3. **Purchase commitments** (`facts.purchase_commitments`): contracted GPU deliveries and datacenter capacity.

## How to attribute

- `stated_amount` or `stated_share` when the company gives one; otherwise:
- `whole_business`: `ai_amount = capex`, confidence 0.9, `basis` "a single-segment AI cloud: all capex is AI infrastructure". Cite `values.capex` for the year.
- Opex: cost of revenue is running the fleet (power, depreciation, datacenter leases); `whole_business` with confidence 0.7 for opex is defensible; say so.

## Traps

- Do not add finance leases to capex in `ai_amount`; report capex and mention leases in `basis`.
- A share of revenue from one customer (Microsoft) is a concentration fact, not an attribution input.
