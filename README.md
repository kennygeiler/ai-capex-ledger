# Capex Ledger

AI agents read SEC 10-K filings and extract revenue, capex and opex, citing the exact cell each number came from. Code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** Cost of revenue without a total line is now built as standard tools do. Agents re-read Oracle's and Applied Digital's 10-Ks with prompt `statements@v2`, classifying and citing each delivery-cost line; code adds them up, and the new `cost_lines_summed` rule lists them for review. Oracle's opex is no longer blank: stage 2 has 66 values, 56 agreeing with XBRL and 10 disagreeing. Faults: 0 of 862 escaped. Cell reads: 140/140 match XBRL where XBRL has the cell. `v0.1.0` (NVDA) stays signed.

**Next:**
1. **Kenny:** decide stage 2's 10 blocking items (A3). In every one, XBRL (the answer key) is the side that differs from the standard definition:
   - **Oracle opex FY2022–FY2026 (5):** Oracle tags no cost of revenue in XBRL, so XBRL's "opex" is all costs. Ours subtracts the delivery costs, as standard tools do.
   - **APLD opex FY2026:** XBRL counts only "services cost of revenue" and misses the $56.8M data-center line.
   - **APLD revenue and opex FY2024–FY2025 (4):** the newest 10-K presents these years differently from XBRL, which mixes two filings (its FY2025 opex is −$0.4M).
2. **Kenny:** confirm the cost lines on the `cost_lines_summed` cards, decide the other warnings, hand-check `reports/stage2-validation.html`, then release and sign `v0.2.0` (due 6 Nov).
3. The rest is in [docs/TICKETS.md](docs/TICKETS.md).

**Critical notes:**
- **Dashes are zero.** APLD's newest 10-K shows "—" for its data-center cost line in FY2024 and FY2025; agents read these as 0.
- **NVDA's capex line includes intangible assets.** Note it when comparing companies.
- **Known blind spot:** a wrong-row misread is caught by comparing a company's filings with each other, so a company's first filing is less protected.
- **Running agents:** extraction runs as Claude Code subagents inside the session (no paid API). Headless runs need `claude login`.
- **Old work is in tags:**
  - `takehome-xbrl-explorer`: the 113-company explorer
  - `quarterly-v0.1`: the quarterly pipeline

## How it works

| Step | Command | Produces |
|---|---|---|
| Ingest | `ingest` | 10-Ks fetched and cached with SHA-256; tables parsed; statements located |
| Extract | `extract --pack`, then agents, then `extract --load` | One task per 10-K (tables only, no XBRL); agent values with citations, each checked against the cell |
| Reconcile | `reconcile` | Fiscal-year values with their basis and first-reported figure, compared with XBRL |
| Rules | `rules` | Exceptions from the 14 rules in `rules/*.yaml` |
| Faults | `faults` | Every cell corrupted in typical ways, and what caught each |
| Report | `report` | `reports/stage<N>-validation.html`: plain-language review page and hand-check |
| Review | `review`, `review decide` | `decisions/decisions.jsonl`; a decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`; refuses while any gate fails, and the same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` |

Every command runs as `uv run python -m ledger <command> --stage N`. The XBRL reference is pulled with `python -m ledger reference`.

## Repo

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, 10-K list, table parser, statement locator |
| `ledger/extract.py`, `reconcile.py` | Tasks and citation checks; fiscal-year values |
| `ledger/rules.py`, `rules/` | Rule engine and the 14 rules |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | XBRL reference pipeline (output: `data/clean/facts.csv`) |
| `agents/` | Prompt and output schema |
| `data/extract/outputs/` | Agent outputs, kept as evidence |
| `docs/` | [PRD](docs/PRD.md), [tickets](docs/TICKETS.md), [fields](docs/FIELDS.md) |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
