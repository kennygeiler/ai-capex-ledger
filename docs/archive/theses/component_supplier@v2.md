# Thesis: memory, storage, networking, optics and servers (component_supplier@v2)

## Thesis

These companies sell the parts and boxes around the GPU: memory, drives, switches, optics, servers and the contract manufacturing that assembles them. They are paid by the buildout, so revenue exposure is the measure that matters. Capex allocation matters for one company, Micron, whose fab and HBM capacity is the one supplier capex that is partly AI and said to be. Project-level investment matters for the fab builders (Micron) and the factory builders (Supermicro, Dell, the contract manufacturers); plans versus reality matters for Micron's capex guidance. The signal to watch is the data-center or AI line of revenue where the company names one, and the HBM share of Micron's capex.

## Companies

Micron (MU), Arista (ANET), Cisco (CSCO), Western Digital (WDC), Seagate (STX), Sandisk (SNDK), Super Micro Computer (SMCI), Dell (DELL), Hewlett Packard Enterprise (HPE), NetApp (NTAP), Ciena (CIEN), Coherent (COHR), Lumentum (LITE), Applied Optoelectronics (AAOI), Fabrinet (FN), Jabil (JBL), Flex (FLEX), Celestica (CLS) and Penguin Solutions (PENG). Micron (HBM), Arista (data-center switching), Supermicro and Dell (AI servers), Coherent and Lumentum (optical transceivers) are the core. At the edge: Cisco, HPE and NetApp sell into data centers as one line among enterprise lines; Western Digital, Seagate and Sandisk sell storage whose cloud end market is broader than AI; Ciena is telecom with a growing cloud-provider customer group; Jabil, Flex, Celestica and Fabrinet are contract manufacturers whose AI exposure is a customer mix they state when they choose to. Celestica moved to 10-K recently, so earlier years are gaps.

## Where the AI money shows up

1. **Segment or market revenue** (`facts.segment_revenue`): Micron "Compute and Networking" / "Cloud Memory"; Arista "Product"; Cisco "Networking". Seller side of the buildout.
2. **Capex** (`values.capex`): Micron's fab and HBM capacity is the one supplier capex that is AI-driven in part; Micron states the share of capex going to HBM/AI capacity in some releases.
3. **What the company says** (`ai_spend`): AI server revenue and orders (Dell, Supermicro, HPE), AI infrastructure orders (Cisco), data-center revenue (Coherent, Lumentum, Jabil, Flex, Celestica) when stated.

## How to attribute

Capex and opex:

- Micron: `stated_share` or `stated_amount` when the company gives the HBM/AI share of capex; otherwise `qualitative` with confidence ≤ 0.4 ("capex driven by HBM and AI demand").
- Arista, Cisco: `none` for capex (their capex is small and not AI); `qualitative` or `none` for opex.
- Every other company here: `none` for capex unless an expansion is stated as being for AI demand with an amount; `qualitative` or `none` for opex.
- As with chip sellers, record data-center or AI revenue in `basis` as the seller-side signal, never in `ai_amount`; the revenue field below is where it becomes a row.

Revenue, in order of hardness:

- `stated_share`: the company states AI's share of revenue. Supermicro states the share from AI platforms; use it. Confidence ≤ 0.9.
- `stated_amount`: the company states AI revenue or AI server revenue for the year (Dell's AI server revenue, HPE's AI systems revenue, Cisco's AI infrastructure orders from hyperscalers when given as revenue). Orders and backlog are not revenue: confidence ≤ 0.5 for an orders figure and say so. Confidence ≤ 0.9 for a revenue figure.
- `segment`: sum of the `segment_revenue` facts that are the data-center line, named per company. Micron "Cloud Memory Business Unit" from FY2025 (before that "Compute and Networking", which includes client and graphics; ≤ 0.5). Coherent's and Lumentum's networking or cloud segment when stated. Dell "Infrastructure Solutions Group" and HPE "Server" are data-center lines that include non-AI servers: ≤ 0.5. Celestica, Jabil and Flex: their cloud or data-center segment when stated, ≤ 0.6. Arista and Cisco have no AI segment; do not use "Product" or "Networking" as one.
- `qualitative`: revenue growth attributed to AI or cloud demand in words only, confidence ≤ 0.3. The common answer for storage, NetApp, Ciena and Fabrinet.
- `none`: no link stated.
- `whole_business`: never, even for Supermicro; use its stated share.

## Projects

A project is a fab or factory with a location and an amount: Micron's fabs (Idaho, New York, Singapore, Japan) and HBM packaging capacity, Supermicro's and Dell's plant expansions, a contract manufacturer's new site stated as being for AI or data-center customers. Words that name one: "fab", "facility", "campus", "expansion", "investment of", "capacity", "square feet" with a location. Not a project: a product launch (a new drive, switch or server), a customer win, an order figure, a hire.

## Traps

- A memory upcycle lifts total revenue; only the AI/HBM part is attributable, and only when stated.
- Orders, bookings and backlog are not revenue; a stated AI order figure gets a low ceiling and the word "orders" in `basis`.
- A server segment (Dell ISG, HPE Server) is a data-center line, not an AI one; cap the confidence.
- Micron renamed its segments in FY2025; an older "Compute and Networking" fact is not comparable to "Cloud Memory".
