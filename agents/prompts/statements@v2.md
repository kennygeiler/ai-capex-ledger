# Extraction prompt: statements@v2

You are reading the income statement and cash-flow statement of one SEC filing. The tables below were parsed from the filing's HTML and show exactly what a reader sees. Extract four line items for **every column** of the statement.

## Fields

| Field | What to take | Sign |
|---|---|---|
| `revenue` | Total revenue or total net sales for the company. If revenue is split into lines (product, service), take the total line, not a component. | As shown (normally positive). |
| `cost_of_revenue` | Total cost of revenue or cost of sales, when the statement has that one total line. | Positive number for a cost, even if the table shows it in parentheses. |
| `cost_of_revenue_part` | **Only when there is no total cost-of-revenue line.** Each line that is a cost of delivering revenue (for example "cloud services and license support", "hardware", "services" or "data center" expenses), one value per line per column. Never include sales and marketing, research and development, general and administrative, amortization, restructuring or acquisition costs. Give a `notes` entry saying why each line is a cost of revenue. Code adds the parts up; you don't. | Positive. |
| `operating_income` | Operating income, or "income (loss) from operations". | As shown: a loss is negative. |
| `capex` | Cash paid for property and equipment in the investing section of the cash-flow statement ("purchases of property and equipment", "capital expenditures", "additions to property and equipment"). If the line also covers intangible assets, use it and say so in `notes`. Do not add other lines together. | **Positive number** for cash spent, even though the table shows it in parentheses. |

## Rules

1. **Cite the cell.** For every value give the `table_id`, the `row_label` and `column_label` exactly as they appear below, and the `cell_text` exactly as shown (e.g. `"(4,434)"`). A value you cannot point to does not exist.
2. **Apply the unit.** The unit line is given for each table, e.g. "(In millions)". `value` is in whole US dollars: cell 96,221 in millions → `96221000000`.
3. **Period.** From the column label, give `period_end` as a date (YYYY-MM-DD) and `months`: 3 for "Three Months Ended", 6, 9, or 12 for a year. If a column label gives only a year (annual tables), the period ends on the fiscal year-end date stated in the filing; use the filing's report period below to work out the day.
4. **Don't guess.** If a field is not in the statement, list it in `not_found` with the reason. Never fill a gap from memory or arithmetic.
5. `confidence`: 1.0 when the row label clearly is the field; lower when you chose between candidate rows, and say why in `notes`.

## Output

Return only one JSON object matching `agents/schemas/extraction@v1.json`:

```json
{"accession": "...", "prompt_version": "statements@v2",
 "values": [{"field": "revenue", "table_id": "t0007", "row_label": "Revenue", "column_label": "Three Months Ended | Jul 26, 2026",
             "cell_text": "96,221", "period_end": "2026-07-26", "months": 3, "value": 96221000000, "confidence": 1.0}],
 "not_found": []}
```
