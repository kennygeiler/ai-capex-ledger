# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

New here, person or agent? Read [docs/HANDOFF.md](docs/HANDOFF.md) first: what a clone contains, setup, the objects and where each lives, how to do the common things, the rules of the house.

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

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, 10-K list, table parser, statement locator, restatement-note finder |
| `ledger/agent.py`, `extract.py`, `reconcile.py` | Headless agent; tasks and citation checks; fiscal-year values |
| `ledger/texts.py`, `sources/ir.yaml` | The text registry: MD&A, 8-K releases, investor-page PDFs; the links a person listed |
| `ledger/guidance.py` | AI spend from the texts: passages, the quote contract, table B |
| `ledger/attribution.py`, `agents/models/` | The attributor's data pack, contract and arithmetic; the six money-flow models, versioned |
| `ledger/evaluation.py`, `gold/ai_capex.yaml` | The reference set of sourced AI-capex figures and the scoring against it |
| `ledger/notes.py`, `reference/dimensions.py` | Facts from the notes: candidate tables, the cell contract, table B; the filing's XBRL instance with segment and category members as the answer key |
| `ledger/steps.py`, `ledger/progress.py` | The pipeline's step list; what a run is doing, for Kenny's Data Emporium's Add page |
| `airflow/dags/capex_ledger.py` | The same steps as an Airflow DAG (one `BashOperator` each); Airflow is not a dependency, point one at this folder |
| `agents/agents.json`, `agents/prompts/`, `ledger/agents.py` | The named agents: model, active prompt, change history; a prompt change is saved as a new version |
| `ledger/app.py`, `app.html`, `proof.py`, `golden.py` | Kenny's Data Emporium: Proof, a company's trail, Rules, Reconcile, Dataset, Explore; the proof model and the golden test (`docs/PROOF.md`) |
| `ledger/rules.py`, `rules/` | Rule engine and the 20 rules (T92: three ties on the note figures and `fact_readings_differ`, `ledger/ties.py`) |
| `ledger/evidence.py`, `scorecard.py` | Rendered-10-K re-read with boxed screenshots; what each company cost |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | The XBRL answer key, built per company from cached SEC data |
| `agents/` | Prompt and output schema |
| `data/extract/outputs/`, `data/notes/outputs/`, `data/aispend/outputs/` | Agent outputs, kept as evidence; `data/text/` holds each filing's MD&A |
| `reports/`, `decisions/`, `golden/`, `releases/` | Validation pages and screenshots; review decisions; hand-checks; signed releases |
| `scripts/` | Measurements: cell accuracy vs XBRL, rerun agreement, locator accuracy |
| `docs/` | [PRD](docs/archive/PRD.md), [tickets](docs/archive/TICKETS.md), [fields](docs/FIELDS.md), [ingestion and learnings](docs/INGESTION.md) |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
