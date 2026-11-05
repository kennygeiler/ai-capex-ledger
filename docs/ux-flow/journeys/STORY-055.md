# STORY-055: Audit the Dataset against the release before a client send

Evidence: live local copy http://localhost:3610, 2026-11-04, headless Chrome 1600x1000, GET only (POSTs blocked in the
script). Screens in `STORY-055-screens/`. Script: `docs/ux-flow/tmp/story055.py`, `story055b.py`.
"Measured" = seen on a screen or in a GET response. "Suspected" = read from code or inferred, not observed.

Verdict: **convoluted**. Steps actual 18 / ideal 8 (catalog); simpler version below: 6.

## Friction Scorecard

| Heuristic | Finding | Evidence | Status |
|---|---|---|---|
| Step economy | 18 steps vs Ideal 8. Steps 3–8 open six lists one by one only to look for non-agree values; no cross-list filter exists. | Catalog steps 3–8; `01-all-rows.png` sidebar | Measured |
| Decision economy | The auditor must pick, per list, which column carries the verdict (`check_label` on Values/Facts, `check` on All rows, none on Statements/Projects/Companies). | `03-values.png`, `05-facts.png`, `01-all-rows.png`, `06-statements-expanded.png` | Measured |
| Recognition over recall | Step 4 ("unresolved" on Values → "0 rows of 81") reads as "none differ". Five rows do differ, in Facts (`check_label` unresolved = 5, all PP&E), and All rows carries `differs` 2 and `to_confirm` 105. The answer depends on knowing which list holds which check. | `04-values-find-unresolved.png`; GET `/api/v1/facts` (agree 180, no_reference 142, unresolved 5); GET `/api/v1/taxonomy` (verbatim 263, agree 200, to_confirm 105, corroborated 33, no_reference 13, differs 2, explained 1) | Measured |
| Re-entry | Find in rows text clears on every list switch (step 5). Rows switch drops the Grid's field and check filter: `#data?view=grid&f=ppe_category&check=unresolved,flag` → Rows lands on `#data`, All rows, 617. | `14-rows-after-grid.png` (URL `#data`) | Measured |
| Hidden state | Grid `check` filter has no control. `12-grid-check-url.png` shows "5 rows", all ≠, while Field/Companies/Kind controls look unfiltered; nothing says a filter is on. Any control change drops it (`setQ` in `data.js`). | `12-grid-check-url.png` | Measured (screen) / Suspected (drop, from code) |
| Confirmations | None in this journey (all GET). | — | No simplification found |
| Dead ends | "0 rows of 81" + "No rows." offers no route to the list where differing rows live. | `04-values-find-unresolved.png` | Measured |
| Missing list | Release packet ships `ai_spend.csv` (71 rows); Dataset has six lists and no AI spend list, so step 18's count comparison cannot cover every packet file. | `18-release.png` Packet v1.9.0 table vs `01-all-rows.png` sidebar | Measured |
| Export routes | Three routes, two shapes. Rows CSV `/api/v1/values.csv` and Explore CSV `/api/v1/values?field=capex&format=csv` share columns (`check_label`, `citations`; 81 and 27 rows). Grid Export CSV is built in the browser with `check`, `provenance`, `source_url`. | GET headers; `exportCsv()` in `ledger/web/pages/data.js` | Measured (server) / Suspected (Grid columns, download not run) |
| Hesitation | Story precondition says 125 valueless rows; screen shows 118 (`02-without-value.png`), matching Release "Rows with no value 118". Catalog count is stale, app is consistent. | `02-without-value.png`, `18-release.png` | Measured |

Release ↔ Dataset counts agree for the six shown lists: taxonomy 617, values 81, facts 327, statements 227, projects 182,
companies 6 (`18-release.png` Packet table vs list headers in `01`, `03`, `05`–`08`). Measured.

## Take-away Pass

**Dataset · Rows (`01-all-rows.png`, `03-values.png`, `05-facts.png`)**
- Row count stated twice: header "617 rows · USD" and "617 rows" beside Find in rows. Keep the one beside the filter (it changes with the filter); drop the header copy.
- "USD" on Companies (`08-companies.png`, "6 rows · USD") states a unit for a list with no money column. Show the unit only where a money column exists.
- All rows renders 40 columns; the first screen shows ticker → standard_concept, and the check column sits off-screen right (`01`). For an audit, `check` belongs next to `value`. Collapse source/accession/scale/currency/unit into the row detail.
- Sidebar subtitles ("Income and cash-flow statement figures", "Note figures") are the names Explore uses for the same lists; one name per list removes the need for a subtitle.
- Primary action: none dominant. CSV and JSON are equal outline buttons top-right, far from the filter that scopes them. Acceptable for a data browser; CSV could be the single primary next to the count.

**Dataset · Grid (`09-grid-capex.png`, `10-grid-commitments.png`, `12-grid-check-url.png`)**
- ~70 px of empty space above the controls row (`12`). Removable.
- Exactly one primary: blue Export CSV. Correct choice for the screen.
- Legend "✓ Verified · ○ Unverified · ≠ Differs from SEC XBRL" is on the same line as the count; fine. Missing: ✗ (Not checked) mark and the Fix / Accepted / Explained / Blocks release badges have no legend entry (`mark()` in `data.js`). Suspected (none rendered today).

**Grid drawer (`11-grid-ppe-drawer.png`)**
- Two figures: Value ($128,683M, "derived") and Verification ("Unverified · citation only", "facts table"). "facts table" is internal; the list is called Facts in the sidebar. Use "Facts" or drop it.
- "Open in 10-K ↗" is the one action. Correct.

**Release (`18-release.png`)**
- The Packet v1.9.0 table (FILE · ROWS · BYTES) is the end point of this audit but sits below 17 check rows and the company table. File names are plain text; each could link to its Dataset list.

## The Simpler Version

Target journey, 6 steps:

1. Navbar **Release** → Packet v1.9.0 table; each file name links to its Dataset list with its row count.
2. Click **taxonomy.csv** → Dataset, All rows, 617.
3. Pick **Verification: Not verified** (one control shared by every list; values: Verified, Unverified, Differs, To confirm, Not checked) → every non-verified row across lists, with a `list` column.
4. Expand a row → detail with the quote in full and Open in 10-K.
5. Switch to **Grid** → same Verification filter shown as a control, field kept.
6. **CSV** → one export, same columns from Rows, Grid and Explore.

Changes to get there:
1. Add a Verification select to Rows and Grid, bound to the `check` URL parameter that Grid already reads (`data.js` line with `q.check`). Show it as a control so the filter is visible and survives other control changes.
2. One check column name and one vocabulary across lists: Values/Facts `check_label` (agree, no_reference, unresolved, definition_gap) and All rows `check` (verbatim, agree, to_confirm, corroborated, no_reference, differs, explained) describe the same verdict with different words (unresolved vs differs).
3. Keep `ticker`, `f`, `check` and Find text across the Rows/Grid switch and across list switches.
4. Grid Export CSV calls the server endpoint (`/api/v1/<list>?…&format=csv`) instead of building its own columns, so the three routes give one shape.
5. Add an AI spend list to Dataset, or drop `ai_spend.csv` from the packet, so every packet file has a list.
6. Link Release packet file names to `#data?list=<name>`; move the Packet table above the check table or give it an anchor.
7. Empty filter result ("No rows.") names the lists where the search term matches, e.g. "unresolved: Facts 5".

## Clarity Issues

| Issue | Where | Fix |
|---|---|---|
| One list, three names: `taxonomy` (Release "617 taxonomy rows", file taxonomy.csv), "All rows" (Dataset title), "All measures" (Dataset subtitle, Explore measure). | `18-release.png`, `01-all-rows.png`, `16-explore.png` | One name everywhere; the file name can follow it. |
| Values = "Statement figures" (Explore), Facts = "Note figures", Statements = "Quoted statements", Projects = "Named projects". | `16-explore.png` vs `01` sidebar | Same label on both pages. |
| Same verdict, two words: `unresolved` (Values/Facts) vs `differs` (All rows); Grid legend says "Differs from SEC XBRL". | `03`, `05`, `01`, `12` | One word: Differs. |
| Raw snake_case headers and values on Rows: `check_label`, `no_reference`, `chip_seller`, `miner_to_hpc`, `as_reported`. The Grid and Proof show "Chip design", "Miner to HPC". | `03-values.png`, `08-companies.png` vs `11` / Proof | Keep raw names in CSV/JSON; show labels in the table, raw name in the header tooltip. |
| "facts table" in the drawer; "derived" under the value with no meaning stated. | `11-grid-ppe-drawer.png` | "Facts"; Kind: Derived. |
| Explore selects mix lowercase raw values ("company stated ai", "ppe gross by type", "BuildingAndBuildingImprovements") with Dataset's "PP&E by category". | `16-explore.png` text | Labels from the same FIELDS/KINDS map. |
| Release check rows carry long sentences in Details ("Every value XBRL can't vouch for, plus a random sample…"), against the product-copy rule. Outside this story's core but on step 18's screen. | `18-release.png` | Short label; sentence in Docs. |
| Grid legend omits ✗ and the status badges. | `mark()` in `data.js` | Add to legend when present. Suspected. |

Banned-style check: no italics, gradients or dividers seen on these screens. Grid status badges (`badge bg-*-lt`) are pill
tags; none render with today's data. Suspected.
