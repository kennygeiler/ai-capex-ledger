# Notes prompt: notes@v1

You are reading note tables from one SEC 10-K: the segment note, the property-and-equipment note, the lease note and the commitments table. The tables below were parsed from the filing's HTML and show exactly what a reader sees. Extract five kinds of fact, for **every column that is a fiscal year or a fiscal year-end**.

## Fields

| Field | What to take | `dimension` | `months` |
|---|---|---|---|
| `segment_capex` | Capital expenditures (additions to property and equipment, expenditures for long-lived assets) **per reportable segment**, from the segment note. One value per segment per year. Skip the consolidated total. | the segment's name as written | 12 |
| `segment_revenue` | Revenue **per segment, or per market / product line** when the filing reports revenue that way (Nvidia's "Data Center", AMD's "Data Center" segment). One value per segment or market per year. Skip the total. | the segment or market name as written | 12 |
| `ppe_category` | Property and equipment, **gross, by category** at the year-end date (land; buildings; servers and network equipment; equipment; leasehold improvements; construction in progress…). Skip the total, accumulated depreciation, and the net line. | the category label as written | 0 |
| `finance_lease_liability` | Total finance lease liabilities at the year-end date (current plus non-current, or the "total finance lease liabilities" line). One value per year-end. | `null` | 0 |
| `purchase_commitments` | Total purchase obligations or purchase commitments as of the year-end date (from a contractual-obligations or commitments table; the total across years, not one year's payment). One value per year-end. | `null` | 0 |

## Rules

1. **Cite the cell.** For every value give `table_id`, `row_label` and `column_label` exactly as they appear below, and `cell_text` exactly as shown. A value you cannot point to does not exist.
2. **Apply the unit.** The unit line is given per table. `value` is whole US dollars, always positive (a balance or a spend).
3. **Period.** `period_end` is the fiscal year-end date (YYYY-MM-DD) the column refers to; if a column gives only a year, use the filing's report period at the top to work out the day. `months` is 12 for a flow (capex, revenue) and 0 for a balance at that date.
4. **Dimension exactly as written.** For segment and category rows, `dimension` is the row's label verbatim (minus footnote marks). Never merge or rename.
5. **Don't guess.** If a field is not in the tables, list it in `not_found` with the reason. A company with one segment has no `segment_capex`; say so.
6. `confidence`: 1.0 when the row plainly is the field; lower when you chose, and say why in `notes`.

## Output

Return only one JSON object matching `agents/schemas/notes@v1.json`:

```json
{"accession": "...", "prompt_version": "notes@v1",
 "values": [{"field": "ppe_category", "dimension": "Servers, network equipment, and software", "table_id": "t0043", "row_label": "Servers, network equipment, and software",
             "column_label": "2026", "cell_text": "112,318", "period_end": "2026-06-30", "months": 0, "value": 112318000000, "confidence": 1.0}],
 "not_found": [{"field": "segment_capex", "reason": "the segment note reports revenue and operating income only"}]}
```
