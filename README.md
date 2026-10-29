# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

New here, person or agent? Read [docs/HANDOFF.md](docs/HANDOFF.md) first: what a clone contains, setup, the objects and where each lives, how to do the common things, the rules of the house.

## Status

*Updated with every commit.*

**Last done (29 Oct 2026, end):** DATAHQ home is the job, not the grid (`docs/FLOW.md`). After Kenny said the flow didn't match what the product is for, and an independent product review of the spec, home is now a queue of issues for a scope (all, an industry, a company): what is blocked, what disagrees with a reference or a tag, what is new at the SEC, what moved since the last release; each row says what it touches downstream and carries the action that resolves it (run, add a definition, open the model, release). Four stages across the top as context, ending at Release: what blocks it, the diff against the last signed release, a drafted change note and the commands. The grid is the Dataset tab, for the consumer. `/api/flow?scope=` serves it. A second independent review of the built screen led to: the queue ranked by dollars at stake with a new-since-release flag, noise collapsed, resolutions persisted (`data/resolutions.jsonl`: accept, explain, fix, blocks) and read by the release line, and a drawer that shows the cell, the tag, the delta, the affected attributions and the resolution controls. A model edit can be dry-run before it is switched on: `ledger attribution --ticker … --run --model-version hyperscaler@v3 --dry-run` (or Dry Run in the model drawer) runs the saved version against its industry and reports which rows would change and how the reference check would move, writing nothing to the table. A definition dry run is still open.

**Before that (29 Oct, last):** DATAHQ as a dataset console, designed from what Arctal does (five people turning filings into source-linked, taxonomy-structured datasets covering spending that has happened, is committed or is planned, distributed through S&P Global Sustainable1; `docs/DATAHQ.md`). One Data screen: a status strip (entities, values agreeing, facts, cells confirmed, faults, reference agreement, blocked); a filter bar (entities by industry, field, kind: spent / committed / planned, saved views); the grid (entities down, years across, shaded, cells that moved since the last run outlined); a provenance panel one click deep (value, method, inputs, XBRL, model and prompt versions, the cell and its screenshot, the filing); a chart of the selection; CSV export with provenance columns. The URL carries the selection. `/api/data` serves the dataset in long format. Pipeline, Insights and the company page folded into it; Add a company under `#run`. Visuals follow the data products analysts already use (Daloopa, Calcbench, the terminals): a top bar with a ticker search, dense sticky tables, a details drawer. The Attribution screen in the same style: the grid grouped by industry with a method badge per cell; the badge opens the industry's model in the panel (versions, edit, save, use, rerun); what changed in the last load and the change log as tables.

**Before that (29 Oct, latest):** DATAHQ data first. Every page opens on numbers and shapes: a coverage heat grid on Pipeline, the shaded AI-capex grid first on Attribution, four charts and an evaluation dot plot on Insights, a six-number strip and capex-with-AI-part bars on the company page. Prose cut to one-line captions (`docs/DATAHQ.md`, "Data first"). `v1.4.0` built, unsigned.

**Before that (29 Oct):** a measured error. The role inside a firm owns a number others act on, so the number needs a reference set and an error band, not an agent's confidence.
- **Reference set** `gold/ai_capex.yaml`: sourced figures for AI's part of capex (what the company said on a call, or an independent estimate), each with URL, quote, date and a line on what it measures. Six entries so far, all company statements; add one whenever a sourced figure turns up, never from memory.
- **`ledger eval`** (in `ledger run` after attribution): scores every attribution row against the set: coverage, agreement within 10%, error on entries that state a figure, by method. `reports/EVALUATION.md`, `EVALUATION.md` in every release, a QUALITY line, and "How wrong is it" on the Insights tab.
- **Result:** we have a number for 5 of 6; 2 agree (Oracle, Amazon), 3 disagree (Microsoft 61% vs at most half; Alphabet FY2025 68% vs 60% stated, FY2024 56% vs a ≥90% floor that measures all technical infrastructure); Tesla has no estimate. Server-category growth overstates the server share because the category includes finance-lease assets and software (type 46); the error is now stated beside the number.
- **Alphabet fixed** (type 45): it renamed its PP&E categories in the FY2024 10-K and the notes reader never saw the table; the candidate words now include the new names, hyperscaler model `@v2` bridges the rename, and Alphabet has FY2024–25 attributions. 1,448 facts, 217 attribution rows, 40 with an AI amount.

**Before that (29 Oct, night):** step five: DATAHQ rebuilt around the three layers, after a design audit (`docs/DATAHQ.md`).
- **Three tabs.** Pipeline (home): what was ingested and cleaned with nobody in the loop; figures for companies, texts, values, facts, cells confirmed, faults, blocked; a coverage-by-layer table per company; findings; add a company inline. Attribution: the six money-flow models with an editor (save as the next version, switch on, both logged), a "Rerun" per industry or for every company that runs the attributor in the background and shows the diff, and the AI-capex grid by company and year with the method under each number. Insights: from the live tables (labelled against the signed release): buyers' AI capex against their total capex by year, AI capex per company with the method named, sellers' data-center revenue beside buyers' AI capex, the method mix.
- **Company page** reordered: the attribution first, then what the company said, the facts, the numbers and their cleaning, the filings, every check.
- **Removed:** the dead question cards and accept control, the Outputs page (the packet download lives under Releases), the Dashboard. The readers' prompts stay under `#agents`.
- API: `/api/attribution`, `/api/insights` (live), `POST /api/models/<industry>/save|use`, `POST /api/attribute`.

**Before that (29 Oct, later):** step four of the plan: the attribution layer.
- **Money-flow models**, one per industry in `agents/models/` (hyperscaler, neocloud, miner-to-HPC, chip seller, component supplier, other), each saying where AI money shows up for that kind of business, which methods are allowed in order of hardness, and the traps. Versioned like prompts; `agents.json` names the version in use per industry; `config.INDUSTRIES` maps companies to models.
- **The attributor** (`ledger attribution`, in `ledger run` after `notes`): one task per company (the model plus the data pack: values, facts, what the company said). Output rows carry the method, the amount, every input by id and a basis in words; code looks the inputs up and recomputes the amount (a stated share × capex, a sum of segment capex, a category's year-on-year growth, the whole business). Editing a model reruns only that industry; `--load` writes `data/attribution/diff.json`.
- **Numbers:** all 31 companies (29 with values): 223 rows, 38 with an AI dollar amount (9 companies: the five hyperscalers by server-category growth, CoreWeave whole-business, Applied Digital and Core Scientific by segment, IREN by stated amounts); by method 118 none, 67 words only, 22 server-category growth, 6 whole business, 6 stated amount, 4 segment; 0 failed, 0 retries, 9.4 agent minutes, 330k tokens. Microsoft FY2026: 83.0B of 115.9B capex (72%) by that method; Meta FY2025 29.6B (43%); Amazon FY2025 59.3B (45%). Three warnings where segment capex (accrual) exceeds cash capex, explained in the basis. Types 41–43 in `docs/INGESTION.md`.
- **Shipped with it:** `attribution.csv` in every release with a README section; the company page section "AI attribution" (method, amount, share, confidence; click for the basis and inputs); `ai_amount_within_capex` also checks attributed amounts.

**Before that (29 Oct):** step three of the plan: more sources for AI spend.
- **`ledger texts`** (in `ledger run`, before `aispend`): one registry of every text the AI spend reader reads, with the fiscal period each speaks to. Three kinds beyond the 10-K MD&A: 8-K earnings releases (Exhibit 99.1, every Item 2.02 8-K since FY2022, through `edgartools`), earnings-call transcripts and CFO commentary from the company's investor page (`sources/ir.yaml`: Meta's 19 transcripts, Nvidia's current year so far; add a company by listing its PDF links). Investor pages sit behind a bot check; code does not render them, a person lists the links from their own browser, and the PDFs download directly and are read with `pypdf`. No paid transcript source.
- **`aispend` reads every text**, not just the MD&A; `ai_statements` and `ai_spend` carry `text_id` and `source`; the most specific statement wins across sources, newest text breaks ties. `ai_spend.csv` has a `source` column.
- **Numbers:** all 31 companies, 702 texts (124 MD&A, 555 earnings releases, 21 transcripts, 2 CFO commentaries); 543 asked, 159 had no passage; 244 statements (105 from releases, 82 MD&A, 57 transcripts), 83 AI-spend rows for 17 companies, 8 with an AI dollar amount (IREN, Core Scientific, Applied Digital, Tesla), 21 explicit totals, 62 words only; 0 failed, 0 retries; 65 agent minutes, 4.1M tokens. Transcripts added words, not numbers: Meta's calls give total-capex guidance, not an AI share. Types 35–40 in `docs/INGESTION.md`.

**Before that (29 Oct, night):** step two of the plan: the facts attribution needs.
- **`ledger notes`** (in `ledger run`, after `aispend`): a third agent (`notes_reader`, prompt `notes@v2`) reads each 10-K's segment, property-and-equipment, lease and commitments tables and cites every cell: capex and revenue per segment, PP&E gross by category, total finance lease liabilities, purchase commitments. Table A `note_extractions`, table B `facts` (per company, field, segment or category, fiscal year; newest filing wins). The check is the filing's own XBRL instance read directly (`reference/dimensions.py`), members matched by name; an untagged fact is `no_reference`, stated as such. `facts.csv` ships in every release; the company page shows "Facts from the notes".
- **Numbers:** all 31 companies, 124 filings: 2,346 cited cells, 1,436 facts (97 segment capex, 550 segment revenue, 699 PP&E categories, 28 finance lease liabilities, 42 purchase commitments); 522 agree with the filing's own tags, 27 differ, 887 untagged (segment capex and most PP&E categories carry no us-gaap member); 0 filings failed; 70 agent minutes, 1.88M tokens, 20 retries. Types 28–34 in `docs/INGESTION.md` (unit fallback, answer-key vintage, column labels, trailing text, untagged segment capex, capex in parentheses, purchase-commitment definitions).
- **Also:** the agent-running steps release the database before the agent runs, so DATAHQ is not "busy" for ten minutes.

**Before that (29 Oct, later):** no more questions for a person. The direction agreed with Kenny: ingest and clean with nobody in the loop, then an attribution agent whose method he edits, then insights.
- **Definitions replace decisions.** `definitions/companies.yaml` holds the judgements made once per company (ExxonMobil's revenue line vs the SEC's wider tag; the cost lines for Oracle, Applied Digital, ExxonMobil, Compass), each with who and why. `reconcile` labels a defined revenue gap `definition_gap`; `cost_lines_summed` stays quiet while the agent's lines are all named. Stage 3 now: 0 block, 0 unresolved (384 values: 354 agree, 14 definition gaps, 16 not reported).
- **Warnings are findings.** A big move, an outlier or a renamed line is a finding about the company with an "SEC data" column: agrees, or can't confirm. Nothing waits on a person except signing. Coverage rests on three legs: the cited cell re-read on the rendered 10-K, XBRL agreement, planted faults. 93 findings on the dashboard, 1 the SEC's data can't confirm.
- `review decide` and the accept-warnings endpoint still exist for overrides and rejects; a definition is the right fix for anything that would be accepted twice.

**Before that (29 Oct):** AI spend from the MD&A, the question behind the ledger.
- **`ledger aispend`** (in `ledger run`, after reconcile): a second agent (`ai_reader`, prompt `aispend@v2`) reads each 10-K's Item 7 passages that mention AI next to capital or operating spending and returns every statement as a verbatim quote; code checks the quote is in the passage. Table A `ai_statements`, table B `ai_spend` (per company, field, fiscal year and kind, the most specific statement from the newest filing). Item 7 comes through `edgartools` (`data/text/`); the table parser is untouched.
- **The finding, honestly:** on all 31 companies, 79 statements, 54 company-year rows, 3 with an AI dollar amount (all IREN). Hyperscalers say "primarily" and "the majority"; the only numbers are total-capex outlooks (Meta $115–135B for 2026, Tesla >$20B), filed as `scope: total`, not AI spend. The explicit AI numbers live in earnings releases (8-K Exhibit 99.1), ticket L4. Types 24–27 in `docs/INGESTION.md`.
- **Shipped with it:** rule `ai_amount_within_capex` (16 rules now), `ai_spend.csv` in every release with its own README section, a DATAHQ company section ("What the filing says about AI spend") and a dashboard column. **`v1.2.0` is built, unsigned** (hash f4a2ded3fc78; no values changed from v1.1.0; 54 AI-spend rows). Signing is Kenny's call.

- **Airflow, as a thin wrapper:** `airflow/dags/capex_ledger.py` is one `BashOperator` per step of `ledger/steps.py`, daily on stage 3. Tested with Airflow 3.3.2 in a scratch virtualenv (`airflow dags reserialize`, `airflow tasks test capex_ledger 04_reconcile`); Airflow is not a project dependency. The pipeline, its caching and its logging stay in the ledger.

**Before that (28 Oct, night):** a code-slop pass after the audit. Four fixes, no behaviour change for a buyer:
- **Add-a-company progress reads data, not printed lines.** `ledger run` writes `data/jobs/progress.json` after every step (`ledger/progress.py`: which step, exit code, and a one-line summary counted from the store and the report files). DATAHQ's Add page reads that file; it no longer regex-parses the run's log. A run started before this change shows every step as waiting.
- **One release-folder helper.** `release.releases()` and `version_key()` sort by version number everywhere; the old "previous release" lookup sorted by string, so `v1.10.0` would have diffed against the wrong release.
- **No stale release label in config.** `STAGES` is the tuple `(1, 2, 3)` and `stage_tickers(n)` gives the companies; stage 3 is every tracked company, read fresh. The report page tells you to run `release <version>` instead of naming a version. Decision kinds live once, in `store.KINDS` (the unused `fix_rule` is gone).
- **Prompt, model and stage 3 are read at call time** (`extract.prompt_version()`, `agent.model()`, `config.stage_tickers(3)`), so switching a prompt or model in DATAHQ takes effect without restarting the server, and a company added in the app joins stage 3 at once.

**Before that (28 Oct, evening):** audit, Insights, client packet, the scale run to 31 companies, and `v1.1.0` signed.
- **Audit fixes:** a prompt edit is saved as the next version and switched on as a second, logged step; the name you sign with lives once in the nav; the release tile shows the exact commands; every question says why code can't decide it.
- **Insights** (`#insights`): on signed data only. Who pays (buyers' capex) and who gets paid (sellers' revenue), FY2022 → FY2025, and every company's capex, revenue and intensity. Each company in `config.AI_SET` and `data/companies.json` carries a role.
- **Client packet:** every release now builds a `README.md` next to `values.csv`, `DATA_DICTIONARY.md` and `QUALITY.md`; DATAHQ serves a signed release as one zip at `/packet/<version>.zip` (Outputs page).
- **Scale run:** 12 companies added from DATAHQ (AAPL, AVGO, INTC, QCOM, TXN, CSCO, IBM, WMT, XOM, JPM, ANET, and Compass by Kenny): 31 tracked. Full run on all 31 with parser `tables@9`: 132 filings, 384 values, 354 agree with the SEC's data, 26 more explained by code (16 the 10-K doesn't report, 10 definition gaps), 1,431 of 1,431 cited cells confirmed on the rendered 10-K, 0 of 7,075 planted faults through. Eight new failure types (16–23) in `docs/INGESTION.md`; seven fixed in code, one is a definition only a person can confirm.

**Released:** `v1.4.0`, signed by Kenny Geiler on 2026-10-29, hash f22c5092f4ef: the same 384 values as v1.1.0 (354 agree with XBRL), `facts.csv` (1,448), `ai_spend.csv` (83), `attribution.csv` (217 rows, 40 AI dollar amounts) and `EVALUATION.md` (5 of 6 reference entries estimated; 2 agree, 3 disagree). DATAHQ serves it as `/packet/v1.4.0.zip`. Earlier signed releases: v1.3.0 (4029e202c594), v1.1.0 (794fb2dfadae); v1.2.0 unsigned and superseded.

**Next (the plan agreed 29 Oct, in order):**
1. Send to Arctal: the repo, `/packet/v1.4.0.zip`, DATAHQ live.
2. Grow the reference set: Meta and Microsoft server-share statements from calls, Micron's HBM capex share, independent estimates (Dell'Oro puts accelerators at about a third of data-center capex industry-wide).
3. Subtract finance-lease additions from server-category growth where the lease note gives them (type 46).
4. Open items: Alphabet's PP&E category after FY2023 (type 44), purchase-commitment definitions (type 34), Nvidia's older-year transcripts and Alphabet's and Microsoft's links in `sources/ir.yaml`, ExxonMobil's 8-Ks under the old CIK (type 40), a `stated_sum` method for quarterly AI figures (type 42). (`ledger signoff v1.2.0 --by "Kenny Geiler"`), then DATAHQ serves it as a packet.
2. L4: 8-K earnings releases through the AI spend reader, where the explicit AI amounts are.
3. M3.1: one question per cause (XOM shows why).

**Critical notes:**
- **Dashes are zero.** APLD's newest 10-K shows "—" for its data-center cost line in FY2024 and FY2025; agents read these as 0.
- **NVDA's capex line includes intangible assets.** Note it when comparing companies.
- **Known blind spot:** a wrong-row misread is caught by comparing a company's filings with each other, so a company's first filing is less protected.
- **Running agents:** `ledger run` and the app's Add company run the agent headless on Kenny's subscription (no paid API). It needs a logged-in `claude` (run `claude`, then `/login`) of version 2.1.280 or later for Opus 5.5. Until the installed one is upgraded, set `LEDGER_CLAUDE` to the desktop app's newer `claude` before `ledger run` and before `ledger app`.
- **Definitions live in `definitions/companies.yaml`**, not in decisions. A new company with no cost-of-revenue total or a wider SEC tag asks once; the answer goes in the file.
- **A parser bump re-opens decisions.** Every value's input hash includes the parser version, so after `tables@9` every earlier decision is superseded and the open list is rebuilt from the rules; that is why the APLD recast decisions are gone and the cost-line confirmations are back.
- **`aispend` needs the network once per filing** (edgartools fetches Item 7, cached in `data/text/`, git-ignored like the rest of `data/`). A 10-K/A with no Item 7 gets an empty task and no agent call.
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
| `ledger/app.py`, `app.html`, `hq.py` | DATAHQ: the Data screen (grid, provenance, export) and Attribution (models, reruns); design audit and the Arctal research in [docs/DATAHQ.md](docs/DATAHQ.md) |
| `ledger/rules.py`, `rules/` | Rule engine and the 16 rules |
| `ledger/evidence.py`, `scorecard.py` | Rendered-10-K re-read with boxed screenshots; what each company cost |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | The XBRL answer key, built per company from cached SEC data |
| `agents/` | Prompt and output schema |
| `data/extract/outputs/`, `data/notes/outputs/`, `data/aispend/outputs/` | Agent outputs, kept as evidence; `data/text/` holds each filing's MD&A |
| `reports/`, `decisions/`, `golden/`, `releases/` | Validation pages and screenshots; review decisions; hand-checks; signed releases |
| `scripts/` | Measurements: cell accuracy vs XBRL, rerun agreement, locator accuracy |
| `docs/` | [PRD](docs/PRD.md), [tickets](docs/TICKETS.md), [fields](docs/FIELDS.md), [ingestion and learnings](docs/INGESTION.md) |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
