# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** M2 is done. All 19 companies run with one command and need nothing from a person, and the repo was cleaned.
- **Fixes by type** after blind run 1 (types 2–6 in [docs/INGESTION.md](docs/INGESTION.md)), then a full rerun of all 19 (`ledger run --stage 3`):
  - 72 10-Ks; 234 values, 224 agree with XBRL, 6 explained by code, 4 already decided by Kenny.
  - 857 of 857 cited cells confirmed on the rendered 10-K.
  - 0 of 4,270 planted faults escaped; 3,104 of 3,104 moved citations noticed.
  - 0 items open for a person. SpaceX is named as having no 10-K yet.
  - The rerun surfaced 2 more types (a zero-width space in one filing, and Oracle repeating a row label), both fixed.
- **Cleanup:** the XBRL answer key is now built per company, on demand, from cached SEC data, with the same 312 values. This removed the 113-company batch job, its quarterly code and the 19 MB `facts.csv`. Also removed: the unused `extract --find` experiment, dead helpers and old ticket numbers.
- `v0.1.0` and `v0.2.0` stay signed.

**Next:**
1. **Kenny:** decide whether to release `v1.0.0` (all 19), using the stage 3 page `reports/stage3-validation.html`. The 4 APLD decisions carry over; there are 57 warnings, no blocks.
2. **Claude (M3):** group review items by cause, so that one decision covers all of them, and make the hand-check file name match `release` for ticker runs.
3. **Later:** prompt `statements@v3` (v2 still explains quarterly columns, which a 10-K-only pipeline doesn't need). Changing it means rerunning the agent.

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
