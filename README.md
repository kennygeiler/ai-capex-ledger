# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** M2 blind run 1. The 13 unseen companies ran with one command and nobody in the loop, with the pipeline frozen at tag `m2-frozen`.
- **Agent and values:** 26 10-Ks read headless (about 9 agent-minutes, 1 retry). 143 of 145 values agree with XBRL, and 0 of 1,555 planted faults escaped.
- **Clean on the first pass:** 6 companies (AMZN, GOOGL, META, MRVL, MU, TSLA).
- **Failures:** 6 types, listed in [docs/INGESTION.md](docs/INGESTION.md). Type 1, the rendered-page re-read on Workiva layouts, is fixed: 311 of 311 cells confirmed.
- **Also:** the coverage rule no longer flags a fiscal year whose 10-K isn't due yet.

**Next:**
1. **Claude (M2.2):** fix types 2–6, each as a type:
   - the locator prefers fiscal-year statements
   - the reference prefers total `Revenues`
   - the statement tie counts operating lines outside the opex block
   - fetch 10-Ks from 2022, and label years before a company's first 10-K
   - name any company with no 10-K
   
   Then rerun all 19 companies until a full rerun needs no code change.
2. **Kenny (optional):** upgrade the installed Claude Code, so that `LEDGER_CLAUDE` isn't needed.

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
| Ingest | `ingest` | 10-Ks fetched and cached with SHA-256; tables parsed; statements located |
| Extract | `extract --pack`, then agents, then `extract --load` | One task per 10-K (tables only, no XBRL); agent values with citations, each checked against the cell |
| Reconcile | `reconcile` | Fiscal-year values with their basis and first-reported figure, compared with XBRL |
| Rules | `rules` | Exceptions from the 14 rules in `rules/*.yaml` |
| Faults | `faults` | Every cell corrupted in typical ways, and what caught each |
| Evidence | `evidence` | Every cited cell re-read on the 10-K rendered in Chrome; boxed screenshots in `reports/evidence/` (`--faults` proves it notices moved citations) |
| Report | `report` | `reports/stage<N>-validation.html`: plain-language review page and hand-check |
| Review | `review`, `review decide` | `decisions/decisions.jsonl`; a decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`; refuses while any gate fails, and the same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` |

Every command runs as `uv run python -m ledger <command> --stage N` or `--ticker X Y`. `evidence` drives the installed Google Chrome through Playwright, with no browser download. The XBRL reference is pulled with `python -m ledger reference`.

## Repo

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, 10-K list, table parser, statement locator, restatement-note finder |
| `ledger/extract.py`, `reconcile.py` | Tasks and citation checks; fiscal-year values |
| `ledger/rules.py`, `rules/` | Rule engine and the 14 rules |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | XBRL reference pipeline (output: `data/clean/facts.csv`) |
| `agents/` | Prompt and output schema |
| `data/extract/outputs/` | Agent outputs, kept as evidence |
| `docs/` | [PRD](docs/PRD.md), [tickets](docs/TICKETS.md), [fields](docs/FIELDS.md), [ingestion and learnings](docs/INGESTION.md) |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
