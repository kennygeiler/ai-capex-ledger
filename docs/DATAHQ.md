# DATAHQ: design audit and the design it runs on now

29 Oct 2026. The app is `ledger/app.py` (routes, read-only on the database) and `ledger/app.html` (one page, no build step).

## Audit of the app as it was (28–29 Oct)

What the ledger does changed under the app. The pipeline no longer asks a person anything; it has three layers (ingest and clean, attribute, insight); the attribution method is the thing a person edits. The app still showed the world of two days ago.

| Finding | Where | Why it mattered |
|---|---|---|
| The first number on the dashboard was "Questions for you", now always 0. | Dashboard | The headline said nothing. The question the ledger exists to answer (how much of the capex is AI) was nowhere on the front page. |
| Five tabs (Dashboard, Companies, Insights, Outputs, Agents) cut across the layers instead of following them. | Nav | Attribution, the layer a person works in, had no tab; its models were editable nowhere. |
| "Your judgement", question cards and the accept-warnings control were dead UI. | Dashboard, company page | Warnings became findings; definitions replaced decisions. Dead controls teach a reader the wrong workflow. |
| The company page put the numbers first and the AI attribution last. | Company page | Inverted: the reader comes for the attribution and wants to walk down to the cells, not up. |
| Insights read only the signed release and showed capex and revenue; no attribution, no money flow. | Insights | The signed release predates attribution; the live tables held the answer and the page ignored them. |
| Outputs duplicated Insights with controls (company, metric, year pickers, CSV) that no one used in the demo. | Outputs | Two pages for one job. The packet download is the one thing Outputs did that nothing else did. |
| Agents mixed the three ingestion readers with the attributor, whose "prompt" is really six model documents. | Agents | A model edit, the loop Kenny asked for (edit, rerun only the agent, see the diff), needs its own place. |
| Visual system: whitespace, one accent, no boxes or dividers, tabular numbers; one hand-drawn line chart. | CSS | Sound. Kept as is. Needed: stacked bars for part-of-whole, and a fixed categorical order (the eight-colour list already is one). |

## The design now

Three tabs, in the order the data flows, plus the company page they all open.

**Pipeline** (home). What was ingested and cleaned, with no one in the loop. Headline figures: companies, filings, texts, facts, cells confirmed on the rendered 10-K, planted faults caught, blocked. A coverage table, one row per company, one column per layer (values agreeing with the SEC's data, facts, statements, AI amount and its method), so a thin company is visible at a glance. Findings with the "SEC data agrees / can't confirm" flag. Add a company, inline, with the step-by-step progress. Links to the readers' prompts and to releases.

**Attribution**. The method is the product. The six money-flow models with the version in use and the companies each covers; an editor that saves a change as the next version and switches it on as a second step, both logged with a name; a "Rerun attribution" button that runs the attributor for one industry or all (nothing is re-read from filings; minutes, not an hour) and shows the diff the load wrote. Below, the grid: companies down, fiscal years across, AI capex with the method under each number; click for the basis and inputs.

**Insights**. From the live tables, labelled as such against the signed release. Buyers' AI capex against their total capex by year, stacked so the unattributed part is visible; AI capex per company for the latest year with the method named, because "server-category growth" and "stated share" are not the same kind of number; sellers' data-center revenue by year beside buyers' AI capex, the money flow; and the method mix. Every chart's colours follow the entity, in fixed order.

**Company**. Attribution first, then what the company said, then the facts from the notes, then the released numbers and how each was cleaned down to the cell, then the filings and every check that fired.

## Who Arctal is, and how they would use this (29 Oct, from public sources)

Arctal is a five-person London company that turns unstructured financial documents (regulatory filings, fund reports) into structured, source-linked datasets for asset managers, allocators and financial-data firms. Its datasets are structured against a taxonomy (an ICMA-aligned one for labelled bonds), cover "spending that has happened, is committed, or is planned", are refreshed continuously, and are distributed through S&P Global Sustainable1 (45,000+ entities, 33,000+ instruments). The role on offer owns ingestion, cleaning, storage, transformation and distribution, with AI agents in the pipeline and data quality as the deliverable.

So the user is not a reader of pages. It is a data team producing a dataset a distributor resells, and the dataset's buyer, who opens it to check one number against its source. What they need from the interface:

- **The dataset as a grid**, filterable by entity, field, year and kind, exportable in long format with provenance columns. Our fields already have Arctal's shape: spent (actual values and facts), committed (purchase commitments, finance leases), planned (outlook statements and guidance).
- **Provenance one click deep**: the cell, the filing, the method, the inputs, the reference figure, the model and prompt versions. Source-linked is their product claim; here it is the panel.
- **Taxonomy as a first-class object**: the money-flow models are the taxonomy that maps a company's disclosures to "AI capex". Versioned, editable, with the effect of a change shown as a diff.
- **Coverage, freshness and measured error** per entity, as a status strip, because a distributor's buyer asks those three questions before any other.
- **Deliveries**: signed releases with packets, and "changed since" a release or a run, because a continuously refreshed dataset must say what moved.

## The data screen (29 Oct)

One screen, default. A filter bar (entities by industry or role, field, years, kind: spent, committed, planned), a status strip (companies, filings, texts, facts, cells confirmed, faults, blocked, reference agreement), the grid (entities down, years across, one field at a time, cells shaded, click for provenance), a chart of the selection (series per entity, or parts of a whole), export of the selection as CSV with provenance, and "changed since the last run" shading. Saved views are links: the URL carries the filter. The Attribution screen keeps the models and the rerun; Releases and the readers' prompts stay secondary. The company page is the grid filtered to one entity.

## Data first (29 Oct)

Kenny's note after the first rebuild: the app explained in sentences what it should have shown in numbers and shapes. Second pass, same three tabs, every page now opens on data:

- **Pipeline**: the coverage table is a heat grid, intensity per layer (values agreeing, texts, facts, statements), the attributed AI amount and a bar for its share; findings are counts by kind as bars, the list behind a disclosure; add-a-company sits beside them.
- **Attribution**: the grid comes first, cells shaded by amount with the share under each; the model editor and the rerun sit below it on one row.
- **Insights**: four charts in two rows (AI inside total capex by year; AI share per buyer over time; buyers' capex and AI capex against sellers' data-center revenue; AI capex per buyer for the latest year), then the evaluation as a dot plot: a tick for the reference, a shaded range for a floor or ceiling, a dot for ours, red when it disagrees. Sources behind a disclosure.
- **Company**: a strip of six numbers (AI capex, share, capex, values agreeing, cells confirmed, facts), then capex with its AI part by year as bars, then the tables.

Captions are one line; the only paragraph left is the attribution basis, which is the number's explanation.

Design rules kept: no tags, italics, dividers, bordered boxes, section numbers or gradient heroes; one accent, red only for a failure; tabular numbers; running text under 65 characters where it is prose; both themes from the same tokens; phone width with a 16px gutter.
