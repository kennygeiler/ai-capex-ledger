# Capex Ledger

Who pays for the AI buildout, and who gets paid, read from SEC filings.

A portfolio piece for an AI data strategist role. It pulls revenue, capex and opex for the main AI buyers (Microsoft, Alphabet, Amazon, Meta, Oracle, CoreWeave, Tesla) and sellers (Nvidia, AMD, Micron) from SEC EDGAR. It lines the figures up by calendar quarter and shows where every number came from.

## Status (2026-10-27)

- **Part 1, design: done, waiting for a pick.** There are four design directions, all on **sample data**. No figure in the repo is real yet.
- **Part 2, data: not started.** This is the EDGAR pipeline that replaces `data/sample.json`.

## Look at the prototype

Open `prototype/standalone.html` in a browser. It is one self-contained file and needs no server. Flip between the variants with the pill at the bottom, the keys `1`–`4`, or `←` `→`.

| # | Variant | Axis | When it's the right choice | Its cost |
|---|---|---|---|---|
| 1 | Report | Editorial, stat-led scroll: one headline figure, small multiples on one scale, a table, a method section | A hiring manager reads it once, top to bottom | Least interactive; it shows the conclusion more than the craft |
| 2 | Desk | Dense analyst workbench: a company rail, revenue/capex/opex side by side, and a table giving each fact's form, XBRL tag, method and accession | Shows data-strategy skill: lineage, normalization, the finance-lease toggle | Reads as a tool rather than a story, so it needs a guided intro |
| 3 | Mirror | One argument: sellers' revenue above the zero line, buyers' capex below it, then a slope chart of capex intensity | The clearest point of view; it works best in a talk or a post | Totals, not transactions. It must keep its caveat (filings don't show who buys from whom) |
| 4 | Terrain | three.js 3D bars, 10 companies × 8 quarters, orbit plus hover | The memorable opener or demo moment | 3D distorts comparison (front against back), and the hallmark skill's data-viz rules advise against it; treat it as an entry point, not the analysis |

These can be combined. For example, use Mirror as the landing page, Desk as the drill-down, and Terrain as a hero teaser.

Developing with a server: run `python3 -m http.server 3600` from the repo root and open `/prototype/`. `index.html` fetches `data/sample.json`. After editing `prototype/*`, rebuild the standalone file with `node scripts/build-standalone.mjs`.

## Files

- `scripts/gen-sample.mjs` writes `data/sample.json`, the stub, in the exact shape part 2 must produce.
- `prototype/index.html`, `style.css` and `app.js` hold the four variants and the variant picker. The picker comes from the `prototype` skill.
- `scripts/build-standalone.mjs` inlines everything into `prototype/standalone.html`. You can pass it a different data file.

## Data contract (what part 2 must output)

```jsonc
{
  "meta": { "quarters": ["2024Q3", ...], "unit": "USD_B", "methods": { "reported": "...", "ytd_diff": "...", "q4_derived": "..." } },
  "companies": [{ "ticker": "MSFT", "name": "Microsoft", "cik": "0000789019", "role": "spender|seller", "fyEnd": 6, "listedFrom": null }],
  "pending":   [{ "ticker": "SPACEX", "name": "SpaceX", "role": "spender", "reason": "..." }],
  "facts": [{
    "ticker": "MSFT", "calQ": "2025Q2", "fiscal": "FY2025 Q4", "metric": "revenue|capex|capex_finance_leases|opex",
    "value": 76.4, "unit": "USD_B", "form": "10-K", "accession": "0000950170-25-...",
    "tag": "RevenueFromContractWithCustomerExcludingAssessedTax", "method": "reported|ytd_diff|q4_derived"
  }]
}
```

## Part 2 plan (EDGAR)

1. Pull `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` for each company. This needs a `User-Agent` header with a name and email, and the limit is 10 requests per second.
2. Map XBRL tags for each company. Revenue appears under several tags (`Revenues`, `RevenueFromContractWithCustomerExcludingAssessedTax`, ...). Capex is `PaymentsToAcquirePropertyPlantAndEquipment`, plus finance-lease payments for MSFT and AMZN.
3. Normalize the figures:
   - Turn year-to-date cash-flow values into single quarters.
   - Derive Q4 as the 10-K full year minus Q1 through Q3.
   - Align fiscal quarters to calendar quarters. NVDA's fiscal year ends in January, MSFT's in June, ORCL's in May and MU's in August.
   - Remove duplicate and restated figures using the `frame` field.
4. Confirm whether SpaceX files with the SEC. If it doesn't, it stays in `pending`.
5. Write `data/edgar.json`, then run `node scripts/build-standalone.mjs data/edgar.json`.
6. Add checks: totals sum, quarters line up, and spot checks against the filings' own figures.

## Design sources

- `prototype` skill (~/.agents/skills/prototype): the variant picker and the divergence rules.
- `hallmark` (github.com/nutlope/hallmark). I read it but did not install it. From it I applied the Floor rules (tokens, no tracked caps, no invented metrics) and its data-viz rules (one accent per role, zero baselines, one y-axis, hairline grids). Its `sloplint` checker was not run.
- `dataviz` skill: colours from its validated palette (slots 1 and 2), tooltips, and no dual axes.
- `threejs-fundamentals`: the Terrain variant.
