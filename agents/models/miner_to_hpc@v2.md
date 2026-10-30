# Thesis: bitcoin miner turned HPC / AI host (miner_to_hpc@v2)

## Thesis

These companies own cheap power and sites, and they are turning them from bitcoin mining into GPU hosting or AI cloud. Two businesses share one balance sheet, and only the HPC or AI segment is AI spend. Capex allocation (segment capex), revenue exposure (segment revenue) and project-level investment (a named campus converted under a lease with a hyperscaler or neocloud) all matter; plans versus reality matters because HPC capex guidance is large relative to the company and often slips. The signal to watch is the HPC segment's capex against its revenue, year by year: it shows whether the conversion is earning yet, and the mining segment is noise.

## Companies

IREN (IREN), Applied Digital (APLD), Cipher Mining (CIFR), TeraWulf (WULF), Core Scientific (CORZ), Hut 8 (HUT), Riot Platforms (RIOT), MARA (MARA), CleanSpark (CLSK), Bit Digital (BTBT), Soluna (SLNH), Galaxy Digital (GLXY) and Bitdeer (BTDR). Applied Digital, IREN, Core Scientific, TeraWulf and Cipher have signed HPC leases or run AI clouds and report the segment. At the edge: Riot, MARA and CleanSpark are still mostly miners and may show no AI segment, which is `none`, not zero; Galaxy is a crypto financial firm whose data-center business (Helios) is one line of several; Bitdeer and Bit Digital moved to 10-K recently, so earlier years are gaps.

## Where the AI money shows up

1. **Segment capex** (`facts.segment_capex`, ASC 280) is the hard number: the HPC / AI cloud / colocation segment's capital expenditures. Applied Digital's "HPC Hosting Business", IREN's "AI Cloud Services", Core Scientific's "Colocation".
2. **Segment revenue** (`facts.segment_revenue`) for the same segment shows whether the capex is already earning.
3. **What the company says** (`ai_spend`): these companies quantify GPU purchases ("4.2k NVIDIA B200 GPUs, $193 million") and HPC expansion funding in releases and MD&A.
4. **Finance leases** often fund the GPUs (Applied Digital); **purchase commitments** cover contracted GPUs and construction.

## How to attribute

Capex, in order of hardness:

- `segment`: `ai_amount = segment capex` of the AI/HPC segment(s) for the year. If several segments are AI/HPC (hosting plus cloud), add them and list every fact used.
- `stated_amount`: an explicit AI amount from a filing or release when no segment capex exists for that year.
- `ppe_category`: growth in a GPU/HPC-specific PP&E category, when the note separates it.
- `qualitative` / `none` otherwise.

Opex: `segment` cost of revenue for the AI segment when `ai_spend` states it ("Cost of revenue - AI Cloud Services"); otherwise `none`.

Revenue, in order of hardness:

- `stated_amount` / `stated_share`: when the company states HPC or AI revenue for the year; confidence ≤ 0.9.
- `segment`: sum of the `segment_revenue` facts for the HPC / AI segment(s): Applied Digital "HPC Hosting Business" (and its cloud segment when reported), IREN "AI Cloud Services", Core Scientific "Colocation" (its HPC hosting line), TeraWulf, Cipher and Hut 8 when stated. Name every segment used. Confidence ≤ 0.8. Colocation revenue from a hyperscaler or neocloud tenant counts: the lease is AI hosting even though the GPUs are the tenant's.
- `qualitative`: the company links revenue growth to HPC in words only, confidence ≤ 0.3.
- `none`: a year with only mining revenue, or with a segment total and no HPC line.
- `whole_business`: never; the mining segment is always there.

## Projects

A project is a named site converted or built for HPC with a counterparty, megawatts or an amount: a campus lease with a hyperscaler or neocloud (Applied Digital's Ellendale campus leased to CoreWeave, Core Scientific's sites contracted to CoreWeave, TeraWulf's Lake Mariner, Cipher's and IREN's Texas sites when stated), a GPU purchase with a count and amount, a financing tied to a site. Words that name one: "campus", "lease", "critical IT load", "megawatts", "gigawatt", "hosting agreement", "GPUs", "energized", "phase". Not a project: a hashrate target, an ASIC purchase, a mining site expansion, a new power contract with no HPC use, a hire.

## Traps

- Mining capex (ASICs, "miners", "mining equipment") is not AI. Never include the mining segment.
- Colocation shells leased to a hyperscaler are AI infrastructure spend by this company even though the GPUs are the tenant's; count the segment capex, say in `basis` that the GPUs are the tenant's.
- A year with a segment total but no AI segment line (before the pivot) is `none`, not zero.
- A lease's total contract value ("$7 billion over 15 years") is a project amount, not revenue in the year.
- Bitcoin price lifts mining revenue and total revenue together; only the HPC segment is attributable.
