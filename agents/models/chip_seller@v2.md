# Thesis: chip seller (chip_seller@v2)

## Thesis

Chip sellers are paid by the buildout. Revenue exposure is the measure that matters: the data-center or AI line of revenue is the hyperscalers' capex arriving. Capex allocation does not matter here, with one exception, Intel, whose capex is fabs and mostly not AI either. Project-level investment matters where a seller builds a fab or commits capital to a customer or partner (Nvidia's investments in OpenAI and Intel, Intel's fabs), and plans versus reality matters only for Intel's capex guidance. The signal to watch is the data-center revenue line and its growth, read against the hyperscalers' capex in the same period.

## Companies

Nvidia (NVDA), AMD (AMD), Broadcom (AVGO), Marvell (MRVL), Astera Labs (ALAB), Credo (CRDO), Intel (INTC), Qualcomm (QCOM), Texas Instruments (TXN), Arm (ARM), Monolithic Power (MPWR), Rambus (RMBS), SiTime (SITM), Synopsys (SNPS) and Cadence (CDNS). Nvidia, AMD, Broadcom and Marvell are the core: they name a data-center or AI revenue line. Astera Labs and Credo are nearly all AI connectivity but report one segment, so revenue exposure comes from what they state. At the edge: Intel is a seller with a buyer's capex (fabs); Qualcomm, Texas Instruments, Monolithic Power, Rambus and SiTime sell into data centers as one end market among several; Arm is royalties; Synopsys and Cadence sell design tools to everyone above and have no AI revenue line of their own. Arm moved to 10-K recently, so earlier years are gaps.

## Where the AI money shows up

1. **Segment or market revenue** (`facts.segment_revenue`): the data-center or AI line. Nvidia "Data Center" (revenue by market), AMD "Data Center" segment, Broadcom "Semiconductor solutions" (AI semiconductor revenue is stated in releases), Marvell "Data center" end market. This is the seller side of the buyers' capex: what hyperscalers paid them.
2. **Their own capex** (`values.capex`) is not AI spend in the ledger's sense. Intel's fabs are the exception that proves it: huge capex, mostly not AI.
3. **What the company says** (`ai_spend`): AI revenue figures and AI-attributed R&D ("investments in AI-related R&D").

## How to attribute

Capex:

- `none` unless the company states an AI amount or share of its own capex (rare: a GPU cluster for internal AI research, Nvidia's "DGX Cloud"). Say in `basis` that a chip seller's capex funds fabs and test, not AI infrastructure.

Opex:

- `stated_share` or `stated_amount` only; otherwise `qualitative` when R&D is said to be AI-driven, else `none`.

Record the seller-side signal in `basis` as before: the data-center segment revenue for the year, cited, so the attribution shows what was received from AI buyers even when nothing is attributed. The revenue field below is where that signal now becomes a row.

Revenue, in order of hardness:

- `stated_share`: the company states AI's share of revenue; confidence ≤ 0.9. Astera Labs and Credo when stated.
- `stated_amount`: the company states AI revenue for the year. Broadcom states "AI semiconductor revenue" in releases; use it rather than the Semiconductor solutions segment, which includes non-AI chips. Confidence ≤ 0.9.
- `segment`: sum of the `segment_revenue` facts that are the data-center line. Nvidia "Data Center" (the market line, not the "Compute & Networking" segment), AMD "Data Center" segment, Marvell "Data center" end market: confidence ≤ 0.8, with `basis` noting that the line includes non-AI servers. Intel "Data Center and AI" is mostly general-purpose Xeon: confidence ≤ 0.5 and say so. Monolithic Power's enterprise data end market when stated: ≤ 0.6.
- `qualitative`: revenue growth attributed to AI in words only (Qualcomm, Texas Instruments, Rambus, SiTime, Arm), confidence ≤ 0.3.
- `none`: Synopsys and Cadence, and any seller with no AI or data-center line; the honest answer for a design-tool vendor whose customers build AI chips.
- `whole_business`: never, even for Astera Labs or Credo; use what they state.

## Projects

A project is a fab, a packaging or test site, or a capital commitment to a named counterparty with an amount: Intel's fabs (Arizona, Ohio) and the government's equity stake, Nvidia's stated investments in OpenAI and Intel, a supercomputer the company builds for itself. Words that name one: "fab", "wafer", "investment of up to", "letter of intent", "equity investment", "capacity", "campus", "gigawatts" when the seller commits to supply or fund them. Not a project: a product launch (a new GPU or accelerator generation), a design win, a supply agreement with no capital from this company, a hire.

## Traps

- Data-center revenue is not this company's AI spend. It is the buyers' spend arriving. Never put it in `ai_amount` for capex; it belongs in the revenue field.
- "Compute & Networking" (Nvidia's segment) includes automotive and professional visualization; the market line "Data Center" is the AI one.
- Broadcom's Semiconductor solutions segment is not AI revenue; the stated AI semiconductor figure is.
- Intel's Data Center and AI segment is a data-center line, not an AI one; cap the confidence.
- A supply commitment from a customer (gigawatts of GPUs to be delivered) is the customer's project; for the seller it is backlog, not spend.
