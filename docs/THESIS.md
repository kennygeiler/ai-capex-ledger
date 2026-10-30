# The four measures, the thesis, the API and the views

What the product is for (Kenny, 30 Oct 2026): extract what moves the needle, not one number for everyone. Four
measures per company: revenue exposure, capex allocation, project-level investment, transition plans versus
reality. The "what" comes from a methodology per sector, vertical and instrument, which for this project is AI
across its supply chain. Each layer carries an investment thesis built from research and edited by a person; the
pipeline ingests, cleans, transforms, understands the documents, and the thesis tells it what to pull out. The
visualizer lets a person create and edit views, and everything is queryable through endpoints so another system can
ingest it.

## The four measures and where each comes from

| Measure | Question | Table | Method | Status |
|---|---|---|---|---|
| Capex allocation | how much of this year's capex is AI | `attribution` (field capex, opex) | stated share or amount, segment capex, PP&E category growth, whole business | built; 100 companies running |
| Revenue exposure | how much of revenue comes from AI demand | `attribution` (field revenue) | stated share or amount, segment revenue, whole business | built 30 Oct: the attributor's third field, same contract and arithmetic |
| Project-level investment | which named projects, how big, what stage, who pays | `projects` | a projects reader over releases, MD&A and transcripts: name, kind, location, amount, status, dates, counterparty, quote | prompt and loader built; runs after the 100-company run frees the pipeline |
| Plans vs reality | what the company said it would spend, and what it spent | `plans` view over `ai_spend` and `values` | code only: guidance for year Y (outlook statements made before Y ends) against the actual for Y; the newest guidance before the year end is "the plan" | built 30 Oct |

A seller's revenue exposure is the seller-side signal the capex models already describe in `basis`; now it is a
row with a method and inputs, so it can be queried and checked, not read out of a sentence.

## The thesis

One per layer, versioned, never edited in place (`agents/models/<layer>@vN.md`; the file was called a money-flow
model and still is, one section of a thesis). Sections, in order:

1. **Thesis**: what moves the needle for this layer in three to six lines; which of the four measures matter and
   which do not; the signal a reader should watch.
2. **Companies**: who sits here and why; who is at the edge of the layer.
3. **Where the AI money shows up**: the data items the methods draw on.
4. **How to attribute**: capex and opex (as before) and revenue, by method, in order of hardness, with confidence
   ceilings.
5. **Projects**: what counts as a project for this layer and the words that name one.
6. **Traps**.

Edit it in DATAHQ (Attribution tab, or Flow, Method), save as the next version, dry-run it, switch it on, rerun
the layer. The dataset changes; the filings are not re-read.

## The API

`/api/v1/...`, served by DATAHQ from the working database, JSON by default and CSV with `?format=csv`. Every list
takes `ticker`, `layer`, `period`, `field` as filters. Read-only. Documented in `docs/API.md` with one example per
endpoint. The production Postgres holds the same tables for signed releases, so an external consumer can read
either: the API for what the pipeline holds now, Postgres for what was signed.

## Views

A view is a saved question: a measure, filters, a grouping, and how to show it (grid, bars by year, share by
company). Stored in `data/views.json`, created and edited in DATAHQ, served at `/api/v1/views` and
`/api/v1/views/<id>/data`, so a view built by a person is a query another system can call.

## Dry runs before the switch-on (30 Oct 2026)

Each sourced thesis (ticket C2) was run against its layer with `attribution --model-version X@vN --dry-run` before `use_model`, under the `attribution@v1` prompt. New rows are mostly revenue exposure; removed rows are `none` rows the thesis no longer emits. The reference column is agreement with `gold/ai_capex.yaml` for the layer's companies, before and after.

| Thesis | replaced | companies | rows changed | new | removed | reference agree before | after |
|---|---|---|---|---|---|---|---|
| ai_software@v3 | ai_software@v1 | 6 | 3 | 5 | 17 | 0/0 | 0/0 |
| chip_equipment@v3 | chip_equipment@v1 | 8 | 0 | 22 | 0 | 0/0 | 0/0 |
| chip_seller@v3 | chip_seller@v1 | 14 | 0 | 66 | 22 | 0/5 | 3/5 |
| component_supplier@v3 | component_supplier@v1 | 18 | 1 | 58 | 82 | 0/3 | 2/3 |
| datacenter_build@v3 | datacenter_build@v1 | 11 | 0 | 35 | 24 | 0/2 | 1/2 |
| datacenter_landlord@v3 | datacenter_landlord@v1 | 3 | 4 | 0 | 1 | 0/0 | 0/0 |
| hyperscaler@v4 | hyperscaler@v2 | 5 | 0 | 6 | 3 | 2/5 | 2/5 |
| miner_to_hpc@v3 | miner_to_hpc@v1 | 11 | 1 | 40 | 10 | 0/5 | 2/5 |
| neocloud@v3 | neocloud@v1 | 1 | 0 | 3 | 0 | 1/2 | 2/2 |
| other@v3 | other@v1 | 12 | 1 | 33 | 56 | 0/1 | 0/1 |
| power@v3 | power@v1 | 4 | 2 | 6 | 7 | 0/0 | 0/0 |
