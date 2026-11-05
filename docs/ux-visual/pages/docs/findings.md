I couldn't write `findings.md`: the harness refused the Write call and said subagents must return findings as text. I didn't route around that with Bash, so the full findings follow. The screenshots and `audit.json` were saved.

**Counts:** 32 findings: P0 0 · P1 6 · P2 17 · P3 9. By level: Component 11 · Group 4 · Page 11 · Layout 6.

**The 5 worst:**
1. **EV-01 (P1, measured):** the single page's biggest figure is the superseded $9,552,000 (26px). The 1,760 the dataset uses appears only in a 12.8px orange line.
2. **EV-02 (P1, measured):** at 1280 the compare crops shrink to 590×108px. Filing text inside them is about 7px, with 260px empty below.
3. **EV-03 (P1, measured):** the filing viewer banner names no company, form, date or accession. It has no Superseded mark and no link back (0 links), and the tab title is "apld-20240531".
4. **EV-04 (P1, observed):** in the not-found state the banner says "Page shows 9,552", so the row was found. The page still stays at the 10-K cover (scrollY 0) of an 84,816px document.
5. **EV-05 (P1, measured):** the status words fail contrast. Orange is 2.91:1 and green 2.74:1 for "Readings differ", "Restated", "Superseded" and "Cell located".

The sixth P1 is **EV-06**: the page scrolls sideways at 860 and 1024 (scrollWidth 1099 and 1107), caused by the header.

## Verdicts

| Viewport | State | Verdict | Shots |
|---|---|---|---|
| 1600 | Compare | Fits one screen (pageScrollY 0). Best of the three: both crops sit at the same height and row, with the cited cells boxed red. Below excellent in five ways:<br>• cards break out of the page column (x=32 against the title at x=156)<br>• card content sits on the border (padding 0)<br>• status words fail contrast<br>• a 74px dead band sits above the title<br>• 44% of the viewport is empty below | `1600-compare.png`, `-full.png`, `-focus.png`, `-hover.png` |
| 1280 | Compare | Fits, but the crops are 590×108 and the filing text is about 7px. The nav wraps "Known gaps" to two lines. | `1280-compare.png`, `-full.png`, `-hover.png` |
| 1600 | Single | Fits. The superseded value is the hero. The Extracted card is a 7-pair vertical stack (409px) next to a 294px Filing card. | `1600-single.png`, `-full.png`, `-hover.png` |
| 1280 | Single | Same as 1600; the crop (722×132) is legible. | `1280-single.png`, `-full.png` |
| both | Filing, cell given | Lands on the cited row, centred, with the cell boxed 3px red. The banner has no identity and no way back. The row tint is hidden under the filing's own cell colours. | `{1600,1280}-filing.png`, `-filing-scrolled.png` |
| both | Filing, not found | Red banner, but the page stays at the top. | `{1600,1280}-filing-notfound.png` |
| both | Filing, bare or bad accession | A bare accession shows no banner. An unknown accession shows raw JSON. | `1280-filing-bare.png`, `1600-filing-404.png` |
| both | Evidence errors | "no cited cell 'nope'" alone on a blank page. Compare with only one id shows URL syntax. | `1600-evidence-error.png` |
| 860 | Compare | Stacks correctly, but scrolls sideways and has two left edges (title x=8, cards x=32). | `860-compare-full.png` |

## Findings

| ID | Level | Element | Problem | Norm | Evidence | Sev | Verified |
|---|---|---|---|---|---|---|---|
| EV-01 | Group | Single · Extracted value | The superseded reading is the largest figure on the page. The used value (1,760) is only in the 12.8px Restated line. There is no Superseded mark next to the hero figure. | H2, C3 | 1600-single.png; `.ev-value` 25.6px vs restated 12.8px | P1 | measured |
| EV-02 | Component | Compare crops at 1280 | 590×108px with about 7px filing text; 260px empty below. | D1, D2 | 1280-compare.png; interact.json | P1 | measured |
| EV-03 | Page | Filing banner | No company, form, filed date, accession, Superseded/Used mark or link back. Tab title is "apld-20240531". | C3, I6 | 1600-filing.png; bannerLinks 0 | P1 | measured |
| EV-04 | Page | Filing, not-found state | Row and column were found, but the page stays at scrollY 0 instead of going to the cell. | I3 | 1280-filing-notfound.png | P1 | observed (synthetic cell value, same code path as a real mismatch) |
| EV-05 | Component | Status words | Orange is 2.91:1 and green 2.74:1, against a 4.5:1 minimum. | A1, C3 | computed from measured colours | P1 | measured |
| EV-06 | Layout | Header at ≤1024px | Page scrolls sideways: scrollWidth 1099 at 860, 1107 at 1024. | L6 | 860-compare-full.png; w860.py | P1 | measured |
| EV-07 | Component | `section.card` | The card has no `card-body`, so padding is 0. Text sits 1px from the border. | Tabler kit misuse, D4 | h2 x=33 vs card x=32 | P2 | measured |
| EV-08 | Layout | `.ev-wide` compare grid | Spills 124px past the page column at 1600 and 54px at 1280. | L4, H6 | geometry overflowSpills | P2 | measured |
| EV-09 | Layout | Above the page header | 74px dead band, on every evidence state including errors. | D2 | page-header y=150 vs scope line ≈76 | P2 | measured |
| EV-10 | Group | Compare status row | A says "Superseded"; B, the used reading, says nothing. | C3, H5 | 1600-compare.png | P2 | observed |
| EV-11 | Component | "Cell located" next to "Superseded" | A green success word sits on a superseded figure. The two words describe different things (the crop and the value) but share one row and one weight. | H4, C3 | single and compare shots | P2 | observed |
| EV-12 | Group | Extracted card | 7-pair vertical stack; card heights 409 vs 294. | D1, D5 | unevenRows [409, 294] | P2 | measured |
| EV-13 | Page | Single | 9,552 appears 4 times. Period appears twice. "6 rows not shown" and "6 rows folded" say the same thing. | C2 | 1600-single.png | P2 | observed |
| EV-14 | Page | Compare | No link to Company trail or to either single evidence page. | H5, I6 | links list | P2 | measured |
| EV-15 | Page | Dates | ISO dates in the Restated line, "Aug 30, 2024" in the card headers. | H5 | 1600-compare.png | P2 | observed |
| EV-16 | Component | Filing row highlight | The `tr` tint is covered by opaque `td` backgrounds (rgb 204,238,255). Only a 1px faint outline shows. | H4 | trBg vs cellBgs | P2 | measured |
| EV-17 | Page | Filing viewer | Once you scroll away, nothing takes you back to the cell. | I6 | pageScrollY 84816 | P2 | observed |
| EV-18 | Page | Bare `/filing/<acc>` | No banner, no identity, no way back. | C3 | 1280-filing-bare.png | P2 | observed |
| EV-19 | Page | Error states | Raw JSON on a 404, terse "no cited cell 'nope'", and URL syntax in the compare error. None offers a way out. | I3, C1 | 404 and error shots | P2 | measured |
| EV-20 | Layout | Nav at 1280 | "Known gaps" wraps; header grows from 56 to 64px. | L5 | wrappedControls | P2 | measured |
| EV-21 | Layout | 860 breakpoint | Title x=8, cards x=32. | L4 | interact.json 860 | P2 | measured |
| EV-22 | Component | "Open in filing" | btn-sm is 86×20, under the 24px minimum. The page's only action is its smallest control. | I4, H2 | smallTargets | P2 | measured |
| EV-23 | Component | Crop highlights | Blue column box, red cell box and green row tint with no legend. | H4 | 1600-single.png | P2 | observed |
| EV-24 | Component | Crop link plus button | Two tab stops to the same URL (four on compare). | I7, C2 | tab order | P3 | measured |
| EV-25 | Component | Column label | "May 31,2024" has no space, in the key-value list and in the banner. | C1 | single and filing shots | P3 | observed |
| EV-26 | Group | Single header | "Company trail" floats mid-header, aligned to no line. | H6 | 1600-single.png | P3 | observed |
| EV-27 | Page | Compare header | Row label shown twice. | C2 | 1600-compare.png | P3 | observed |
| EV-28 | Page | Value format | $9,552,000 on single vs $9.6M on compare. | H5 | single vs compare | P3 | observed |
| EV-29 | Layout | Compare at 1600 | Content ends at y=558 of 1000 while the crops are only 137px tall. | D2 | evgrid metrics | P3 | measured |
| EV-30 | Component | Filing banner type | 13px system font, not Inter. | H5 | viewer.py | P3 | observed |
| EV-31 | Page | Headings | Two h1s: a screen-reader-only one plus the visible page title. | A2 | interact.json | P3 | measured |
| EV-32 | Page | Spacing and type scale | Off-scale gaps of 6, 10 and 11px; 6 font sizes; "Signer" at 3.0:1 on the navbar. | D3, H3, A1 | audit.json | P3 | measured |

## Excellent as is
- The red box on the cited cell in a real crop of the stored filing.
- Compare crops share the same height and row position (both at y=358).
- Compare and single fit one screen at 1600 and 1280.
- The filing viewer centres the cited row and states what it found in words.
- The not-found banner says what the page shows against what was cited.
- Every tab stop shows a visible focus ring; filing links open in a new tab with `rel=noopener`.
- The Restated line states the deciding fact ("dataset uses 1,760") and links to Compare filings.
- The layout stacks cleanly under 900px.

The `-full.png` screenshots of the filing pages are about 22MB each, so I didn't open those four; the viewport shots cover them. The `evidence` → Proof nav highlight is deliberate in `_router.js` and isn't counted as a finding.

Files are in /Users/kennygeiler/ai-capex-ledger/docs/ux-visual/:
- pages/evidence/shots/
- pages/evidence/audit.json
- tmp/evidence/interact.json
- tmp/evidence/shots.py
- tmp/evidence/interact.py
- tmp/evidence/w860.py