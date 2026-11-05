Audit is done: 28 findings, 1 P0. The `findings.md` report was not written, because the harness refused that file write ("Subagents should return findings as text"). The full report content is below for the caller to save as `/Users/kennygeiler/ai-capex-ledger/docs/ux-visual/pages/trail/findings.md`.

Screenshots are in `/Users/kennygeiler/ai-capex-ledger/docs/ux-visual/pages/trail/shots/`, and the measurements for each viewport and state are in `/Users/kennygeiler/ai-capex-ledger/docs/ux-visual/pages/trail/audit.json`. The scripts are `docs/ux-visual/tmp/trail/shoot.py` and `extra.py`. The bundled Chromium was missing, so they ran in system Chrome. All non-GET requests were blocked and none were attempted.

## Counts
- **By severity:** P0 1 · P1 4 · P2 14 · P3 9 (total 28)
- **By level:** page 10 · group 2 · component 15 · layout 1
- **By check type:** measured 11 · observed 15 · suspected 2

## 5 worst
1. **V1 · P0 · red means two things (H4, C3).** The legend uses red for both "Needs review" and "Blocks release". APLD shows 9 red rows while its Release card says "Done · No blocking items · Complete". Shots: `1600x1000-apld-top.png`, `1600x1000-apld-release-view.png`.
2. **V2 · P1 · mixed units in one cell (H5, C1).** The Verification cell for restated rows puts "$9.6M → $1.8M" next to "9,552 → 1,760" with no unit, which reads like a 1,000× discrepancy. Shot: `1600x1000-apld-notes-expanded.png`.
3. **V3 · P1 · open work sits at the bottom (L7, H1).** MSFT's 6 open items are 2,599 px down, below three "Complete" cards. At 1280 the first screen of APLD shows only complete content. Measured in `audit.json`.
4. **V4 · P1 · bad column split in Note figures (L4, D2).** Item (≈276 px) wraps to 2–3 lines and Verification (≈299 px) to 6–8 lines, while Source (≈527 px) holds one 210 px line on 7 of 9 open rows. Rows run 166–461 px and the page is 16,441 px when expanded. Measured.
5. **V5 · P1 · Category mapping cards are walls of text (C4, D5, D2).** FASB definitions repeat verbatim, the model and date line repeats on all 16 cards, and half the second row is empty. The card takes 3,096 px, 59% of the page. Measured; this adds to the already-decided one-row cards.

---

# Company trail — visual audit

| Item | Value |
|---|---|
| Surface | Company trail, `#proof/<ticker>` |
| Date | 2026-11-04 |
| Data | Local copy, http://localhost:3610, data as of Nov 1, 2026 |
| Viewports | 1600×1000, 1280×800 |
| States | APLD top · APLD Note figures expanded · APLD Category mapping · APLD crop lightbox · MSFT top · AMD top |
| Method | Playwright with system Chrome, GET only (non-GET aborted: 0 attempted). `layout-audit.js` + `geometry-audit.js` per state → `audit.json`. Scripts: `docs/ux-visual/tmp/trail/shoot.py`, `extra.py` |
| Out of scope | Decisions already taken in `docs/ux-flow/report.md` (DP4 header link, DI1 count drift, #10 one-row mapping cards, collapsed Filings, HI2 naming). Cited here only where the visual problem goes beyond the decision. |

Shots: `docs/ux-visual/pages/trail/shots/`.

## Verdicts by viewport × state

**1600×1000 · APLD top** — `1600x1000-apld-top.png`, `-full.png`. Below excellent. About 80 px of empty space sits between the "6 companies · Data as of" line (y≈68) and the H1 (y≈164). Under the H1, an 8-entry legend wraps to two lines and leaves the "Proposed" dot at the end of line 1 with its word on line 2. The "Before release" card states coverage and verification clearly, but its right half (Last release, Changes since release) has two lines in a 216 px card. The Filings table uses 45 px rows, an all-"—" Value column and "Done · Statements located" five times. The page is 5,279 px tall (5.3 screens, measured), and Category mapping takes 3,096 px of that (59%).

**1280×800 · APLD top** — `1280x800-apld-top.png`, `-full.png`. Same issues as at 1600, plus the "Known gaps" nav item wraps to two lines and makes the navbar 64 px (geometry `wrappedControls`, measured). The legend orphans the "Unverified" dot instead. The first screen shows the header, the summary card and the Filings table, all of which are complete. No open item appears above the fold.

**1600×1000 · Note figures expanded** — `1600x1000-apld-notes-expanded.png`, `-full.png`. Strong source evidence in weak column allocation. Each red row's crop pair with "Superseded" under the old reading reads well. But the Item column (≈276 px) wraps "Segment capex · FY2023 · Parts vs total" onto two lines. Next to it, the Source column (≈527 px) holds one 210 px text line on 7 of 9 open rows. The Verification column (≈299 px) carries up to 7 lines of orange prose that mix $M ("$9.6M → $1.8M") with raw thousands ("9,552 → 1,760") in the same cell. The card is 12,104 px tall and the page 16,441 px (16 screens, measured).

**1280×800 · Note figures expanded** — `1280x800-apld-notes-expanded.png`. Worse at this width. Item wraps to 3 lines ("PP&E by category · Other / equipment and fixtures · / FY2024"), Verification wraps to 7–8 lines, and a crop row is 189–461 px tall. Two rows fit on the first screen.

**1600×1000 · Category mapping** — `1600x1000-apld-mapping.png`, `1600x1000-apld-mapping-card.png`, `1600x1000-apld-release-view.png`. Information-rich and well labelled, but each card runs as a wall. FASB definitions repeat verbatim (the "Building and Building Improvements" paragraph appears twice in a row). "Claude Fable 5.1 · 2026-11-01" appears on all 16 cards. Member names in monospace break mid-word ("…DevelopmentCostsMem / ber"). Card heights are 291–521 px (measured). The second row (Alternatives, Affects) leaves the two right columns empty. In `1600x1000-apld-mapping.png` the crop thumbnails above the card render as empty white boxes.

**1280×800 · Category mapping** — `1280x800-apld-mapping-full.png`. Card heights are 291–466 px (measured). The same wall pattern, with narrower columns and more wrapping.

**1600×1000 · Crop lightbox** — `1600x1000-apld-lightbox.png`. Excellent with small defects. The crop is legible at 1240 px wide. A blue box outlines the column header and a red box outlines the cell. Focus moves to Close on open, Escape closes, and focus returns to the thumbnail (measured). Defects: the caption reads "May 31,2024" with no space, and the prior-year cell (1,684) shares the green row tint, so two figures look selected until the red box is found.

**1280×800 · Crop lightbox** — `1280x800-apld-lightbox.png`. Same as at 1600. The dialog uses 1,176 of 1,280 px and the image stays legible.

**1600×1000 · MSFT top** — `1600x1000-msft-top.png`, `1600x1000-msft-category-view.png`. Calmer, because four stages collapse to one tally line. The header says "6 to review" and Statement figures, Note figures and AI disclosures all say "Complete". The 6 open items are 2,599 px further down, in Category mapping. Money format changes by company: MSFT reads "$182,749M" where APLD reads "$279.3M".

**1280×800 · MSFT top** — `1280x800-msft-top.png`. Filings rows grow to 65 px because the source line wraps (measured `rowHeights`).

**1600×1000 / 1280×800 · AMD top** — `1600x1000-amd-top.png`, `1280x800-amd-top.png`. The H1 reads "AMD AMD". At 1280 the 10-K/A item breaks its date across lines ("FY ending 2025-12- / 27"). This is the only company where "Changes since release" has content ("2 added · Details"), and that tile works.

## Findings

| id | level | element | problem | norm violated | evidence | severity | verified |
|---|---|---|---|---|---|---|---|
| V1 | page | Status colour, red | Red means both "Needs review · open item" and "Blocks release" in the legend. APLD shows 9 red rows, yet its Release card reads "Release gate · Done · No blocking items" and "Complete". A reader cannot tell which red rows block release, so the red reads as "blocks" while the gate says nothing does. | H4, C3 | `1600x1000-apld-top.png` legend; `1600x1000-apld-release-view.png` | P0 | observed |
| V2 | component | Verification cell, restated rows | Units mix inside one cell: "$9.6M → $1.8M" next to "9,552 (10-K 2024-08-30) → 1,760 … dataset uses 1,760". Raw thousands sit beside $M with no unit, so it reads like a 1,000× discrepancy. | H5, C1 | `1600x1000-apld-notes-expanded.png` rows 1–2 | P1 | observed |
| V3 | page | Stage order vs open work | Open work sits at the bottom. MSFT's 6 open items are all in Category mapping, 2,599 px down, below three "Complete" cards. On APLD the first screen at 1280 holds only complete content. Stage cards stay in pipeline order whatever their state. | L7, H1 | `1600x1000-msft-top.png`, `1280x800-apld-top.png`, `audit.json` msft cards | P1 | measured |
| V4 | group | Note figures table, column widths | Fixed column split. Item ≈276 px wraps to 2–3 lines and Verification ≈299 px to 6–8 lines, while Source ≈527 px holds one 210 px line on 7 of 9 open rows. Rows are 166–461 px tall. | L4, D2 | `audit.json` deadSpace `col.c-source` w 527; `rowHeights`; `1280x800-apld-notes-expanded.png` | P1 | measured |
| V5 | group | Category mapping card | Long-text wall: FASB definitions verbatim, repeated in adjacent cards (Building ×2, Electric Generation ×3, Technology Equipment ×2). The model and date line appears on all 16 cards. The second row leaves two of four columns empty. Card heights are 291–521 px, 59% of the page. The flow report already decided on one-row cards; this finding adds that definitions should collapse behind the member name. | C4, D5, D2 | `1600x1000-apld-mapping-card.png`; `audit.json` mapping itemHeights | P1 | measured |
| V6 | component | Legend under H1 | 8 states with explanatory phrases ("ties to totals or confirmed in 2 filings") wrap to two lines at both widths. The coloured dot ends line 1 and its word starts line 2 ("●" / "Proposed" at 1600, "●" / "Unverified" at 1280). | C4, H6 | `1600x1000-apld-top.png`, `1280x800-apld-top.png` | P2 | observed |
| V7 | page | One state, three words | The legend says "Proposed", the card tag says "To confirm" and the stage tally says "8 to review", all for the same items. The Verification tile says "Tie to totals" and "Confirmed in 2 filings", while the tallies and legend say "corroborated". | C1, H5 | `1600x1000-apld-mapping.png`, `1600x1000-msft-top.png` | P2 | observed |
| V8 | page | Orange overloaded | Orange carries "17 to review", "SEC checked 7d ago · out of date", "Proposed", "To confirm", "Superseded" and "Restated: …" prose. Five meanings dilute the to-review signal. | H4 | `1600x1000-apld-top.png`, `1600x1000-apld-notes-expanded.png` | P2 | observed |
| V9 | component | "Differs:" in mapping | The company's own tag differing from the proposal is shown in red, the colour for "Needs review / Blocks release". It is information, not a failure. | H4 | `1600x1000-apld-mapping-card.png` | P2 | observed |
| V10 | page | Header whitespace | About 80 px of empty space between the meta line (y≈68) and the H1 (y≈164) at both widths. The H1 then has only about 6 px below it before the legend. | D2, D4 | `1600x1000-apld-top.png`, `1280x800-apld-top.png` | P2 | measured |
| V11 | page | Money format by company | MSFT shows "$182,749M" and "$132,836M", APLD shows "$279.3M". The same column type uses two scales across companies. | H5 | `1600x1000-msft-category-view.png` vs `1600x1000-apld-mapping-card.png` | P2 | observed |
| V12 | page | Three date formats | "Data as of Nov 1, 2026", "As of 5 Nov 2026, 04:56 UTC" and "Filed 2026-07-29" sit 180 px apart. The UTC stamp also reads as later than the data date. | H5, C1 | `1600x1000-apld-top.png` | P2 | observed |
| V13 | layout | Nav at 1280 | "Known gaps" wraps to two lines and the navbar grows to 64 px. | L6, P2 | `audit.json` 1280 `wrappedControls`; `1280x800-apld-top.png` | P2 | measured |
| V14 | component | Crop thumbnails | At about 250×120 px the table text inside is about 5 px and illegible, and the top row is cut off mid-glyph. During capture the thumbnails rendered as empty white boxes (`loading="lazy"`, no placeholder or state). | I8, D5 | `1600x1000-apld-notes-expanded.png`; `1600x1000-apld-mapping.png`; `_shared.js:228` | P2 | observed (blank boxes: suspected lazy-load timing) |
| V15 | page | Keyboard path | 482 links and 138 crop buttons with no skip link. 21 tab stops pass before the first open item. | I7 | `audit.json` tabOrder, nLinks 482, nThumbs 138 | P2 | measured |
| V16 | component | Summary card, right half | "Last release" and "Changes since release" fill 2 of 8 lines in a 216 px card. Half the card is blank when there are no changes (APLD, MSFT). | D2 | `1600x1000-apld-top.png`, `1600x1000-msft-top.png` | P2 | observed |
| V17 | component | Filings rows | Rows are 45 px, 65 px at 1280 for MSFT, against a 28–36 px tool norm. The Value column is "—" in every row. | D1, D5 | `audit.json` rowHeights; `1280x800-msft-top.png` | P2 | measured |
| V18 | component | AMD 10-K/A row | The date breaks across lines ("2025-12- / 27") at 1280. | C4, L6 | `1280x800-amd-top.png` | P2 | observed |
| V19 | component | Mapping member names | Monospace member names break mid-word ("SoftwareAndSoftwareDevelopmentCostsM / ember"). | C4 | `1600x1000-apld-mapping-card.png`, `1600x1000-apld-release-view.png` | P3 | observed |
| V20 | component | Navbar "Signer" label | Contrast 1.43:1 on the dark navbar. | A1 | `audit.json` lowContrast | P2 | measured |
| V21 | component | Header links | "Reconcile" (59×15), "Dataset" (46×15) and "Review in Reconcile →" (135×18) are smaller than the 24 px minimum. | I4 | `audit.json` smallTargets | P3 | measured |
| V22 | component | Lightbox caption | "May 31,2024" has no space after the comma. | C1 | `1600x1000-apld-lightbox.png` | P3 | observed |
| V23 | component | Lightbox row tint | The prior-year cell (1,684) shares the green highlight, so two numbers look selected. | H2 | `1600x1000-apld-lightbox.png` | P3 | observed |
| V24 | component | AMD H1 | Reads "AMD AMD" because the name and ticker are identical. | C2 | `1600x1000-amd-top.png` | P3 | observed |
| V25 | component | Disclosure chevrons | The expander for the long form is a 6 px "⌄"/"›" at the end of the status line, hard to see and hard to hit. | I1, I4 | `1600x1000-apld-notes-expanded.png`, `1600x1000-apld-mapping-after5s.png` | P3 | observed |
| V26 | page | Spacing scale | Off-scale gaps of 6, 10, 11 and 14 px. | D3 | `audit.json` spacing.offScale | P3 | measured |
| V27 | component | Navbar focus ring | Nav links focus with a box-shadow at 0.25 alpha of blue on the dark navbar, likely invisible. | I7, A1 | `audit.json` tabOrder outline | P3 | suspected |
| V28 | page | Loading state | Content loads async for about 2–4 s. No skeleton or progress state was captured. | I2, L5 | not captured | P3 | suspected |

## Excellent as is

- The crop lightbox: a legible cell crop with the column header boxed blue and the cell boxed red. Focus moves to Close on open, Escape closes, and focus returns to the thumbnail. There are links to the filing and to sec.gov.
- Paired crops for restated figures, with "Superseded" under the old reading: the disagreement shows at a glance.
- Complete stages collapse to one tally line ("27 verified · 31 corroborated · 5 unverified"), which makes MSFT's top calm.
- Status always pairs a word with its colour ("Needs review", "Done", "Verified"). Colour never carries a state alone.
- "SEC checked 7d ago · out of date" states freshness in plain words.
- Bounded 1,320 px container, no horizontal scroll at either width (`pageOverflowX 0`). Numeric Value column right-aligned.
- Type discipline: 5 sizes (12/13/14/16/20), Inter plus monospace for member names, no italics, no serif display face.
- Verification tile: label left, count right, tabular figures.
- AMD's "2 added · Details" changes tile.