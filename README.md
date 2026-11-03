# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

Looking for where something lives? [docs/MAP.md](docs/MAP.md). New here, person or agent? Read [docs/HANDOFF.md](docs/HANDOFF.md) first: what a clone contains, setup, the objects and where each lives, how to do the common things, the rules of the house.

Building a ticket? [docs/BUILD.md](docs/BUILD.md): the pre-mortem against eight failure patterns, the claims register, and the builder and reviewer briefs. What is not yet true is on the Gaps page and in [docs/CLAIMS.md](docs/CLAIMS.md).

## How it works

| Step | Command | Produces |
|---|---|---|
| Run | `run --ticker X` | All steps below for any tickers, agent included, then the scorecard |
| Ingest | `ingest` | 10-Ks from FY2022 on, fetched and cached with SHA-256; tables parsed; statements located; the XBRL answer key built for each company |
| Extract | `extract --run`, then `extract --load` | One task per 10-K (tables only, no XBRL); the headless agent's values with citations, each checked against the cell |
| Reconcile | `reconcile` | Fiscal-year values with their basis and first-reported figure, compared with XBRL |
| Notes | `notes --run`, then `notes --load` | Facts from the notes for attribution: capex and revenue per segment, PP&E by category, finance lease liabilities, purchase commitments; a third agent over candidate note tables, every cell resolved; table A `note_extractions`, table B `facts`, checked against the filing's own XBRL instance where the member is tagged |
| Texts | `texts` | Every text the AI spend reader reads, in the `texts` table with the fiscal period each speaks to: each 10-K's MD&A (Item 7 via `edgartools`), each 8-K earnings release (Exhibit 99.1), and the transcripts and CFO commentary a company's investor page offers, from PDF links a person lists in `sources/ir.yaml` (free; the pages sit behind a bot check that code does not get around, the PDFs download directly) |
| AI spend | `aispend --run`, then `aispend --load` | What every text says about AI's part of capex and opex: the AI spend reader over the passages that mention AI next to spending, every statement a verbatim quote checked against its passage; table A `ai_statements`, table B `ai_spend` (most specific statement wins, newest text breaks ties, `source` says where it came from) |
| Attribution | `attribution --run`, then `attribution --load` | AI's part of capex and opex per company and fiscal year: the attributor reads the industry's money-flow model (`agents/models/`) and the company's data pack, names every input, and code recomputes each number by the method's arithmetic; table `attribution`, `attribution.csv` in releases, a diff on every load |
| Evaluate | `eval` | The attribution against the reference set `gold/ai_capex.yaml`: coverage, agreement, error band per method; `reports/EVALUATION.md` |
| Rules | `rules` | Exceptions from the 20 rules in `rules/*.yaml` |
| Faults | `faults` | Every cell corrupted in typical ways, and what caught each |
| Evidence | `evidence` | Every cited cell re-read on the 10-K rendered in Chrome; boxed screenshots in `reports/evidence/` (`--faults` proves it notices moved citations) |
| Report | `report` | `reports/<name>-validation.html` (`stage2`, `AMD`): plain-language review page, scorecard and checks |
| Review | `review`, `review decide` | `decisions/decisions.jsonl`; a decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`; refuses while any gate fails, and the same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` |
| Watch | `watch [--run]` | `data/watch.json`: 10-Ks and 10-K/As at the SEC the ledger hasn't read; `--run` reads them |
| App | `app` | Kenny's Data Emporium at http://127.0.0.1:3610 (start it with `LEDGER_CLAUDE` set, so Add company can run the agent): dashboard, each company through every step, the agents (model, prompt versions, every run), outputs explorer with CSV export |

Every command runs as `uv run python -m ledger <command> --stage N` or `--ticker X Y` (release and signoff take a stage). `evidence` drives the installed Google Chrome through Playwright, with no browser download.

## Repo

Where everything lives, and what to edit for the common changes: [docs/MAP.md](docs/MAP.md).

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
