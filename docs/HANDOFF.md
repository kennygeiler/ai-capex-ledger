# Start here

Where the code lives and what to edit for a change: [docs/MAP.md](MAP.md), one page. The pipeline in one picture: [docs/OVERVIEW.md](OVERVIEW.md). Routine operation: [docs/OPERATIONS.md](OPERATIONS.md).

For an operator or an automated agent taking over a fresh clone. Read this, then `git log` for recent changes,
then the document for the area being changed.

## What this is, in four sentences

A pipeline reads a company's SEC 10-K filings and returns revenue, capex and opex, each citing the exact table cell it
came from, checked against the SEC's own XBRL data and re-read on the rendered filing. A second set of agents reads the
notes, the MD&A, earnings releases and call transcripts for facts and statements about AI. An attributor reads a
money-flow model for the company's industry and the cleaned data and says how much of the capex is AI, naming every
input so code recomputes the number. A person edits the models and definitions, reruns, checks against a reference
set, and signs a release; nobody is asked anything else.

Built by Kenny Geiler in October 2026 as a working prototype for Arctal. 100 companies
across the AI supply chain (`docs/COMPANIES.md`), annual, fiscal years 2022 to 2026. See `docs/PROOF.md` for who Arctal is and why the app looks the way it does.

## What a clone contains, and what it does not

Tracked, present on clone:

- Code (`ledger/`), tests (`tests/`), the rules (`rules/*.yaml`), the agents' prompts (`agents/`), the taxonomy
  (`taxonomy/`: the categories and their standards, the asset-type mappings, the stated figures), per-company
  definitions (`definitions/companies.yaml`), the investor-page links (`sources/ir.yaml`), the hand-check (`golden/`),
  the golden test's frozen inputs and expectation (`fixtures/`), the gold set a person verifies (`gold/`, T82, docs/EVALS.md).
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
echo 'DATABASE_URL="postgresql://…"' >> .env                 # production Postgres, only to publish releases
echo 'DATABASE_READONLY_URL="postgresql://…"' >> .env        # the arctal_reader string, SELECT only; the one to hand a consumer
claude                                                      # then /login: the agents run on a Claude subscription, headless
export LEDGER_CLAUDE="$(which claude)"                      # the claude binary the pipeline should use
uv run python -m ledger test --fast                         # the whole suite, offline, a few minutes; the count and result land in reports/tests.json (drop --fast for golden too)
```

**Offline mode** (`LEDGER_OFFLINE=1`, `ledger/ingest/edgar.py`): every SEC read is served from the `data/raw` cache whatever
its age (under a temporary `LEDGER_ROOT`, from the checkout's own `data/raw`), and anything uncached raises `Offline`; the
edgartools and investor-PDF paths refuse too. No `SEC_USER_AGENT` is needed. `ledger test` and `ledger golden --check` run
offline unless `--online`, and `tests/__init__.py` sets it for a bare `python -m unittest`, so a worktree with no `.env`
runs the whole suite. A test that needs a filing must find it in `data/raw` (symlinked in a worktree) or fail with `Offline`.

The `evidence` step drives the installed Google Chrome through Playwright. The `texts` step downloads PDFs from the
links in `sources/ir.yaml`; it never renders investor pages (they sit behind a bot check, and code must not get
around it; a person lists the links).

## The five-minute tour

```bash
uv run python -m ledger run --ticker NVDA        # every step for one company, agents included, then the scorecard
uv run python -m ledger run --stage 3            # all 31 (about 30 minutes on a fresh clone, mostly fetching and Chrome)
uv run python -m ledger app                      # Kenny's Data Emporium at http://127.0.0.1:3610 (LEDGER_CLAUDE="$(which claude)" only to start runs from it)
uv run python -m ledger golden --check           # the proven six rebuilt from frozen inputs, every table compared, plus every gold verdict
uv run python -m ledger gold --status            # the gold set: verdicts, error rate with n and a Wilson interval (--draw writes the sample)
uv run python -m ledger test                     # the whole suite, golden included; writes reports/tests.json, the Release page's test line (--fast skips golden)
uv run python -m ledger mapper MU                # the mapping assistant (T33): a us-gaap member proposed per unmapped PP&E category; approve on #reconcile?scope=MU
uv run python -m ledger release v1.8.0           # the scope (config.SCOPE), a gate table per company; refuses on any failing row; then signoff, by the owner only
uv run python -m ledger publish v1.5.0           # a signed release to the production Postgres; --status lists what is there
```

Every command takes `--stage 3` (every tracked company) or `--ticker X Y`. `python -m ledger` lists them.

## The objects, and where each lives

| Object | What it is | File or table | Doc |
|---|---|---|---|
| values | revenue, capex, opex per company and fiscal year, from statement cells | table `values`, `releases/*/values.csv` | `docs/FIELDS.md` |
| facts | segment capex and revenue, PP&E by category, finance leases, purchase commitments, from the notes | tables `note_extractions`, `facts`, `facts.csv` | `docs/DATA_DICTIONARY.md` |
| texts, statements | MD&A, 8-K releases, transcripts; what each says about AI's part of spend, as verbatim quotes | tables `texts`, `ai_statements`, `ai_spend`, `ai_spend.csv` | `docs/INGESTION.md` |
| taxonomy | one row shape for spent, committed, derived, planned and company-stated AI, every category a named standard's concept; built by code, no agent | `taxonomy/taxonomy.yaml`, `ledger/release/taxonomy.py`, `/api/v1/taxonomy`, `taxonomy.csv` (next release) | `docs/TAXONOMY.md` |
| asset-type mappings | each company's reported PP&E category mapped to a us-gaap member, with the note's words as evidence; an unmapped one is open on Proof, and so is one without a person's `confirmed_by` (T63: a proposal, to confirm) | `taxonomy/asset_types.yaml` | `docs/TAXONOMY.md` |
| prompts | one per agent, versioned the same way | `agents/prompts/`, `agents/schemas/` | `agents/agents.json` |
| charters | one per agent, live or retired: what it owns, what it never touches, its input and output files, model, tools, prompt versions, the checks that judge it, written from the code | `agents/charters/<id>.md`, path in `agents/agents.json` | the Rules page, `/api/agents` |
| definitions | judgements made once per company and applied every run | `definitions/companies.yaml` | this file, Data conventions |
| stated figures | figures companies stated about AI, gathered from releases, calls and press, verbatim with the source; `company_stated_ai` rows | `taxonomy/stated_figures.yaml` | `docs/TAXONOMY.md` |
| failure types | every failure type INGESTION.md logged, as data: id, cause class, origin, the check in code that catches it or `none`, count seen | `taxonomy/failures.yaml`, `ledger/checks/failures.py` | `docs/INGESTION.md` |
| rules, guards | the checks in `rules/*.yaml`, each with its rationale and owner; the two guards that tag part-year and program statements | `rules/*.yaml`, `ledger/checks/rules.py`, `ledger/checks/guards.py` | `docs/PROOF.md` |
| resolutions | what a person decided about a queue item, keyed `kind|ticker|field|period|dimension|rule_id|subject` (`resolutions.key_for`); `status` on exported rows | `decisions/resolutions.jsonl` (tracked, append-only; `ledger resolutions migrate-keys` re-keys lines from before T62, archive under `decisions/archive/`) | `docs/PROOF.md`, `docs/API.md` |
| releases | plain files whose content hash a person signs | `releases/v*/` | release `README.md` |
| production | the signed releases, one table per release file plus `ledger_releases`; `current_*` views follow the highest version | Postgres at `DATABASE_URL`, `ledger/release/publish.py` | this file |
| companies | the 100 companies by supply-chain layer (`group`, a reading aid); the proven set in `config.PROVEN` | `data/companies.json`, `ledger/core/config.py` | `docs/COMPANIES.md`, `docs/PROOF.md` |

## The hosted copy

https://datahq-production.up.railway.app is Kenny's Data Emporium read-only: the same pages and read API, from a snapshot of the working database,
the evidence screenshots and the signed releases. Nothing writes there (every POST is refused; the header says "read-only copy")
and it never reaches the SEC (`ledger/ingest/edgar.py` raises `Offline` instead of fetching). It is what to send someone who should
look without a checkout. Redeploy after a run or a release: `uv run python scripts/stage_hosted.py && railway up --service datahq` from this directory (the script stages the stored filings in scope into `deploy/raw/`; crops need `ledger evidence --crops` first), then
`uv run python -m ledger claims --deployed` and commit `claims/hosted.json` (without that record the Gaps page reads the hosted copy stale) (the `Dockerfile`;
`.railwayignore` and `.dockerignore` re-include `data/ledger.duckdb` and the distilled XBRL instances `data/raw/*/filings/*.facts.json`,
which git ignores: without the instances the restatement guard (`proof._restated`) cannot name a tag's filing, and the hosted copy
counts those rows open while the local one counts them explained, and every untagged note figure reads "XBRL instance not
loaded", F17). The signed releases also sit in the production Postgres,
`DATABASE_READONLY_URL` in `.env`, the only connection string to hand out.

## The work

`docs/TICKETS.md`: the tickets for the sign-with-confidence flow, in order. Pick the first open one; close it with a commit that names it.

Every ticket is built by `docs/BUILD.md`: a pre-mortem against eight failure patterns before code, one test per answer, and
the claims register (`claims/claims.yaml`, `claims/findings.jsonl`) kept current. What is not yet true, and every review
finding not yet fixed, is on the Gaps page (`#gaps`), `/api/v1/claims` and `docs/CLAIMS.md`.

## How to do the common things

- **Add a company**: `ledger run --ticker X`. It joins stage 3. Give it an
  industry in `ledger/core/config.py` `INDUSTRIES`, or it gets the `other` model.
- **A resolution with a key from before T62** (`kind|ticker|where`, two pipes) is not live. `ledger resolutions migrate-keys
  --dry-run` shows what each would become; without `--dry-run` it appends the re-keyed lines and copies the unmappable ones
  to `decisions/archive/resolutions-keys-<date>.jsonl`; it removes nothing and a second run is a no-op.
- **Map a reported asset type**: Proof shows it open under Mapping. `ledger mapper <TICKER>` (T33; `--dry-run` writes the
  task only) asks the mapper agent for a us-gaap member per unmapped category with the note's words as evidence; the
  proposals land in `decisions/mapping_proposals.jsonl` and on Reconcile's Category mapping cards (`#reconcile?scope=<TICKER>`,
  in scope or not), where Approve or Choose another writes the entry to `taxonomy/asset_types.yaml` under the signer's name (`POST
  /api/mapping`: the one writer; a member off the header's list or a second entry for the same name is refused) and
  Reject logs the member so the next run proposes another (T100: a delayed proposal of a rejected member is never current;
  Reconcile shows it as "re-proposed after rejection", and a proposal after an approval changes nothing). Or write the entry by hand, with the note's own words as
  evidence, who and when. Either way, rerun `ledger rules` (or any taxonomy read) and the row shows `mapped`. A mapping
  is a classification, never a number; a proposal is nothing until a person approves it. T63: an entry counts as checked
  only with `confirmed_by` and `confirmed_at` (Approve writes both; an agent never does). One without them, like the 47
  an agent proposed in one batch, is open on Proof as "to confirm", fails gate G6, and sits in the same Reconcile
  group: Approve confirms its line, Choose another replaces it confirmed, Reject removes it and logs the member.
- **Settle a disagreement with the SEC's data**: add a definition for the company in `definitions/companies.yaml`
  (who, why), rerun `reconcile` and `rules`. Never accept the same thing twice.
- **Write an explanation once (T36)**: on Reconcile, after Explain or Accept, "Make this a rule" (an info `explains` rule in
  `rules/`, matching the finding's rule, field and the company's whole line labels, so it closes the same cause at every company
  reading those lines) or "Make this a definition" (`definitions/companies.yaml`); `POST /api/judgement`, by a name on
  `config.PEOPLE`. Rerun `ledger rules` (or `reconcile`), then commit the file. A rule targets only label-driven findings
  (`rules.EXPLAINABLE`, row_label_switch) and matches only exactly its set of lines; a revenue or opex definition carries
  `periods`, the year the person saw, and applies to no other. `by` is unauthenticated until T6 (the local trust
  boundary): a rule's or definition's `by` is a claim, not proof of a person, as for resolutions and gold.
- **Decide a block finding**: `ledger review decide <id> accept|override|reject --reason "…" --by "<name on
  config.PEOPLE>" --as person --ticker X`; `--as person|run` is required, so the command says who decides, and every
  line records `reviewer` and `author_kind`. An agent writes `--as run`: its decision is recorded and closes nothing that blocks; the finding stays open under G4 and Proposed (G6, Proof, Reconcile) until a person decides
  it (F14). A run's decision on a warning closes it, as before.
- **Add a figure a company stated about AI**: `taxonomy/stated_figures.yaml`, verbatim, with the URL and the quote.
- **Release**: Kenny's Data Emporium's Release page (`#release`) is the checklist: every line that could make a signature wrong, green or
  red with its count and the page that fixes it, and the packet built in memory. Its Sign button (enabled only when every
  required line is green and the signer box holds a name on `config.PEOPLE`) writes `releases/<version>/`, signs as that name, stores the checklist as it
  was in `SIGNOFF.json`, and publishes; that is the one place a release is signed (`docs/PROOF.md`). Its test line reads
  `reports/tests.json`, which `ledger test` writes: run it on the commit being signed, or the line reads stale. The line is required since a00b67f;
  releases up to v1.8.0 were signed while it only informed (their `SIGNOFF.json` records it not run, `required: false`). Two required lines replace the old Golden line: Hand check reads every verdict in `gold/*.json` live (a verdict given on Proof counts at once, no CLI run) and is green only when every item has a verdict and every verdict holds, so nothing signs until a person gives them; Regression test reads `reports/golden.json` (tables unchanged since the freeze, with its date and, since F20, the commit, tree and code hash it ran on): equal tables on other code or a dirty tree, or a report with no code hash, read stale and block, so run `ledger golden --check` on the commit being signed (it still exits 0 on unverified-only). A required line "Verified or explained with no record behind it" walks every verified or explained row in scope for the record it names, on the live tables (F16).
  **Signing, in order** (F18, F20): (1) commit the code; (2) `ledger golden --check`, commit `reports/golden.json`; (3)
  `ledger claims`, commit `docs/CLAIMS.md` when it changed; (4) `ledger test`, commit `reports/tests.json`. Each run
  records a code hash (`testreport.code_hash`: every tracked file HEAD holds, less `reports/tests.json`,
  `reports/golden.json` and `docs/CLAIMS.md`); the Test run and Regression lines read the checkout at every checklist and
  pass only when it is clean (no uncommitted code; a `git status` that fails reads dirty), the run was on a clean tree,
  and the report's hash equals the checkout's. Committing the three record files keeps the hash; any other commit moves
  it and the lines read stale. Neither report file makes the tree dirty. The hash proves the code is the code the report
  names, not that the run happened: a report written by hand can name the right hash (F-TR2). (5) The signer types a
  name in the signer box (empty by default, remembered in this browser) and presses Sign; or `ledger signoff vX.Y.Z --by
  "<name>"`. Both pass one gate first (`checklist.preflight`): no uncommitted code, and the Regression test and Test run
  lines pass on this checkout; anything else refuses before anything is built or signed. Every write, from the page or
  `signoff`, refuses a name off `config.PEOPLE` (400 on the page, exit 1 on the command line). The command line
  does the same in pieces: `ledger release vX.Y.Z` builds the packet for `config.SCOPE`, prints the gate table (one row
  per company, G1 G4 G5 G6) and refuses on any failing row (`--stage N` only names the hand-check file); `ledger signoff
  vX.Y.Z --by "<name>"` signs without a checklist; `ledger publish vX.Y.Z` pushes the signed files to production and
  refuses an unsigned release or one whose files no longer match the signed hash; publishing the same version again
  replaces its rows in one transaction. Signing is the one human act and belongs to the owner; agents never sign or publish.
- **Ask what a filing said on a date** (a backtest, no lookahead): `/api/v1/values?as_of=YYYY-MM-DD` or `/api/v1/taxonomy?as_of=…`
  (`ledger/web/pit.py`, `docs/API.md`): the newest filing filed by that day, with its accession; absent where nothing was filed yet.
- **Find why something is wrong**: `docs/INGESTION.md` logs every failure type found so far (72), where it showed,
  what caught it, what fixed it; `taxonomy/failures.yaml` holds each as data with its class and catching check. Add to both.

## Operating notes

- **A server older than the checkout**: the app imports its Python at start; pages and scripts are read on every request.
  `/api/hq` returns `code {running, checkout, state}` and the page shows "App code differs from checkout · restart" under
  the scope line when the code under `ledger/` changed since the server started, newer or reverted (F21). Reconcile's queue cache is keyed on
  the database and every input file (decisions, mapping proposals, `data/watch.json`, `rules/`, `definitions/`,
  `taxonomy/`), so a write to any of them rebuilds it on the next read.
- **Worktrees share `data/raw`, `data/docs` and `data/text` with the main checkout through symlinks.** A builder on an
  older base that runs `ledger ingest` rewrites the shared parses with old code (this has reverted the shared AMZN parses
  to tables@12 once). Run `ingest` only on current main, or give the worktree its own data copy; after any ingest,
  `cmp` fixtures/data/docs against data/docs for the six. A worktree needs those three symlinks, the crop PNGs symlinked
  (below), and a copy of `data/ledger.duckdb` and `data/watch.json`; tests run offline with no `.env`.
- **The crop pictures are not in git** (the repository is public; 42 MB): `reports/evidence/crops/*.png` is ignored,
  `reports/evidence/crops.json` is committed. After a clone, or when a crop reads "Crop file missing" or "Crop out of
  date", run `uv run python -m ledger evidence --crops --ticker MSFT GOOGL AMZN NVDA APLD AMD` (Chrome, about 3 minutes,
  offline; needs the stored filings in data/raw). The hosted copy has neither the filings nor the pictures (F-EV3, F-EV4).
- **An agent output loads only if it answered the current task** (T100, `agent.stale`): after any change that repacks
  tasks (a locator, a parser, a prompt version), run the step's `--run` before `--load`, or the loader refuses the old
  answers as `*_failed` "stale output". 13 statement outputs carry no `_run.task_sha` (written by hand before headless
  runs) and are re-asked on the next `extract --run`: APLD 0001144879-24-000216, -25-000021, -26-000048; CRWV
  0001769628-26-000104; MSFT 0000950170-24-087843, 0000950170-25-100235, 0001193125-26-323660; NVDA
  0001045810-24-000029, -25-000023, -26-000021; ORCL 0000950170-24-075605, 0000950170-25-087926, 0001193125-26-277521.
  MSFT, NVDA and APLD are proven: check golden after that run.
- **Golden**: `ledger golden --check` before any commit that touches a parser, a rule, a loader or the taxonomy; `--freeze`
  only on purpose, in its own commit that says why. Freeze copies the live DB's tables, so rerun `ledger rules` on the
  proven six first when a rule changed.
- **After a merge** (`.gitattributes` keeps these from conflicting; `claims/findings.jsonl` merges by union, both sides'
  lines kept), in this order, committing after each: `ledger golden --check` (rewrites `reports/golden.json`, which the
  live register's gold and golden claims read); `ledger claims` (regenerates `docs/CLAIMS.md`: a union merge leaves it stale,
  and the Release line "Claims doc current" and `tests.test_claims.Doc` fail until it runs); then `ledger test` on that
  commit (rewrites `reports/tests.json`; a later commit that changes only that file keeps the Test run line green).
  `docs/CLAIMS.md` reads neither report (the last run, the golden report and the gold verdict count say "see the Release
  page" there and are checked live), so `ledger test` or `golden --check` never leaves it stale: two test runs in a row
  and `ledger claims --check` stay green. Only a change to the register, the findings, the gold set reaching all
  verdicts, the mappings or the signed releases needs `ledger claims` again. The
  two report files keep the checked-out side on a merge once a clone runs `git config merge.ledger-report.driver true`
  (without it they conflict as before; either side is stale on the merge commit anyway).
- **Finding ids** are branch-prefixed, `F-<BRANCH CODE><n>` (`F-RC7`, `F-EV2`) or `S-<n>` for state findings; plain
  `F<n>` ids stop at F30. `claims.findings()` refuses a first line that is not open, a second open line for an id, or a
  new plain `F<n>` id.
- An asset-type mapping is a person's only with `confirmed_by` on the entry (T63); an agent never writes that field, and
  never in a person's name.
- Release files are LF, hashed before the write, read back byte-exact; `publish` adds a release's new columns to existing tables.

## Data conventions

Dashes are zero; NVDA's capex includes intangibles; banks and oil majors are partly blank on purpose; old work is in tags
(`takehome-xbrl-explorer`, `quarterly-v0.1`).

## The rules of the house

1. The commit message is the record: what changed, why, what is left open. Open review findings go in
   `claims/findings.jsonl`. There is no status diary to update.
2. Only add what is needed. Remove stale files; old work lives in git tags and history.
3. Pipeline first: fix the failure type, not the instance, and log it in `docs/INGESTION.md`.
4. A person sees only surprises and judgement calls, and each one says why code could not decide it.
5. No paid API: the agents run on a Claude subscription through `claude -p`.
6. Never sign a release without the owner's explicit approval for that release.
7. The SEC contact and the production database URL live only in `.env`. Never commit them, never print them.
8. Never get around a bot check. Investor-page links are listed by a person.
9. Prompts and models are never edited in place; a change is the next version, switched on as a second step.
   Charter before code (T50): a new agent or source starts with `agents/charters/<id>.md`, written from the code it will
   run under (what it owns, what it never touches, task and output file shapes, model, tools, prompt versions, the rule
   and guard ids that judge it; "not stated in code" where the code does not say). A retired agent keeps its charter,
   marked retired with why. The Rules page shows each live charter with the prompt history and the runs per company.
10. The design rules for Kenny's Data Emporium are in `docs/PROOF.md`; one thing per screen; numbers before words.

## Reading order and invariants

Read in this order: this file, `docs/MAP.md`, `git log --first-parent main` (what landed lately), `docs/BUILD.md` (how every ticket is built), `docs/PROOF.md`, `docs/STATES.md` (every implicit state machine, its states, transitions and UI words), `docs/EVALS.md` (how the pipeline is measured: golden, faults, scores, gates), `docs/DISCIPLINES.md` (seven discipline audits against the code, with the tickets T67–T79 they proposed), `docs/TAXONOMY.md`, `docs/INGESTION.md` (skim the tables), then the
module being changed. Run the tests before and after. The invariants that must hold:

- Every value in `values` resolves to a cell in a parsed table; `extract --load` rejects anything else.
- No column holds a number the pipeline made up: every taxonomy row is a reported figure, a verbatim quote, or
  arithmetic on reported balances marked `derived`. An asset type maps to a published us-gaap member or stays open.
- A release is reproducible from its inputs: same inputs, same hash. Never edit a file under `releases/`.
- `decisions/` and the agents' history are append-only.

Verify, don't assert: the pipeline writes `runs`, snapshots and `data/jobs/progress.json`; `ledger golden --check` says
whether the proven six still rebuild equal; read them rather than the log. Some shells wrap commands with `rtk`, which
truncates long output; use `rtk proxy <cmd>` or a Python one-liner to read a full file or an HTTP body.

`docs/PROOF.md` is the frame: the pipeline proves every number on the proven set (`config.PROVEN`) first; `ledger golden --check` is the bar. `docs/archive/REPLICATION.md` is the walk through the app as its user would do it that led there.
