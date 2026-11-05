I've finished the audit, but `findings.md` was not written: the harness refused the file write and said to return the findings as text instead. The findings are below; save them to `/Users/kennygeiler/ai-capex-ledger/docs/ux-visual/pages/proof-board/findings.md` if you need the file.

Everything was captured and measured: 10 states, at 1600×1000 and 1280×800, each with a viewport and full-page screenshot. Every non-GET request was aborted (none were attempted) and no write control was clicked.

## Counts
21 findings in total.

| Severity | Count |
|---|---|
| P0 | 1 |
| P1 | 4 |
| P2 | 11 |
| P3 | 5 |

| Level | Count |
|---|---|
| Component | 12 |
| Group | 2 |
| Page | 5 |
| Layout | 2 |

## 5 worst
1. **F1 · P0 · component** The Value cell's full-dollar line spills 23–62 px out of its 9.5rem column and is cut off by the crop next to it ("$9,320,00", "$215,874,00"). This is the screen where figures are checked by eye to the dollar (L6, C4). Measured: geometry `overflowSpills` on `td.num`.
2. **F2 · P1 · group** The company picker is six fused 20 px outline buttons. APLD 19/20, the only company with work left, looks the same as the five 20/20 companies (I4, H2, C3). Measured: `smallTargets` h 20.
3. **F3 · P1 · group** The Hand check summary is five lines of "N right · N wrong · N can't say · N unchecked · error rate (95% CI…)", mostly zeros. The same string repeats in the card header and in every group row, which buries "1 unchecked" (C2, D5, wall of text). Observed.
4. **F4 · P1 · component** Each decided row states its verdict three times and keeps an empty note box. MSFT is fully decided yet renders 93 live buttons and 20 empty inputs (I5, C2, H1). Measured.
5. **F5 · P1 · component** Thumbnail crop text is about 6–8 px and rows are sliced mid-line, so every check needs the lightbox (A1, C4). Observed.

## All findings
| id | level | element | problem | norm | evidence | sev | verified |
|---|---|---|---|---|---|---|---|
| F1 | component | Value cell | As-filed $ line clipped 23–62 px | L6, C4 | `overflowSpills`; 1600-handcheck-apld.png, 1280-handcheck-msft.png | P0 | measured |
| F2 | group | Company picker | 20 px buttons; 19/20 looks the same as 20/20 | I4, H2, C3 | `smallTargets`; 1600-board-handcheck-section.png | P1 | measured |
| F3 | group | Summary block | 5-line count/CI wall, repeated in card and group headers | C2, D5 | notes APLD_head_text; 1600-handcheck-apld.png | P1 | observed |
| F4 | component | Check cell | Verdict stated 3×; empty note on every row; 93 live buttons on a decided company | I5, C2, H1 | notes MSFT_disabled_btns; 1600-handcheck-msft.png | P1 | measured |
| F5 | component | Thumbnails | 6–8 px text, white bands, rows sliced | A1, C4 | 1280-handcheck-msft.png | P1 | observed |
| F6 | layout | Table columns | Source column 540/465 px, about half dead on single-cite rows; verdict ~900 px from item | D2, I4 | notes APLD_cols | P2 | measured |
| F7 | component | Calculated row | Figure shown 4× in 2 formats; 3rd crop wraps alone; row 443 px | C2, D2 | notes calc_text/calc_row_h; 1600-calculated.png | P2 | measured |
| F8 | component | Group names | Link-blue and pass-green used for categories | H4, I1 | 1600-calculated.png | P2 | observed |
| F9 | page | Board header | ~70 px dead band above "Proof" | D2 | notes sections_top; 1600-board.png | P2 | measured |
| F10 | component | Stage cells | 4 unlabeled numbers; meaning only in legend and hover; green zeros; separators misaligned | C1, H6, I7 | 1600-board.png | P2 | observed |
| F11 | component | Lightbox | No focus trap: Tab goes to "Skip to content" | I7 | notes lightbox_tab1 | P2 | measured |
| F12 | page | Board | "119 of 120 checked" shown 3× | C2 | 1600-board-full.png | P2 | observed |
| F13 | page | Failure types | Chart and table duplicate the numbers; ~350 px dead band; snake_case labels | C2, D2, C1 | `deadSpace`; 1600-board-full.png | P2 | measured |
| F14 | layout | 1280 nav and table | Nav wraps ("Known gaps"); company cells take 3 lines (row 120 px) | L6, D1 | `wrappedControls`; 1280-board.png | P2 | measured |
| F15 | component | Note input | Placeholder cut at 1280 | C4 | 1280-handcheck-msft.png | P2 | observed |
| F16 | page | Hand check framing | Loose text between cards, unlike every other section | H5 | 1600-board-handcheck-section.png | P2 | observed |
| F17 | component | Verdict buttons | 20 px tall; widths 40/48/63 | I4 | `unevenRows`, `smallTargets` | P3 | measured |
| F18 | component | Stage rows | Last column has no header; 2 tab stops per company | C1, I7 | notes focus_order | P3 | measured |
| F19 | page | Spacing | Off-scale 6/10/11/14 px | D3 | `spacing.offScale` | P3 | measured |
| F20 | component | Lightbox caption | "FY2026 · 2026" repeated; two equal-weight links | C2, H1 | 1600-lightbox.png | P3 | observed |
| F21 | component | Signer label | Contrast 1.43:1 | A1 | `lowContrast` | P3 | measured |

Two audit hits are not counted. The 1.0 contrast reported on the selected "MSFT 20/20" button is a measurement artifact, since the screenshot shows it legible. The 9000×9000 Plotly tester svg is a library artifact.

## Verdicts
- **Board (both viewports):** clean Tabler table, but four unlabeled numbers per cell, a dead band above the title, the hand-check status said three times, and Failure types shown twice. At 1280 the nav and company cells also wrap.
- **Hand check, APLD and MSFT:** value line clipped, the unfinished company not distinguished in the picker, a summary wall of numbers, and decided rows that look undecided. At 1280 the note placeholder is also cut.
- **Calculated item:** the formula with role-labelled crops is the best idea on the page, but the figure repeats four times and the row is 443 px.
- **Lightbox:** excellent content; Esc works and focus returns to the thumbnail; Tab escapes the dialog.

## Excellent as is
- **Lightbox content:** cell boxed in red, column in blue, row highlighted, "1 row not shown".
- **Calculated formula line:** the substituted figures plus one crop per operand, labelled by role.
- **As-filed figure plus scale** ("9,320 / In thousands").
- **No horizontal overflow** at either viewport (`pageOverflowX` 0 in all 10 captures).
- **Small type scale:** six font sizes; numbers right-aligned in tabular figures.
- **Group header rows** in the Hand check table carry their own rate.
- **Bounded width:** 1288 px at 1600 and 1108 px at 1280, with equal gutters.

Files are in `/Users/kennygeiler/ai-capex-ledger/docs/ux-visual/`:
- `pages/proof-board/shots/` — 30 PNGs
- `pages/proof-board/audit.json`
- `tmp/proof-board/capture.py`
- `tmp/proof-board/notes.json`