# Dataset and Explore — visual audit

Local copy http://localhost:3610, data as of Nov 1, 2026. Headless Chrome via Playwright, GET only (non-GET requests aborted; none fired). Viewports 1600×1000 and 1280×800. Shots: `shots/`. Metrics: `audit.json` (layout-audit + geometry-audit per viewport/state) and `../../tmp/dataset-explore/interact.json` (tab walks, geometry, drawer, skin checks). Flow decisions in `docs/ux-flow/report.md` (DP2 one export, DP7 Save as view, HI3 display labels, 13 Dataset filters) are not re-argued here; findings below are visual.

## Verdicts

| Viewport · state | Verdict | Shots |
|---|---|---|
| 1600 · Rows | Below excellent. A 617-row, 40-column raw dump on one page: 19,110 px tall, table 5,493 px wide in a 1,069 px pane (19% visible), header not sticky. Side list and toolbar read well; the 68 px band above the title and the duplicated count do not. | `1600x1000-rows.png`, `-full.png`, `-rows-detail.png`, `-rows-statements.png` |
| 1600 · Grid | Best surface here. Fits one screen, right-aligned tabular numbers, company + ticker, one click to provenance. Loses points on 195–212 px year columns for 9-character values, a two-tone first column, a 2.63:1 check mark, and a blank table when a filter matches nothing. | `1600x1000-grid.png`, `-grid-drawer.png`, `-grid-planned.png`, `-grid-segment.png`, `-grid-picker.png` |
| 1600 · Find in rows | Works (129 of 617 for NVDA) but the redraw drops the kit skin: every column header becomes a native grey outset button. Title still says 617 rows. | `1600x1000-find.png`, `-find-empty.png` |
| 1600 · Explore default | Clean chart, honest axis, Data table under it. The FY2026 bar sums 3 of 6 companies and reads as a 57% capex collapse. 13 unlabeled controls in sentence fragments wrap to 3 ragged lines. Show rows grows the page to 3,471 px with unskinned headers. | `1600x1000-explore.png`, `-explore-tooltip.png`, `-explore-data-rows-full.png`, `-explore-lines.png`, `-explore-empty.png`, `-explore-projects.png` |
| 1600 · Saved view | Same chart and the same FY2026 drop, under a developer note ("schema v11 dropped the duplicate `group` column"). Saved list indented 10 px off its header. | `1600x1000-saved.png` |
| 1280 · Rows | As 1600, plus the nav wraps "Known gaps" to two lines (header 56→64 px); 5 of 40 columns visible. | `1280x800-rows.png`, `-full.png` |
| 1280 · Grid | Fits; columns 168–182 px. Holds up. | `1280x800-grid.png` |
| 1280 · Find | As 1600. | `1280x800-find.png` |
| 1280 · Explore | Controls wrap so "to" starts line 3, split from "from"; chart still fits. | `1280x800-explore.png` |
| 1280 · Saved | Page scrolls 6 px. | `1280x800-saved.png` |
| Dark (1600 grid, explore) | Parity: chart reads theme tokens, marks keep contrast. | `1600x1000-grid-dark.png`, `-explore-dark.png` |

## Findings

| id | level | element | problem | norm violated | evidence | severity | verified |
|---|---|---|---|---|---|---|---|
| DE1 | page | Explore chart, FY2026 (default and saved view) | FY2026 sums only the 3 companies that have filed (MSFT, NVDA, APLD). Bar drops $293B→$125B with no partial-year mark. A reader sees capex collapse. | C3 status legible; H2 | `1600x1000-explore.png`; Data table Hyperscaler FY2026 $115,948M = MSFT alone (`-explore-data-rows-full.png`); Grid 2026 blank for AMZN, GOOGL, AMD (`-grid.png`) | P0 | measured |
| DE2 | layout | Rows table | All 617 rows and 40 columns render at once: page 19,110 px (pageScrollY 18,110), table 5,493 px wide in 1,069 px (19% visible; 5 cols at 1280), thead `position: static`. | L1; P1 data-grid conventions (sticky header, paging, column set) | audit.json rows: pageScrollY 18110; interact.json rows_geom tablewrap 5493/1069, cols 40, thead_sticky static; `1280x800-rows-full.png` | P1 | measured |
| DE3 | component | Column headers after Find, and the Explore rows tables | Redraw skips `skin()`: header buttons lose all classes and show native outset borders. Same in Explore Show rows and bar-click tables. | H5 consistency; I8 | interact.json find_skin className "" borderStyle "outset"; ex_rows btns ""; `1600x1000-find.png`, `-explore-data-rows-full.png` | P1 | measured |
| DE4 | component | Row detail expander | Label/value list spans the 5,493 px table: values start ~900 px right of labels, long values clipped at the pane edge, `value` shows raw 1069000000; 1,068 px tall. | D4 proximity; H6; C4 | `1600x1000-rows-detail.png`; rows_detail 1068 | P1 | measured |
| DE5 | component | Grid empty result | Kind = Planned: header row "COMPANY" only, no message; Export CSV stays primary on 0 rows. | I8 empty state | `1600x1000-grid-planned.png` | P1 | observed |
| DE6 | component | Explore chart on cold deep link | `#explore?measure=projects…` loaded directly shows "Chart unavailable" over a 400 px blank; Plotly is `defer` from CDN and the page renders first. Same route from in-app navigation draws. | I8; I2 | `1600x1000-explore-projects.png`; proj.py run (Plotly present after load, message stays) | P1 | observed (cause suspected) |
| DE7 | group | Explore controls | 13 controls, 0 visible labels; values as fragments ("every asset type", "then", "x: fiscal year", "series: layer"); two controls both named "Measure"; 3 ragged lines; at 1280 From and To split across lines. | C1; A2; P2; D4 | interact.json ex_geom sels/labels 0 (both viewports); `1600x1000-explore.png`, `1280x800-explore.png` | P1 | measured |
| DE8 | component | Explore Show rows table | 27 rows at ~53 px each: reported name wraps 4 lines, source accession ids wrap 3; page grows to 3,471 px. | D1 density; L3 | `1600x1000-explore-data-rows-full.png`; ex_rows sh 3471 | P2 | measured |
| DE9 | component | Saved view note | Developer sentence: "us-gaap PaymentsToAcquire…, (schema v11 dropped the duplicate `group` column)". | Product copy only; C1 | `1600x1000-saved.png`; saved_geom.note | P2 | observed |
| DE10 | component | Chart tooltip | "$119,016M" while the axis reads $B; "3 row(s)". | H5; C1 | `1600x1000-explore-tooltip.png` | P2 | observed |
| DE11 | component | Stacked bars by layer | Hyperscaler is 97–99% of each bar; Chip design and Miner to HPC render as 1–3 px slivers, unreadable. | H2; dataviz form fit | `1600x1000-explore.png`; tooltip "99% of the fiscal year" | P2 | observed |
| DE12 | layout | Band under scope line | 44 px (Grid, Explore) and 68 px (Rows) of empty space between "6 companies · Data as of" and the first control. | D2 dead band | interact.json scopeY 82 vs ctrlY 126; rows pagehead y 150 | P2 | measured |
| DE13 | group | Rows count | "617 rows · USD" under the title and "617 rows" beside Find; title stays 617 when Find shows "0 rows of 617". | C2 | `1600x1000-find-empty.png` | P2 | observed |
| DE14 | page | Rows/Grid switch and export | Switch sits beside the title on Rows, first in the control line on Grid; Grid has no title; export is a filled primary on Grid, outline CSV/JSON on Rows, text links on Explore. | H5 | `1600x1000-rows.png`, `-grid.png`, `-explore.png` | P2 | observed |
| DE15 | component | Rows side list | Active item bleeds 20 px left of the content edge (x 136 vs 156); items 70 px tall with wrapping descriptions; geometry spill 12 px. | L4; D5 | interact.json rows_geom active x 136; audit overflowSpills 12 | P2 | measured |
| DE16 | component | Grid columns | Year columns 195–212 px for ≤10-char values (168–182 at 1280); first column white against transparent cells; "2022" headers vs "FY2022" in Rows and Explore. | D5; H5 | interact.json grid_geom ths/tds | P2 | measured |
| DE17 | component | Grid units | "$390,000" next to "$9.8M" in one column set. | H5 | `1600x1000-grid-segment.png` | P2 | observed |
| DE18 | component | Verification marks | ✓ at 2.63:1; ○ at opacity .6; legend is a run-on muted string in the control line. | A1; C3 | audit.json grid lowContrast mk.t 2.63 | P2 | measured |
| DE19 | component | Controls sizing | Rows/Grid 41×20, Export CSV 76×20, CSV/JSON 20 px, every select 21 px, sort headers 18 px. | I4 (≥24) | audit.json smallTargets, all states | P2 | measured |
| DE20 | component | Rows/Grid active segment | No focus ring when tabbed. | I7 | interact.json rows_tab[0], grid_tab[1] ring NONE | P2 | measured |
| DE21 | component | Companies "Custom…" picker | Select reads "Custom…" as soon as the drawer opens though nothing is applied; closing without Apply keeps the false label; no all/none. | C3; I5 | `1600x1000-grid-picker.png` | P2 | observed |
| DE22 | component | Provenance drawer crop | Crop renders as an empty 256×120 frame after 4 s. | I8 loading/error state | `1600x1000-grid-drawer.png` | P2 | observed (cause suspected) |
| DE23 | component | Statements list | First column a 90-char pipe id cut with "…"; amounts monospace "135,000,000" where Grid and Explore use "$135M". | D5; H5 | `1600x1000-rows-statements.png` | P2 | observed |
| DE24 | group | Explore output line | "27 rows · JSON · CSV · Save as view" sits 4 px under the controls with no break between input and output groups; the one primary is buried mid-line. | D4; H1 | `1600x1000-explore.png` | P2 | observed |
| DE25 | layout | Header at 1280 | Nav wraps "Known gaps" to two lines; header 56→64 px. | L6 reflow | interact.json header 64 at 1280; `1280x800-rows.png` | P2 | measured |
| DE26 | group | Saved views list | Items indented 9.6 px from the "4 saved views" header; meta lines in machine words ("taxonomy · ppe gross by type"). | H6; C1 | saved_geom viewrows padding 9.6px; `1600x1000-saved.png` | P3 | measured |
| DE27 | component | Plotly modebar | Grey strip over the top-right gridline on hover. | H4 | `1600x1000-explore-tooltip.png` | P3 | observed |
| DE28 | component | Series colours | AMD #2f5bd3 and APLD #3d8fc4 near-identical; colour order is first-seen per browser (localStorage), so viewers see different colours for the same company. | H4; H5 | `1600x1000-explore-lines.png`; explore.js colorReg | P3 | observed / suspected |
| DE29 | component | Projects Basis column | Text cut mid-word ("R&D projec") without ellipsis. | C4 | `1600x1000-explore-projects.png` | P3 | observed |
| DE30 | page | Spacing scale | Off-scale gaps 3, 6, 10, 11 px; near-dupes 10/11/12. | D3 | audit.json spacing.offScale | P3 | measured |
| DE31 | component | "Signer" label (header) | 1.43:1. | A1 | audit.json lowContrast | P3 | measured |

## Excellent as is

- Grid table: right-aligned tabular figures, company name + muted ticker, one screen at both viewports, uppercase compact header, no horizontal page scroll (pageOverflowX 0 in every state).
- Provenance drawer: value and verification as two figure cards, the 10-K line and column quoted, Open in 10-K link; Escape closes it and focus goes to Close on open.
- Find in rows: 150 ms debounce, "129 rows of 617" count updates inline.
- Explore Data disclosure: the plotted numbers as a copyable table directly under the chart.
- Dark mode parity on Grid and Explore; the chart reads the kit tokens.
- Chart axis: zero-based, $ prefix, unit in the axis title, category order by year.
