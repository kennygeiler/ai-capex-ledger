# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

New here, person or agent? Read [docs/HANDOFF.md](docs/HANDOFF.md) first: what a clone contains, setup, the objects and where each lives, how to do the common things, the rules of the house.

## Status

*Updated with every commit. The diary of earlier entries is in `docs/archive/README-status-diary.md`.*

**Last done (1 Nov 2026):** the consolidation. The frame is `docs/PROOF.md`: the pipeline proves every number it produces, on the proven set first (`config.PROVEN`: Microsoft, Alphabet, Amazon, Nvidia, Applied Digital, AMD; six of six proven, golden test equal). Every exported row carries `proven`, `status` and `flag`. Judgement lives in two places: `definitions/` (a person edits) and `decisions/` (the two append-only logs the app writes). DATAHQ is six pages: Proof, a company's trail, Rules (with the theses and the readers), Reconcile, Dataset, Explore; the rest is gone, `ledger/app.html` 904 lines from 1,414. Docs are PROOF (the spec), INGESTION (the failure log, 72 types), API (the contract), FIELDS, COMPANIES, DATA_DICTIONARY, HANDOFF (the start page); the rest is archived under `docs/archive/`. v1.6.0 is signed and published; the next release carries `proven`.

**Next:**
0. Kenny reads `docs/TAXONOMY.md` and `taxonomy/taxonomy.yaml` (draft, unwired): every category from a named standard, the inferred AI-share methods listed for removal, three questions at the end. Then wire: category ids on rows, remap the six, verification flags on committed and planned.
1. Widen the proven set one company at a time (Micron, Tesla, Iron Mountain, Equinix), golden green at each step. Nothing runs across 100 until then.
2. Put "unreferenced" on the Proof board as its own column; grow the reference set with a sourced, scoped figure per proven company-year.
3. Kenny confirms the replication decisions (`decisions/resolutions.jsonl`) and the four thesis switches, all marked for him.
4. Send to Arctal: the repo, the v1.6.0 packet, DATAHQ, `DATABASE_READONLY_URL`.

**Critical notes:**
- Never sign a release without Kenny's explicit OK for that release. Never run agents on a paid API; `claude -p` on the subscription (`LEDGER_CLAUDE`).
- `ledger golden --check` before any commit that touches a parser, a rule, a loader or a thesis; `--freeze` only on purpose, in a commit that says why.
- A code guard needs its thesis to say the same thing, or the attributor keeps answering the old way and a failed run empties the company.
- `.env` holds `SEC_USER_AGENT`, `DATABASE_URL` (owner, publish only) and `DATABASE_READONLY_URL` (the one to hand out); never committed.
- Release files are LF, hashed before the write, read back byte-exact; `publish` adds a release's new columns to existing tables.
- Theses and prompts are versioned, never edited in place; dry-run on the company before the switch.
- Dashes are zero; NVDA's capex includes intangibles; banks and oil majors are partly blank on purpose; old work is in tags (`takehome-xbrl-explorer`, `quarterly-v0.1`).

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
| Rules | `rules` | Exceptions from the 16 rules in `rules/*.yaml` |
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
| `ledger/texts.py`, `sources/ir.yaml` | The text registry: MD&A, 8-K releases, investor-page PDFs; the links a person listed |
| `ledger/guidance.py` | AI spend from the texts: passages, the quote contract, table B |
| `ledger/attribution.py`, `agents/models/` | The attributor's data pack, contract and arithmetic; the six money-flow models, versioned |
| `ledger/evaluation.py`, `gold/ai_capex.yaml` | The reference set of sourced AI-capex figures and the scoring against it |
| `ledger/notes.py`, `reference/dimensions.py` | Facts from the notes: candidate tables, the cell contract, table B; the filing's XBRL instance with segment and category members as the answer key |
| `ledger/steps.py`, `ledger/progress.py` | The pipeline's step list; what a run is doing, for DATAHQ's Add page |
| `airflow/dags/capex_ledger.py` | The same steps as an Airflow DAG (one `BashOperator` each); Airflow is not a dependency, point one at this folder |
| `agents/agents.json`, `agents/prompts/`, `ledger/agents.py` | The named agents: model, active prompt, change history; a prompt change is saved as a new version |
| `ledger/app.py`, `app.html`, `proof.py`, `golden.py` | DATAHQ: Proof, a company's trail, Rules, Reconcile, Dataset, Explore; the proof model and the golden test (`docs/PROOF.md`) |
| `ledger/rules.py`, `rules/` | Rule engine and the 16 rules |
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
