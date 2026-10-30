# Tickets

The backlog for [PRD.md](PRD.md), grouped by milestone. Owner of every ticket: Kenny Geiler. Tickets marked **you** need him; the rest are done by Claude Code.

## Open

### C: the critique of 30 Oct (ten tickets, ranked)

| ID | Ticket | Done when |
|---|---|---|
| C1 | **Revenue exposure has no stated inputs.** The AI-spend reader reads capex and opex statements only, so `stated_share` / `stated_amount` for `revenue` can never fire; Broadcom's "AI semiconductor revenue" is invisible. | `aispend@v4` reads revenue statements too (field `revenue`, scope `ai`: "AI revenue of $X", "data center revenue was N% of total"); `ai_statements`/`ai_spend` carry them; a rerun over every text; the attributor's revenue rows use them. |
| C2 | **Theses are thin.** Written by an agent without sources; company facts hedged with "when stated". | Every thesis's next version cites at least three sources per layer (filings, calls, independent estimates) in a Sources section, names each company's AI segment or stated share with the source, and is dry-run before use. |
| C4 | **Most of the 100 attribute `none`.** Honest, but the dataset says nothing about them. | A coverage roll-up per layer and measure (`/api/v1/coverage`, Status tab): companies with an amount, with words only, with nothing, per field; the Companies section of each thesis says why a `none` company is in the set. |
| C5 | **Committed and planned are weak.** Purchase commitments and finance leases are extracted but never attributed; planned is total guidance only. | Attribution has `kind: committed` (method `commitment`: AI part of purchase commitments or lease commitments per the thesis) and `kind: outlook` rows from AI guidance; the Dataset's committed and planned columns fill from them. |
| C6 | **Views are a filtered grid.** Bars and shares are hints, no real charts. | A view shows as a grid, a bar chart by group, a line chart by year per company, or a share grid; charts use the existing chart helpers and the ledger palette. |
| C7 | **Two production shapes.** `/api/v1` serves the working database; Postgres holds releases with other table names. | One shape: the release holds every list the API serves (companies, values, facts, attribution, statements, plans, projects), `ledger publish` pushes those files, and `/api/v1/<list>?release=vX.Y.Z` serves a signed release's files unchanged. |
| C8 | **No cost accounting for the agents.** Tokens sit in run logs; no cost per company, step or release. | `ledger cost` and the Status tab: tokens, seconds, attempts and estimated cost per step, per company and per release, with the price per million tokens in `ledger/config.py` and the date it was set. |
| C9 | **Built blind.** Views tab, `/api/v1`, theses in the attributor, projects reader: none run against the real database yet. | Each exercised in the browser on the real database after the 100-company run, screenshots in `reports/evidence/datahq/`, problems logged. |
| C10 | **The error band is a count.** "2 of 6 agree" is not an interval. | `ledger eval` reports a Wilson interval on the agreement rate overall and per method and layer, and the error distribution (median, interquartile range) on `eq` entries. |

### M3: review scales

| ID | Ticket | Done when |
|---|---|---|

### Later

| ID | Ticket | Done when |
|---|---|---|
| L4 | Feed the 8-K earnings release (Exhibit 99.1) filed with each 10-K through the AI spend reader: that is where the explicit AI amounts and shares are (type 27). | `ai_spend.csv` has `ai_amount` rows for the hyperscalers. |
| L2 | Non-functional checks as tests: SEC request spacing and contact header; no email or key in any output; parse under 60 s; `uv sync --frozen` works. | 4 tests. |

## Done

| C3 | Reference set 6 to 26 sourced entries across 7 layers (15 revenue, 11 capex), each with URL, quote and date; press-reported statements marked `company_statement_via_press`; `ledger eval` reports agreement and intervals per layer. Done 30 Oct 2026. |

- **Data screen (29 Oct):** DATAHQ as a dataset console after researching Arctal: filter bar, status strip, shaded grid with changed-cell outlines, provenance panel, chart of the selection, CSV export, saved views as links; `/api/data` long format.
- **Evaluation (29 Oct):** `gold/ai_capex.yaml` reference set, `ledger eval`, `EVALUATION.md` in releases, Insights section; Alphabet's renamed PP&E categories fixed (type 45); server-category overstatement measured (type 46).
- **DATAHQ three tabs (29 Oct, M7):** design audit and the new design in `docs/DATAHQ.md`; Pipeline, Attribution (model editor, rerun, diff, grid), Insights (live tables); company page attribution-first; dead question UI and Outputs removed.
- **Money-flow models + attributor (29 Oct, M6):** six models in `agents/models/`, agent `attributor` (`attribution@v1`) with an arithmetic contract, table `attribution`, `attribution.csv`, diff on load, company page section. The Attribution tab with model editing is M7.
- **Sources (29 Oct, M5):** `ledger texts` registry (MD&A, 8-K Exhibit 99.1, investor-page transcripts and CFO commentary via `sources/ir.yaml`); `aispend` over every text with `source`. Meta and Nvidia pages wired; Alphabet and Microsoft are per-company additions.
- **Facts from the notes (29 Oct, M4):** `ledger notes`, agent `notes_reader` (`notes@v2`), tables `note_extractions` / `facts`, XBRL-instance answer key with members, `facts.csv` in releases, company page section. Types 28–32.
- **No questions (29 Oct):** `definitions/companies.yaml` + `ledger/definitions.py`; reconcile and `cost_lines_summed` read it; warnings are findings with an SEC-data flag. M3.1 closed by this (one definition per cause).
- **Airflow DAG (29 Oct):** `airflow/dags/capex_ledger.py`, one task per step of `ledger/steps.py`; parsed and task-tested with Airflow 3.3.2 (L5).
- **AI spend from the MD&A (29 Oct):** `ledger aispend`, agent `ai_reader` (`aispend@v2`), tables `ai_statements` / `ai_spend`, rule `ai_amount_within_capex`, `ai_spend.csv` in every release, DATAHQ company section and dashboard column; Item 7 through `edgartools`. Types 24–27 in INGESTION.
- **Slop pass (28 Oct, night):** DATAHQ progress from `data/jobs/progress.json`, not log regexes; one release-sort helper (string sort would have broken at `v1.10.0`); stale `STAGES` release labels and the unused `fix_rule` kind removed; prompt, model and stage-3 tickers read at call time.
- **`v1.1.0` (28 Oct):** all 31 tracked companies, 384 values, signed by Kenny Geiler, hash 794fb2dfadae; 8 decisions by Kenny (cost lines ×4, XOM revenue definition ×4).

- **Client packet (L1, L3, 28 Oct):** every release builds `README.md` (what the file is, every column, how to read a basis) next to `values.csv`, the dictionary and `QUALITY.md`; DATAHQ serves a signed release as one zip (`/packet/<version>.zip`); `DIFF.md` lists added values too.
- **Scale run (28 Oct):** 12 companies added from DATAHQ (31 tracked); 8 new failure types (16–23) in `INGESTION.md`, 7 fixed in code; the Reader agent refused to guess three times, each with a usable reason.
- **Audit (28 Oct):** prompt edits are saved as a version and switched on as a second step; one name field in the nav signs every decision; Insights page on signed data (who pays, who gets paid).

- **DATAHQ app (28 Oct):** `ledger app`: dashboard, per-company pipeline, named agents with versioned prompts and every run, outputs explorer with CSV export.
- **Restatement notes (L4, 28 Oct):** cost lines are compared line by line; v1.0.1 drops 10 false notes, values unchanged; signed by Kenny Geiler, hash 6d10c2b1990f.
- **`v1.0.0` (28 Oct, M3.3):** all 19 companies, 234 values, signed by Kenny Geiler, hash 9f8014b3175f. Every value XBRL can't vouch for, plus 10 random ones, confirmed by the machine re-read; nothing needed a person.
- **M2, a new company needs no code (28 Oct):** blind run 1 on the 13 unseen companies found 6 failure types. Each was fixed as a type, and a full rerun of all 19 needs nothing from a person: 857/857 cells confirmed, 224/234 values agree with XBRL, the rest explained by code or decided. Details in [INGESTION.md](INGESTION.md).
- **Cleanup (28 Oct):** the XBRL answer key is built per company on demand (same 312 values). Removed the batch job, its quarterly code and `facts.csv`, the `--find` experiment, dead helpers and stale ticket numbers.

- **M1, it runs unattended (28 Oct):** `ledger run --ticker X` takes any company from ticker to validation page and scorecard with nobody in the loop. Headless agent (`claude -p`, Opus 5.5 pinned, no tools, isolated from the desktop session and user hooks), every command takes `--ticker`, per-company scorecard. First unattended company: AMD, 21 s end to end, 12/12 values agree with XBRL, 24/24 cells confirmed on the rendered 10-K, 0 code changes, nothing for a person.

- **`v0.2.0` (28 Oct):** 5 companies, 66 values, signed by Kenny Geiler, hash a4319cfd12b5. M0 complete.

- **Rendered-10-K re-read (28 Oct):** `ledger evidence` confirms each cited cell on the 10-K as rendered in Chrome and screenshots it boxed; G5 accepts a machine confirmation, and a person answers only cards it can't confirm.
- **Sampled hand-check (M3.2, pulled forward, 28 Oct):** a person checks only the values XBRL can't vouch for, plus 10 random agreeing ones. Each is one yes/no question on the page; decisions show as decided, not red. Stage 2: 20 checks instead of 66.
- **M0, built by hand (to 28 Oct 2026):**
  - **Ingest:** 10-K list per company; documents cached with SHA-256; table parser (`tables@7`, fixture-tested); statement locator (72/72 10-Ks correct); restatement-note finder.
  - **Extraction:** tasks with no XBRL in them; prompts `statements@v1` and `@v2` (cost lines classified when there is no total); citation resolver; outputs kept in git.
  - **Values:** one filing per company-year; opex from one column; restated basis with `first_reported` kept; summed cost lines; `definition_gap` when only XBRL's cost-of-revenue definition differs.
  - **Rules:** 15 in `rules/*.yaml`, each with a rationale, a plain-English explanation and an action, each tested to pass and fail.
  - **Fault injection:** 0 of 862 misreads escaped (stage 2).
  - **Validation pages:** plain-language story, decision cards, charts, links into each filing, the filing's own restatement sentence.
  - **Review, release, sign-off:** decisions re-apply only on unchanged inputs; gates G1, G4 and G5; deterministic hash.
  - **`v0.1.0`** (NVDA, 15 values) signed by Kenny Geiler, hash 2b15699badbe.
  - **Held-out test:** ORCL and APLD, run once with the prompt frozen; 140/140 checkable cells read correctly across stage 2.

The quarterly-era tickets and results are in tag `quarterly-v0.1`. How the pipeline works and what each finding changed: [INGESTION.md](INGESTION.md).
