# Fields

What each released number means. The extraction prompt (`agents/prompts/`) and the rules (`rules/`) implement these definitions; when they disagree, this file wins.

**Source:** 10-K annual reports only, one value per company per fiscal year, FY2022–FY2026.

| Field | Definition | How it is built |
|---|---|---|
| `revenue` | Total revenue, or total net sales. | One cell: the income statement's total line, never a component. |
| `capex` | Cash paid for property and equipment. Shown as a positive number. | One cell: one line in the investing section of the cash-flow statement. Lines are never added together. |
| `opex` | Operating expenses: the costs below gross profit, such as R&D, sales, general and administrative, and depreciation. This is the standard analyst definition, and excludes cost of revenue. | Revenue − cost of revenue − operating income, all three from the same 10-K column. |

**One filing per company-year.** Every field of a company-year comes from the newest 10-K that reports that year. A year never mixes filings.
- If that 10-K has no such line, the value is blank, labelled `not_reported`. For example, Oracle reports no cost of revenue, so its opex is blank. Standard data tools fill this by adding up a company's cost lines; we don't add lines together.

**Restatements.** A later 10-K may show a different figure for a past year, for example after selling part of the business. The newest figure is used, and the first-filed one is kept in `first_reported`.
- `basis` is `restated` when the two differ by more than 1% (and more than rounding); otherwise it is `as_reported`.

**When a line differs from the definition,** it is used as reported, and the `definition_note` rule records the difference on every release. For example, NVDA's capex line includes intangible assets.

**Periods and units.** `period` is the company's own fiscal year (NVIDIA's FY2026 ended 25 Jan 2026), with its end date in `period_end`. Values are whole US dollars, unscaled.
