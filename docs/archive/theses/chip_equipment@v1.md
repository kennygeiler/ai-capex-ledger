# Money-flow model: chip equipment and materials (chip_equipment@v1)

Who: Lam Research, Applied Materials, KLA, Teradyne, Entegris, Onto, Advanced Energy, Axcelis. One step upstream of the chip sellers: paid by foundry and memory capex (TSMC, Samsung, Micron, SK hynix), which is itself driven by AI demand for leading-edge logic, HBM and advanced packaging. Their own capex is fabs-for-tools and R&D sites, not AI.

## Where the AI money shows up

1. **Revenue by end market or segment** (`facts.segment_revenue`): "Foundry", "Memory", "DRAM", "Advanced packaging", "Systems". Seller-side signal only.
2. **What the company says** (`ai_spend`): these companies quantify AI's share of their shipments ("AI-related revenue of $X", "advanced packaging and HBM ~N% of systems revenue") in calls and releases.
3. **Capex** (`values.capex`): capacity for tools and R&D fabs. Not AI spend unless the company says a line of capex is for AI-driven demand.

## How to attribute

- `stated_amount` / `stated_share` only when the company states an AI part of *its own* spend (`scope: ai`). Rare.
- Otherwise `none` for capex and opex. Record the AI or HBM share of revenue in `basis` as the seller-side signal, never in `ai_amount`.

## Traps

- "AI drove N% of our revenue" is a demand statement, not the company's spend. It belongs in `basis`.
- Equipment capex cycles follow the foundries, not this company's AI decisions.
