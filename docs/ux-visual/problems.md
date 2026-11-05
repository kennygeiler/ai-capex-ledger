# Visual problems — consolidated, 2026-11-05

App: Kenny's Data Emporium, local copy http://localhost:3610, owner mode, data as of Nov 1, 2026. Viewports 1600×1000 and 1280×800. Sources: `pages/*/findings.md`, `pages/*/audit.json`, `pages/*/shots/`, `tmp/*/` probes. Flow decisions in `docs/ux-flow/report.md` stand; a cluster here names the flow item it touches and keeps only the visual layer.

## Coverage

| Page (route) | findings.md | audit.json | States measured | Finding ids |
|---|---|---|---|---|
| Dataset + Explore (`#data`, `#explore`) | yes | yes | rows, grid, find, explore, saved, dark | DE1–DE31 |
| Reconcile (`#reconcile`) | yes | yes | default, rule-open, mapping-open, by-company, filtered, selected | F01–F33 |
| Proof board + Hand check (`#proof`) | **missing** | yes | board, handcheck-apld, handcheck-msft, calculated, lightbox | PB1–PB9 (derived here) |
| Company trail (`#proof/<ticker>`) | **missing** | yes | apld-top, apld-notes-expanded, apld-mapping, apld-lightbox, msft-top, amd-top | TR1–TR8 (derived here) |
| Release (`#release`) | **missing** | yes | checklist, failing-expanded, cards | RL1–RL4 (derived here) |
| Evidence (`#evidence/<id>`) | **missing** | yes | compare, single, filing, filing-bare | EV1–EV5 (derived here) |
| Rules + Known gaps (`#rules`, `#gaps`) | **missing** | yes | rules, gaps | RG1–RG6 (derived here) |
| Docs (`#docs/*`) | **missing** | yes | overview, operations, glossary, handoff | DC1 (derived here) |
| All pages, 1280 | — | yes | navbar | X1 (derived here) |

Six of eight page audits stopped before writing `findings.md`. Their findings below are derived from `audit.json` measurements plus the shots `1600-board.png`, `1600-handcheck-apld.png`, `1600x1000-apld-top.png`, `1600x1000-apld-notes-expanded.png`, `1600x1000-checklist.png`, `1600-compare.png`, `1600-rules.png`, `1600-gaps.png`, `1600-overview.png`, `1600-handoff-codeblocks.png`. They are less exhaustive than DE/F: hover, focus and dark states on those six pages were not reviewed one by one.

Not covered by any audit: read-only (hosted) mode, dark mode beyond Dataset/Explore and the Release checklist, phone width (only `docs/390-*` and `release/390-checklist-full.png` exist).

### Derived findings (pages without findings.md)

| id | element | problem | evidence | severity |
|---|---|---|---|---|
| PB1 | Proof stage cells | Every stage cell is an unlabeled tuple of coloured digits ("0 · 5 · 0 · 0", "15 · 0 · 0"); 3 parts in some columns, 4 in others; the key sits under the table | `proof-board/shots/1600-board.png` | P1 |
| PB2 | Proof headline | "0 of 6 proven" is 13 px bold under the H1, the weakest text on the page, above a table that is mostly green | `1600-board.png` | P1 |
| PB3 | Proof page head | 82 px empty between "Data as of" (y 68) and the H1 (y 150) | `1600-board.png` | P2 |
| PB4 | Hand check table | Rows 166 px, calculated rows 443–461 px; table 4,658–4,769 px; page 7,561 px; header not sticky | `audit.json` handcheck-* `deadSpace col.c-*` h 4769, `pageScrollY` 6561; notes.json `APLD_row_h` | P1 |
| PB5 | Hand check Value cell | "In thousands · $9,320,000" overflows the 152 px column by 23–62 px into Source and is cut | `overflowSpills td.num` 23/50 px; `1600-handcheck-apld.png` | P2 |
| PB6 | Right / Wrong / Can't say, company switcher | Segments 20 px tall; company buttons 20 px | `smallTargets` (30 per state); `1600-handcheck-apld.png` | P2 |
| PB7 | Failure type charts | Two SVGs 594×468 and 594×244 at 0–1 % fill | `deadSpace` board | P2 |
| PB8 | Hand check summary | Five lines of run-on stats with CIs instead of a table | notes.json `APLD_head_text`; `1600-handcheck-apld.png` | P3 |
| PB9 | Hand check note input | "Note (required for Wrong / Can't say)" box shown on every row, including 119 rows marked Right | `1600-handcheck-apld.png` | P3 |
| TR1 | Trail state legend | Legend wraps at 1600: line 1 ends on an orphan orange dot, "Proposed" starts line 2 | `trail/shots/1600x1000-apld-top.png` | P1 |
| TR2 | Trail length | APLD 5,279 px, 16,441 px with notes open; MSFT 3,865; AMD 4,476; column heights 10,738 px; no sticky header | `audit.json` `pageScrollY`, `deadSpace col.c-source` | P1 |
| TR3 | Crop thumbnails | 7.5 rem frames show the filing at ~6 px text; neighbouring thumbs overlap (242×65); "Open · sec.gov" overlaps a thumb by 6–15 px | `overlaps crop-thumb`; `1600x1000-apld-notes-expanded.png` | P1 |
| TR4 | Verification cell | Restatement and tie figures as 4–6 lines of orange prose ("Restated: 9,552 (10-K 2024-08-30) → 1,760 …") | `1600x1000-apld-notes-expanded.png` | P2 |
| TR5 | Filings card | VALUE column is "—" in all 5 rows | `1600x1000-apld-top.png` | P2 |
| TR6 | Trail page head | Same 82 px empty band above the company name | `1600x1000-apld-top.png` | P2 |
| TR7 | Before release card | Four columns; "Changes since release" holds "None", "Last release" two lines; ~60 % of the card empty | `1600x1000-apld-top.png` | P2 |
| TR8 | Header links | "Reconcile", "Dataset" links 15 px tall | `smallTargets` | P3 |
| RL1 | Checklist header | Sortable headers render sentence case ("State", "Check") beside uppercase "FIX IN" in the same row | `release/shots/1600x1000-checklist.png` | P2 |
| RL2 | Sort header buttons | 18 px tall; no focus ring (outline none, shadow transparent) | `smallTargets`; notes.json `tab_order` | P2 |
| RL3 | Release page head | Same 82 px band | `1600x1000-checklist.png` | P2 |
| RL4 | Release checks by company | G1/G4/G5 columns of "·"; card 11 % filled (flow #2 decides whether the card stays) | `deadSpace div.col-xl-7` 761×430 | P2 |
| EV1 | Compare grid | `.ev-wide` spans 1,536 px from x 32 while the title sits at x 156; overflows the column by 108–124 px; ~440 px empty below at 1600 | `overflowSpills`; `tmp/evidence/interact.json` evgrid x 32; `evidence/shots/1600-compare.png` | P1 |
| EV2 | Compare crops | The filing table renders at ~8–9 px text inside a 750 px card | `1600-compare.png` | P2 |
| EV3 | "Open in filing" | Primary button 86×20; two primaries on one page | `smallTargets`; `1600-compare.png` | P2 |
| EV4 | Accession line | Raw accession number in mono as the second line of each card | `1600-compare.png` | P3 |
| EV5 | Evidence page head | Same 82 px band | `1600-compare.png` | P2 |
| RG1 | Rules agent cards | Page 10,874 px; Charter column holds 2 lines with ~600 px empty beside the Score stack; Charter prose blocks 611×238 at 0 % fill | `tmp/rules-gaps/extra.json` docH; `deadSpace p.mb-2`; `rules-gaps/shots/1600-rules.png` | P1 |
| RG2 | Runs per company | Table clipped at the card edge ("ATTEMPT" and its values cut), no scroll cue | `1600-rules.png` | P2 |
| RG3 | Score block | "Caught 1,712 of 1,837 · Missed 1 · No effect 124 · Without the SEC XBRL check: caught 1,705, missed 8" as prose | `1600-rules.png` | P2 |
| RG4 | Agent description | Indented 16 px off the agent name | `1600-rules.png` | P3 |
| RG5 | Known gaps header | Sentence-case sortable headers; "Claim"/"Where" buttons 34×18 | `smallTargets`; `1600-gaps.png` | P2 |
| RG6 | Rules / gaps page head | Same 82 px band | `1600-rules.png`, `1600-gaps.png` | P2 |
| DC1 | Handoff code blocks | Setup and Five-minute tour command blocks render blank: text at 1:1 contrast, 146–315 px of empty space | `lowContrast code` ratio 1; `docs/shots/1600-handoff-codeblocks.png` | P0 |
| X1 | Navbar at 1280 | "Known gaps" wraps on all 8 pages; header 56 → 64 px | `wrappedControls a.nav-link` at 1280 in every audit.json | P2 |

## Totals

| Severity | DE | F | Derived | All |
|---|---|---|---|---|
| P0 | 1 | 0 | 1 | **2** |
| P1 | 6 | 4 | 8 | **18** |
| P2 | 18 | 20 | 20 | **58** |
| P3 | 6 | 9 | 5 | **20** |
| All | 31 | 33 | 34 | **98** |

98 findings fold into 23 clusters (V1–V23) plus 1 rejected finding. Ranking: P0 first; then severity (P1 3, P2 2, P3 1) × reach (1 page 1, 2–4 surfaces 2, 5+ 3) × centrality (owner review → grade → decide → sign loop and the CEO's `#proof` / `#proof/<ticker>` first screen 3, other trust pages 2, rest 1) ÷ effort (XS 1, S 2, M 3). `#proof` counts reach 2: every session lands there.

## Ranking

| Rank | id | Title | Sev | Reach | Score | Status |
|---|---|---|---|---|---|---|
| 1 | V1 | Partial fiscal year drawn as a complete bar | P0 | Explore default + saved views | P0 | **Carried forward** |
| 2 | V2 | Docs code blocks render blank | P0 | Docs (Handoff, any fenced block) | P0 | **Carried forward** |
| 3 | V3 | Controls under 24 px, no focus ring, active segment looks like Save | P2 | all 8 pages | 18 | **Carried forward** |
| 4 | V4 | Long tables: no sticky header, tall rows | P1 | Reconcile, Hand check, trail, Dataset rows, Explore rows | 13.5 | **Carried forward** |
| 5 | V5 | 82 px empty band under the scope line | P2 | 7 of 8 pages | 12 | **Carried forward** |
| 6 | V6 | Proof states unreadable: unlabeled tuples, buried headline, broken legend | P1 | `#proof`, `#proof/<ticker>` | 9 | **Carried forward** |
| 7 | V7 | Filing crops too small to read | P1 | trail, Evidence, Dataset drawer | 9 | **Carried forward** |
| 8 | V8 | Layout jumps on select and expand | P1 | Reconcile | 9 | **Carried forward** |
| 9 | V9 | Empty columns keep their width; no empty state | P1 | Reconcile, trail, Release, Dataset | 6 | Deferred |
| 10 | V10 | Content breaks or clips the page column | P1 | Evidence, Rules, Hand check, Dataset | 6 | Deferred |
| 11 | V11 | Figures stated in prose instead of value cells | P2 | Reconcile, trail, Rules | 6 | Deferred |
| 12 | V12 | Wrapping at 1280 | P2 | all pages at 1280 | 6 | Deferred |
| 13 | V13 | Colour does not map to state | P2 | Reconcile, Dataset | 6 | Deferred |
| 14 | V14 | Row affordance and current row unclear | P2 | Reconcile | 6 | Deferred |
| 15 | V15 | Nested bordered cards and dead columns | P2 | Reconcile, Rules, Proof | 4 | Deferred |
| 16 | V16 | Money shown in four formats | P2 | Dataset, Explore, Hand check | 4 | Deferred |
| 17 | V17 | Redrawn tables lose the kit skin | P1 | Dataset, Explore | 3 | Deferred |
| 18 | V18 | Counts not scoped to what is shown | P1 | Reconcile, Dataset | 4.5 | Deferred (flow #4 owns the number) |
| 19 | V19 | Filter state invisible | P2 | Reconcile, Dataset | 3 | Deferred |
| 20 | V20 | Explore controls and chart | P1 | Explore | 1.5 | Deferred |
| 21 | V21 | Table header and column style differ by page | P2 | Release, gaps, Reconcile, Dataset | 3 | Deferred |
| 22 | V22 | Machine words and raw ids on screen | P2 | Reconcile, Dataset, Evidence | 2 | Deferred (flow #9 owns labels) |
| 23 | V23 | Off-scale spacing | P3 | all pages | 3 | Deferred |

## Carried forward

### V1 · Partial fiscal year drawn as a complete bar — P0
- **Root cause:** Explore sums a fiscal year across whichever companies have filed it. FY2026 holds 3 of 6 companies, so the bar falls $293B → $125B with no partial mark. Page logic in `pages/explore.js`, not a shared component.
- **Findings:** DE1.
- **Surfaces:** `#explore` default, every saved view that includes FY2026.
- **Evidence:** `dataset-explore/shots/1600x1000-explore.png`; Data table FY2026 Hyperscaler $115,948M = MSFT only (`-explore-data-rows-full.png`); Grid 2026 blank for AMZN, GOOGL, AMD (`-grid.png`).
- **Reach:** default chart, first thing Explore draws.
- **Acceptance:**
  - A year where fewer companies have filed than in the prior year is drawn distinct (hatched or outlined) and labelled "3 of 6 filed" on the axis or bar.
  - Tooltip and Data table row for that year state the filed count.
  - Same holds in line mode and in every saved view; screenshot at 1600 and 1280 shows the mark.

### V2 · Docs code blocks render blank — P0
- **Root cause:** `pre.raw > code` from `pages/_markdown.js:90` takes Tabler's `pre` text colour without its dark background (no `.md pre` rule in `app.html`), so text equals background.
- **Findings:** DC1.
- **Surfaces:** `#docs/handoff` (Setup, Five-minute tour), any fenced block in any doc.
- **Evidence:** `docs/shots/1600-handoff-codeblocks.png`; `audit.json` handoff `lowContrast code` ratio 1 at both viewports.
- **Reach:** the handoff journey (flow 068); one CSS rule.
- **Acceptance:**
  - Every `.md pre` block measures ≥ 4.5:1 text contrast in light and dark (layout-audit `lowContrast` lists no `code`).
  - Handoff shot shows the `uv sync` and `uv run python -m ledger run` commands.
  - Long lines scroll inside the block; page `pageOverflowX` stays 0.

### V3 · Controls under 24 px, no focus ring, active segment looks like Save — P2
- **Root cause:** `skin()` in `pages/_shared.js` makes every button `btn-sm` / `btn-link p-0` and every select `form-select-sm` (20–21 px). `app.html:164` paints `.btn-group .btn.active` in `--tblr-primary`, the same fill as the primary action. Header-button sorts (`btn-link`) and segments carry no `:focus-visible` style.
- **Findings:** F06, F16, F29, DE19, DE20, PB6, RL2, EV3, TR8, RG5.
- **Surfaces:** Reconcile decision + bulk bar, Hand check Right/Wrong/Can't say + company switcher, Rows/Grid switch, every sortable header (Release, Known gaps, Dataset), selects everywhere, Evidence "Open in filing", header jump + Signer inputs.
- **Evidence:** `reconcile/shots/1600-rule-open-zoom-decision.png` (Fix 27×20, Accept 51×20); `proof-board/shots/1600-handcheck-apld.png`; `smallTargets` 22–30 per state on every page; tab probes (`tmp/reconcile/extra.json`, `tmp/release/notes.json`, `tmp/dataset-explore/interact.json`) show no ring.
- **Reach:** every page; the decide and grade steps of the owner loop.
- **Acceptance:**
  - `smallTargets` lists no button, select, segment or input under 24 px tall at either viewport (inline text links exempt).
  - Segmented controls use one shared class: ≥ 28 px tall, ≥ 8 px side padding; the active segment is a neutral selected fill, not `--tblr-primary`.
  - Only one element per screen uses the primary fill (Save, Sign, Export).
  - Tabbing reaches every segment and sort header and shows a ≥ 2 px ring.

### V4 · Long tables: no sticky header, tall rows — P1
- **Root cause:** Sticky headers exist only for `table.grid` / `table.heat` (`app.html:57`). Generic `.table` headers scroll away. Rows carry two-line cells, permanent inputs and full crops, so rows run 53–461 px. Rows renders all 617 × 40 at once.
- **Findings:** DE2, DE8, F04, F23, PB4, PB9, TR2.
- **Surfaces:** Reconcile (4,719 px scroll), Hand check (table 4,769 px), company trail (up to 16,441 px), Dataset Rows (19,110 px), Explore Show rows (3,471 px).
- **Evidence:** `pageScrollY` per audit.json; `reconcile/shots/1600-mapping-open.png` (no header on screen); `tmp/dataset-explore/interact.json` `thead_sticky static`; `tmp/proof-board/notes.json` row heights.
- **Reach:** the review, grade and audit steps; the trail is the CEO's company page.
- **Acceptance:**
  - Every table over one viewport keeps its header row visible while scrolling (shared `.table thead th { position: sticky }` inside its card).
  - Reconcile rows ≤ 44 px collapsed; Hand check Right rows ≤ 120 px with the note input shown only after Wrong or Can't say.
  - Dataset Rows draws ≤ 100 rows per page with a pager; page height ≤ 3 viewports.
  - Re-measure: Reconcile default `pageScrollY` ≤ 2,500 at 1600.

### V5 · 82 px empty band under the scope line — P2
- **Root cause:** `#scopeline` (`pages/_router.js:37`) sits in its own `container-xl` right under the navbar; Tabler `.page-body` margin plus `main { padding-top: 1.25rem }` (`app.html`) then push the H1 to y 150–164. Shared layout.
- **Findings:** DE12, F14, PB3, TR6, RL3, EV5, RG6.
- **Surfaces:** every page except Docs (Docs starts at y 134).
- **Evidence:** `1600-board.png`, `1600x1000-apld-top.png`, `1600x1000-checklist.png`, `1600-compare.png`, `1600-rules.png`, `1600-gaps.png`; Reconcile y 68 → 164; Dataset scopeY 82 vs ctrlY 126, Rows 150.
- **Reach:** the first screen of every page, `#proof` included.
- **Acceptance:**
  - Navbar bottom → scope line ≥ 12 px; scope line → H1 ≤ 24 px; H1 top ≤ 110 px at 1600 on every page.
  - The scope line shares the H1's left edge and container.
  - Proof board shows all 6 company rows and the legend above the fold at 1280×800.

### V6 · Proof states unreadable: unlabeled tuples, buried headline, broken legend — P1
- **Root cause:** Stage cells print state counts as bare coloured digits from `stateGroups()` (`pages/_shared.js:117`) with the key under the table; the headline status is the smallest bold text; the trail legend is an inline run that wraps anywhere. Hand-check summary is prose. Count definitions are flow #4 / DI1; this cluster covers how they are drawn.
- **Findings:** PB1, PB2, PB8, TR1.
- **Surfaces:** `#proof` board, `#proof/<ticker>` legend, Proof Hand check summary.
- **Evidence:** `proof-board/shots/1600-board.png`; `trail/shots/1600x1000-apld-top.png`; `tmp/proof-board/notes.json` `APLD_head_text`.
- **Reach:** the CEO's first screen and each company page.
- **Acceptance:**
  - Each stage cell reads without the legend: either a column sub-header names the parts ("Checked · Unverified · To review") or zero parts are hidden and the rest carry a word on hover and in the accessible name.
  - Every column uses the same part order and count.
  - The headline ("0 of 6 proven") is the largest status on the page, ≥ 20 px, beside the H1.
  - The legend sits above the table and never wraps between a dot and its word (`white-space: nowrap` per item); at 1600 it fits one line.
  - Hand check summary is a table: rows = check source, columns = right · wrong · can't say · unchecked · error rate.

### V7 · Filing crops too small to read — P1
- **Root cause:** `cropBox()` (`pages/_shared.js:211`) and `.crop-thumb` (`app.html:101`, height 7.5 rem, `object-fit: contain`) shrink a full table crop into a 120 px frame; side-by-side thumbs overflow their cell and overlap. The Evidence compare reuses the full-width crop at ~8 px text. The drawer crop can render as an empty frame.
- **Findings:** TR3, EV2, DE22.
- **Surfaces:** company trail Note figures, Evidence compare/single, Dataset Grid drawer.
- **Evidence:** `trail/shots/1600x1000-apld-notes-expanded.png`; `overlaps crop-thumb` 242×65 in trail audit.json; `evidence/shots/1600-compare.png`; `dataset-explore/shots/1600x1000-grid-drawer.png`.
- **Reach:** the CEO's proof that a number came from the filing; the owner's grade step.
- **Acceptance:**
  - The thumbnail is cropped to the highlighted row ± 1 row and its column header, so the cited figure renders at ≥ 11 px.
  - `overlaps` reports no `crop-thumb` pairs at either viewport.
  - Evidence compare crops render filing text at ≥ 12 px.
  - A crop that fails to load shows "Crop unavailable · Open in filing" within 2 s, never an empty frame.

### V8 · Layout jumps on select and expand — P1
- **Root cause:** Reconcile inserts the 73 px bulk bar above the table in flow, and tables use auto layout, so selecting moves the clicked row 101 px and expanding a row moves numeric columns 11–26 px.
- **Findings:** F03, F11.
- **Surfaces:** Reconcile Rule findings and Category mapping (decide step).
- **Evidence:** `reconcile/shots/1600-selected.png` vs `1600-default.png` (row y 386 → 487); `1600-rule-open.png` (Dataset x 887 → 861).
- **Reach:** every bulk decision.
- **Acceptance:**
  - Ticking a checkbox moves no row (bulk bar overlays or occupies reserved space): clicked-row y identical before and after.
  - Opening a row moves no column header by more than 1 px (`table-layout: fixed` with set numeric widths).

## Deferred

| id | Title | Root cause | Findings | Surfaces | Sev | Acceptance (short) |
|---|---|---|---|---|---|---|
| V9 | Empty columns keep their width; no empty state | `table()` in `_shared.js` draws every column even when all cells are "—"; no empty-result row | F01, F05, F12, F22, TR5, TR7, RL4, DE5 | Reconcile (by-company 105 px rows at 1280), trail Filings, Release by company, Grid | P1 | A column that is "—" in every row is hidden or ≤ 48 px; Reconcile by-company rows ≤ 44 px at 1280; 0 rows shows "No rows for Kind = Planned" and disables Export. Flow #5/#6 decides which columns get data. |
| V10 | Content breaks or clips the page column | `.ev-wide` transform (`app.html:78`); auto table layout; no ellipsis rule for fixed cells | EV1, RG2, PB5, DE4, DE15, DE29, RG4 | Evidence compare, Rules runs table, Hand check Value, Rows detail, Rows side list, Projects Basis | P1 | `overflowSpills` empty on every page; Evidence cards share the H1 left edge; clipped tables show a scroll cue or fit; truncated text ends in "…". |
| V11 | Figures stated in prose instead of value cells | Detail and verification text built as sentences | F10, TR4, RG3 | Reconcile rule detail, trail Verification, Rules Score | P2 | Sum, tagged, gap, restated-from/to, caught/missed each in a labelled value cell; no figure appears only inside a sentence. Flow #6 fills the gap columns. |
| V12 | Wrapping at 1280 | Nav links wrap; filter bars wrap; header inputs fixed widths | X1, DE25, F32, F24 | Navbar on all pages; Reconcile filter bar | P2 | Navbar 56 px and one line at 1280; Reconcile filter bar one line (`wrappedControls` empty) at 1280. |
| V13 | Colour does not map to state | No single state → colour token map; red used for the routine queue | F13, F33, DE18 | Reconcile, Grid marks | P2 | Red only for Blocks release; Needs review one hue used everywhere; ✓ mark ≥ 3:1; one cell carries one state colour. |
| V14 | Row affordance and current row unclear | `tr.item` has pointer cursor, no hover fill; first row painted `.cur` on load | F15, F17, F18, F25 | Reconcile | P2 | Hover fill on clickable rows; no row painted current until focus; ≤ 1 tab stop per row; keyboard help reachable by keyboard. |
| V15 | Nested bordered cards and dead columns | `skin()` turns sections into cards inside cards; two-column grids with unbalanced content | F07, F08, F09, RG1, PB7 | Reconcile expanded rows, Rules agent cards, Proof failure charts | P2 | No bordered card inside a card; `deadSpace` lists nothing over 300 px at < 10 % fill; Rules page ≤ 6,000 px. |
| V16 | Money shown in four formats | No shared money formatter | DE10, DE17, DE23 | Explore tooltip, Grid, Statements | P2 | One formatter: axis unit governs tooltip; one unit per column; no raw integers in product cells. |
| V17 | Redrawn tables lose the kit skin | Find / Show rows / bar-click redraw without `skin()` | DE3 | Dataset Find, Explore rows | P1 | After every redraw header buttons carry kit classes; no `borderStyle: outset`. |
| V18 | Counts not scoped to what is shown | Header counts read global totals | F02, DE13 | Reconcile header, Dataset title | P1 | With filters on, counts read "7 of 16"; title count follows Find. Flow #4 owns the definition. |
| V19 | Filter state invisible | Changed selects look like defaults; duplicate scope lists | F19, F20, DE21 | Reconcile filters, Grid company picker | P2 | Changed filters visibly marked with an active count and Clear; picker reads Custom only after Apply. |
| V20 | Explore controls and chart | Sentence-fragment controls, no labels; Plotly late-load; slivers; colour order per browser | DE6, DE7, DE11, DE24, DE27, DE28 | Explore | P1 | Every control labelled; one line at 1600; cold deep link draws; series colours fixed per company. Flow HI3 owns the words. |
| V21 | Table header and column style differ by page | Sort headers as `btn-link` drop the uppercase th style; mixed alignment | RL1, F26, F27, DE14, DE16 | Release, Known gaps, Reconcile, Grid | P2 | All table headers one case and size; numeric headers right-aligned; Rows/Grid switch and export in the same place on both. |
| V22 | Machine words and raw ids on screen | Keys and concept names passed straight to cells | F21, F30, F31, DE9, DE26, EV4 | Reconcile, Saved views, Evidence | P2 | No snake_case, `…Member` or schema notes in product text; accession ids behind a link. Flow #9 owns the vocabulary. |
| V23 | Off-scale spacing | Ad hoc 6/10/11 px gaps | DE30, F28 | all pages | P3 | `spacing.offScale` empty against a 4/8/12/16/24 scale. |

### Rejected

| id | Reason |
|---|---|
| DE31 | "Signer" 1.43:1 sits on the dark navbar and reads fine in every shot; layout-audit background-detection false positive (Reconcile audit reached the same verdict). The same probe's `MSFT 20/20` ratio 1 is also a false positive: the active segment renders white on blue in `1600-handcheck-apld.png`. |

## Flow items not re-clustered

Owned by `docs/ux-flow/report.md` and left out here: Release row order and Details truncation (#2), six Download links and Releases table placement (#8, HI5), Proof carrying four jobs (#11, HI4), Save as view (DP7), one export (DP2), Fix-in targets (#1), Category mapping split and Approve-all (#5), Known limitations in Docs (HI7).
