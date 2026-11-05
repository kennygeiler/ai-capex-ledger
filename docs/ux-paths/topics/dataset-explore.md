# Dataset and Explore: user journey stories

Topic: **dataset-explore**, the consumer read path. Written 2026-11-04 from `ledger/web/pages/data.js`,
`pages/explore.js`, `pages/_shared.js`, `pages/_router.js` and `app.py`, with read-only GETs against the local copy on
port 3610 (617 taxonomy rows, 81 values, 327 facts, 227 statements, 182 projects, 6 companies, 4 saved views).

Surfaces covered: `#data` (Rows view, list sidebar, Company select, "Every row / With a value / Without a value",
"Find in rows", **CSV** / **JSON**), `#data?view=grid` (Field, Companies incl. "Custom…" drawer, Kind, cells, provenance
drawer, **Export CSV**), `#company/<T>`, `#tables/<list>`, header jump box, `#explore` (controls, Plotly chart, "Data"
disclosure, "Show rows", bar click, **Save as view** / **Save changes** / **Delete**, JSON / CSV links), `#explore/<id>`,
`#views/<id>`, `/api/v1/<list>[.csv]`.

Findings recorded inside the stories (for the redundancy and friction passes):

- **Broken: Save as view / Save changes / Delete.** `api()` posts without `Content-Type: application/json`; the server
  answers 403 "a write needs Content-Type: application/json". Save shows that text in the drawer; Delete has no
  try/catch, so the rejection is unhandled and the page silently stays put (STORY-007, STORY-008).
- **Broken saved view:** "What companies state about AI, in dollars" (`company-stated-ai`) has `chart: null`,
  `show: grid`; Explore falls back to x = `period`, which taxonomy rows do not have, so it renders "No rows match" for
  118 rows that exist (STORY-006).
- **Explore JSON / CSV links drop filters:** they carry only field, kind, layer, ticker; the taxonomy Measure,
  Category, Standard type and From/To are left out, so the "Capex by layer, by year" CSV holds all 617 taxonomy rows
  instead of the 27 capex rows charted (STORY-005).
- **Grid "Custom…" cannot be reopened** once the selection is already custom (the select's `change` does not fire on
  the already-selected option); an empty Custom selection, or an industry with no companies in scope (e.g. "Power
  producer"), silently means every company (STORY-003, STORY-004).
- **"Find in rows" is not in the URL**: lost on Back, refresh or a list switch; it matches the whole row as JSON, so
  "capex" also hits URLs and concept names (STORY-001).
- **Redundancy:** a company's figures can be read in five places (Dataset Rows, Dataset Grid, Explore "Show rows",
  Company trail `#proof/<T>`, Reconcile evidence); CSV export exists three ways (Rows **CSV** = server
  `/api/v1/<list>.csv`, Grid **Export CSV** = client-side blob with different columns, Explore **CSV** =
  `?format=csv`); the header jump box, `#company/<T>` and the Rows Company select all land on the same Rows view.
  "Measure" names three different things (Explore's list select, the taxonomy measure select, and the Grid Kind
  option "Every measure").

---

## STORY-001: Find Microsoft's FY2026 capex in the raw rows and copy it

**Type**: short
**Topic**: dataset-explore
**Persona**: Equity analyst at a long-only fund, first visit, wants one number with a source
**Goal**: Read MSFT's FY2026 cash-flow capex and see where it came from
**Preconditions**: Local or hosted copy open on `#proof`; MSFT in scope
**Ideal path**: 3: type the ticker, filter to the line, read the row (a search scoped to a company should be enough)
**Alternate paths**: (a) navbar **Dataset** → Company select "Microsoft MSFT" → "Find in rows"; (b) type `#company/MSFT` (redirects to the same Rows view); (c) Dataset → **Values** list (81 rows) → Company select; (d) Dataset → **Grid** → Field "Capex" → MSFT row, FY26 cell → provenance drawer; (e) Company trail `#proof/MSFT` → "Statement figures" stage card; (f) Explore with Measure "Statement figures", Field "Capex", Tickers "MSFT", then **Show rows**; (g) `/api/v1/values?ticker=MSFT&field=capex` directly
### Steps
1. Types "MSFT" in the header jump box "Ticker or company…" and picks Microsoft from the datalist -> Route `#data?ticker=MSFT`; tab **Dataset** highlighted; heading "All rows", "71 rows · USD", Company select shows "Microsoft MSFT", value select "Every row".
2. Hesitates: 71 rows across derived, planned and company-stated-AI measures; not sure which is "capex". Types "capex" in **Find in rows** -> After ~150 ms the count reads "<n> rows of 71"; the matches include the cash-flow line plus rows whose `standard_concept`/URL text happens to contain "capex".
3. Clicks the column header **fiscal_year** twice to put FY2026 on top -> Table re-sorts (first click ascending, second descending).
4. Clicks the FY2026 row with `reported_name` "capital expenditures (cash-flow line)" -> A detail row opens listing every column (`value` 115948000000, `standard_concept` PaymentsToAcquirePropertyPlantAndEquipment, `accession`, `source_url`, `check`).
5. Clicks the `source_url` "open" link in the table -> sec.gov 10-K opens in a new tab.
### Variations
- Searches "Microsoft" instead of selecting the company: matches nothing in taxonomy rows (they carry `ticker`, not the name) unless the URL or a quote contains it; the jump box is the reliable route.
- Starts from the **Values** list: the same figure is `value` 115948000000 with `check_label` agree and a `citations` string ("… 'Purchases of property and equipment' …").
- Clicks the ticker cell "MSFT" in the table -> goes to the Company trail `#proof/MSFT` instead of expanding the row.
### Edge Cases
- Jump box text "msft" (lowercase) works (uppercased); "Micro" does not navigate (needs the full company name or a 1–6 letter ticker); an out-of-scope ticker like "ORCL" navigates and shows "0 rows · USD" / "No rows.".
- Pressing Back after searching clears "Find in rows" (search is not in the hash); the count resets to "71 rows".
- Searching a number with separators ("115,948") fails: search runs over raw JSON (`115948000000`).

## STORY-002: Download every Note figure for the chip sellers as CSV

**Type**: short
**Topic**: dataset-explore
**Persona**: Data engineer loading the ledger into a warehouse
**Goal**: Get facts (note figures) for NVDA and AMD as a file
**Preconditions**: Any copy, including read-only
**Ideal path**: 3: pick the list, pick the companies, download (one multi-company filter would make it 3; the Rows view allows only one company)
**Alternate paths**: (a) Dataset Rows → **Facts** → **CSV** (all companies) and filter in a spreadsheet; (b) twice: Company "NVIDIA NVDA" → CSV, then "AMD" → CSV; (c) `/api/v1/facts.csv?ticker=NVDA,AMD` typed by hand (the API takes a comma list); (d) Explore Measure "Note figures", Tickers "NVDA, AMD", **CSV** link (`?format=csv`); (e) **JSON** button for the same list; (f) Release packet `/packet/<v>.zip` from Proof "Releases" (signed data only)
### Steps
1. Clicks navbar **Dataset** -> `#data`, "All rows" (617 rows).
2. Clicks **Facts** ("Note figures") in the list sidebar -> `#data?list=facts`, "327 rows · USD".
3. Looks for a multi-select; finds only the Company select. Picks "NVIDIA NVDA" -> `#data?list=facts&ticker=NVDA`.
4. Clicks **CSV** -> Browser downloads `/api/v1/facts.csv?ticker=NVDA` (`text/csv`).
5. Switches Company to "AMD" and clicks **CSV** again -> second file; merges them by hand.
### Variations
- Uses Explore instead: Measure "Note figures", Tickers "NVDA, AMD" (input uppercases and strips spaces → `NVDA,AMD`), then the small **CSV** link → one file; this is the only UI route to a two-company CSV.
- Clicks **JSON** -> opens `/api/v1/facts?ticker=NVDA` in a new tab with `{list, count, filters, rows}`.
### Edge Cases
- On the **Companies** list the Company select still shows and filters the 6-row list down to one.
- The "Every row / With a value / Without a value" select only appears on **All rows** (taxonomy); switching lists drops `has_value` from the URL.
- Read-only copy: CSV and JSON still work (GET).

## STORY-003: Compare hyperscaler capex year by year in the Grid

**Type**: medium
**Topic**: dataset-explore
**Persona**: Sell-side analyst building an AI capex comp table
**Goal**: See MSFT, GOOGL, AMZN capex FY2022–FY2026 side by side, verified marks visible, then export
**Preconditions**: Any copy; values verified ("agree") for all three
**Ideal path**: 4: open Grid, pick field, pick group, export (Capex is already the default field)
**Alternate paths**: (a) `#data?view=grid&t=MSFT,GOOGL,AMZN&f=capex` typed or shared; (b) Companies "Custom…" drawer ticking the three; (c) Explore with Measure "Statement figures", Field "Capex", Layer "Hyperscaler", x: year, series: company, Chart type "bars", then "Data" disclosure; (d) saved view "Capex by layer, by year" (layer totals, not per company); (e) Rows view → **Values** → CSV and pivot by hand
### Steps
1. Clicks navbar **Dataset**, then **Grid** -> `#data?view=grid`; Field "Capex", Companies "All companies", Kind "Every measure"; caption "6 rows · USD · ✓ Verified · ○ Unverified · ≠ Differs from SEC XBRL".
2. Reads rows sorted by largest value: Amazon AMZN, Microsoft MSFT, Alphabet GOOGL first; columns "2022"…"2026" -> AMZN FY2026 blank (not filed yet), MSFT 2026 $115.9B with ✓.
3. Hesitates over Companies: "Buyers" would include APLD (role buyer). Picks the industry group "Hyperscaler" -> `t=MSFT,GOOGL,AMZN`; caption "3 rows".
4. Sets Kind to "Spent" -> URL gains `k=spent`; same three rows (cash-flow capex is spent).
5. Hovers a ✓ mark -> tooltip "Verified · matches SEC XBRL" (word from `checkWord`).
6. Clicks GOOGL's 2025 cell ($91.4B) -> Drawer: "Alphabet, Capex, FY2025", figures Value / Verification ("values table"), SEC XBRL line, "Open in 10-K ↗", then the cited cell source (Line, Column, crop thumbnail).
7. Clicks the crop thumbnail -> lightbox with "Open in filing" and "sec.gov ↗"; Escape closes it, Escape again closes the drawer (focus returns to the cell).
8. Clicks **Export CSV** -> client-side download `capex-ledger-capex.csv` with columns ticker, company, field, dimension, period, kind, value, check, basis, source_url, provenance.
9. Copies the URL to a colleague -> the link reproduces the same grid (state lives in the hash).
### Variations
- Arrives from Reconcile "Open in Dataset" -> `#data?view=grid&t=<T>&f=<field>,capex`: a **Field** column appears because two fields are selected; the Field select shows only the first.
- Clicks the company name in a row -> narrows the grid to that one company (`t=<T>`); switching to **Rows** then keeps `ticker=<T>`.
- Field "Segment capex": a "Segment or category" column appears (APLD "Data Center Hosting Business", "HPC Hosting Business").
### Edge Cases
- Picking an industry with no companies in scope ("Power producer", "Neocloud") sets `t=` empty, which the page reads as every company; the select snaps back to "All companies" with no message.
- A cell whose value changed since the last release gets the `moved` highlight, but there is no legend for it.
- A `check` label the server does not declare shows ✗ "Not checked", never a pass.
- Grid **Export CSV** and Rows **CSV** produce different column sets for the same values (redundant exports, different shapes).

## STORY-004: Build a custom company set in the Grid and then change it

**Type**: medium
**Topic**: dataset-explore
**Persona**: Analyst comparing AI chip sellers against one buyer (NVDA, AMD, MSFT)
**Goal**: Show capex for an ad-hoc set, then add APLD
**Preconditions**: Grid open on "All companies"
**Ideal path**: 4: open picker, tick, apply; reopen, tick, apply
**Alternate paths**: (a) edit `t=` in the URL; (b) pick "Chip design" group, then edit URL to add MSFT; (c) Explore Tickers "NVDA, AMD, MSFT" (free text, no picker)
### Steps
1. Selects Companies "Custom…" -> Drawer "Companies" with checkboxes grouped by industry (Hyperscaler: MSFT GOOGL AMZN; Chip design: NVDA AMD; Miner to HPC: APLD), all ticked.
2. Unticks GOOGL, AMZN, APLD -> nothing changes behind the drawer yet.
3. Clicks **Apply** -> `#data?view=grid&t=MSFT,NVDA,AMD&f=capex`; select shows "Custom…"; "3 rows".
4. Wants to add APLD; re-selects "Custom…" in the Companies select -> nothing happens (already selected, no change event).
5. Confused; picks "All companies" then "Custom…" again -> drawer opens with all six ticked (the previous custom set is gone).
6. Unticks GOOGL, AMZN, ticks nothing else, clicks **Apply** -> `t=MSFT,NVDA,AMD,APLD`.
### Variations
- Edits the URL instead (`&t=MSFT,NVDA,AMD,APLD`): works first time, the select shows "Custom…".
- Closes the drawer with Escape or the close button instead of Apply: ticks are discarded, but the select still shows "Custom…" until the next render.
### Edge Cases
- Unticking every company and pressing **Apply** shows all six companies (empty `t` means everyone).
- Ticks that exactly match a group (NVDA + AMD) render the select as "Chip design", not "Custom…".
- Lowercase tickers in a hand-typed `t=msft` find no data (Grid does not uppercase `t`, unlike Rows' `ticker`).

## STORY-005: Chart capex by layer and export what the chart shows

**Type**: medium
**Topic**: dataset-explore
**Persona**: Journalist writing about AI infrastructure spend
**Goal**: A stacked bar of capex by supply-chain layer per fiscal year, plus the numbers behind it
**Preconditions**: Explore defaults
**Ideal path**: 3: open Explore (defaults already chart this), open Data, export
**Alternate paths**: (a) saved view "Capex by layer, by year" (`#explore/capex-by-group` or `#views/capex-by-group`); (b) Grid Field "Capex" + Export CSV and sum by layer by hand; (c) Rows **All rows** with Find "capex" + CSV; (d) `/api/v1/taxonomy.csv?category=capex`
### Steps
1. Clicks navbar **Explore** -> `#explore`; left "4 saved views" + "New"; controls Measure "All measures", Measure "spent", Category "capex", "every asset type", "every field", "every kind", Value "the value as reported", "every layer", tickers box, From/To, "then", "x: fiscal year", "series: layer", Chart type "stacked bars".
2. Reads "<n> rows" and the stacked chart (Hyperscaler, Chip design, Miner to HPC in fixed colours); y axis "capex, $billion".
3. Hovers FY2025's Hyperscaler segment -> "<b>$…</b> Hyperscaler, x% of the fiscal year · n row(s)".
4. Opens the **Data** disclosure -> table: layer × FY columns with dollar sums; copies it.
5. Clicks the **CSV** link expecting the charted rows -> downloads `/api/v1/taxonomy?&format=csv`: all 617 taxonomy rows (category and measure filters are not in the export link).
6. Notices the mismatch, goes back and opens the **JSON** link -> same, `filters: {}`.
7. Falls back to typing `/api/v1/taxonomy.csv?category=capex&measure=spent` or uses the Data table.
### Variations
- Opens the saved view instead: identical chart, heading "Capex by layer, by year" with the view's note.
- Chart type "share of total" -> y axis "share of the total, %".
- Value "change from the prior year" -> plots `change_from_prior`; y title adds ", change from the prior year".
### Edge Cases
- From "FY2024" To "FY2022" (inverted) -> "No rows match".
- More than 8 series (e.g. series: standard type) -> extras folded into "Other" (grey), caption ", n smaller series folded into Other".
- Plotly CDN blocked -> "Chart unavailable" and the row table shows directly.
- Same numbers appear in the Data disclosure, Show rows, the JSON link and Grid: four surfaces for one series.

## STORY-006: Open each saved view to see what is already built

**Type**: medium
**Topic**: dataset-explore
**Persona**: New team member told "the views are in Explore"
**Goal**: Browse the 4 saved views and pick one to reuse
**Preconditions**: 4 views in `data/views.json`
**Ideal path**: 4: one click per view
**Alternate paths**: (a) `#views/<id>` (same page, Explore tab highlighted); (b) `/api/v1/views` JSON listing; (c) `/api/v1/views/<id>/data` (rows only, API)
### Steps
1. Navbar **Explore** -> left list: "Capex by layer, by year" (taxonomy · capex, fiscal year by layer), "Technology equipment, gross balance by company", "What companies state about AI, in dollars" (taxonomy · company stated ai), "Committed: purchase obligations and finance leases".
2. Clicks "Technology equipment, gross balance by company" -> `#explore/technology-equipment-gross`; lines per company over fiscal year; Category "ppe gross by type", Standard type "TechnologyEquipment".
3. Clicks a line point (MSFT FY2024) -> "Microsoft MSFT, FY2024" rows table below with Company link, Year, reported name, Value, Basis.
4. Clicks "What companies state about AI, in dollars" -> heading shows the view's name; chart area says "No rows match" although the measure has 118 rows.
5. Hesitates: checks the X axis select; no option matches (`period` is not a taxonomy column; the view was saved as `show: grid` with no chart). Changes X axis to "x: fiscal year" -> chart appears; URL becomes `#explore?…` (no longer the view).
6. Clicks "Committed: purchase obligations and finance leases" -> grouped bars by company per fiscal year.
7. Clicks **New** -> back to `#explore` defaults.
### Variations
- Arrives via a shared `#views/committed` link: identical page.
### Edge Cases
- Changing any control on a saved view leaves `#explore/<id>` for `#explore?<state>`; the heading reverts to "Explore" and the button becomes **Save as view** (there is no way to "Save changes" after tweaking, because tweaking drops the view id).
- Unknown id `#explore/nope` silently shows the default chart under "Explore".

## STORY-007: Save a new view (fails on the Content-Type guard)

**Type**: short
**Topic**: dataset-explore
**Persona**: Kenny (owner) on the local copy, Signer "Kenny Geiler"
**Goal**: Save "AI capex vs total, FY2023–FY2026" as a view
**Preconditions**: Local copy (not read-only), Signer set
**Ideal path**: 3: Save as view, name, Save
**Alternate paths**: none found in the UI (views are otherwise only editable in `data/views.json`)
### Steps
1. Sets Category "ai capex", From "FY2023", To "FY2026", series: company -> chart redraws; URL `#explore?…`.
2. Clicks **Save as view** -> Drawer "Save as view", Name (placeholder "e.g. Capex by industry, FY2022–FY2026"), Note.
3. Types the name and "Company-stated AI capex", clicks **Save** -> red message under the button: "a write needs Content-Type: application/json"; drawer stays open.
4. Retries -> same error. Nothing saved; no other route exists.
### Variations
- Read-only copy: the read-only guard runs first -> "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository".
### Edge Cases
- Empty Name: server would reject, but the Content-Type refusal comes first, so the user never sees name validation.
- Signer box empty: the button is not disabled here (unlike Reconcile writes); `by: ''` would also be refused.

## STORY-008: Edit and delete a saved view (both fail; Delete fails silently)

**Type**: medium
**Topic**: dataset-explore
**Persona**: Kenny tidying views before sharing the hosted link
**Goal**: Rename "Committed: purchase obligations and finance leases", then delete "What companies state about AI, in dollars"
**Preconditions**: Local copy, Signer set
**Ideal path**: 5: open view, Save changes, rename, Save; open other view, Delete + confirm (6)
**Alternate paths**: none found in the UI
### Steps
1. Clicks "Committed: purchase obligations and finance leases" -> `#explore/committed`, buttons **Save changes** and **Delete**.
2. Clicks **Save changes** without touching controls -> Drawer "Save changes" with Name and Note prefilled.
3. Edits Name to "Committed obligations", **Save** -> "a write needs Content-Type: application/json" in the drawer.
4. Closes the drawer (Escape) -> name unchanged in the list.
5. Clicks "What companies state about AI, in dollars" (already broken, STORY-006), clicks **Delete** -> button text becomes "Confirm delete" (armed for 5 s).
6. Clicks **Confirm delete** -> the POST is refused 403; no message, no navigation; the button keeps reading "Confirm delete" until the timer resets it to "Delete" (unhandled promise rejection in the console).
7. Unsure whether it worked, reloads -> the view is still listed (4 saved views).
### Variations
- Waits more than 5 s between clicks -> the button disarms and the second click re-arms instead of deleting.
### Edge Cases
- Read-only copy: Delete fails the same silent way (403 read-only), while Save shows the message.
- The `aria-live` on the Delete button announces "Confirm delete" but never an error.

## STORY-009: Quarterly research pass: from a hunch on APLD to a shareable chart and a source check

**Type**: long
**Topic**: dataset-explore
**Persona**: Buy-side analyst covering Applied Digital (APLD), comparing it with the hyperscalers' capex ramp
**Goal**: Quantify APLD's capex jump, check it against the filing, find the segment split, and send a colleague a chart link plus a CSV
**Preconditions**: Any copy; APLD capex FY2022 $55.0M → FY2026 $2.87B, all "agree"
**Ideal path**: 10: jump to APLD, Grid capex, open FY2026 cell + source, switch field to Segment capex, Explore with APLD + series, Data table, copy link, export CSV
**Alternate paths**: (a) Company trail `#proof/APLD` for the source of every figure (Statement figures and Note figures stages); (b) Rows view **Values** / **Facts** with Company "Applied Digital APLD"; (c) Reconcile `#reconcile?scope=APLD` evidence "Open in Dataset"; (d) Explore **Show rows** for every row; (e) API `/api/v1/facts?ticker=APLD&field=segment_capex`
### Steps
1. Types "APLD" in the jump box -> `#data?ticker=APLD`, "All rows", "<n> rows · USD".
2. Selects "With a value" -> `has_value=true`; count drops (taxonomy rows without values hidden).
3. Clicks **Grid** -> `#data?view=grid&t=APLD`; Field "Capex"; one row "Applied Digital APLD": 2022 $55.0M … 2026 $2.9B, all ✓.
4. Clicks the 2026 cell -> drawer "Applied Digital, Capex, FY2026", Value $2.9B, Verification Verified, SEC XBRL $2.9B, "Open in 10-K ↗", source line and crop.
5. Clicks the crop -> lightbox; clicks "Open in filing" -> `/filing/<accession>` in a new tab with the cell outlined.
6. Returns, presses Escape to close the drawer; switches Field to "Segment capex" -> rows per segment ("Data Center Hosting Business", "HPC Hosting Business", "Cloud Services Business") under "Segment or category".
7. Hesitates: wants the hyperscalers next to APLD on one chart; Grid sorts by size, so APLD drops to the bottom. Switches Field back to "Capex", Companies "Custom…", ticks MSFT and APLD, **Apply**.
8. Values differ by 40×; the grid has no growth view. Opens navbar **Explore**.
9. Sets Measure "Statement figures" -> Field resets to "Capex", x: year.
10. Types "APLD, MSFT" in the tickers box, tabs out -> `ticker=APLD,MSFT`.
11. Sets Series "series: company", Chart type "lines" -> two lines, hover "x unified".
12. MSFT dwarfs APLD; switches Measure back to "All measures" to use Value "change from the prior year" -> Category resets to "capex", Measure "spent", tickers kept.
13. Sets Value "change from the prior year", series: company, lines -> change lines plotted; FY2022 has no prior and drops out.
14. Double-clicks the chart to reset after a drag-zoom; toggles MSFT off in the legend to read APLD alone.
15. Opens **Data** -> APLD and MSFT rows by fiscal year; copies the table.
16. Clicks a point -> rows table "Applied Digital APLD, FY2026" with Basis text.
17. Clicks the company link in the rows table -> Company trail `#proof/APLD` (now outside this topic; checks "Coverage" next 10-K date), then Back.
18. Tries **Save as view** to keep it -> fails (STORY-007); instead copies the `#explore?…` URL, which reproduces the chart.
19. Clicks the **CSV** link -> downloads rows filtered by ticker only (not category/measure), so gets every APLD and MSFT taxonomy row; filters in a spreadsheet.
20. Sends the link and the CSV.
### Variations
- Uses Grid **Export CSV** at step 7 instead of Explore's CSV: exact charted rows, but no change-from-prior column.
- Uses Layer "Miner to HPC" instead of tickers: same APLD series (APLD is the only miner_to_hpc company).
### Edge Cases
- The colour of APLD is stored per browser (`localStorage.datahq-colors`); the colleague may see different colours for the same link.
- Typing "APLD MSFT" (space, no comma) becomes `APLDMSFT` after whitespace stripping -> "No rows match".
- The Grid row link and the jump box both reset the Grid's field to capex unless `f` is carried.

## STORY-010: Audit the Dataset against the release before a client send

**Type**: long
**Topic**: dataset-explore
**Persona**: Kenny, owner, checking that what consumers will download matches what Proof says
**Goal**: Walk every list, spot unverified or flagged values, and confirm exports are consistent across the three CSV routes
**Preconditions**: Local copy; release v1.9.0 not yet signed
**Ideal path**: 8: one filter for "not verified" across lists, one export (the UI has no such filter; the Grid's `check` URL parameter is the closest)
**Alternate paths**: (a) Release checklist "Fix in" → Dataset; (b) Reconcile filters (Cause "Differs from SEC XBRL"); (c) Proof Company trail stage tallies; (d) hand-typed `#data?view=grid&check=unresolved,flag` (supported in code, no control for it)
### Steps
1. Navbar **Dataset** -> "All rows" 617 rows.
2. Selects "Without a value" -> 125 rows; scans `measure` (planned, company_stated_ai) to confirm these are text-only statements, not missing numbers.
3. Selects "Every row", clicks **Values** -> 81 rows; sorts **check_label** to group anything other than agree.
4. Types "unresolved" in **Find in rows** -> count "0 rows of 81" (none differ today).
5. Clicks **Facts** -> search box clears (not kept across lists); 327 rows; sorts **check** column.
6. Clicks **Statements** -> 227 rows; expands a row to read `quote` (cut at 90 characters in the table, full in the detail).
7. Clicks **Projects** -> 182 rows; looks at `amount_low`/`amount_high`.
8. Clicks **Companies** -> 6 rows: MSFT, GOOGL, AMZN hyperscaler; NVDA, AMD chip_seller; APLD miner_to_hpc.
9. Switches to **Grid**, Field "Capex", All companies -> 6 rows, every cell ✓.
10. Field "Purchase commitments", Kind "Committed" -> rows for the companies that disclose them; looks for ≠ or ○ marks and Fix / Accepted / Explained / Blocks release badges.
11. Field "PP&E by category" -> wide table with "Segment or category"; clicks a ○ cell -> drawer: Verification "Unverified · citation only".
12. Hand-types `&check=unresolved,flag` on the Grid URL -> only differing or flagged rows remain.
13. Clicks **Export CSV** -> `capex-ledger-ppe_category.csv` (client-side).
14. Switches to **Rows** -> lands on `#data` (Rows switch keeps only list/ticker), All rows.
15. Clicks **Values** → **CSV** (server `/api/v1/values.csv`) and compares to Grid's export for capex: different columns (`check_label` vs `check`, `citations` vs `provenance`).
16. Opens Explore, Measure "Statement figures", Field "Capex" -> **CSV** (`?field=capex&format=csv`): same columns as the Rows CSV.
17. Notes three export shapes for one dataset; files a finding.
18. Opens **Release** to see "Packet v1.9.0" files and compares row counts with steps 3–8.
### Variations
- Read-only copy: every step works (all GET).
- Uses `#tables/facts` from an old bookmark -> redirects to `#data?list=facts`.
### Edge Cases
- Grid ignores `check` in its controls: the filter is invisible and survives only until a control is changed (`setQ` drops it).
- The table renders every row (no paging); on All rows (617) the page is long.
- A `#data?list=bogus` URL falls back to All rows silently.
