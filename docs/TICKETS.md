# Tickets

The backlog for [PRD.md](PRD.md), grouped by milestone. Owner of every ticket: Kenny Geiler. Tickets marked **you** need him; the rest are done by Claude Code.

## Open

### M0: finish the hand-run loop

| ID | Ticket | Done when |
|---|---|---|
| P1 | **you:** Decide stage 2's 4 blocking items: APLD revenue and opex FY2024–FY2025, recast after the ChronoScale transaction (the page quotes the note). Confirm the ORCL and APLD cost lines; decide the warnings. | `ledger review --stage 2` shows 0 open. |
| P2 | **you:** Look over the stage 2 page (all 20 checks are machine-confirmed, with boxed screenshots), then say to release and sign `v0.2.0`. | Signed. |

### M1: it runs unattended

| ID | Ticket | Done when |
|---|---|---|
| M1.1 | **you:** run `claude login` once in a terminal, so agents can run headless on the subscription. | `claude -p "ok"` answers. |
| M1.2 | Headless extraction: one `claude -p` call per filing with the frozen prompt; validate the output, retry once, log a failure otherwise. Record model, tokens and seconds in `runs`. | A filing is extracted with nobody in the chat. |
| M1.3 | `ledger run --ticker X [X…]`: fetch, parse, extract, check, report in one command. Cached and safe to rerun. Ticker sets replace `--stage`. | A never-seen company gets its validation page with no manual step. |
| M1.4 | Scorecard: per company, the code changes it needed, items that reached a person, person minutes, and agent tokens and seconds. One table in the validation page and in INGESTION.md. | Shows for the 5 stage 2 companies. |

### M2: a new company needs no code

| ID | Ticket | Done when |
|---|---|---|
| M2.1 | Blind run: the 14 unseen companies, pipeline frozen. Record every failure by type (parsing, locating, reading, definition) in INGESTION.md, with the first-pass rate. | Every failure has a type. |
| M2.2 | Fix by type, never by company; rerun the whole batch after each fix. The IREN locator miss is the first known type. | A full rerun of all 19 needs no code change. |

### M3: review scales

| ID | Ticket | Done when |
|---|---|---|
| M3.1 | Group open items by cause, so one decision (for example "APLD recast after ChronoScale") covers every item it explains. | `ledger review` lists causes, not rows. |
| M3.3 | **you:** review, hand-check the sample, and sign `v1.0.0` (19 companies). | Signed. |

### Later

| ID | Ticket | Done when |
|---|---|---|
| L1 | Client view: released values only, each with its basis, source and citation link. | Built from a release folder. |
| L2 | Non-functional checks as tests: SEC request spacing and contact header; no email or key in any output; parse under 60 s; `uv sync --frozen` works. | 4 tests. |

## Done

- **Rendered-10-K re-read (28 Oct):** `ledger evidence` confirms each cited cell on the 10-K as rendered in Chrome and screenshots it boxed; G5 accepts a machine confirmation, and a person answers only cards it can't confirm.
- **Sampled hand-check (M3.2, pulled forward, 28 Oct):** a person checks only the values XBRL can't vouch for, plus 10 random agreeing ones. Each is one yes/no question on the page; decisions show as decided, not red. Stage 2: 20 checks instead of 66.
- **M0, built by hand (to 28 Oct 2026):**
  - **Ingest:** 10-K list per company; documents cached with SHA-256; table parser (`tables@7`, fixture-tested); statement locator (176/177 correct); restatement-note finder.
  - **Extraction:** tasks with no XBRL in them; prompts `statements@v1` and `@v2` (cost lines classified when there is no total); citation resolver; outputs kept in git.
  - **Values:** one filing per company-year; opex from one column; restated basis with `first_reported` kept; summed cost lines; `definition_gap` when only XBRL's cost-of-revenue definition differs.
  - **Rules:** 14 in `rules/*.yaml`, each with a rationale, a plain-English explanation and an action, each tested to pass and fail.
  - **Fault injection:** 0 of 862 misreads escaped (stage 2).
  - **Validation pages:** plain-language story, decision cards, charts, links into each filing, the filing's own restatement sentence.
  - **Review, release, sign-off:** decisions re-apply only on unchanged inputs; gates G1, G4 and G5; deterministic hash.
  - **`v0.1.0`** (NVDA, 15 values) signed by Kenny Geiler, hash 2b15699badbe.
  - **Held-out test:** ORCL and APLD, run once with the prompt frozen; 140/140 checkable cells read correctly across stage 2.

The quarterly-era tickets and results are in tag `quarterly-v0.1`. How the pipeline works and what each finding changed: [INGESTION.md](INGESTION.md).
