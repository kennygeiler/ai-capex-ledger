# Money-flow model: bitcoin miner turned HPC / AI host (miner_to_hpc@v1)

Who: IREN, Applied Digital, Cipher, TeraWulf, Core Scientific. Two businesses share the balance sheet: bitcoin mining (ASICs, cheap power) and HPC or AI hosting (GPU clusters or colocation shells leased to a hyperscaler or neocloud). Only the second is AI spend.

## Where the AI money shows up

1. **Segment capex** (`facts.segment_capex`, ASC 280) is the hard number: the HPC / AI cloud / colocation segment's capital expenditures. Applied Digital's "HPC Hosting Business", IREN's "AI Cloud Services", Core Scientific's "Colocation".
2. **Segment revenue** (`facts.segment_revenue`) for the same segment shows whether the capex is already earning.
3. **What the company says** (`ai_spend`): these companies quantify GPU purchases ("4.2k NVIDIA B200 GPUs, $193 million") and HPC expansion funding in releases and MD&A.
4. **Finance leases** often fund the GPUs (Applied Digital); **purchase commitments** cover contracted GPUs and construction.

## How to attribute, in order of hardness

- `segment`: `ai_amount = segment capex` of the AI/HPC segment(s) for the year. If several segments are AI/HPC (hosting plus cloud), add them and list every fact used.
- `stated_amount`: an explicit AI amount from a filing or release when no segment capex exists for that year.
- `ppe_category`: growth in a GPU/HPC-specific PP&E category, when the note separates it.
- `qualitative` / `none` otherwise.
- Opex: `segment` cost of revenue for the AI segment when `ai_spend` states it ("Cost of revenue - AI Cloud Services"); otherwise `none`.

## Traps

- Mining capex (ASICs, "miners", "mining equipment") is not AI. Never include the mining segment.
- Colocation shells leased to a hyperscaler are AI infrastructure spend by this company even though the GPUs are the tenant's; count the segment capex, say in `basis` that the GPUs are the tenant's.
- A year with a segment total but no AI segment line (before the pivot) is `none`, not zero.
