# Capex Ledger

A pipeline that turns SEC 10-K filings into a versioned dataset of revenue, capex, opex, note-level facts (segment
capex and revenue, PP&E by category, finance leases, purchase commitments) and company statements about AI spend.
Agents read the filings; deterministic code checks every number against the cell it cites and, where one exists, against
the filer's own XBRL, a tie to a tagged total or a second reading in a later filing; a person reviews only what code
cannot decide and signs each release. Every figure carries its citation and its verification level. Many carry no more
than the citation: on the six companies in scope, more than half the rows (about 56% at the golden fixtures) have no
answer key and read Unverified, citation only.

Coverage: six companies in the release scope (`config.PROVEN`: MSFT, GOOGL, AMZN, NVDA, APLD, AMD), 100 tracked
(`docs/COMPANIES.md`), fiscal years 2022 to 2026, annual. A company is proven when none of its rows is open (each is
checked or explained); that is not a claim that every figure is right. The hand-check gate on the Release page stays
red until every gold item has a verdict.

The web app, Kenny's Data Emporium (`ledger app`, port 3610), shows every row's state, the review queue, the release
checklist and these docs.

## Architecture

```mermaid
flowchart TD
  subgraph Ingest["ledger/ingest"]
    A["EDGAR fetch<br/>10-K, 10-K/A, cached with SHA-256"] --> B["Table parser and statement locator"]
    A --> K["XBRL answer key<br/>reference_values"]
  end
  subgraph Read["ledger/extract"]
    B --> T["Task per filing<br/>tables only, no XBRL<br/>task fingerprint task_sha"]
    T --> R["Headless agents, claude -p, no tools<br/>versioned prompts agents/prompts/name@vN"]
    R --> O["Outputs with citations<br/>data/*/outputs, kept as evidence"]
  end
  subgraph Check["ledger/checks"]
    O --> C["Citation resolution<br/>cell exists and equals the value"]
    C --> L["Verification ladder<br/>answer keys, graded"]
    K --> L
    L --> U["Rules<br/>20 in rules/*.yaml"]
    U --> S["One state per row<br/>checked, explained, open, blocked"]
    C --> E["Second read on the rendered 10-K<br/>crops of the cited cell"]
  end
  subgraph Review["ledger/review"]
    S --> Q["Reconcile queue<br/>open rows only"]
    Q --> D["Definitions, rules, resolutions<br/>append-only, keyed to content"]
    D --> S
  end
  subgraph Eval["evaluation"]
    G["Golden regression<br/>fixtures/, ledger golden --check"]
    H["Gold hand-check set<br/>gold/TICKER.json"]
    F["Planted faults<br/>ledger faults"]
  end
  subgraph Release["ledger/release"]
    S --> CL["Release checklist<br/>gates G1 G4 G5 G6, golden, gold, tests, claims"]
    G --> CL
    H --> CL
    CL --> P["Packet releases/vX.Y.Z<br/>CSVs, QUALITY, DIFF, LIMITATIONS, manifest"]
    P --> SG["Signoff by a person<br/>SIGNOFF.json, content hash"]
    SG --> PG["Postgres<br/>one table per file, current_* views, read-only role"]
  end
```

The stages, with the module that owns each (full map: [docs/MAP.md](docs/MAP.md)):

1. **Fetch** (`ledger/ingest/edgar.py`). 10-Ks from FY2022 on, cached by SHA-256. `LEDGER_OFFLINE=1` serves every read
   from the cache and refuses anything uncached.
2. **Locate** (`ledger/ingest/tables.py`, `statements.py`). HTML tables parsed into cells; income, cash-flow and note
   tables located. The filer's XBRL facts become the answer key (`reference_values`), never shown to a reader.
3. **Extract** (`ledger/extract/`). One task per filing per reader. Five live agents, each with a charter in
   `agents/charters/`: statements (`statements@v2`), notes (`notes@v3`), AI statements (`aispend@v4`), projects
   (`projects@v1`) and the asset-type mapper (`mapper@v1`). They run headless on a subscription (`claude -p`, no tools),
   answer in JSON against a schema (`agents/schemas/`), get one retry with the reason, then a logged failure. Every run
   records model, tokens, seconds, attempts and the task's SHA-256 (`runs`). An output loads only if it answered the
   current task.
4. **Resolve citations** (`ledger/extract/extract.py`, rule `citation_resolves`). Every value names table, row, column
   and cell; the cell must exist in the parsed filing and equal the value with its unit and sign rule. Quotes must
   match their source text after normalisation.
5. **Verify** (`ledger/checks/`, `ledger/core/status.py`). The answer keys, the rules, and a second read of the cited
   cells on the 10-K rendered in Chrome (`ledger/checks/crops.py`): for the six in scope, a crop of each cited cell,
   written by `ledger evidence --crops` and not kept in git. Each row's state (checked, explained, open, blocked) comes
   from one function, `status.state`, which Proof, Reconcile, the trail and the gates read. The other words a page shows
   (crop, gold verdict, checklist line, EDGAR freshness and more) come from their own state machines in
   `ledger/core/states.py` ([docs/STATES.md](docs/STATES.md)).
6. **Review** (`ledger/review/`, the Reconcile page). Only open rows reach a person, each with the reason code could
   not decide it. A decision is a definition (`definitions/companies.yaml`), a rule (`rules/`), or a resolution
   (`decisions/resolutions.jsonl`) keyed to a hash of the item's content, so it lapses when its inputs change.
7. **Evaluate** (`ledger/checks/golden.py`, `ledger/review/gold.py`, `ledger/checks/faults.py`). Below.
8. **Release** (`ledger/release/`). The checklist gates the packet; a person signs its content hash; `publish` writes
   it to Postgres.

## Verification ladder

A checked row names the strongest record that agrees with it, ranked by how independent it is of the reading. Strongest first
(`status.KEY_GRADE`, `ties.fact_state`, words from `ledger/core/states.py`):

| Rung | Page word | Proves | Does not prove |
|---|---|---|---|
| Twin XBRL match (`xbrl`) | Verified | The number read from the document is the number the filer tagged for the same concept and period, to the unit and sign. The reader never saw the tag. | That the filer is right. XBRL and the 10-K come from the same company, so an error made in both passes. |
| Tie to a tagged total (`rule:<id>_tie`) | Corroborated | The parts one filing prints sum to the total the same filing tags, within (n + 1) × half the coarsest rounding unit. | That any one part is right. Two misreads that offset inside the bound still tie. |
| Second reading (`reading:<accession>`) | Corroborated | Two or more of the filer's 10-Ks print the same figure within half a rounding unit, so it is not one reader's one-off misread. | Anything upstream of the table: it is usually the same preparer's table carried forward and read by the same reader. |
| Company tag (`mapping:filer_tag`) | Matches company tag | A reported PP&E category's us-gaap member is the one the company's own XBRL uses for it. | That the amount is right; this is a classification check. |
| Citation only (`label:no_reference`) | Unverified | The cited cell exists and holds the value. | Anything beyond the citation: no tag, no tie, one reading. |

A label never counts as a check: every checked or explained row must point at the record it rests on, and a walk over
the proven set fails on any that does not (`status.evidence_gap`, `proof.unevidenced`). The Proof page counts the rows
by their strongest key ("Rows by answer key"); [docs/PROOF.md](docs/PROOF.md) explains the grading. Second source and
later truth are declared keys that no row carries yet.

## Evaluation

No model grades another model. Every check is deterministic code, so a score reruns to the same result.
Detail: [docs/EVALS.md](docs/EVALS.md).

- **Golden regression** (`ledger golden --check`). Rebuilds the proven six from frozen inputs (`fixtures/`: parsed
  tables, texts, the agents' answers) in a temporary folder with nothing fetched and no agent asked, and compares every
  table column by column. Agents are frozen on purpose: their answers are inputs, the checks on them are under test.
  Equal tables mean nothing changed, not that anything is right. Last run: tables equal (`reports/golden.json`).
- **Gold set** (`gold/<TICKER>.json`, `ledger gold`). Per proven company 10 values and 10 facts, stratified by field and
  year, untagged facts oversampled to 6 of 10, drawn with a per-release seed. A person gives each item a verdict
  against the filing: right, wrong or can't say. The error rate is wrong of (right + wrong) with a Wilson 95% interval
  (`ledger/core/stats.py`), overall and per group of what else vouches for the item (`gold.rates`): no SEC counterpart,
  definition differs, not extracted, not reconciled, calculated, matches SEC XBRL. The group with no SEC counterpart is
  quoted first, because there the person is the only check. Verdicts are being given now; the live counts and intervals
  are in `ledger gold --status` and the Hand check section of the Proof page. Until every item has a verdict the
  Golden line on the Release page is red.
- **Planted faults** (`ledger faults`). Real extractions corrupted one at a time in nine ways (wrong column, stale
  column, wrong row, scale, sign, digits, omission, wrong table, systematic). Stage 3 run
  (`reports/stage3-faults.json`): 31,206 planted, 29,258 caught by a rule, 131 caught only by XBRL, 1,805 no effect on a
  released value, 12 escaped. With XBRL off (`reports/stage3-faults-xbrl-off.json`): 143 escaped. Planted kinds are not
  the real error mix; the catch rate bounds what the checks can see.
- **Per-agent scores** (`ledger/checks/score.py`, Rules page). Each reader's outputs counted checked, explained, open and
  blocked, agreement with its twin where one exists, with denominators and a Wilson interval.
- **Tests.** `ledger test` runs the suite offline and writes `reports/tests.json`, which the Release page's Test run
  line reads.

## Data model

DuckDB in development (`data/ledger.duckdb`, schema in `ledger/core/store.py`), Postgres for signed releases. Full
column reference: [docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md).

| Table | Grain | Holds |
|---|---|---|
| `documents` | filing | accession, form, dates, SHA-256, parser version, the located statement tables |
| `reference_values` | XBRL fact | the answer key: concept, period, value, from the filer's instance |
| `extractions` | cited cell | the statements reader's value with table, row, column, cell |
| `values` | company × field × fiscal year | revenue, capex, opex with basis, first-reported figure and reconcile label |
| `note_extractions`, `facts` | cited cell, fact | note figures per filing, and per fact across filings |
| `texts`, `ai_statements`, `ai_spend` | text, quote | MD&A, 8-K releases, transcripts; verbatim AI-spend statements |
| `projects` | named project | data centers, fabs, power, commitments, with quotes |
| `rules`, `exceptions` | rule, firing | the rule registry with file hashes; every firing on a row |
| `decisions`, `runs` | decision, agent call | review decisions; model, tokens, seconds, attempts, task hash |

The release's `taxonomy` list gives one row shape for spent, committed, derived, planned and company-stated AI figures,
every category a named standard's concept, built by code ([docs/TAXONOMY.md](docs/TAXONOMY.md)). The read API
(`/api/v1/`, [docs/API.md](docs/API.md)) serves every list as JSON or CSV, with `?as_of=YYYY-MM-DD` for point-in-time
reads from filing dates.

## Releases and contracts

- **Gates** (`ledger/release/release.py` `GATES`, per company):
  - G1: every filing ended in a valid output or a logged failure, and no failure is open.
  - G4: no block exception without a current decision.
  - G5: every value XBRL can't vouch for, plus a random sample of those it can, confirmed on the filing at the value
    being released: by the re-read of the rendered 10-K, or by the hand-check file (`golden/stage<N>-handcheck.json`)
    where the re-read did not confirm the cell.
  - G6: no decision left by a run for a person to confirm (`decisions/resolutions.jsonl`, "to confirm"), and no
    asset-type mapping without a person's `confirmed_by` (`taxonomy/asset_types.yaml`).
- **Checklist** (`ledger/release/checklist.py`, the Release page): the gates plus open and blocked items, answer-key
  values missing from the dataset, unmapped asset types, the golden test and gold set, the test run on the signed
  commit, the claims register and the previous releases' hashes. Signing is enabled only when every required line is
  green.
- **Packet** (`releases/vX.Y.Z/`): `values.csv`, `facts.csv`, `statements.csv`, `ai_spend.csv`, `projects.csv`,
  `taxonomy.csv`, `companies.csv`, `README.md`, `QUALITY.md` (what a person checked), `DIFF.md` (against the previous
  version), `LIMITATIONS.md` (from `taxonomy/limitations.yaml`, from the next release on) and `manifest.json` (prompt,
  parser, model, rule file hashes). Files are LF, hashed before writing and read back byte-exact; the same inputs give
  the same hash.
- **Signoff** (`SIGNOFF.json`): signer, time, hash and the checklist as it stood. A person signs; agents never do.
  Latest: v1.8.0, 71 values, 327 facts, 617 taxonomy rows, 227 statements, 182 projects, signed by Kenny Geiler
  (`releases/v1.8.0/SIGNOFF.json`).
- **Production** (`ledger/release/publish.py`): Postgres, one table per release file plus `ledger_releases`; every row
  carries its release version, and `current_*` views follow the highest published version. Consumers get the
  read-only `DATABASE_READONLY_URL` role, SELECT only.
- **Claims register** (`claims/claims.yaml`, `claims/findings.jsonl`, `ledger claims`): every claim a page, the API or a
  release makes, with the functions and tests that back it and a computed status; generated view in
  [docs/CLAIMS.md](docs/CLAIMS.md), live on the Known gaps page.

## Known limitations

From `taxonomy/limitations.yaml`, `docs/CLAIMS.md` and [docs/HANDOFF.md](docs/HANDOFF.md):

- **Same-filer answer key.** XBRL and the 10-K are both the company's; agreement is an independent reading of one
  source, not independent sources.
- **Ties bound sums, not parts.** Two offsetting misreads inside the tolerance still tie.
- **Second readings share pedigree.** A repeated misreading of a carried-forward table agrees with itself.
- **Without a structured twin, systematic errors escape.** With XBRL off, 143 planted faults escaped (above); sources
  without tags (ESEF without tags, KPI tables, transcripts) are exposed.
- **Omissions.** Some planted omissions escape every check.
- **"Proven" means nothing open.** Every row is checked or explained; explained rows include citation-only figures.
- **Gold is incomplete.** Not every gold item has a verdict yet, and with a small sample the error-rate interval is
  wide (live: `ledger gold --status`).
- **Crops are local and cover the six.** The pictures of cited cells are not in git (the repository is public); a clone
  rebuilds them with `ledger evidence --crops`. Companies outside the scope have none, and neither has the hosted copy.
- **Old statement outputs without a fingerprint.** 13 statement outputs predate task fingerprints (`_run.task_sha`) and
  load unjudged until they are read again (listed in [docs/HANDOFF.md](docs/HANDOFF.md)).
- **Open review findings.** The current list is on the Known gaps page and in [docs/CLAIMS.md](docs/CLAIMS.md).
- **One person.** The same person builds, reviews and signs; there is no second reviewer and no sign-in (the name in the
  signer box is a claim, checked against `config.PEOPLE`).
- **Interpretive fields unmeasured.** For AI statements and projects only the quote is checked, not what the reader
  concluded from it.
- **Asset-type mappings.** Agent proposals until a person confirms each or the company's own tag matches; unconfirmed
  ones fail G6.
- **Outside the proven set** numbers are not proven and not released.
- **Survivor bias.** The universe is today's AI-relevant names.
- **Older vintages** in point-in-time reads are not checked against their own XBRL.
- **No monitoring thresholds.** No floor on twin agreement or fault catch rate stops a release.
- **Stale inputs.** The EDGAR check is manual (`ledger watch`), and the hosted read-only copy has no deploy record.

## Quickstart

```bash
uv sync                                                        # Python 3.12, DuckDB, edgartools, pypdf, playwright
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env        # the SEC requires a contact; never commit .env
uv run python -m ledger test --fast                            # whole suite offline; writes reports/tests.json
uv run python -m ledger run --ticker NVDA                      # every step for one company, agents included
uv run python -m ledger app                                    # http://127.0.0.1:3610
```

The agents run on a Claude subscription, headless: run `claude`, `/login`, then `export LEDGER_CLAUDE="$(which claude)"`.
Without it every code stage still runs on the stored agent outputs. To add a company: `ledger run --ticker X`, give it an
industry in `ledger/core/config.py` `INDUSTRIES`, map its asset types (`ledger mapper X`) and review it on Reconcile.
Release, review and grading routines: [docs/OPERATIONS.md](docs/OPERATIONS.md).

## Repository map

Where everything lives and what to edit for a change: [docs/MAP.md](docs/MAP.md). How the system fits together:
[docs/OVERVIEW.md](docs/OVERVIEW.md). Taking it over: [docs/HANDOFF.md](docs/HANDOFF.md). How a change is built:
[docs/BUILD.md](docs/BUILD.md). Every state machine and its page words: [docs/STATES.md](docs/STATES.md).
