# Attribution prompt: attribution@v1

You are attributing one company's capital expenditures (`capex`) and operating expenses (`opex`) to AI, one row per fiscal year and kind, using only the data pack below and the money-flow model for the company's industry. The model says where AI money shows up for this kind of business and which methods are allowed, in order of hardness. You pick the hardest method the data supports, show every input you used, and never invent a number.

## Output rows

One row per (`field`, `period`, `kind`) you can say something about. `kind` is `actual` (money spent in that fiscal year) or `outlook` (expected for a later year, from a statement).

| Field | Meaning |
|---|---|
| `method` | One of `stated_share`, `stated_amount`, `segment`, `ppe_category`, `whole_business`, `qualitative`, `none`. The model says which are allowed for this industry. |
| `ai_amount` | Whole US dollars, or `null` for `qualitative` and `none`. |
| `ai_share` | `ai_amount ÷ the company's value for that field and year`, when that value is in the pack; else `null`. |
| `inputs` | Every pack item the number rests on, by its id, with the value you took from it: `[{"id": "fact:…", "value": 1234}]`. Code recomputes `ai_amount` from these. |
| `basis` | One or two sentences a reader can check: the arithmetic and what the number does and does not include. For sellers, the seller-side signal (data-center revenue) goes here, never in `ai_amount`. |
| `confidence` | 0 to 1. The model gives ceilings per method. |

## Arithmetic the code checks

- `stated_amount`: `ai_amount` equals the statement's amount (the midpoint of a range); the input is that statement (`stmt:…`).
- `stated_share`: `ai_amount = round(share × value)`; inputs are the statement and the value (`value:…`).
- `segment`: `ai_amount` is the sum of the listed `fact:…` segment capex (or cost) inputs.
- `ppe_category`: `ai_amount = gross(t) − gross(t−1)` of one category; inputs are the two facts, newer first.
- `whole_business`: `ai_amount = value`; the input is the value.
- `qualitative` / `none`: `ai_amount` and `inputs` empty; `basis` says what was said, or that nothing was.

## Rules

1. Only ids from the pack. An id that is not there, or a value that differs from the pack's, is rejected and you are asked again.
2. Hardest method the data supports. Do not fall back to words when a segment or a stated share exists.
3. A company total "to support AI" is the whole, never the AI part.
4. Years: one row per fiscal year present in the pack's values for `actual`; `outlook` rows only from statements with `kind: outlook`.
5. Say what is missing in `none_found`: fields and years with no basis, and why.

## Output

Return only one JSON object matching `agents/schemas/attribution@v1.json`:

```json
{"ticker": "APLD", "prompt_version": "attribution@v1", "model": "miner_to_hpc@v1",
 "rows": [{"field": "capex", "period": "FY2025", "kind": "actual", "method": "segment", "ai_amount": 976506000, "ai_share": 0.84,
           "inputs": [{"id": "fact:APLD|segment_capex|HPC Hosting Business|FY2025", "value": 976506000}],
           "basis": "Capital expenditures of the HPC Hosting Business segment; the Data Center Hosting (bitcoin) segment's 9.3M is excluded. The GPUs are the tenant's; this is the shell and fit-out.", "confidence": 0.9}],
 "none_found": [{"field": "opex", "period": "FY2025", "reason": "no segment cost line and no statement attributes opex to AI"}]}
```
