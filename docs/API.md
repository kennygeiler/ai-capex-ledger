# The read API: /api/v1

Served by DATAHQ (`ledger app`, http://127.0.0.1:3610) from the working database. What the pipeline holds now;
the production Postgres holds what was signed (`ledger publish`, `docs/HANDOFF.md`). Read-only except views.
JSON by default; CSV with `?format=csv` or a `.csv` suffix. No authentication: it binds to localhost. Put it
behind a proxy that authenticates before exposing it.

## Lists

| Path | One row per | Columns |
|---|---|---|
| `/api/v1/companies` | company | ticker, name, layer, group, role, note |
| `/api/v1/values` | company, field, fiscal year | ticker, field, period, period_end, value, check_label, basis, source, extraction_ids, layer |
| `/api/v1/facts` | company, note field, dimension, year | ticker, field, dimension, period, period_end, value, check_label, xbrl, accession, basis, layer |
| `/api/v1/attribution` | company, field (capex, opex, revenue), year, kind | ticker, field, period, kind, method, ai_amount, ai_share, confidence, basis, inputs, model, prompt_version, run_id, layer |
| `/api/v1/statements` | statement an agent read | statement_id, ticker, field, period, kind, scope, class, amount_low, amount_high, amount_mid, share, quote, source, date, url, layer |
| `/api/v1/plans` | company, field, year, scope | ticker, field, period, scope, plan_low, plan_high, plan_mid, plan_date, plan_source, plan_quote, plan_url, actual, actual_method, gap, gap_share, inside_range, layer |
| `/api/v1/projects` | named project | ticker, period, name, kind, location, amount_low, amount_high, status, announced, in_service, counterparty, quote, source, url, layer (empty until the projects reader has run) |
| `/api/v1/theses` | layer | layer, version, versions, text, companies |
| `/api/v1/views` | saved view | id, name, measure, filters, group, show, note, by, at |

The four measures (`docs/THESIS.md`): capex allocation and revenue exposure are `attribution` rows with field
`capex` or `revenue`; project-level investment is `projects`; plans versus reality is `plans`.

## Filters and grouping

Every list takes `ticker`, `layer`, `period`, `field`, `kind`, `method`, `scope`, `dimension`, `source` as
comma-separated values, matched without regard to case. `group=<column>` rolls the list up: one row per distinct
value with `rows`, `amount` (the sum of the list's amount column: ai_amount, value, amount_mid, gap or amount) and
`with_amount`.

```
/api/v1/attribution?field=capex&kind=actual&layer=hyperscaler
/api/v1/attribution?field=revenue&group=layer
/api/v1/plans?field=capex&scope=total&ticker=META,MSFT&format=csv
/api/v1/facts?field=segment_capex&ticker=APLD
```

A JSON response is `{"list", "count", "filters", "rows"}`.

## Views

A view is a saved question: `{id, name, measure, filters, group, show, note}` where `measure` is one of the lists
above (attribution, values, facts, statements, plans, projects), `filters` and `group` are as above, and `show` is
`grid`, `bars` or `shares` (a hint for the visualizer). Views live in `data/views.json`, tracked.

```
GET  /api/v1/views                 the saved views
GET  /api/v1/views/<id>/data       {"view", "rows"}: the view's query, run now (format=csv for the rows)
POST /api/v1/views                 {"view": {...}, "by": "name"}: save (same id replaces; the old one goes to history)
POST /api/v1/views/<id>/delete     {"by": "name"}
```

## Errors

`404` with `{"error", "lists"}` for an unknown list; `400` for a bad filter or view; `503` while the pipeline holds
the database (`{"error": "the pipeline is writing to the database; try again when the run ends"}`).
