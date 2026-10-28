# Tickets

The backlog for [PRD.md](PRD.md), grouped by milestone. Owner of every ticket: Kenny Geiler. Tickets marked **you** need him; the rest are done by Claude Code.

## Open

### M3: review scales

| ID | Ticket | Done when |
|---|---|---|
| M3.1 | Group open items by cause, so one decision (for example "APLD recast after ChronoScale") covers every item it explains. | `ledger review` lists causes, not rows. |

### Later

| ID | Ticket | Done when |
|---|---|---|
| L1 | Client view: released values only, each with its basis, source and citation link. | Built from a release folder. |
| L4 | `QUALITY.md` notes compare `cost_of_revenue_part` line by line, so separate cost lines aren't reported as restatements. | ORCL and APLD notes show only true restatements; `v1.0.1`. |
| L3 | `DIFF.md` also lists values added since the last release (new companies or years), not only changed ones. | v0.2.0-style "No values changed" can't happen when companies were added. |
| L2 | Non-functional checks as tests: SEC request spacing and contact header; no email or key in any output; parse under 60 s; `uv sync --frozen` works. | 4 tests. |

## Done

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
