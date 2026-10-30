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

## The attribution screen (29 Oct)

Same style. A strip of counts by method with the badge each uses (SH stated share, ST stated amount, SEG segment capex, PPE server-category growth, ALL whole business, Q words only). The grid grouped by industry, each group headed by its model version; every cell carries its amount, share and a method badge. A cell opens the basis and inputs in the panel; a badge opens the industry's model in the same panel, with the version list, edit, save as the next version, use, and rerun for that industry. Below: what changed in the last load as a before-and-after table, and the model and prompt change log as a table.

## The design plan, applied (29 Oct)

From the `frontend-design` planning pass. Subject: a ledger of AI capital spending read from filings; the vernacular is the accountant's, ruled ledger paper and the auditor's tick mark beside a traced number. Palette: paper `#FAFBF8`, ink `#1B1E1C`, rule `#D9DED8`, traced green `#1E6B4E`, red pencil `#B5452E`; dark mirrors it. Type: IBM Plex Sans only, tabular figures, numbers at 500 and labels at 400 in muted ink. The one bold thing is the mark: ✓ in green where a number agrees with its source (XBRL, or a stated figure for an attribution), a faint ✓ where it was checked but has no source to agree with, ✗ in red where it disagrees. Colour means evidence, never magnitude: the heat wash is gone. Meta strings no longer join with middle dots.

## Audit against the Web Interface Guidelines (29 Oct)

Two skills installed for this work: Vercel's `web-design-guidelines` (an audit of UI code against 100+ rules, run by fetching the current rules and reading the page) and Anthropic's `frontend-design` (a plan-before-code process: palette, type roles, wireframe, principles, then a pass that strikes defaults). The audit's findings on `app.html` and their fixes: clickable rows and cells were mouse-only (now `role=button`, tabbable, Enter and Space act); the drawer had no label, did not take focus and scrolled the page behind it (now labelled, focus moves to Close, `overscroll-behavior: contain`); inputs lacked `name` and `autocomplete`; no `theme-color`, skip link or page heading; buttons had no hover state; status text was not `aria-live`; placeholders lacked the trailing ellipsis; button labels were not Title Case. Left as is: screenshot images without fixed dimensions (sizes vary per cell; they are below the fold and lazy).

## One thing at a time (29 Oct)

Kenny: "way too visually confusing." The screen held a seven-number strip, two selects, three checkboxes, thirty-one company checkboxes in six rows, the grid, a permanent panel, a chart and a footer. Now: one line of controls (field, companies as a group or a custom list, kind, export) and the grid. Details open in a drawer only when a cell or a badge is clicked, and close with Esc. The chart is behind a disclosure. The pipeline's numbers, the findings and the reference check moved to a Status page. Shading is lighter, headings plain, changed cells marked with a thin left bar.

## Visual conventions of the data products (29 Oct)

Daloopa, Calcbench and the terminals share a look their users already know: a top bar with the product name and a ticker search, a compact toolbar, dense tables at 13px with a sticky header and a sticky first column, right-aligned tabular numbers, row hover, a details drawer. DATAHQ now follows them: the bar is a band with a ticker-or-company search that jumps to the company's grid, the status strip sits in the same band colour, tables are dense with sticky header and first column, the provenance panel is a drawer in the band colour, headings are small uppercase labels. Light and dark from the same tokens.

## Data first (29 Oct)

Kenny's note after the first rebuild: the app explained in sentences what it should have shown in numbers and shapes. Second pass, same three tabs, every page now opens on data:

- **Pipeline**: the coverage table is a heat grid, intensity per layer (values agreeing, texts, facts, statements), the attributed AI amount and a bar for its share; findings are counts by kind as bars, the list behind a disclosure; add-a-company sits beside them.
- **Attribution**: the grid comes first, cells shaded by amount with the share under each; the model editor and the rerun sit below it on one row.
- **Insights**: four charts in two rows (AI inside total capex by year; AI share per buyer over time; buyers' capex and AI capex against sellers' data-center revenue; AI capex per buyer for the latest year), then the evaluation as a dot plot: a tick for the reference, a shaded range for a floor or ceiling, a dot for ours, red when it disagrees. Sources behind a disclosure.
- **Company**: a strip of six numbers (AI capex, share, capex, values agreeing, cells confirmed, facts), then capex with its AI part by year as bars, then the tables.

Captions are one line; the only paragraph left is the attribution basis, which is the number's explanation.

Design rules kept: no tags, italics, dividers, bordered boxes, section numbers or gradient heroes; one accent, red only for a failure; tabular numbers; running text under 65 characters where it is prose; both themes from the same tokens; phone width with a 16px gutter.

## Reconcile and Explore (30 Oct)

Kenny, after the 100-company run: "there's no charts for me to manipulate", and "if I am supposed to be cleaning
data, the way it is presented to me is extremely difficult to actually reconcile." Both were true. Views were
static bar lists; the Flow queue was sentences with one dollar figure, the two numbers a person needs were one
drawer away for every one of 198 items, rows interleaved companies and causes, and the page took five seconds.

**Reconcile** (`#reconcile`, `/api/v1/reconcile?scope=`): every open item as one row: company, where, ours,
reference, delta (dollars or share points, and a percent), decision. Grouped by cause or by company, filtered by
cause, layer and field, resolved rows hidden by default. Enter opens the evidence under the row, not in a drawer:
the amount, method and inputs with their values for an attribution; the cited cell, its row, column, table and
screenshot for a fact; the quote with its source and date for a stated figure; before and after for a move. The
decision sits beside the evidence: Accept, Explain, Fix or Blocks, a reason, Save. Keyboard: j and k move, Enter
opens, a, e, f, b pick the decision and focus the reason, space selects; a selection gets one form that resolves
every selected row with one reason (`/api/resolve/bulk`, each row logged on its own). A key press never animates.
The Flow page keeps its four stages and links here for the work.

**Explore** (`#explore`, replaces Views): a measure (attribution, values, facts, statements, plans, projects), its
field and kind, a layer, tickers, a year range; then an x axis, a series and a chart type (bars, stacked, lines,
share of total). Plotly draws it: hover for the value and its share of the x, click a legend entry to hide a series,
drag to zoom, double-click to reset, click a bar or point for the rows behind it with links into the dataset. More
than eight series fold into Other; a series keeps its colour across filters (a registry in the browser). Save as
view keeps the spec (`show: chart`, `chart: {x, series, type, value}`) in `data/views.json`; a saved view is still a
query at `/api/v1/views/<id>/data`. Y axis in $B or $M by the data; axis and grid hairlines in the page's own
neutrals, both themes.

**Speed:** the Flow page (and so Reconcile) took five seconds because the scorecard ran each of its queries twice
and one of them scanned the runs table; both fixed, and `flow()` is cached by scope until anything it reads changes
(database, resolutions, diff, evaluation, releases, companies, evidence). Cold 0.3 s, warm instant.

