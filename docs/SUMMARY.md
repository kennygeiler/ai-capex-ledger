# Capex Ledger: one-page summary

**What I built.** A pipeline that pulls revenue, capex and opex for 113 companies directly from SEC EDGAR. It cleans and normalizes the data into a tidy dataset and serves it to an explorer page. Every number links back to the filing it came from. The data was pulled live on 27 Oct 2026: 228 API calls, 0 failures, 100 seconds.

**Scope against the brief.**

- **Companies:**
  - The AI-trade names you listed (Alphabet, Nvidia, Meta, Microsoft, Amazon, SpaceX, Oracle, Tesla, Micron, AMD).
  - CoreWeave plus 8 more Nasdaq-listed companies outside the S&P 500: Marvell, Astera Labs, Credo, IREN, Applied Digital, Cipher, TeraWulf and Core Scientific.
  - Then the S&P 100 for the "then 100" step.
- **Periods:** both of the brief's options. 8 calendar quarters (Q3 2024 to Q2 2026), built from 10-Qs plus 10-Ks, and 5 fiscal years (FY2021 to FY2025) from 10-Ks.
- **Formats:**
  - Tidy CSV with full lineage (`facts.csv`)
  - Wide tables (`quarterly_wide.csv`, `annual_wide.csv`)
  - JSON
  - A browser explorer with line, bar, small-multiple and heat-table views, pivot tables and CSV export

**How the data is made.**

1. **Ingest.** Tickers are resolved to CIKs live. Each company's XBRL `companyfacts` and `submissions` are fetched at 6.7 requests per second (SEC allows 10). The raw responses are cached with SHA-256 hashes.
2. **Find each company's label.** Every us-gaap concept a company has filed is scanned against patterns. Matches are ranked by how many quarters they cover in the last three years.
   - Revenue: 56% of companies use `RevenueFromContractWithCustomerExcludingAssessedTax`, 38% use `Revenues`, and the rest use a bank tag or a tax-inclusive variant.
   - Capex: Verizon tags it as `PaymentsToAcquireOtherProductiveAssets`, a tag nobody would guess.
3. **Parse.**
   - Three-month facts are taken as filed.
   - Year-to-date cash-flow lines are differenced into single quarters.
   - Q4 = 10-K full year minus nine months.
   - When a period appears in several filings, the latest filing's value is kept.
4. **Normalize.**
   - Fiscal quarters are mapped to calendar quarters by majority of days. This covers Nvidia's January year-end, Microsoft's June, and Costco's 12/12/12/16-week year.
   - Opex is defined consistently: revenue − cost of revenue − operating income. Each fallback route is labelled.
5. **Validate.**
   - Signs, quarter lengths, and jumps of more than 3×.
   - Quarters must add up to the filed totals: 1,328 of 1,340 checks pass.
   - Every gap carries a written reason.

**What made it harder than "relatively straightforward".**

- Oracle's 10-Ks tag a full year's revenue ($39B) as a single quarter, in four separate years. The pipeline detects this, drops the bad fact and derives the quarter instead.
- SEC's `companyfacts` API had not yet picked up 11 companies' Q2 2026 10-Qs (Coca-Cola, Visa, Abbott and others). For those filings the pipeline parses the filing's own XBRL instance XML.
- ExxonMobil reorganized under a new CIK in 2026. Its history is merged in from the old CIK.
- Applied Digital restated its history for discontinued operations. Q4 is rebuilt from the restated quarters, and the issue is flagged.
- Banks and insurers don't report capex as a tagged line. Their opex falls back to non-interest expense.

**Coverage.**

- Out of 113 companies, these have all 8 quarters:
  - revenue: 110
  - opex: 110
  - capex: 103
- The capex gaps are mostly banks and insurers, which have no tagged capex line.
- SpaceX only listed in June 2026, so it has 3 quarters.
- 2 quarters are flagged as errors (Honeywell and Intuit capex comes out negative after restatements). They stay visible rather than hidden.

**Three findings from the real data.**

1. **Five companies now account for most big-company capex.** Microsoft, Alphabet, Amazon, Meta and Oracle went from 39% of all S&P 100 capex in Q3 2024 to 63% in Q2 2026 ($61B to $182B a quarter).
2. **Capex is outpacing revenue.** Those five went from spending 17% of their revenue on capex to 37%. Oracle went from 17% to 86%, and Meta from 20% to 50%. CoreWeave spends about 2.5× its revenue.
3. **The suppliers are booking it.** Nvidia's quarterly revenue rose from $35B to $96B over the same 8 quarters. Opex (excluding cost of revenue) is rising too: Meta's was up 65% year on year in Q2 2026.

**Limits and next steps.**

- **The S&P 100 list is 2025 membership (102 tickers).** Check it against the current index. Also check whether any of the Nasdaq names joined the S&P 500 in 2026.
- **Capex excludes finance leases,** which are large for Microsoft and Amazon. Next: add new right-of-use lease assets.
- **Next: data-center segment revenue,** which needs dimensional XBRL that `companyfacts` leaves out.
- **Next: a metric registry over DuckDB,** to support "ask the data" queries.
- **Next: a scheduled refresh after each earnings season,** with a diff of what changed.
