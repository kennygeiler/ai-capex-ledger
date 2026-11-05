# Reconcile — visual critique, 2026-11-04

App: http://localhost:3610/#reconcile (local, owner mode, data as of Nov 1, 2026). Headless Chrome via Playwright, GET only: every non-GET request was aborted, and none was attempted. Viewports 1600×1000 and 1280×800. Measurements: `audit.json` (layout-audit.js + geometry-audit.js per viewport/state). Scripts: `docs/ux-visual/tmp/reconcile/`. The flow decisions in `docs/ux-flow/report.md` stand. Where a finding touches one, it is limited to the visual layer and names the decision.

Shots: `shots/{viewport}-{state}.png` and `-full.png`. States: default, rule-open, mapping-open, by-company, filtered. Extra 1600 shots: focus-row, hover-row, selected (also 1280-selected).

## Verdicts

**1600 · default** (`1600-default.png`, `-full.png`). The page is 5,719 px tall: 63 rows in two cards, with 4,719 px of page scroll (measured). Rows are 63 px each. The four value columns in Rule findings show "—" in all 16 rows, and the only coloured signal is a red "Needs review" repeated 16 times. Below the "Data as of" strip, an 80 px empty band pushes the title down. The type scale is tight (4 sizes) and the width is bounded at 1,288 px. Verdict: tidy kit components, but a low-information first screen. About ten rows are visible, and none of them shows a number.

**1600 · rule-open** (`1600-rule-open.png`, `-zoom-decision.png`). The expanded row is 249 px. A 390 px-wide Details paragraph full of accession numbers and XBRL concept names leaves about 860 px empty beside it. Below it sits a bordered "Decision" card inside the table card. The decision control is a cramped 20 px segmented group, and Accept appears in the same blue as Save. Opening the row moves the numeric columns 11–26 px left. Verdict: below excellent. The detail has no layout of its own, and the decision control looks broken.

**1600 · mapping-open** (`1600-mapping-open.png`). A grey row holds two white cards: card inside grey inside card. The "Note wording" card is 421×520 and 5 % filled (measured dead space). The key/value grid leaves about 130 px empty under "Company line" because the FASB definition beside it is long. Raw `…Member` names in mono appear four times. Verdict: this is the right content for a mapping decision, but nesting and dead space hide it.

**1600 · by-company** (`1600-by-company-full.png`). The page is 6,494 px. Rows grow to 85 px, the Cause column repeats "Category mapping" for every mapping row, and rule rows and mapping rows share one header whose columns mean different things per row. Verdict: grouping adds height and repetition and gives the eye nothing new.

**1600 · filtered** (`1600-filtered.png`). This is the best state: 7 rows, no page scroll, one card. The header still reads "Needs review 16" over 7 rows, and the changed selects look exactly like their defaults. Verdict: close to excellent, apart from an unscoped count.

**1280 · default** (`1280-default.png`). The navbar wraps "Known gaps" onto two lines. The filter row wraps "Show 6 settled" to a second line (8 wrapped controls measured). The page is 6,178 px. Verdict: same issues as 1600, plus wrapping.

**1280 · rule-open / mapping-open** (`1280-rule-open.png`, `1280-mapping-open.png`). The expanded rows are 267 px and 632 px. At 1280 the 595 px-tall Note wording card fills 4 % of its area and spans 21 % of the viewport. The Alternatives list wraps mid-name. Verdict: as at 1600, with worse dead space.

**1280 · by-company** (`1280-by-company.png`). This is the worst state. Cause and Item are squeezed to about 90 px and wrap to four lines, so each row is 105 px. Four value columns that hold only "—" keep about 650 px. The page is 7,590 px. Verdict: fails; it reads as a broken table.

**1280 · filtered** (`1280-filtered.png`). Fits with 75 px of page scroll. The same unscoped count as at 1600.

## Findings

| id | level | element | problem | norm violated | evidence | severity | verified |
|---|---|---|---|---|---|---|---|
| F01 | layout | Grouped-by-company table at 1280 | Cause and Item columns shrink to ~90 px and wrap to 4 lines; rows are 105 px while four all-"—" value columns keep ~650 px | L6, D1, D2 | `1280-by-company.png`; rowH 105 (1600: 85) | P1 | measured |
| F02 | component | Header counts (Needs review / Proposed / Unverified) | With filters on, the header still shows the global counts ("Needs review 16" above 7 rows) | C3, C2 | `1600-filtered.png`, `1280-filtered.png` | P1 | observed |
| F03 | group | Bulk-selection bar | Ticking the first checkbox inserts a 73 px bar above the table, so the row just clicked jumps 101 px down under the pointer | L5, L3 | `1600-selected.png` vs `1600-default.png` (row y 386 → 487); bulk rect h 73 | P1 | measured |
| F04 | layout | Page scroll, headers | 4,719 px of page scroll at 1600 (5,378 at 1280; by-company 5,494 / 6,790). Table headers and filters are not sticky, so deep in Category mapping no column names are on screen | L1, I6 | audit `viewport.pageScrollY`; `1600-mapping-open.png` (no thead visible) | P1 | measured |
| F05 | group | Rule findings columns | Dataset, SEC XBRL, Gap and Difference are "—" in 16 of 16 rows and take ~45 % of the table width. Filling them is decided (flow #6); until then the columns should shrink, and once filled they still need fixed widths | D2, D5 | `1600-default.png` | P2 | observed |
| F06 | component | Decision segmented control (row + bulk) | 20 px tall, ~2 px side padding, "Fix" is 27 px wide; the active segment is the same blue fill as the Save primary beside it, so two blue elements compete | I4, P2, H1 | `1600-rule-open-zoom-decision.png`; smallTargets Accept 51×20, Fix 27×20 | P2 | measured |
| F07 | group | Expanded rows | Bordered cards nest inside the table card (Decision card; mapping card + Note wording card on a grey band); the owner's banned "bordered boxes everywhere" | D2, owner rule | `1600-rule-open.png`, `1600-mapping-open.png` | P2 | observed |
| F08 | component | Note wording card | 421×520 at 5 % fill (1280: 363×595, 4 %) for "Note text unavailable" + one link | D2 | audit `deadSpace` mapping-open | P2 | measured |
| F09 | component | Mapping detail key/value grid | Row height set by the long FASB definition leaves ~130 px empty under Company line; Alternatives wrap mid-name | D2, H6 | `1600-mapping-open.png`, `1280-mapping-open.png` | P2 | observed |
| F10 | group | Rule detail "Details" | A 390 px-wide prose block with an accession number, an XBRL concept name and a tolerance, and ~860 px empty beside it. The figures it states (sum, tagged, gap) belong in labelled value cells | D2, C1, owner rule (no prose) | `1600-rule-open.png` | P2 | observed |
| F11 | group | Table columns on expand | Opening a row moves the numeric columns 11–26 px left (auto table layout) | L5 | `1600-default.png` vs `1600-rule-open.png` (Dataset "—" x 887 → 861; status x 1257 → 1246) | P2 | measured |
| F12 | group | Category mapping header | The proposed category text sits in the column headed DATASET, right-aligned under it; the dashes sit under SEC XBRL and DIFFERENCE; the reported name sits under ITEM | H6, C1 | `1600-mapping-open.png` | P2 | observed |
| F13 | page | Semantic colour | Red marks the routine queue state "Needs review" (16× in a row) and also "Company tags …"; one mapping cell can carry orange, green and red at once | H4 | `1600-default.png`, `1600-default-full.png` | P2 | observed |
| F14 | layout | Page head | "6 companies · Data as of" sits 12 px under the navbar with an ~80 px empty band before the H1 | D2, D4 | `1600-default.png` (y 68 → 164) | P2 | measured |
| F15 | component | Table rows | Rows have `cursor: pointer` but no hover background (transparent), so it is unclear which row a click will open | I1, I8 | `1600-hover-row.png`; hoverBg rgba(0,0,0,0) | P2 | measured |
| F16 | component | "Select all N" button | No visible focus indicator (outline none, no shadow) | I7, A | tab-order probe in `tmp/reconcile/extra.json` | P2 | measured |
| F17 | page | Tab order | 3 tab stops per row (row, checkbox, company link) × 63 rows, about 190 stops to reach the end; j/k exists, but only a hover tooltip reveals it | I7 | tab-order probe; `1600-focus-row.png` | P2 | measured |
| F18 | component | First row | Painted as the current row on load (blue bar + tint) with no focus or selection, so it reads as selected | H4, I6 | `1600-default.png`, `1600-filtered.png` | P2 | observed |
| F19 | group | Filter bar | Changed selects look the same as defaults; no active-filter count and no Clear | I6, C3 | `1600-filtered.png` | P2 | observed |
| F20 | group | Scope + Industry selects | Both list the same three industries, side by side (the order issue is flow 027; this is the visible duplicate) | C2, I5 | probe: Scope options include chip_seller/hyperscaler/miner_to_hpc | P2 | measured |
| F21 | component | Bulk bar text, checkbox names | "1 selected: APLD segment_capex FY2026"; checkbox labels "Select Applied Digital segment_capex FY2026" | C1, A2 | `1600-selected.png`; tab probe | P2 | measured |
| F22 | group | Grouped-by-company rows | The Cause cell repeats "Category mapping" for every mapping row and "Does not tie to reported total" per rule row; rule and mapping rows share one header whose columns differ by row | D5, H5 | `1600-by-company-full.png` | P2 | observed |
| F23 | page | Row density | 63 px rows for two short text lines in a review tool (85/105 px when grouped by company) | D1 | extra.json rowH | P2 | measured |
| F24 | group | Filter bar at 1280 | "Show 6 settled" wraps to a second line and the bar grows from ~40 to 67 px | L6, L4 | `1280-default.png`; geometry `wrappedControls` 8 | P2 | measured |
| F25 | component | "Keyboard" in the header stats | Looks like a stat; it is a hover-only tooltip, so keyboard and touch users cannot reach it | C4, I7 | `1600-default.png` | P3 | observed |
| F26 | component | Company cell | "AMD AMD" when name = ticker; in Category mapping the company wraps to 2 lines (column ~90 px) while Rule findings shows it on one | D5, H5 | `1600-mapping-open.png`, `1280-mapping-open.png` | P3 | observed |
| F27 | component | GAP header | Left-aligned among right-aligned numeric headers | H6 | `1600-default.png` | P3 | observed |
| F28 | page | Spacing | Off-scale gaps 6 and 11 px; near-duplicates 4/6, 6/8, 11/12 | D3 | audit `spacing` (all states) | P3 | measured |
| F29 | component | Selects, checkboxes, small buttons | 20–21 px tall, under the 24 px floor | I4 | audit `smallTargets` (Scope 122×21, checkbox 20×20, Select all 78×20) | P3 | measured |
| F30 | component | Mapping detail | Raw `…Member` names in mono repeated 4× next to their readable labels | C1, D5 | `1600-mapping-open.png` | P3 | observed |
| F31 | component | Check select | Option reads "other", lowercase and raw | C1 | probe: `Check: other=other` | P3 | measured |
| F32 | layout | Navbar at 1280 | "Known gaps" wraps to two lines and the navbar grows to 64 px | L6 | `1280-default.png`; `wrappedControls` nav | P3 | measured |
| F33 | component | "Unverified 6" | Accent blue used for a state count, next to red and orange | H4 | `1600-default.png` | P3 | observed |

Audit note: layout-audit flags "Signer" at 1.43:1 contrast in every state. It sits on the dark navbar, and the shot shows it legible. This looks like a background-detection false positive in the audit, so no finding is filed.

## Excellent as is

- Filtered state at 1600: 7 rows, one card, no page scroll. This is the shape the whole page should have (`1600-filtered.png`).
- Keyboard model: j/k move, Enter opens and Escape closes, both confirmed (enterOpens true, escCloses true). The row focus ring is a solid 2 px.
- Bounded width: the 1,288 px container, with no horizontal overflow at either viewport (pageOverflowX 0).
- Type scale: 4 sizes (12/13/14/20) in every state, with clear weight steps.
- Rule row item cell: field + period on top, the check name muted beneath. Two lines, scannable, product copy.
- Status in words plus colour ("Needs review"), never colour alone.
- Mapping detail content set: company line with history, proposal with source, company tag, basis with author and date, alternatives, affects. Every fact a mapping decision needs, labelled as values.
