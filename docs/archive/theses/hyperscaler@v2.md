# Money-flow model: hyperscaler (hyperscaler@v2)

Who: Microsoft, Alphabet, Amazon, Meta, Oracle. They buy the AI buildout: GPUs and servers, networking, datacenter shells and power.

## Where the AI money shows up

1. **Capex** (`values.capex`, cash paid for property and equipment) is the main line, but it understates the buildout: finance leases (`facts.finance_lease_liability`, growing fast at Microsoft and Meta) and third-party-funded datacenters (Meta's Hyperion joint venture) sit outside it.
2. **PP&E by category** (`facts.ppe_category`): the "servers and network equipment" category (Microsoft: "Servers, network equipment, and software"; Meta: "Servers and network assets"; Alphabet: "Technical infrastructure" from the FY2024 10-K, "Information technology assets" before, the same category renamed; Amazon: "Equipment") is where GPUs land. Its year-on-year growth in gross value is the hard number closest to compute capex. Buildings and land are the shell, not AI as such.
3. **What the company says** (`ai_spend`): these companies give total-capex guidance "to support AI" (`scope: total`) and, on calls, sometimes a split ("roughly half short-lived assets"). An explicit AI share from the company (`scope: ai`, `explicit_share`) beats any estimate.
4. **Purchase commitments** (`facts.purchase_commitments`) are forward: contracted GPUs and cloud capacity. A jump in commitments precedes capex by a year.

## How to attribute, in order of hardness

- `stated_share`: the company states the AI (or GPU/server) share of capex → `ai_amount = share × capex`.
- `stated_amount`: the company states an AI dollar amount for the year (`scope: ai`, `explicit_amount`).
- `ppe_category`: growth in the server/network category: `ai_amount = category gross(t) − category gross(t−1)`, when both years are in `facts`. Name the category. This counts all server growth, not only AI; say so in `basis` and set confidence ≤ 0.6.
- `qualitative`: the company says "primarily AI" but gives nothing to compute from: no amount, confidence ≤ 0.3.
- `none`: nothing links spend to AI.

## Traps

- A total-capex figure "to support our AI efforts" is the whole, never the AI part. Never copy it into `ai_amount`.
- Gross PP&E categories are cumulative balances; the flow is the difference between year-ends, and a disposal or reclassification can make it negative (then `none`).
- Opex: AI shows up as depreciation of the fleet and as R&D headcount; no hyperscaler quantifies it. Expect `qualitative` or `none` for opex.
