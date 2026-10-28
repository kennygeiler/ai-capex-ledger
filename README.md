# Capex Ledger

AI agents read SEC 10-K filings and extract revenue, capex and opex, citing the exact cell each number came from. Code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** the project now uses 10-Ks only: one value per company per fiscal year, no quarterly arithmetic.
- **Fields:** revenue, capex and opex (revenue − cost of revenue − operating income, from one 10-K column). See [docs/FIELDS.md](docs/FIELDS.md).
- **Reading:** all 140 10-K cells match XBRL, including 56/56 on the held-out ORCL and APLD.
- **Fault injection:** 0 of 700 escaped.
- **Restatements:** the newest 10-K wins and the first figure is kept. A year never mixes filings.
- **Removed:** the quarterly work, including the earlier signed `v0.1.0`. It's preserved in tag `quarterly-v0.1`.

**Next:**
1. **Kenny:** hand-check NVDA's 15 values on `reports/stage1-validation.html` and save the export as `golden/stage1-handcheck.json`. Then:
   ```bash
   uv run python -m ledger release v0.1.0 --stage 1
   uv run python -m ledger signoff v0.1.0 --by "Kenny Geiler"
   ```
2. **Kenny:** decide stage 2's 2 blocking items. APLD's revenue for FY2024 and FY2025 differs from XBRL because the newest 10-K presents those years differently. Then decide the warnings, hand-check, and release `v0.2.0` (due 6 Nov).
3. The rest is in [docs/TICKETS.md](docs/TICKETS.md).

**Critical notes:**
- **Oracle's opex is blank.** Oracle reports no cost-of-revenue line. Data vendors fill this by adding up cost lines; whether we do is an open decision (A9).
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
| Rules | `rules` | Exceptions from the 13 rules in `rules/*.yaml` |
| Faults | `faults` | Every cell corrupted in typical ways, and what caught each |
| Report | `report` | `reports/stage<N>-validation.html`: plain-language review page and hand-check |
| Review | `review`, `review decide` | `decisions/decisions.jsonl`; a decision counts only while its inputs are unchanged |
| Release | `release <v>` | `releases/<v>/`; refuses while any gate fails, and the same inputs give the same hash |
| Sign | `signoff <v> --by` | `SIGNOFF.json` |

Every command runs as `uv run python -m ledger <command> --stage N`. The XBRL reference is pulled with `python -m ledger reference`.

## Repo

| Path | What |
|---|---|
| `ledger/ingest/` | SEC client, 10-K list, table parser, statement locator |
| `ledger/extract.py`, `reconcile.py` | Tasks and citation checks; fiscal-year values |
| `ledger/rules.py`, `rules/` | Rule engine and the 13 rules |
| `ledger/faults.py`, `review.py`, `release.py` | Fault injection, decisions, releases |
| `ledger/store.py` | DuckDB schema and write contracts ([docs/DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md)) |
| `ledger/reference/` | XBRL reference pipeline (output: `data/clean/facts.csv`) |
| `agents/` | Prompt and output schema |
| `data/extract/outputs/` | Agent outputs, kept as evidence |
| `docs/` | [PRD](docs/PRD.md), [tickets](docs/TICKETS.md), [fields](docs/FIELDS.md) |

## Setup

```bash
uv sync
echo 'SEC_USER_AGENT="Your Name you@example.com"' > .env   # SEC requires a contact email
uv run python -m unittest discover -s tests -t .
```
