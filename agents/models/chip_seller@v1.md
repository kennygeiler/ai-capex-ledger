# Money-flow model: chip seller (chip_seller@v1)

Who: Nvidia, AMD, Broadcom, Marvell, Astera Labs, Credo, Intel, Qualcomm, Texas Instruments. They are paid by the AI buildout; their own capex is fabs, test and R&D equipment, not AI infrastructure.

## Where the AI money shows up

1. **Segment or market revenue** (`facts.segment_revenue`): the data-center or AI line. Nvidia "Data Center" (revenue by market), AMD "Data Center" segment, Broadcom "Semiconductor solutions" (AI semiconductor revenue is stated in releases), Marvell "Data center" end market. This is the seller side of the buyers' capex: what hyperscalers paid them.
2. **Their own capex** (`values.capex`) is not AI spend in the ledger's sense. Intel's fabs are the exception that proves it: huge capex, mostly not AI.
3. **What the company says** (`ai_spend`): AI revenue figures and AI-attributed R&D ("investments in AI-related R&D").

## How to attribute

- For `capex`: `none` unless the company states an AI amount or share of its own capex (rare: a GPU cluster for internal AI research, Nvidia's "DGX Cloud"). Say in `basis` that a chip seller's capex funds fabs and test, not AI infrastructure.
- For `opex`: `stated_share` or `stated_amount` only; otherwise `qualitative` when R&D is said to be AI-driven, else `none`.
- Record the seller-side signal separately in `basis`: the data-center segment revenue for the year, cited, so the attribution shows what was received from AI buyers even when nothing is attributed.

## Traps

- Data-center revenue is not this company's AI spend. It is the buyers' spend arriving. Never put it in `ai_amount`.
- "Compute & Networking" (Nvidia's segment) includes automotive and professional visualization; the market line "Data Center" is the AI one.
