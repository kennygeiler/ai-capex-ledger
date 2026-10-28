# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** `v1.0.1` released and signed by Kenny Geiler, hash 6d10c2b1990f. Same 234 values as `v1.0.0`; the `restated` rule now compares cost lines (`cost_of_revenue_part`) line by line, so 10 false restatement notes (7 ORCL, 3 APLD) are gone.
- Earlier today: DATAHQ dashboard (https://claude.ai/artifact/Eap67fDB2Vs85qsGmY12tw, `scripts/datahq.py`); `v1.0.0` signed.

**Next:**
1. **Claude:** new-filing watcher: check SEC daily for new 10-Ks, run `ledger run` on them, refresh DATAHQ.
2. **Claude (M3):** group review items by cause, so that one decision covers all of them, and make the hand-check file name match `release` for ticker runs.
3. **Later:** `DIFF.md` lists added values; prompt `statements@v3` (v2 still explains quarterly columns; needs an agent rerun).

**Critical notes:**
- **Dashes are zero.** APLD's newest 10-K shows "—" for its data-center cost line in FY2024 and FY2025; agents read these as 0.
- **NVDA's capex line includes intangible assets.** Note it when comparing companies.
- **Known blind spot:** a wrong-row misread is caught by comparing a company's filings with each other, so a company's first filing is less protected.
- **Running agents:** `ledger run` runs the agent headless on Kenny's subscription (no paid API). It needs a logged-in `claude` (run `claude`, then `/login`) of version 2.1.280 or later for Opus 5.5. Until the installed one is upgraded, set `LEDGER_CLAUDE` to the desktop app's newer `claude`.
- **Old work is in tags:**
  - `takehome-xbrl-explorer`: the 113-company explorer
  - `quarterly-v0.1`: the quarterly pipeline

## How it works

| Step | Command | Produces |
|---|---|---|
| Run | `run --ticker X` | All steps below for any tickers, agent included, then the scorecard |
| Ingest | `ingest` | 10-Ks from FY2022 on, fetched and cached with SHA-256; tables parsed; statements located; the XBRL answer key built for each company |
| Extract | `extract --run`, then `extract --load` | One task per 10-K (tables only, no XBRL); the headless agent's values with citations, each checked against the cell |
| Reconcile | `reconcile` | Fiscal-year values with their basis and first-reported figure, compared with XBRL |
| Rules | `rules` | Exceptions from the 15 rules in `rules/*.yaml` |
| Faults | `faults` | Every cell corrupted in typical ways, and what caught each |
| Evidence | `evidence` | Every cited cell re-read on the 10-K rendered in Chrome; boxed screenshots in `reports/evidence/` (`--faults` proves it notices moved citations) |
| Report | `report` | `reports/<name>-validation.html` (`stage2`, `AMD`): plain-language review page, scorecard and checks |
| Review | `review`, `review decide` | `decisions/decisions.jsonl`; a decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`; refuses while any gate fails, and the same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` |

Every command runs as `uv run python -m ledger <command> --stage N` or `--ticker X Y` (release and signoff take a stage). `evidence` drives the installed Google Chrome through Playwright, with no browser download.

## Repo

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, 10-K list, table parser, statement locator, restatement-note finder |
| `ledger/agent.py`, `extract.py`, `reconcile.py` | Headless agent; tasks and citation checks; fiscal-year values |
| `ledger/rules.py`, `rules/` | Rule engine and the 15 rules |
| `ledger/evidence.py`, `scorecard.py` | Rendered-10-K re-read with boxed screenshots; what each company cost |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | The XBRL answer key, built per company from cached SEC data |
| `agents/` | Prompt and output schema |
| `data/extract/outputs/` | Agent outputs, kept as evidence |
| `reports/`, `decisions/`, `golden/`, `releases/` | Validation pages and screenshots; review decisions; hand-checks; signed releases |
| `scripts/` | Measurements: cell accuracy vs XBRL, rerun agreement, locator accuracy |
| `docs/` | [PRD](docs/PRD.md), [tickets](docs/TICKETS.md), [fields](docs/FIELDS.md), [ingestion and learnings](docs/INGESTION.md) |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
