# Thesis: neocloud (neocloud@v3)

## Thesis

A neocloud is the pure play. The whole business is renting AI compute, so the whole capex is AI capex and the whole revenue is AI revenue. All four measures matter and all four are easy to read: capex allocation and revenue exposure are the whole business; projects are the GPU clusters, sites and customer contracts that the capex serves; plans versus reality is capex guidance against the actual, which moves with GPU deliveries and financing. The signal to watch is the gap between contracted backlog (customer commitments, purchase commitments for GPUs) and the capex the company can finance, because the balance sheet, not demand, is the constraint. The scale as of 2026: CoreWeave guides 2026 capex at $35 to $39 billion against a $104 billion backlog; Nebius guides $20 to $25 billion against more than $40 billion of customer commitments. Synergy Research puts the whole neocloud market above $25 billion of revenue in 2025, growing over 200% a year.

## Companies

CoreWeave (CRWV). The model neocloud and the reason the layer exists.
- Segment: none. The 10-Q for June 30 2026 says "The Company operates its business in one operating segment and, therefore, has one reportable segment." The FY2025 10-K reports the same single business.
- Revenue: $5,131 million in 2025, up from $1,915 million in 2024 (FY2025 release, Feb 26 2026). Q2 2026 revenue $2,575 million (Q2 2026 release, Aug 11 2026). All of it is AI cloud compute.
- Capex: "Purchase of property and equipment, including capitalized internal-use software" $10,309 million in 2025 (FY2025 release); the 10-K states cash paid for property and equipment of $10.3 billion in 2025 and $8.7 billion in 2024. Six months to June 30 2026: $14,117 million (10-Q). 2026 capex guidance $35 to $39 billion, given on the Q2 2026 call, not in the release (MarketBeat call highlights, Aug 11 2026).
- Stated AI share of capex or revenue: none stated, and none needed; the filings describe one business, AI cloud. Not disclosed as a share as of 2026-10-29 (FY2025 10-K, Q2 2026 10-Q checked).
- Backlog: revenue backlog $66.8 billion at Dec 31 2025 and about $104 billion at June 30 2026; defined as "remaining performance obligations, plus other amounts we estimate will be recognized as revenue in future periods" under committed contracts. RPO $60.7 billion at Dec 31 2025 (up 302% from $15.1 billion) and $103.7 billion at June 30 2026.
- Customers: Microsoft was "approximately 67% of our revenue" in 2025 (10-K); the top two customers were about 77% in 2024. In Q2 2026 Customer A was 36%, Customer B 26%, Customer C 10% of revenue (10-Q). OpenAI "has committed to pay us up to approximately $11.9 billion through October 2030" plus "up to approximately $6.5 billion through May 31, 2031"; Meta "initially committed to pay us up to approximately $14.2 billion through December 2031" (10-K).
- Financing: total indebtedness $21.6 billion at Dec 31 2025; DDTL 1.0 up to $2.3 billion, DDTL 2.0 up to $7.6 billion, DDTL 2.1 up to $3.0 billion, DDTL 3.0 up to $2.6 billion; $2.0 billion 2030 notes, $1.75 billion 2031 notes, $2.6 billion 1.75% convertible notes due 2031 (10-K). At June 30 2026: recourse debt $31,405 million, non-recourse debt $3,663 million, finance lease liabilities $221 million (Q2 2026 release and 10-Q). Operating lease liabilities $8.2 billion at Dec 31 2025.
- Power: over 850 MW active and about 3.1 GW contracted at Dec 31 2025; 1.5 GW active and about 3.7 GW contracted at June 30 2026; 43 data centers at year end 2025. All GPUs are NVIDIA GPUs (10-K).

Nebius Group (NBIS). The second pure play, at the edge of the layer because of its other businesses and its filing form.
- Segments: three, named "Nebius", "Avride" and "TripleTen" in the FY2025 annual report. Segment revenue 2025 (2024): Nebius $480.3 million ($68.3 million), Avride $1.3 million ($0.3 million), TripleTen $54.1 million ($28.8 million); total revenue $529.8 million ($91.5 million). The Nebius segment is the AI cloud. Toloka was deconsolidated in May 2025; ClickHouse and Toloka are equity stakes. In 2026 letters the company reports "Nebius AI cloud" against "Other businesses".
- AI share: the Nebius segment was 91% of 2025 revenue (computed from the segment table above). Q1 2026: Nebius AI revenue $390 million of $399 million group revenue, "98% of group revenue" (Q1 2026 call). Q2 2026: $574.9 million of $582.3 million, about 98% (Q2 2026 letter). ARR $3.0 billion at end of June 2026.
- Capex: purchases of property and equipment $4,066.0 million in 2025 and $807.5 million in 2024 (FY2025 20-F). Q2 2026 capex about $5.7 billion, "mostly for GPUs, GPU-related hardware, and data center expansion." 2026 capex guidance raised to $20 to $25 billion from $16 to $20 billion (Q1 2026 call, May 13 2026) and held in Q2.
- Contracts: Microsoft, signed Sept 8 2025, "total contract value is about $17.4 billion through 2031," up to about $19.4 billion with optional capacity, served from Vineland, New Jersey (6-K). Meta, Nov 2025, "approximately $3 billion, with a five-year term" (Q3 2025 letter). Meta, signed March 13 2026, "up to approximately $27 billion": $12 billion of dedicated GPU clusters from early 2027 plus an unsold-capacity order of up to $15 billion (6-K). Customer commitments "more than $40 billion" at Q2 2026; customer prepayments expected above $9 billion in 2026.
- Customer concentration: no percentages disclosed as of 2026-10-29 (FY2025 20-F and Q2 2026 letter checked).
- Power: about 170 MW active at Dec 31 2025; more than 2 GW contracted by Feb 2026; 5 GW contracted expected by end of 2026.
- Filing form: Nebius filed a Form 20-F for FY2025 and says it expects to keep foreign private issuer status, so the 10-K pipeline holds no annual report for it yet; its years are gaps until a 10-K exists.

Miners that host GPUs (IREN, Applied Digital, Core Scientific, which Synergy lists among neoclouds) look like neoclouds but keep a mining segment; they sit in `miner_to_hpc`.

## Where the AI money shows up

1. **Capex** (`values.capex`) is almost entirely GPUs, servers, networking and datacenter fit-out. CoreWeave's 10-K says capital investments "consist primarily of servers and network equipment for computing, storage, and networking requirements." Nebius says Q2 2026 capex was "mostly for GPUs, GPU-related hardware, and data center expansion."
2. **Finance leases** (`facts.finance_lease_liability`) and GPU-backed debt carry part of the buildout outside cash capex. At CoreWeave the finance leases are small ($221 million at June 30 2026); the DDTL facilities and non-recourse debt ($3.7 billion) are the GPU-backed part, and operating leases ($8.2 billion of liabilities) carry the shells.
3. **Purchase commitments** (`facts.purchase_commitments`): contracted GPU deliveries and datacenter capacity. CoreWeave's 10-K refers to lease commitments not yet commenced and enforceable purchase commitments (Note 9); amounts were not in the fetched text as of 2026-10-29.
4. **Revenue and backlog** (`values.revenue`, `ai_spend`): all revenue is AI compute; contracted backlog with named customers is the forward number. CoreWeave: RPO and revenue backlog. Nebius: customer commitments and ARR.
5. **Customer prepayments** (deferred revenue): CoreWeave's deferred revenue was $9.7 billion at June 30 2026; Nebius expects over $9 billion of prepayments in 2026. Prepayments fund capex before revenue arrives.

## How to attribute

Capex:

- `stated_amount` or `stated_share` when the company gives one. Neither company has given an AI share of capex as of 2026-10-29, because the whole of it is AI. Otherwise:
- `whole_business`: `ai_amount = capex`, confidence 0.9, `basis` "a single-segment AI cloud: all capex is AI infrastructure". Cite `values.capex` for the year. CoreWeave: cite the one-segment statement. Nebius: confidence ≤ 0.7 while Avride and TripleTen sit in consolidated capex (they were 9% of 2025 revenue), or `segment` when the company reports the Nebius segment's capex. The FY2025 20-F gives segment revenue, not segment capex; check the segment note of each later filing.

Opex: cost of revenue is running the fleet (power, depreciation, datacenter leases); `whole_business` with confidence 0.7 for opex is defensible; say so. CoreWeave's cost of revenue rose 181% year on year in Q2 2026 (10-Q), tracking the fleet.

Revenue, in order of hardness:

- `stated_share` / `stated_amount`: rarely needed; the company does not split what is all one thing. Nebius does state the AI cloud share ("98% of group revenue" in Q1 and Q2 2026); use it with confidence ≤ 0.9.
- `segment`: Nebius, the "Nebius" segment's revenue ($480.3 million in 2025) separately from Avride and TripleTen; confidence ≤ 0.8.
- `whole_business`: CoreWeave, `ai_amount = revenue`, confidence 0.9, `basis` "a single-segment AI cloud: all revenue is AI compute". This is the one layer where `whole_business` is the normal revenue method.
- `qualitative` / `none`: only for a year before the business was an AI cloud (Nebius before the 2024 split from Yandex, CoreWeave's mining years).

## Projects

A project is a GPU cluster or site with a size and a counterparty: a data-center lease or build with megawatts and a location (Nebius's Vineland, New Jersey site for Microsoft; its 1.2 GW owned Pennsylvania site), a GPU delivery contract with a count or an amount, a customer contract with a named customer and amount (CoreWeave's contracts with Microsoft, OpenAI up to $11.9 billion plus $6.5 billion, and Meta up to $14.2 billion; Nebius's Microsoft $17.4 billion and Meta $3 billion and $27 billion contracts), and a financing facility tied to a named site or GPU batch (CoreWeave's DDTL facilities; Nebius's $775 million secured facility backed by deployed GPUs). Words that name one: "megawatts", "contracted power", "site", "cluster", "delivery", "master services agreement", "infrastructure service agreement", "order", "tranche", "delayed draw term loan" when tied to a site, "backlog", "customer commitments". Not a project: general availability of a new GPU type, a software feature, a hire, an equity raise with no use named.

## Traps

- Do not add finance leases or debt to capex in `ai_amount`; report capex and mention leases and GPU-backed debt in `basis`.
- CoreWeave quotes capex on calls and in guidance on a basis that can differ from the cash-flow line; the FY2025 release's cash-flow line is $10,309 million while 2026 guidance is $35 to $39 billion. Use the filing's cash-flow figure for `values.capex` and record the guidance in `ai_spend` as planned, not spent.
- A share of revenue from one customer (Microsoft at 67% of CoreWeave's 2025 revenue) is a concentration fact, not an attribution input.
- Backlog is contracted future revenue, not revenue in the year; it belongs in `basis` and in a project row, never in `ai_amount`. Revenue backlog ($104 billion) is wider than RPO ($103.7 billion); say which.
- A customer prepayment (deferred revenue) is cash, not revenue; it fills the financing gap and belongs in `basis`.
- Nebius's $27 billion Meta contract is $12 billion firm plus $15 billion of unsold-capacity obligation; record the firm part as the project amount and the option in `basis`.
- Nebius files 20-F, not 10-K, as of its FY2025 annual report; its years are a gap in this pipeline, not a zero.

## Sources

- CoreWeave operates one segment; cash paid for PP&E $10.3bn 2025 vs $8.7bn 2024; RPO $60.7bn; Microsoft 67% of 2025 revenue; OpenAI up to $11.9bn and $6.5bn, Meta up to $14.2bn; total indebtedness $21.6bn; DDTL facilities; 850 MW active, 3.1 GW contracted. CoreWeave FY2025 Form 10-K, filed March 2026. https://www.sec.gov/Archives/edgar/data/1769628/000176962826000104/crwv-20251231.htm
- "One operating segment and, therefore, one reportable segment"; PP&E purchases $14,117m six months to June 30 2026; finance lease liabilities $221m; Customer A 36%, B 26%, C 10% in Q2 2026; RPO $103.7bn; deferred revenue $9.7bn. CoreWeave Form 10-Q for June 30 2026. https://www.sec.gov/Archives/edgar/data/0001769628/000176962826000366/crwv-20260630.htm
- FY2025 revenue $5,131m; capex $10,309m; revenue backlog $66.8bn and its definition; 2026 guidance deferred to the call. CoreWeave release, Feb 26 2026. https://investors.coreweave.com/news/news-details/2026/CoreWeave-Reports-Strong-Fourth-Quarter-and-Fiscal-Year-2025-Results/default.aspx
- Q2 2026 revenue $2,575m; capex $6,422m; backlog about $104bn; 1.5 GW active, 3.7 GW contracted; recourse and non-recourse debt; $3.1bn HPC-backed term loan. CoreWeave release, Aug 11 2026. https://investors.coreweave.com/news/news-details/2026/CoreWeave-Reports-Strong-Second-Quarter-2026-Results/default.aspx
- 2026 capex guidance $35bn to $39bn; revenue guidance $12.4bn to $13.2bn; year-end active power above 1.85 GW. MarketBeat Q2 2026 call highlights, Aug 11 2026. https://www.marketbeat.com/instant-alerts/coreweave-q2-earnings-call-highlights-2026-08-11/
- Segments Nebius, Avride, TripleTen with 2025 and 2024 revenue; PP&E purchases $4,066.0m 2025 vs $807.5m 2024; 170 MW active at Dec 31 2025, more than 2 GW contracted by Feb 2026; expects to remain a foreign private issuer. Nebius Group FY2025 Form 20-F, 2026. https://www.sec.gov/Archives/edgar/data/0001513845/000110465926052948/nbis-20251231x20f.htm
- Microsoft agreement Sept 8 2025, about $17.4bn through 2031, up to $19.4bn, Vineland NJ, five-year term. Nebius Form 6-K, Sept 2025. https://www.sec.gov/Archives/edgar/data/1513845/000110465925088312/tm2525580d1_6k.htm
- Meta agreement March 13 2026, up to about $27bn: $12bn dedicated clusters from early 2027, up to $15bn unsold-capacity order, five-year orders. Nebius Form 6-K, March 16 2026. https://www.sec.gov/Archives/edgar/data/1513845/000110465926027886/tm268879d1_6k.htm
- Meta agreement about $3bn, five years; Q3 2025 revenue $146.1m; capex $955.5m; over 2.5 GW contracted expected by end 2026. Nebius Q3 2025 shareholder letter, Nov 11 2025. https://www.sec.gov/Archives/edgar/data/1513845/000110465925109806/tm2530882d1_ex99-2.htm
- Q1 2026 group revenue $399m, Nebius AI $390m (98%); 2026 capex guidance raised to $20bn to $25bn; Meta $27bn deal; over 3.5 GW contracted. Nebius Q1 2026 call transcript, Motley Fool, May 13 2026. https://www.fool.com/earnings/call-transcripts/2026/05/13/nebius-nbis-q1-2026-earnings-transcript/
- Q2 2026 group revenue $582.3m, AI cloud $574.9m; capex about $5.7bn; ARR $3.0bn; customer commitments above $40bn; 5 GW contracted expected by end 2026; $775m GPU-backed facility. Nebius Q2 2026 shareholder letter, Aug 12 2026. https://www.sec.gov/Archives/edgar/data/0001513845/000110465926094568/tm2622968d1_ex99-2.htm
- Neocloud revenue passed $5bn in Q2 2025, up 205%; on track for over $23bn in 2025; almost $180bn by 2030; leaders CoreWeave, Crusoe, Lambda, Nebius. Synergy Research Group, Oct 13 2025. https://www.srgresearch.com/articles/neoclouds-currently-growing-by-over-200-per-year-will-reach-180-billion-in-revenues-by-2030
- Neocloud revenue $9bn in Q4 2025, up 223%, above $25bn for 2025; approaching $400bn by 2031 at 58% CAGR; leaders include CoreWeave, Crusoe, Core Scientific, Lambda, Nebius, Nscale. SDxCentral citing Synergy Research, April 7 2026. https://www.sdxcentral.com/news/neocloud-revenue-exceeds-25b-in-2025/
