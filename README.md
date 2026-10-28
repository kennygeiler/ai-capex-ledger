# Capex Ledger

This project pulls revenue, capex and opex from SEC EDGAR for the AI-trade companies, Nasdaq names outside the S&P 500, and the S&P 100: 113 companies in all.

The pipeline cleans the data and normalizes it to calendar quarters (and fiscal years), then serves it to an explorer page. Every number links back to its filing.

**Start here:** [docs/SUMMARY.md](docs/SUMMARY.md) is the one-page summary. `explorer/standalone.html` is the tool; open it in any browser.

## Status (2026-10-27)

- **Live pull, 27 Oct 2026, 20:30 UTC.**
  - 228 SEC API calls, 0 failures, 100 seconds
  - 45,537 clean facts
  - 1,328 of 1,340 checks pass where quarters should add up to the filed totals
  - 2 errors flagged (Honeywell and Intuit capex comes out negative after restatements), 77 warnings
  - 7 unit tests pass
- **Periods:**
  - Quarters: Q3 2024 to Q2 2026. Q3 2026 is partly filed and shows as "partial".
  - Fiscal years: FY2021 to FY2025 (10-K).
- **Coverage out of 113 companies, all 8 quarters:**
  - revenue: 110
  - opex: 110
  - capex: 103
  - Every gap has a reason in the Data quality tab: banks and insurers have no capex line, SpaceX only listed in June 2026, BNY tags revenue only as interest income, ConocoPhillips and NextEra use extension tags for capex.
- **Not verified:**
  - Current S&P 100 membership. The list is from 2025 and has 102 tickers.
  - Whether any of the Nasdaq names joined the S&P 500 in 2026.
- **The explorer** is a React app built with [shadcn/ui](https://github.com/shadcn-ui/ui) (Radix + Tailwind, shadcn charts on Recharts) in `web/`. It builds to one self-contained `explorer/standalone.html` (about 4.7 MB with the data and font inlined). It was tested on the full dataset in light, dark and phone widths.

## Run

```bash
python3 -m pipeline.run              # fetch (24h cache), clean, validate, export to data/clean/
python3 -m pipeline.run --refresh    # re-download everything from SEC
python3 -m pipeline.run --only NVDA,MSFT
python3 -m unittest discover -s tests -t .
cd web && pnpm install && pnpm build # rebuild explorer/standalone.html (type-check, Vite, inline data)
cd web && pnpm dev                   # live explorer at http://localhost:3601, reads data/clean/viz.json
```

The pipeline uses only the Python standard library. SEC requires a contact email in the User-Agent: set `SEC_USER_AGENT="Name email"` in `.env`, which is git-ignored.

## Companies (`data/clean/companies.csv`)

- **AI set (19):**
  - NVDA, MSFT, GOOGL, AMZN, META, ORCL, TSLA, MU, AMD, SPCX (SpaceX)
  - Nasdaq, not in the S&P 500: CRWV, MRVL, ALAB, CRDO, IREN, APLD, CIFR, WULF, CORZ
- **S&P 100 (102 tickers, 2025 membership):**

  AAPL ABBV ABT ACN ADBE AIG AMD AMGN AMT AMZN AVGO AXP BA BAC BKNG BLK BMY BNY BRK-B C CAT CHTR CL CMCSA COF COP COST CRM CSCO CVS CVX DE DHR DIS DUK EMR F FDX GD GE GILD GM GOOGL GS HD HON IBM INTC INTU ISRG JNJ JPM KO LIN LLY LMT LOW MA MCD MDLZ MDT MET META MMM MO MRK MS MSFT NEE NFLX NKE NOW NVDA ORCL PEP PFE PG PLTR PM PYPL QCOM RTX SBUX SCHW SO SPG T TGT TMO TMUS TSLA TXN UBER UNH UNP UPS USB V VZ WFC WMT XOM
- **Left out:**
  - NBIS and ARM: foreign filers (20-F), so no quarterly XBRL.
  - SMCI: in the S&P 500.
  - GOOG: same company as GOOGL.

## Pipeline (`pipeline/`)

| Step | File | What it does |
|---|---|---|
| Ingest | `edgar.py` | Resolves tickers to CIKs (`company_tickers.json`), then fetches `companyfacts` and `submissions` at no more than 6.7 requests a second. Every call is logged (URL, status, ms, bytes) and each raw file is cached with its SHA-256. |
| Fill gaps | `xbrl_instance.py` | When a recent 10-Q or 10-K isn't in companyfacts yet (11 companies on this pull), parses that filing's XBRL instance XML. Reads contexts, periods and USD units, and skips segment rows. |
| Find labels | `normalize.discovery_scan` | Scans every us-gaap concept a company has filed against patterns for each line item, and counts the discrete quarters each match yields. |
| Parse | `normalize.discrete_quarters` | Takes three-month facts as filed, differences YTD cash-flow lines, and derives Q4 as the 10-K year minus nine months. Keeps the latest-filed vintage and records restatements. |
| Clean | same | Drops "quarters" that carry a full-year value (Oracle filer error). Rebuilds Q4 from restated quarters. Merges a predecessor CIK's history (ExxonMobil). |
| Align | `normalize.calendar_quarters_ranked` | Assigns each period to the calendar quarter with the most days. Collisions caused by non-13-week calendars (Costco) shift to the next-best quarter, with no cascade. |
| Metrics | `normalize.derive_costs` | Opex = revenue − cost of revenue − operating income, with labelled fallbacks: reported OperatingExpenses, total costs where there is no cost-of-revenue line, SG&A + R&D, and non-interest expense for banks. |
| Validate | `validate.py` | Signs, quarter length, jumps over 3×, tiling against filed totals, restatements, tag switches, and coverage with a reason for each gap. |
| Export | `run.py` | Writes to `data/clean/`: `facts.csv` (tidy, with lineage), `quarterly_wide.csv`, `annual_wide.csv`, `companies.csv`, `dataset.json`, `viz.json`, `pull_log.json`, `quality.md`. |

## Explorer (`web/` → `explorer/standalone.html`)

Built with shadcn/ui components: Tabs, Card, Select, Toggle group, Checkbox, Table, Sheet (the lineage drawer), Badge, Sonner toasts, and shadcn charts. Light and dark follow the OS.

- `web/src/data.ts` loads the dataset and builds lookups; `state.ts` keeps the view in the URL; `model.ts` computes values and transforms.
- `web/src/pages/` has one file per tab; `web/src/components/` has the charts, lineage drawer and shared pieces; `components/ui/` is shadcn's generated code.
- `scripts/build-standalone.mjs` runs the Vite build and inlines `data/clean/viz.json` as `window.__DATA__`.

- **Explore:**
  - quarterly or annual periods
  - company universe: AI set, S&P 100 or all, with search
  - metrics: revenue, capex, opex, total costs, capex ÷ revenue, opex ÷ revenue
  - views: value, indexed, period-on-period or year-on-year
  - charts: lines, bars, small multiples, heat table
  - a pivot table where clicking any cell shows its lineage, with links to EDGAR
  - state is saved in the URL, and the view can be exported to CSV
- **Data quality:** coverage for each company (quarters and years), the tag each one uses, a filterable list of issues, and the companies that were excluded.
- **How it was found & parsed:**
  - which tag each company uses for revenue and capex, and which route it needs for opex
  - the full concept scan for any company
  - a step-by-step trace of any number for the AI set: the raw facts from every filing, the arithmetic, the calendar placement and the final clean row
- **Admin:**
  - the last pull: time, duration, requests, bytes and errors
  - the API endpoints used
  - how fresh each company's data is (latest filing and latest quarter in the data)
  - the full request log
  - the raw files with their hashes
- **Method:** definitions for the metrics and methods, and the tags tried.

## Repo map

- `pipeline/`, `tests/`, `scripts/`: the code
- `data/raw/`: the SEC cache (git-ignored)
- `data/clean/`: the outputs
- `web/`: the explorer source (React + shadcn/ui)
- `explorer/standalone.html`: the built explorer, one file
- `docs/SUMMARY.md`: the one-page summary
- `archive/`: superseded work, outside the deliverable. This holds the earlier storytelling prototypes, their sample data, the agent design review, and the first plain-JS explorer (`archive/explorer-vanilla/`, replaced by the shadcn/ui version on 2026-10-27). Kenny switched the project to a data tool on 2026-10-27.
