# Capex Ledger

AI agents read SEC filings and extract revenue, cost of revenue, operating income and capex, citing the exact cell each number came from. Code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** restatements now follow standard practice ([docs/FIELDS.md](docs/FIELDS.md)):
- Values use the restated basis; the newest filing wins.
- Each value carries `basis` (`as_reported`, `restated` or `mixed`) and its `first_reported` value.
- A quarter whose inputs span a restatement ships blank.
- **APLD:** 25 quarters on the restated basis agree with XBRL; 5 are blank because no single basis exists.
- **Blocking items:** down from 12 to 4.
- **Fault injection:** 0 of 3,014 escaped. The first rerun after the restatement change found 140 escapes: a corrupted cell could quietly turn a quarter blank, because only cells behind released values were checked. `citation_resolves` now checks every extracted cell.
- **Validation pages:** they explain all of this in plain language.

**Next (Kenny):**
1. Decide the 4 blocking items on the stage 2 page:
   - **APLD Q3 2025 cost of revenue:** $55.6M against XBRL's restated $58.8M. The later filing splits the line into parts, which we don't add together.
   - **APLD Q3 2024:** a one-time gain inside operating expenses.
   - **Two sub-1% recasts:** APLD fiscal-2024 nine-month operating income, outside the window.
2. Decide the 16 warnings.
3. Settle the hand-check scope: all 151 values, or only the held-out companies (G5).
4. Hand-check, release `v0.2.0`, sign. Due 6 Nov.

**Critical notes:**
- **Stage 1 doesn't prove accuracy elsewhere.** It proves the system works on the company the prompt was written for. Accuracy on companies the agents haven't seen starts with stage 2.
- **Stage 2 must be done before the call with the data-startup CEO (11/12 Nov).**
- **Capex definitions differ.** NVDA's capex line includes intangible assets. See [docs/FIELDS.md](docs/FIELDS.md) before comparing companies.
- **Known blind spot:** about a third of wrong-row misreads are caught only by comparing a company's filings with each other, so a company's first filing is less protected.
- **Running agents:** today, Claude Code subagents run inside the session (no paid API). Headless runs (`claude -p --tools ""`) need `claude login` in a terminal first.
- **The old work is in a tag.** The 113-company XBRL explorer, the one-page summary and the earlier prototypes are no longer in the tree. Recover them with `git checkout takehome-xbrl-explorer`.

## How it works

| Step | Command | Produces | Guarantee |
|---|---|---|---|
| Ingest | `ingest` | Filings fetched and cached with SHA-256; tables parsed; statements located | A rerun makes no network calls and gives byte-identical output |
| Extract | `extract --pack`, then agents, then `extract --load` | One task per filing (tables only, no XBRL); agent values with citations | A value without a cell that matches is never stored |
| Reconcile | `reconcile` | Calendar quarters, each with its fiscal label, compared with XBRL | Same derivation code as the reference |
| Rules | `rules` | Exceptions from the 15 rules in `rules/*.yaml` | Each rule has a passing and a failing test |
| Faults | `faults` | Every extraction corrupted in 6 ways, and what caught each | Stage 1: 0 of 710 escaped |
| Report | `report` | `reports/stage<N>-validation.html`: every value, its arithmetic and cells, and links into the filing | The hand-check is exported to `golden/` |
| Review | `review`, `review decide` | `decisions/decisions.jsonl` | A decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`: values, quality notes, diff, manifest | Refuses while any gate fails; same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` | Signs the content hash |

All commands are `uv run python -m ledger <command> --stage N`. The XBRL reference is pulled with `python -m ledger reference`.

## Stages

| Stage | Companies | Hand-checked | Claim | Release |
|---|---|---|---|---|
| 1 | NVDA | all 32 | The system works end to end | `v0.1.0` (signed) |
| 2 | + MSFT, CRWV (tuning); ORCL, APLD (held out) | held-out values | Reading: 216/216 held-out cells, error rate under 1.4% at 95% confidence | `v0.2.0` (awaiting decisions) |
| 3 | all 19 | 300 held-out values | Error rate under 1% at 95% confidence | `v1.0.0` |

## Stage 1 evidence

- 11 filings read; 130 cells cited, all resolving.
- All 32 quarterly values agree with XBRL, and Kenny hand-checked all 32.
- **Fault injection:** 0 of 710 injected misreads escaped the rules.
- **No-locator test:** given every table, the agent found the statements in 3 of 3 filings and gave the same 34 values.
- **Repeatability:** a fresh agent rerun matched 34 of 34.
- Details: [docs/QA-stage1.md](docs/QA-stage1.md).

## Repo

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, filing list, table parser, statement locator |
| `ledger/extract.py`, `derive.py`, `reconcile.py` | Tasks and citation checks; quarters; XBRL labels |
| `ledger/rules.py`, `rules/` | Rule engine and the 15 rules |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | The XBRL reference pipeline (output: `data/clean/facts.csv`) |
| `agents/` | Prompt and output schema |
| `data/extract/` | Agent outputs, kept as evidence |
| `golden/`, `decisions/`, `releases/` | Hand-checks, decisions, signed releases |
| `docs/` | [PRD](docs/PRD.md), [tickets](docs/TICKETS.md), [fields](docs/FIELDS.md), [QA](docs/QA-stage1.md), and the review pages in `docs/review/` |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
