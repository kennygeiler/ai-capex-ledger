# Start here

For a person, or an AI agent, who has just cloned this repository. Read this, then the README's Status block, then
the document for whatever you are about to touch.

## What this is, in four sentences

A pipeline reads a company's SEC 10-K filings and returns revenue, capex and opex, each citing the exact table cell it
came from, checked against the SEC's own XBRL data and re-read on the rendered filing. A second set of agents reads the
notes, the MD&A, earnings releases and call transcripts for facts and statements about AI. An attributor reads a
money-flow model for the company's industry and the cleaned data and says how much of the capex is AI, naming every
input so code recomputes the number. A person edits the models and definitions, reruns, checks against a reference
set, and signs a release; nobody is asked anything else.

Built by Kenny Geiler in late October 2026 as a working prototype for a data-science role at Arctal. 100 companies
across the AI supply chain (`docs/COMPANIES.md`), annual, fiscal years 2022 to 2026. See `docs/PROOF.md` for who Arctal is and why the app looks the way it does.

## What a clone contains, and what it does not

Tracked, so you have it on clone:

- Code (`ledger/`), tests (`tests/`), the rules (`rules/*.yaml`), the agents' prompts (`agents/`), the taxonomy
  (`taxonomy/`: the categories and their standards, the asset-type mappings, the stated figures), per-company
  definitions (`definitions/companies.yaml`), the investor-page links (`sources/ir.yaml`), the hand-check (`golden/`),
  the golden test's frozen inputs and expectation (`fixtures/`).
- Every agent output, kept as evidence: `data/extract/outputs/` (statement cells), `data/notes/outputs/` (note
  facts), `data/aispend/outputs/` (AI statements), `data/projects/outputs/` (named projects). A rebuild reuses them;
  no agent runs unless a task changes.
- Signed releases (`releases/v*/`), the decisions log (`decisions/`), the reports and evidence screenshots
  (`reports/`), and every document in `docs/`.

Not tracked, rebuilt by `ledger run` (needs the network and about 30 minutes for all 31):

- The database `data/ledger.duckdb`, the raw filings `data/raw/`, parsed tables `data/docs/`, MD&A and release texts
  `data/text/`, the task files, snapshots, `data/watch.json`, the jobs folder, `resolutions.jsonl`, dry runs.

## Setup

```bash
uv sync                                                     # Python 3.12, DuckDB, edgartools, pypdf, playwright
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env     # the SEC requires a contact; never commit it
echo 'DATABASE_URL="postgresql://…"' >> .env                 # production Postgres, only if you will publish releases
echo 'DATABASE_READONLY_URL="postgresql://…"' >> .env        # the arctal_reader string, SELECT only; the one to hand a consumer
claude                                                      # then /login: the agents run on a Claude subscription, headless
export LEDGER_CLAUDE="$(which claude)"                      # the claude binary the pipeline should use
uv run python -m unittest -q                                # 114 tests, offline, seconds
```

The `evidence` step drives the installed Google Chrome through Playwright. The `texts` step downloads PDFs from the
links in `sources/ir.yaml`; it never renders investor pages (they sit behind a bot check, and code must not get
around it; a person lists the links).

## The five-minute tour

```bash
uv run python -m ledger run --ticker NVDA        # every step for one company, agents included, then the scorecard
uv run python -m ledger run --stage 3            # all 31 (about 30 minutes on a fresh clone, mostly fetching and Chrome)
LEDGER_CLAUDE="$(which claude)" uv run python -m ledger app   # DATAHQ at http://127.0.0.1:3610
uv run python -m ledger golden --check           # the proven six rebuilt from frozen inputs, every table compared
uv run python -m ledger release v1.5.0 --stage 3 # refuses while a gate fails; then signoff, by the owner only
uv run python -m ledger publish v1.5.0           # a signed release to the production Postgres; --status lists what is there
```

Every command takes `--stage 3` (every tracked company) or `--ticker X Y`. `python -m ledger` lists them.

## The objects, and where each lives

| Object | What it is | File or table | Doc |
|---|---|---|---|
| values | revenue, capex, opex per company and fiscal year, from statement cells | table `values`, `releases/*/values.csv` | `docs/FIELDS.md` |
| facts | segment capex and revenue, PP&E by category, finance leases, purchase commitments, from the notes | tables `note_extractions`, `facts`, `facts.csv` | `docs/DATA_DICTIONARY.md` |
| texts, statements | MD&A, 8-K releases, transcripts; what each says about AI's part of spend, as verbatim quotes | tables `texts`, `ai_statements`, `ai_spend`, `ai_spend.csv` | `docs/INGESTION.md` |
| taxonomy | one row shape for spent, committed, derived, planned and company-stated AI, every category a named standard's concept; built by code, no agent | `taxonomy/taxonomy.yaml`, `ledger/taxonomy.py`, `/api/v1/taxonomy`, `taxonomy.csv` (next release) | `docs/TAXONOMY.md` |
| asset-type mappings | each company's reported PP&E category mapped to a us-gaap member, with the note's words as evidence; an unmapped one is open on Proof | `taxonomy/asset_types.yaml` | `docs/TAXONOMY.md` |
| prompts | one per agent, versioned the same way | `agents/prompts/`, `agents/schemas/` | `agents/agents.json` |
| definitions | judgements made once per company and applied every run | `definitions/companies.yaml` | README Critical notes |
| stated figures | figures companies stated about AI, gathered from releases, calls and press, verbatim with the source; `company_stated_ai` rows | `taxonomy/stated_figures.yaml` | `docs/TAXONOMY.md` |
| rules, guards | the 15 checks, each with its rationale and owner; the two guards that tag part-year and program statements | `rules/*.yaml`, `ledger/rules.py`, `ledger/guards.py` | `docs/PROOF.md` |
| resolutions | what a person decided about a queue item; `status` on exported rows | `decisions/resolutions.jsonl` (tracked, append-only) | `docs/PROOF.md`, `docs/API.md` |
| releases | plain files whose content hash a person signs | `releases/v*/` | release `README.md` |
| production | the signed releases, one table per release file plus `ledger_releases`; `current_*` views follow the highest version | Postgres at `DATABASE_URL`, `ledger/publish.py` | this file |
| companies | the 100 companies by supply-chain layer (`group`, a reading aid); the proven set in `config.PROVEN` | `data/companies.json`, `ledger/config.py` | `docs/COMPANIES.md`, `docs/PROOF.md` |

## How to do the common things

- **Add a company**: DATAHQ, `#run`, type the ticker; or `ledger run --ticker X`. It joins stage 3. Give it an
  industry in `ledger/config.py` `INDUSTRIES`, or it gets the `other` model.
- **Map a reported asset type**: Proof shows it open under Mapping; add the entry to `taxonomy/asset_types.yaml`
  with the note's own words as evidence, who and when. A mapping is a classification, never a number.
- **Settle a disagreement with the SEC's data**: add a definition for the company in `definitions/companies.yaml`
  (who, why), rerun `reconcile` and `rules`. Never accept the same thing twice.
- **Add a figure a company stated about AI**: `taxonomy/stated_figures.yaml`, verbatim, with the URL and the quote.
- **Release**: `ledger release vX.Y.Z --stage 3` (refuses while a gate fails), then `ledger signoff vX.Y.Z --by
  "<name>"`. Signing is the one human act and belongs to the owner. Then `ledger publish vX.Y.Z` pushes the signed
  files to production; it refuses an unsigned release or one whose files no longer match the signed hash, and
  publishing the same version again replaces its rows in one transaction.
- **Find why something is wrong**: `docs/INGESTION.md` logs every failure type found so far (46), where it showed,
  what caught it, what fixed it. Add to it.

## The rules of the house

1. After every commit, update the README Status block: last done, next, critical notes (`CLAUDE.md`).
2. Only add what is needed. Remove stale files; old work lives in git tags.
3. Pipeline first: fix the failure type, not the instance, and log it in `docs/INGESTION.md`.
4. A person sees only surprises and judgement calls, and each one says why code could not decide it.
5. No paid API: the agents run on a Claude subscription through `claude -p`.
6. Never sign a release without the owner's explicit approval for that release.
7. The SEC contact and the production database URL live only in `.env`. Never commit them, never print them.
8. Never get around a bot check. Investor-page links are listed by a person.
9. Prompts and models are never edited in place; a change is the next version, switched on as a second step.
10. The design rules for DATAHQ are in `docs/PROOF.md`; one thing per screen; numbers before words.

## If you are an AI agent

Read in this order: this file, README Status, `docs/PROOF.md`, `docs/TAXONOMY.md`, `docs/INGESTION.md` (skim the tables), then the
module you will change. Run the tests before and after. The invariants that must hold:

- Every value in `values` resolves to a cell in a parsed table; `extract --load` rejects anything else.
- No column holds a number the pipeline made up: every taxonomy row is a reported figure, a verbatim quote, or
  arithmetic on reported balances marked `derived`. An asset type maps to a published us-gaap member or stays open.
- A release is reproducible from its inputs: same inputs, same hash. Never edit a file under `releases/`.
- `decisions/` and the agents' history are append-only.

Verify, don't assert: the pipeline writes `runs`, snapshots and `data/jobs/progress.json`; `ledger golden --check` says
whether the proven six still rebuild equal; read them rather than the log. `rtk` wraps shell commands in some sessions and
truncates long output; use `rtk proxy <cmd>` or a Python one-liner to read a full file or an HTTP body.

`docs/PROOF.md` is the frame since 31 Oct 2026: the pipeline proves every number on five companies first; `ledger golden --check` is the bar. `docs/archive/REPLICATION.md` is the walk through the app as its user would do it that led there.
