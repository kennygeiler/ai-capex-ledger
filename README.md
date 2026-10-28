# Capex Ledger

AI agents read SEC 10-K filings and extract revenue, capex and opex, citing the exact cell each number came from. Code checks every citation, rules encode the judgement, XBRL serves as a free answer key, and a person reviews and signs each release.

## Status

*Updated with every commit.*

**Last done (28 Oct 2026):** Review now asks a person only what code can't explain.
- 6 of stage 2's 10 XBRL disagreements had one known cause: XBRL draws cost of revenue differently (Oracle tags none; APLD's FY2026 tag covers one of two lines). Code now labels these `definition_gap` and shows both numbers. You confirm the cost lines once per company instead.
- For restated or disputed values, the page quotes the 10-K's own explanation, with a link.
- New [docs/INGESTION.md](docs/INGESTION.md): the flow, who decides what, and a learnings log; every finding must end as a definition, rule, code or prompt change, or a recorded decision.
- Stage 2: 66 values: 56 agree, 6 definition gaps, 4 blocking. Faults 0 of 862 escaped. `v0.1.0` (NVDA) stays signed.

**Next:**
1. **Kenny (your turn):** on `reports/stage2-validation.html`, decide the 4 blocking APLD items (revenue and opex, FY2024–FY2025). Each card quotes APLD's note: prior years were recast after it moved its Cloud Services business to ChronoScale. Read it, then accept with that reason, or tell Claude to.
2. **Kenny:** confirm the cost lines on the ORCL and APLD `cost_lines_summed` cards; decide the other warnings; hand-check; release and sign `v0.2.0` (due 6 Nov).
3. The rest is in [docs/TICKETS.md](docs/TICKETS.md).

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
