# Fields

What each released number means. The extraction prompt (`agents/prompts/`) and the rules (`rules/`) implement these definitions; when they disagree, this file wins.

| Field | Definition | Read from | Sign |
|---|---|---|---|
| `revenue` | Total revenue, or total net sales, for the period. | The income statement's total line, never a component. | As reported |
| `cost_of_revenue` | Total cost of revenue, or cost of sales. | The income statement. If there is no such line, the value is missing with that reason. | Positive |
| `operating_income` | Operating income, or income (loss) from operations. | The income statement. | As reported; a loss is negative |
| `capex` | Cash paid for property and equipment. | The investing section of the cash-flow statement, as one line. Lines are never added together. | Positive |

**When a line differs from the definition,** the reported line is used as is and the `definition_note` rule records the difference on every release. For example, NVDA's capex line includes intangible assets.

**Periods.** Every value has two labels:
- `cal_q`: the calendar quarter holding most of the fiscal quarter's days.
- `fiscal_period`: the company's own label.

For example, NVDA's quarter ended 26 Jul 2026 is `2026Q2` and `FY2027 Q2`.

**Units.** Whole US dollars, unscaled.
