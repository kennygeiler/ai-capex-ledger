# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** The machine now checks citations itself. `ledger evidence` opens each 10-K in headless Chrome as a person would see it, finds the cited row and column by position on the page (not through our parser), and compares the text. It also saves a screenshot with the cell boxed.
- **Stage 2:** 173 of 173 cited cells confirmed, and 708 of 708 deliberately moved citations noticed. All 20 checks on the page are machine-confirmed, so none need Kenny. Each card can show the boxed screenshots.
- **G5** now accepts a machine confirmation. A person answers only the cards the machine can't confirm, with the screenshot showing exactly where to look.
- **All release gates pass for `v0.2.0`.** It is not built or signed yet.

**Next:**
1. **Kenny:** skim `reports/stage2-validation.html` (open "Show where" on any card), then say "release and sign v0.2.0".
2. **Kenny (M1.1):** run `claude login` once in a terminal.
3. **Claude (M1.2–M1.4):** headless extraction, `ledger run --ticker X`, scorecard; `ledger run` will include `evidence`.

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
| Evidence | `evidence` | Every cited cell re-read on the 10-K rendered in Chrome; boxed screenshots in `reports/evidence/` (`--faults` proves it notices moved citations) |
| Report | `report` | `reports/stage<N>-validation.html`: plain-language review page and hand-check |
| Review | `review`, `review decide` | `decisions/decisions.jsonl`; a decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`; refuses while any gate fails, and the same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` |

Every command runs as `uv run python -m ledger <command> --stage N`. `evidence` drives the installed Google Chrome through Playwright, with no browser download. The XBRL reference is pulled with `python -m ledger reference`.

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
