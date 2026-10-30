# AI spend prompt: aispend@v4

You are reading passages from the MD&A (Item 7) of one company's 10-K. Your job: find every statement about how much of the company's **capital expenditures** (`capex`) or **operating expenses** (`opex`: research and development, infrastructure costs, headcount) goes to AI, and every statement of how much of its **revenue** (`revenue`) comes from AI or data-center demand (the seller side: "AI revenue was $12.2 billion", "data center revenue of $51.2 billion", "AI accounted for roughly 40% of revenue", "AI server revenue", "HBM revenue"), for the fiscal year the filing reports and for any future year it gives an outlook on.

## What a statement is

| `class` | When | Give |
|---|---|---|
| `explicit_amount` | The sentence states a dollar amount or range. | `amount_low` and `amount_high` in whole US dollars (`$115 billion` → `115000000000`; a single figure → both the same). |
| `explicit_share` | The sentence states a share or fraction ("roughly two-thirds", "more than half", "about 40%"). | `share` between 0 and 1 (two-thirds → `0.67`; "more than half" → `0.5` and say so in `notes`). |
| `qualitative` | The sentence links the spend to AI in words only ("primarily", "the majority", "significant investments", "driven by"). | No number. |

`scope` says what the amount or share is **of**:

- `ai`: the sentence quantifies the AI part itself ("$X of capex for AI infrastructure", "half of our capex went to GPUs"; for `revenue`: AI, data-center, AI-server or HBM revenue as a figure or a share of total revenue).
- `total`: the sentence gives the company's total capex, opex or revenue and says AI is a reason or driver ("capital expenditures of $115 to $135 billion in 2026 to support our AI efforts and core business"). This is **not** AI spend; record it with `scope: total` so the total is not mistaken for the AI part.

`kind`: `actual` when the sentence reports what was spent (a completed period: "capital expenditures were", "we spent"); `outlook` when it states what is expected, anticipated, planned or guided, **even for the current fiscal year** ("we anticipate full-year 2024 capital expenditures of $35–40 billion" from a mid-year release is an `outlook` for 2024). `fiscal_year` is the year as the company names it ("fiscal 2027" → `2027`; "in 2026" → `2026`). When the sentence names no year (present tense: "we continue to invest…", "we expect to increase…"), give `fiscal_year: null`; code then uses the filing's reported year for an `actual` and the year after it for an `outlook`, and says so.

## Rules

1. **Quote the sentence.** `quote` is one complete sentence copied **verbatim** from the passage, and `passage` is that passage's tag (`p03`). Code checks that the quote is in the passage; a quote that is not there is rejected and the task is asked again.
2. **One statement per sentence.** If a sentence covers both an actual and an outlook, or both capex and opex, give one statement each, same quote.
3. **Prefer the specific.** When the filing gives both a number and words for the same thing, give the number (`explicit_amount` or `explicit_share`) and skip the words.
4b. **Revenue is the seller side.** A chip, server or component seller's data-center revenue is what buyers paid it; record it as `field: revenue`, never as the seller's own capex. A buyer's cloud segment (Microsoft Intelligent Cloud, Google Cloud, AWS) is not AI revenue; skip it unless the sentence states the AI part.
4. **Never compute or infer.** If the filing does not state an amount or share, the class is `qualitative`. Do not derive an AI amount from a total, a percentage from two numbers, or a year from context that is not in the sentence.
5. **Boilerplate is not a statement.** A description of what the company sells, or a risk-factor sentence about AI in general, says nothing about spend. Skip it.
6. **Say when there is nothing.** For a field with no statement in any passage, add it to `none_found` with a reason ("no sentence links capital expenditures to AI").
7. `confidence`: 1.0 when the sentence plainly says what you recorded; lower when wording is ambiguous, and say why in `notes`.

## Output

Return only one JSON object matching `agents/schemas/aispend@v4.json`:

```json
{"accession": "...", "prompt_version": "aispend@v4",
 "statements": [{"field": "capex", "fiscal_year": 2026, "kind": "outlook", "scope": "total", "class": "explicit_amount",
                 "amount_low": 115000000000, "amount_high": 135000000000,
                 "quote": "We anticipate making capital expenditures of approximately $115 billion to $135 billion in 2026 to support our AI efforts and core business.",
                 "passage": "p07", "confidence": 1.0}],
 "none_found": [{"field": "opex", "reason": "no sentence quantifies or attributes operating expenses to AI"}, {"field": "revenue", "reason": "a buyer; no sentence states AI's part of revenue"}]}
```
