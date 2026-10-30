# The 100 companies, by layer of the AI supply chain

Added 29 Oct 2026 to take the ledger from 31 to 100 companies and see the pipeline work at scale. Each company sits in
one layer; the layer picks the money-flow model the attributor reads (`ledger/config.py` `INDUSTRIES`,
`agents/models/<layer>@vN.md`). A company that fits no layer gets `other`, which attributes only what the company
states. Tickers in `data/companies.json` (group "Scale to 100", with `layer`).

| Layer | Model | Who | Where AI spend shows up for this layer |
|---|---|---|---|
| Hyperscalers | `hyperscaler` | MSFT GOOGL AMZN META ORCL | their own capex: server category, stated shares, finance leases |
| Neoclouds | `neocloud` | CRWV NBIS | nearly all capex is GPUs and the shells around them |
| Miners turned HPC | `miner_to_hpc` | IREN APLD CIFR WULF CORZ HUT RIOT MARA CLSK BTBT SLNH GLXY BTDR | segment capex of the HPC / AI segment; mining is not AI |
| Chip design and IP | `chip_seller` | NVDA AMD AVGO MRVL ALAB CRDO INTC QCOM TXN ARM MPWR RMBS SITM SNPS CDNS | sellers; AI revenue is the signal, own capex rarely AI (Intel's fabs are the exception) |
| Chip equipment and materials | `chip_equipment` | LRCX AMAT KLAC TER ENTG ONTO AEIS ACLS | one step upstream; paid by foundry and memory capex; own capex not AI |
| Memory, storage, networking, optics, servers | `component_supplier` | MU ANET CSCO WDC STX SNDK SMCI DELL HPE NTAP CIEN COHR LITE AAOI FN JBL FLEX CLS PENG | sellers; Micron's HBM capex is the one supplier capex that is partly AI |
| Data-center build | `datacenter_build` | VRT ETN NVT MOD JCI PWR FIX EME GEV POWL BE | power, cooling, switchgear, turbines, construction; data-center revenue and backlog, own capex rarely AI |
| Data-center landlords | `datacenter_landlord` | EQIX DLR IRM | development capex is data-center capacity, which is broader than AI |
| Power producers | `power` | VST CEG NRG TLN | growth capex tied to a named data-center project or PPA |
| AI software and data platforms | `ai_software` | CRM NOW ADBE SNOW PLTR DDOG | cloud purchase commitments (committed, not spent) and hosting cost of revenue |
| Adopters, physical AI, commodities | `other` | AAPL TSLA IBM WMT XOM JPM COMP SPCX UBER SYM VZ T TMUS FCX | only what the company states (Tesla's AI capex); copper (FCX) and warehouse robots (SYM) as the physical end |

## What the set cannot hold

The pipeline reads 10-K filings. The foundries, lithography and Korean memory makers that investors put at the base
of the chain (TSMC, ASML, SK hynix, Samsung) file 20-F or nothing with the SEC, so they are out until the pipeline
reads 20-Fs (an open failure type, see `docs/INGESTION.md`). Nebius (NBIS), Bitdeer (BTDR), Arm (ARM) and Celestica
(CLS) moved to 10-K recently; their earlier years come from 20-F or 40-F and will show as gaps.

## How the layers were chosen

Investor maps of the AI value chain (OECD's competition report on AI infrastructure, VanEck's value-chain note,
Fidelity's infrastructure supply-chain note) agree on four tiers: compute (design, manufacturing, memory), data
centers (hyperscalers, real estate, cooling, grid), power, and application. The layers above split those tiers where
the money flows differently enough to need a different model: a chip designer and a chip-tool maker are both sellers,
but the tool maker is paid by foundry capex, not by the hyperscalers; a landlord and a power producer both build
physical capacity, but one's capex is the data center and the other's is contracted generation.
