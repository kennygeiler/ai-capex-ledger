# Tickets

The backlog for [PRD.md](PRD.md). Owner of every ticket: Kenny Geiler. Tickets marked **you** need him; the rest are done by Claude Code.

## Open

| ID | Ticket | Done when |
|---|---|---|
| A3 | **you:** Decide stage 2's 4 blocking items: APLD revenue and opex FY2024–FY2025, recast after the ChronoScale transaction (the page quotes the note). Then confirm the `cost_lines_summed` lines and decide the warnings. | `ledger review --stage 2` shows 0 open. |
| A4 | **you:** Hand-check stage 2's values; release and sign `v0.2.0`. | Signed before 11 Nov. |
| A5 | Stage 3: run extraction on the remaining 14 companies' 10-Ks with the frozen prompt; fix the IREN locator miss first. | Release `v1.0.0`. |
| A6 | Run evidence: headless agent runs (`claude -p --tools ""`) that record model, tokens and time per filing. **You** first need to run `claude login` in a terminal. | `runs` rows carry model and tokens. |
| A7 | Client view: a page showing released values only, each with its basis, source and citation link. | Built from a release folder. |
| A8 | Non-functional checks as tests: SEC request spacing and contact header; no email or key in any output; parse time under 60 s; `uv sync --frozen` works. | 4 tests. |

## Done (28 Oct 2026)

- **Review asks only what code can't explain:** XBRL cost-of-revenue definition gaps are labelled by code (6 items no longer block); the page quotes each restated filing's own explanation; [INGESTION.md](INGESTION.md) holds the flow, who decides what, and the learnings log.

- **Cost of revenue without a total line** is now built as standard tools do: an agent classifies and cites each cost line (prompt `statements@v2`), code adds them up, and `cost_lines_summed` lists them for review (Kenny's decision, 28 Oct).

- **Stage 1:** `v0.1.0` (NVDA, 15 values) signed by Kenny Geiler, hash 2b15699badbe.

- **Ingest:** 10-K list per company, documents cached with SHA-256, table parser (`tables@7`, fixture-tested), statement locator (176/177 correct).
- **Store:** DuckDB schema, write contracts, generated data dictionary.
- **Extraction:**
  - tasks with no XBRL in them; prompt `statements@v1`
  - citation resolver; outputs kept in git
- **Values:** one filing per company-year; opex computed from one column; restated basis with `first_reported` kept; `not_reported` when a line is missing.
- **Rules:** 14 in `rules/*.yaml`, each with a rationale, a plain-English explanation and an action, each tested to pass and fail.
- **Fault injection:** 0 of 862 misreads escaped (stage 2).
- **Validation pages:**
  - plain-language story, task steps and decision cards
  - charts by company; links into each filing
- **Review, release and sign-off:** decisions re-apply only on unchanged inputs; gates G1, G4 and G5; deterministic hash.
- **Held-out test (quarterly era):** ORCL and APLD, run once with the prompt frozen, read 216/216 cells correctly. Those same 10-K outputs feed stage 2.

The quarterly-era tickets and results are in tag `quarterly-v0.1`.
