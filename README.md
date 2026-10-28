# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026, evening):** audit, Insights, client packet, the scale run to 31 companies, and `v1.1.0` signed.
- **Audit fixes:** a prompt edit is saved as the next version and switched on as a second, logged step; the name you sign with lives once in the nav; the release tile shows the exact commands; every question says why code can't decide it.
- **Insights** (`#insights`): on signed data only. Who pays (buyers' capex) and who gets paid (sellers' revenue), FY2022 → FY2025, and every company's capex, revenue and intensity. Each company in `config.AI_SET` and `data/companies.json` carries a role.
- **Client packet:** every release now builds a `README.md` next to `values.csv`, `DATA_DICTIONARY.md` and `QUALITY.md`; DATAHQ serves a signed release as one zip at `/packet/<version>.zip` (Outputs page).
- **Scale run:** 12 companies added from DATAHQ (AAPL, AVGO, INTC, QCOM, TXN, CSCO, IBM, WMT, XOM, JPM, ANET, and Compass by Kenny): 31 tracked. Full run on all 31 with parser `tables@9`: 132 filings, 384 values, 354 agree with the SEC's data, 26 more explained by code (16 the 10-K doesn't report, 10 definition gaps), 1,431 of 1,431 cited cells confirmed on the rendered 10-K, 0 of 7,075 planted faults through. Eight new failure types (16–23) in `docs/INGESTION.md`; seven fixed in code, one is a definition only a person can confirm.

**Released:** `v1.1.0`, all 31 tracked companies (30 with a 10-K), 384 values, signed by Kenny Geiler, hash 794fb2dfadae. 14 decisions applied: the 8 above (four cost-line confirmations, ExxonMobil's revenue definition for four years) plus six earlier. DATAHQ serves it as `/packet/v1.1.0.zip`.

**Next:** the demo goal is met: a working pipeline with oversight. Optional, only if needed:
1. M3.1: one question per cause (XOM shows why).
2. Schedule `ledger watch --run` daily (cron or launchd).
3. Prompt `statements@v3` (v2 still explains quarterly columns; needs an agent rerun).

**Critical notes:**
- **Dashes are zero.** APLD's newest 10-K shows "—" for its data-center cost line in FY2024 and FY2025; agents read these as 0.
- **NVDA's capex line includes intangible assets.** Note it when comparing companies.
- **Known blind spot:** a wrong-row misread is caught by comparing a company's filings with each other, so a company's first filing is less protected.
- **Running agents:** `ledger run` and the app's Add company run the agent headless on Kenny's subscription (no paid API). It needs a logged-in `claude` (run `claude`, then `/login`) of version 2.1.280 or later for Opus 5.5. Until the installed one is upgraded, set `LEDGER_CLAUDE` to the desktop app's newer `claude` before `ledger run` and before `ledger app`.
- **A parser bump re-opens decisions.** Every value's input hash includes the parser version, so after `tables@9` every earlier decision is superseded and the open list is rebuilt from the rules; that is why the APLD recast decisions are gone and the cost-line confirmations are back.
- **Banks and oil majors come out partly blank on purpose.** JPMorgan has no capex or operating income line; IBM and ExxonMobil have no operating income line, so opex can't be computed. Those are `not_reported` rows with the reason, not errors.
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
| Watch | `watch [--run]` | `data/watch.json`: 10-Ks and 10-K/As at the SEC the ledger hasn't read; `--run` reads them |
| App | `app` | DATAHQ at http://127.0.0.1:3610 (start it with `LEDGER_CLAUDE` set, so Add company can run the agent): dashboard, each company through every step, the agents (model, prompt versions, every run), outputs explorer with CSV export |

Every command runs as `uv run python -m ledger <command> --stage N` or `--ticker X Y` (release and signoff take a stage). `evidence` drives the installed Google Chrome through Playwright, with no browser download.

## Repo

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, 10-K list, table parser, statement locator, restatement-note finder |
| `ledger/agent.py`, `extract.py`, `reconcile.py` | Headless agent; tasks and citation checks; fiscal-year values |
| `agents/agents.json`, `agents/prompts/`, `ledger/agents.py` | The named agents: model, active prompt, change history; a prompt change is saved as a new version |
| `ledger/app.py`, `app.html`, `hq.py` | DATAHQ web app (read-only on the database) and its numbers |
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
