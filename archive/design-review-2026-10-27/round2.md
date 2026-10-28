# Design review, round 2: responses to each other (2026-10-27)


## CEO

**(a) Where peers changed my mind**
- **Architect, on the finance-lease toggle.** `FinanceLeasePrincipalPayments` repays old leases, so adding it to capex counts the same spending twice. New lease spending should come from the right-of-use asset tag, shown as its own stacked layer. My "leases on by default" was wrong.
- **Architect, on opex and the hero label.** Opex is not comparable across companies, so drop it. The $488B figure should say "capex", not "AI buildout".
- **Architect, on sellers.** Adding Broadcom alone does not fix Mirror. Total seller revenue includes gaming and PC chips, so the gap is built into the data.
- **Design, on the slope chart and sharing.** The slope chart throws away 6 of 8 quarters. Views must be saveable in the URL.

**(b) Where I hold my position**
- **Persona.** The hiring manager and the informed reader are primary. An analyst with Bloomberg won't adopt a site covering 10 companies. We still build to an analyst's standard, because that rigor is the hiring proof. The outcome barely changes; what changes is how we judge the page: it must land in 60 seconds.
- **Scope.** No free-text box and no WebLLM in v1. Every feature waits until real numbers exist.

**(c) Open disputes**
- **Persona:** as above. The analyst's questions are the content; the hiring manager is the judge.
- **What comes first:** both, as one task. Write contract v2 (whole dollars, period dates, filed date, dimensions, vintages, `derived_from`) and prove it on MSFT, NVDA and CRWV right away. A contract fixed without real data will be fixed again.
- **Sellers:** use data-center segment revenue, and add Broadcom's AI semiconductor segment. Micron's segment reorganisation gets a footnote until its restatement bridge is built.
- **Chat:** the metric registry and DuckDB-WASM are the backbone. v1 shows that registry as precomputed, editable chips, each with citations. A natural-language box can come later as a fast way to set chips.

**(d) Joint plan**
1. **Contract v2 plus corrected metric definitions, proven on real EDGAR data for MSFT, NVDA and CRWV.** Covers ROU-based leases, opex dropped, a written calendar rule, Tesla behind a flag, and the hero renamed to "capex". Effort: L.
2. **Metric registry in YAML, plus a set of golden-question evals.** Covers acceleration, capex ÷ operating cash flow, FCF after capex, and lease share. Effort: M.
3. **Landing page: Mirror rebuilt on data-center revenue, beside a growth-rate panel.** The caveat sits next to the chart, and the uncovered gap is labelled. Effort: M.
4. **Desk as the drill-down.** Compare mode, shared/own scale toggle, CoreWeave included, a filterable fact table, and full state saved in the URL. Effort: M.
5. **Lineage drawer on every bar.** Shows `derived_from` with links to EDGAR. Effort: S–M.
6. **Chip query bar compiled from the registry over DuckDB-WASM, with a refusal state.** No API spend. Effort: M.


## Chief of Design

**(a) Where a peer changed my mind**
- **The Mirror gap is built into the data, not a finding (CEO and Architect).** I had framed the gap as "how far spend outruns supplier revenue." I withdraw that. Seller revenue covers all segments of only three companies, so the gap can't carry the thesis until the coverage is fixed.
- **The lease toggle double-counts (Architect).** `FinanceLeasePrincipalPayments` is repayment of old leases. I'll redesign the toggle as a separate stacked layer built from right-of-use assets obtained.
- **Opex can't be compared across companies, and the hero overclaims (Architect).** Desk drops the opex panel. The hero says "capex", not "AI buildout spending".
- **Drop WebLLM (CEO).** The download cost lands on the visitor, and its answers can't be verified.
- **Show CoreWeave.** It belongs in the view with an own-scale callout.

**(b) Where I hold my position**
- **Shareable state, mobile and scale toggles are not polish.** Saving the view in the URL, a stacked-row fact table on phones, and a shared/own scale switch decide whether a recruiter's shared link works at all. I hold this against the CEO's "data before design."
- **Cap the signal layer.** The Architect's list is too long for one screen. Hand-annotated depreciation notes, special-purpose vehicles (SPVs, the off-balance-sheet financing vehicles), and guidance extracted from 8-K text go to a later phase. The page ships at most four signals.
- **Growth rate goes above the fold, beside Mirror.** "Accelerating?" is the first question.

**(c) The open disputes**
- **Persona:** Use the CEO's framing. The hiring manager and the informed reader are the audience. The analyst's questions are the content, and Desk must survive an analyst's five-second sniff test.
- **What comes first:** Fix the contract and definitions first, then load real data for three companies right after. Loading real data into a wrong schema is pure rework, and the contract fix is days, not weeks.
- **Sellers:** Data-center segment only. Add Broadcom only if its AI-relevant segment can be cleanly tagged; otherwise label it in an explicit "not covered" band.
- **Chat:** A query builder over DuckDB-WASM plus a metric registry, with precomputed chips as saved builder states. I drop my natural-language box.

**(d) Joint plan**
1. **Fix the contract** (whole dollars, period dates, vintages, `derived_from`, dimensions) and the metric definitions (capex label, ROU-based leases, no opex, calendar rule, Tesla flagged). *M*
2. **Load real EDGAR data for MSFT, NVDA and CRWV**, with golden checks against the filings. *L*
3. **Data-center seller pipeline, with a "not covered" band on Mirror.** *M*
4. **Signal layer, capped at four:** acceleration, capex/OCF, free cash flow after capex and leases, concentration. *M*
5. **Build the merged screen**, with URL state and mobile layouts. *M*
6. **Metric registry, DuckDB-WASM builder and chips**, with about 50 golden-question evals. *L*

**Merged screen**
The top shows Mirror: data-center seller revenue above zero, buyer capex below it, with finance-lease ROU as a hatched layer. A grey "not covered" band names what's missing: foundry, networking, power, construction. The caveat sits directly under the chart.
To its right is an acceleration strip: a QoQ/YoY growth heatmap by buyer and quarter, so rollovers show as colour breaks.
Below that is a ranked table, Report's table rebuilt: capex, capex/OCF, lease share and growth, sortable, with outlier flags and CoreWeave included.
Clicking a row opens Desk inline. Desk shows that company's panels on a labelled shared or own scale, plus a filterable fact table.
Clicking any number opens a lineage drawer with the form, tag, method, source facts and an EDGAR link.
A chip/builder bar sits above everything. Every state, including the company, metric, range, lease setting and scale, lives in the URL.


## AI Data Architect

**AI Data Architect, round 2**

**(a) Where peers changed my mind**
- **CEO, on the persona.** He's right that analysts have Bloomberg and FactSet. I now agree the design should serve the hiring manager and informed reader, with the analyst's questions as the content.
- **Design, on capex/OCF.** It should replace capex/revenue as the headline risk ratio, not sit alongside it.
- **Design, on URL state.** A shareable URL is a cheap form of reproducibility, so it belongs in my contract too.
- **CEO, on the "unaccounted" band.** It is more honest than my silent footnote.

**(b) Where I hold my position**
- **Against the CEO's "real data first".** The hard part is the plumbing, not the 3-company sample. The companyfacts API omits dimensioned facts, so segment revenue needs the filing XBRL instance or the SEC Financial Statement & Notes datasets. Real numbers in the current contract would ship the wrong lease measure and single-accession derived values.
- **Against a free NL box first (Design).** Chips are only trustworthy if a metric registry backs them.

**(c) Open disputes**
- **Persona:** the hiring manager and informed reader come first. Everything shown must still pass an analyst's sniff test.
- **Real data or contract first:** the same step. Build the contract v2 by running real EDGAR for MSFT, NVDA and CRWV through it; the hard cases force the right schema.
- **Sellers:** use data-center segment revenue, and add Broadcom as a labelled partial. Broadcom's fiscal year ends on the Sunday nearest 31 October, so it is off by one month, like Micron. Its "AI semiconductor revenue" appears only in press releases and calls, not in XBRL. Only the Semiconductor Solutions segment is tagged, which overstates AI. Show it hatched, with "segment ≠ AI" on the label.
- **Chat:** all three, in layers on one spec.
  - A metric registry compiles to SQL over DuckDB-WASM.
  - Chips are saved instances of that spec.
  - The query builder edits the spec.
  - An NL box (grammar parser, WebLLM later) only fills the spec.
  - $0 runtime throughout.

**(d) Joint plan**
1. **Contract v2, run on real EDGAR for MSFT, NVDA and CRWV (L).** Whole dollars, period and filed dates, dimensions, vintages, `derived_from`, and a written calendar rule.
2. **Metric fixes (S).**
   - Label the hero "capex".
   - Use ROU additions as the lease measure.
   - Make capex/OCF and lease share the risk ratios.
   - Drop opex and the seller capex ratios.
   - Flag Tesla.
   - Bring CoreWeave back on a broken axis.
3. **One product (M).** Mirror as the landing page, with a growth/acceleration panel and the caveat next to it. Desk as the drill-down, with a lineage drawer on every bar and state in the URL. Report's table moves into Desk.
4. **Coverage honesty (M).** Data-center segment revenue for sellers; Broadcom as a hatched partial; an "unaccounted: foundry, networking, power, construction" band.
5. **Metric registry, DuckDB-WASM and 10–15 chips (M).** Answers cite accessions. A 50-question golden eval set with exact-match numbers and refusal checks.
6. **Extend to all 10 companies, then the query builder and NL-to-spec (L).** Precede it with a "watch next quarter" strip driven by filing dates.
