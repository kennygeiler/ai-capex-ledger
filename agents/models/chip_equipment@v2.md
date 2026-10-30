# Thesis: chip equipment and materials (chip_equipment@v2)

## Thesis

Equipment makers are one step upstream of the chips. They are paid by foundry and memory capex, which is itself pulled by AI demand for leading-edge logic, HBM and advanced packaging. Revenue exposure is the measure that matters, and it is only as good as what the company states, because end-market lines (foundry, memory) are broader than AI. Capex allocation does not matter: their own capex is tool fabs and R&D sites. Project-level investment matters a little (plant and R&D expansions); plans versus reality does not. The signal to watch is the stated AI, HBM or advanced-packaging share of shipments, and behind it the capex guidance of TSMC, Samsung, Micron and SK hynix, which the ledger does not hold.

## Companies

Lam Research (LRCX), Applied Materials (AMAT), KLA (KLAC), Teradyne (TER), Entegris (ENTG), Onto Innovation (ONTO), Advanced Energy (AEIS) and Axcelis (ACLS). Lam, Applied and KLA are the core: they quantify AI-related demand in calls and releases. Teradyne tests the chips and states a compute or AI share when it does. At the edge: Entegris sells materials by wafer volume, Advanced Energy sells power subsystems into tools and into data centers, Axcelis sells implant tools mostly to mature-node and power-chip fabs; their AI exposure is a demand statement, not a line. The foundries and lithography (TSMC, ASML) that pay these companies file no 10-K and are out of the set.

## Where the AI money shows up

1. **Revenue by end market or segment** (`facts.segment_revenue`): "Foundry", "Memory", "DRAM", "Advanced packaging", "Systems". Seller-side signal only.
2. **What the company says** (`ai_spend`): these companies quantify AI's share of their shipments ("AI-related revenue of $X", "advanced packaging and HBM ~N% of systems revenue") in calls and releases.
3. **Capex** (`values.capex`): capacity for tools and R&D fabs. Not AI spend unless the company says a line of capex is for AI-driven demand.

## How to attribute

Capex and opex:

- `stated_amount` / `stated_share` only when the company states an AI part of its own spend (`scope: ai`). Rare.
- Otherwise `none` for capex and opex. Record the AI or HBM share of revenue in `basis` as the seller-side signal, never in `ai_amount`; the revenue field below is where it becomes a row.

Revenue, in order of hardness:

- `stated_share`: the company states AI's, HBM's or advanced packaging's share of systems or total revenue; confidence ≤ 0.8, lower (≤ 0.6) when the statement is about orders or shipments rather than revenue.
- `stated_amount`: the company states AI-related or advanced-packaging revenue for the year; confidence ≤ 0.8.
- `segment`: not allowed. "Foundry", "Memory" and "DRAM" are end markets broader than AI; a DRAM line is not an HBM line. Record them in `basis` only.
- `qualitative`: AI named as the driver of demand with no figure, confidence ≤ 0.3. The common answer for Entegris, Onto, Advanced Energy and Axcelis.
- `none`: no link stated.
- `whole_business`: never.

## Projects

A project is a plant or R&D site expansion with a location and an amount: a new tool factory, a research center, a packaging-development line. Words that name one: "facility", "campus", "expansion", "square feet", "investment of", "center" with a location. Not a project: a tool launch, a customer's fab (the customer's project, not this company's), an order, a hire.

## Traps

- "AI drove N% of our revenue" is a demand statement, not the company's spend. It belongs in `basis` for capex and in the revenue field as `stated_share`.
- Equipment capex cycles follow the foundries, not this company's AI decisions.
- A share of orders or shipments is not a share of revenue; cap the confidence and say which it was.
- A customer's fab announcement (TSMC Arizona, Micron Idaho) is not this company's project.
