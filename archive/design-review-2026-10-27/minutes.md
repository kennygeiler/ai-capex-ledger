# Design review: meeting minutes (2026-10-27)

**Attendees:** CEO, Chief of Design, AI Data Architect (three Claude subagents, each given a role).

**Reviewed:** the Report, Desk and Mirror prototypes on sample data. Terrain was cut before the meeting. Screenshots are in `screens/`.

**Format:** independent critiques first (`round1.md`), then each reviewer answered the other two (`round2.md`). These minutes record where they ended up.

## Headline

None of the three directions ships as it stands. All three show **how big** the spending is. The questions that matter are different:

- Is it **speeding up**?
- **Who captures** it?
- **Where is the risk**?

Two framing errors would sink the piece in an interview:

- The hero says "AI buildout spending" but shows total capex.
- Mirror's gap comes from what the data leaves out, not from the market. Seller revenue covers all segments of only three companies.

The data contract also cannot carry the answers yet.

**Unanimous direction:** carry **Mirror forward as the front page and Desk as the drill-down**. Fold Report's table into Desk and drop Report as a standalone view.

## Persona (resolved)

The CEO's framing won. An analyst with Bloomberg won't switch to a site covering 10 companies, so the **audience is the hiring manager and the informed reader** who shares a chart. **The analyst's questions are the content.**

The test is that a hiring manager gets the point in 60 seconds, and every number survives an analyst's five-second sniff test.

## The five questions: consensus answers

**1. Is this the most useful way to present the data for the persona?**

No. All three views show levels. The persona's questions are about rates of change and risk. Fixes:

- Lead with acceleration (QoQ/YoY growth).
- Make capex ÷ operating cash flow the risk ratio.
- Rename the hero to "capex".

**2. Is the UI actionable and flexible enough?**

No. Only Desk can be manipulated, and only one company at a time. Missing:

- compare mode;
- a time-range control;
- a shared/own scale toggle;
- a filterable fact table;
- view state saved in the URL (only the variant is saved today);
- a phone layout for tables.

Desk's three panels sit side by side on different y-scales without saying so.

**3. Are the data outcomes actionable?**

Partly. The lineage is strong, and the "Derived" column is the best data-strategist signal in the piece, but it goes unexplained. Not actionable yet because:

- capex/revenue is the wrong risk ratio;
- the ratios for sellers mean nothing;
- the outlier (CoreWeave) is hidden;
- nothing points to next quarter.

Specific errors to fix:

- `FinanceLeasePrincipalPayments` counts old leases twice. Use `RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability` instead, as a separate layer.
- Opex can't be compared across companies, so drop it.
- Tesla doesn't belong in a list of AI buyers, so put it behind a flag.

**4. Which charts and data experiences are optimal?**

Capped at four signals on the page (the Chief of Design's limit):

| Experience | Answers | Metric |
|---|---|---|
| Mirror, rebuilt | Is the money flowing through? | Buyer capex (with ROU leases hatched) below zero. Seller **data-center segment** revenue above. A grey "not covered" band for foundry, networking, power and construction. Caveat directly under the chart. |
| Acceleration strip (heatmap, buyer × quarter) | Speeding up or rolling over? | QoQ and YoY capex growth, plus the change in growth |
| Ranked table (Report's table, rebuilt) | Who's stretching? | Capex, capex ÷ OCF, lease share, growth. Sortable, with outlier flags. CoreWeave included. |
| FCF after capex + leases | Who funds it from cash vs debt or leases | OCF − capex − ROU additions |
| Concentration (100% stacked bar) | How much of the cycle rests on 2 or 3 firms | Share of combined capex |
| Lineage drawer on every number | Can I trust this? | Form, tag, method, `derived_from` facts, EDGAR link |

**Dropped:** the first-vs-last slope chart, which throws away 6 of 8 quarters. **Deferred to a later phase:** depreciation and useful-life notes, SPV financing, and guidance (none of these are in XBRL, so they need text extraction with a human check).

**5. Can the user chat with the data and manipulate it?**

Manipulate it, yes. Open-ended chat, no: not in v1.

The agreed architecture never lets a language model produce a number:

- A **metric registry** (YAML: name, SQL, grain, tags, caveats) compiles to SQL over **DuckDB-WASM** in the browser.
- **Chips** are saved query states, for example "Did any buyer cut capex QoQ?" or "How much capex is leases?".
- A **query builder** edits the same spec.
- Every answer shows a sentence, a mini chart and the accessions it cites. An out-of-scope question gets an explicit refusal ("not in filings, here's why").
- A golden eval set of about 50 questions, with exact-match numbers and checks that it refuses when it should.

**Runtime cost: $0.**

**Later options:** a natural-language box that only fills the spec (a grammar parser first). WebLLM was rejected because it means a 1GB+ download for visitors and its answers can't be verified. A hosted model capped at $5 would break the no-API-spend rule and needs Kenny's yes.

## Disputes and how they resolved

| Dispute | Positions | Outcome |
|---|---|---|
| Real data first, or contract first? | CEO: real data first. Architect: contract first. Design: contract, then data. | **One sprint.** Write contract v2 (days) and prove it straight away on real EDGAR data for MSFT (June fiscal year), NVDA (January fiscal year) and CRWV (recent listing). |
| How to define sellers | CEO: add Broadcom. Architect and Design: data-center segment only. | **Data-center segment revenue.** Broadcom is shown as a hatched partial labelled "segment ≠ AI". Its AI revenue is only in press releases and calls, its fiscal year ends near 31 October, and it is off by one month, like Micron. |
| Is URL state and mobile polish? | CEO: no features before real numbers. Design: they decide whether a shared link works. | **Both in the merged-screen step,** before chat. |
| How many signals? | Architect: about 8. Design: cap at 4. | **Cap at 4 on the page.** The rest are deferred. |

## Technical warning from the Architect

The `companyfacts` API **omits facts broken out by dimension**, so segment revenue is not in it. The data-center pipeline must parse each filing's XBRL instance or the SEC Financial Statement & Notes datasets. This is the hardest work in the project, and also the best proof of skill.

## Agreed plan (all three signed)

1. **Contract v2 and metric fixes. M.**
   - Store whole dollars, period start and end, filed date, fy/fp, dimensions, every vintage (keep restatements) and `derived_from`.
   - Write the calendar rule: the quarter containing the period-end date.
   - Label the hero "capex"; use ROU leases; drop opex; put Tesla behind a flag; bring CoreWeave back on its own scale.
2. **Prove it on real EDGAR data for MSFT, NVDA and CRWV,** with golden checks against the filings' own totals. **L.**
3. **Data-center segment pipeline for sellers,** a "not covered" band, and Broadcom as a hatched partial. **M.**
4. **Signal layer, capped at four:** acceleration, capex ÷ OCF, FCF after capex and leases, concentration. **M.**
5. **Merged screen.**
   - Mirror plus the acceleration strip above the fold.
   - The ranked table, with Desk opening inline when you click a row.
   - A lineage drawer on every number.
   - All state in the URL, and phone-friendly table rows.
   - **M.**
6. **Metric registry, DuckDB-WASM, query builder and chips,** with about 50 golden-question evals. Then extend to all 10 companies and add a "watch next quarter" strip driven by filing dates. **L.**

## Decisions for Kenny

- Approve the plan above, or reorder it.
- Confirm that the chat stays $0 (registry plus chips, no hosted model).
