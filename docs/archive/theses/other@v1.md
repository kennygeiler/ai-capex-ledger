# Money-flow model: everything else (other@v1)

Who: Apple, Tesla, IBM, Walmart, ExxonMobil, JPMorgan, Compass, SpaceX and any company added without an industry. AI may be a cost line (Tesla's AI training compute, JPMorgan's technology budget) or nothing.

## How to attribute

- `stated_amount` / `stated_share`: only what the company states as the AI part (`scope: ai`). Tesla states AI-related capex in its releases; use it.
- `qualitative` when spend is linked to AI in words only; `none` otherwise.
- Never estimate from PP&E categories or segments here: there is no industry pattern to lean on, and a guess would be a number with nothing behind it.

## Traps

- "Technology" or "software" capex is not AI capex.
- Opex: AI headcount or model costs are rarely quantified; `none` is the common, honest answer.
