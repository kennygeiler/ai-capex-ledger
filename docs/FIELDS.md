# Fields

What each released number means. The extraction prompt (`agents/prompts/`) and the rules (`rules/`) implement these definitions; when they disagree, this file wins.

**Source:** 10-K annual reports (and 10-K/A amendments that carry the financial statements), one value per company per fiscal year, FY2022–FY2026.

| Field | Definition | How it is built |
|---|---|---|
| `revenue` | Total revenue, or total net sales. | One cell: the income statement's total line, never a component. |
| `capex` | Cash paid for property and equipment. Shown as a positive number. | One cell: one line in the investing section of the cash-flow statement. Lines are never added together. |
| `opex` | Operating expenses: the costs below gross profit, such as R&D, sales, general and administrative, and depreciation. This is the standard analyst definition, and excludes cost of revenue. Because it is derived, it also includes everything else the company puts in its operating section: impairments, restructuring, and for bitcoin miners unrealized losses and fair-value changes. That is why opex can exceed revenue (Core Scientific FY2022, Cipher FY2025). | Revenue − cost of revenue − operating income, all three from the same 10-K column. If there is no total cost-of-revenue line, cost of revenue is the sum of the lines that are costs of delivering revenue (see below). |

**One filing per company-year.** Every field of a company-year comes from the newest 10-K that reports that year. A year never mixes filings.
- If that 10-K has no such line, the value is blank, labelled `not_reported`.

**No total cost-of-revenue line** (Oracle; Applied Digital's newer 10-Ks). As standard data tools do, cost of revenue is the sum of the lines that are costs of delivering revenue: for example cloud services, hardware, services or data-center costs, but never sales, R&D, admin, amortization or restructuring.
- The agent classifies and cites each line (`cost_of_revenue_part`), and code adds them up.
- The `cost_lines_summed` rule lists the lines, so a person confirms the classification once per company.
- XBRL often draws cost of revenue differently for these companies. When revenue and operating income agree with XBRL, an opex difference can only come from that, so it is labelled `definition_gap` and not raised for review.

**Restatements.** A later 10-K may show a different figure for a past year, for example after selling part of the business. The newest figure is used, and the first-filed one is kept in `first_reported`.
- `basis` is `restated` when the two differ by more than rounding; otherwise it is `as_reported`. The size of the change is `value` against `first_reported`.

**When a line differs from the definition,** it is used as reported, and the `definition_note` rule records the difference on every release. For example, NVDA's capex line includes intangible assets.

**Periods and units.** `period` is the company's own fiscal year (NVIDIA's FY2026 ended 25 Jan 2026), with its end date in `period_end`. Values are whole US dollars, unscaled.
