# Capex Ledger

A pipeline that takes a company's 10-K filings and returns revenue, capex and opex, each citing the exact cell it came from. AI agents read, code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release. Success is measured by what the next company costs, not by how many are done.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** The hand-check is now 20 yes/no questions instead of 66 open-ended checks (Kenny's call; G5 changed).
- **Who checks what:** a person checks the values XBRL can't vouch for (the 4 APLD recast values and 6 Oracle/APLD definition gaps) plus 10 random values XBRL agrees with. The other 46 are verified by two independent sources, the 10-K cell and XBRL.
- **The page:** shows a "Check these numbers" card for each, naming the row, column and number to find in the filing, with Yes/No buttons. Decided items now show "accepted by Kenny Geiler" instead of red.
- **Earlier today:** Kenny's 6 stage 2 decisions recorded, and the cost-line check fixed (0 of 862 faults escape).

**Next:**
1. **Kenny (P2):** answer the 20 cards on `reports/stage2-validation.html`, click "Download hand-check", save it as `golden/stage2-handcheck.json`, then say to release and sign `v0.2.0`.
2. **Kenny (M1.1):** run `claude login` once in a terminal.
3. **Claude (M1.2–M1.4):** headless extraction, `ledger run --ticker X`, scorecard.

**Critical notes:**
- **Dashes are zero.** APLD's newest 10-K shows "—" for its data-center cost line in FY2024 and FY2025; agents read these as 0.
- **NVDA's capex line includes intangible assets.** Note it when comparing companies.
- **Known blind spot:** a wrong-row misread is caught by comparing a company's filings with each other, so a company's first filing is less protected.
- **Running agents:** extraction runs as Claude Code subagents inside the session (no paid API). Headless runs need `claude login`.
- **Old work is in tags:**
  - `takehome-xbrl-explorer`: the 113-company explorer
  - `quarterly-v0.1`: the quarterly pipeline

## How it works

| Step | Command | Produces |
|---|---|---|
| Ingest | `ingest` | 10-Ks fetched and cached with SHA-256; tables parsed; statements located |
| Extract | `extract --pack`, then agents, then `extract --load` | One task per 10-K (tables only, no XBRL); agent values with citations, each checked against the cell |
| Reconcile | `reconcile` | Fiscal-year values with their basis and first-reported figure, compared with XBRL |
| Rules | `rules` | Exceptions from the 14 rules in `rules/*.yaml` |
| Faults | `faults` | Every cell corrupted in typical ways, and what caught each |
| Report | `report` | `reports/stage<N>-validation.html`: plain-language review page and hand-check |
| Review | `review`, `review decide` | `decisions/decisions.jsonl`; a decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`; refuses while any gate fails, and the same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` |

Every command runs as `uv run python -m ledger <command> --stage N`. The XBRL reference is pulled with `python -m ledger reference`.

## Repo

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, 10-K list, table parser, statement locator, restatement-note finder |
| `ledger/extract.py`, `reconcile.py` | Tasks and citation checks; fiscal-year values |
| `ledger/rules.py`, `rules/` | Rule engine and the 14 rules |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | XBRL reference pipeline (output: `data/clean/facts.csv`) |
| `agents/` | Prompt and output schema |
| `data/extract/outputs/` | Agent outputs, kept as evidence |
| `docs/` | [PRD](docs/PRD.md), [tickets](docs/TICKETS.md), [fields](docs/FIELDS.md), [ingestion and learnings](docs/INGESTION.md) |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
