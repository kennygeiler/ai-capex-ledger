# Money-flow model: memory and networking supplier (component_supplier@v1)

Who: Micron (HBM and DRAM), Arista (datacenter switching), Cisco (networking). Paid by the AI buildout, like chip sellers, with one difference: Micron's own capex is partly AI-driven (HBM fabs and packaging) and the company says so.

## Where the AI money shows up

1. **Segment or market revenue** (`facts.segment_revenue`): Micron "Compute and Networking" / "Cloud Memory"; Arista "Product"; Cisco "Networking". Seller side of the buildout.
2. **Capex** (`values.capex`): Micron's fab and HBM capacity is the one supplier capex that is AI-driven in part; Micron states the share of capex going to HBM/AI capacity in some releases.
3. **What the company says** (`ai_spend`).

## How to attribute

- Micron: `stated_share` or `stated_amount` when the company gives the HBM/AI share of capex; otherwise `qualitative` with confidence ≤ 0.4 ("capex driven by HBM and AI demand").
- Arista, Cisco: `none` for capex (their capex is small and not AI); `qualitative` or `none` for opex.
- As with chip sellers, record data-center or AI revenue in `basis` as the seller-side signal, never in `ai_amount`.

## Traps

- A memory upcycle lifts total revenue; only the AI/HBM part is attributable, and only when stated.
