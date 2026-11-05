Counts: **18 findings**. By severity: P0 1, P1 4, P2 8, P3 5. By level: component 10, page 4, layout 4.

**`findings.md` was not written.** The Write tool blocked it ("Subagents should return findings as text"), so the full content is below for the caller to save. The shots and `audit.json` are on disk.

**5 worst:**
1. **P0, DV1, Handoff code blocks:** in the light scheme the text is the same colour as the background, so the Setup and five-minute-tour commands can't be seen (contrast ratio 1, measured). Tabler's `pre` text colour stays while `.raw` changes the background.
2. **P1, DV2, docs sidebar:** `position: sticky` has no effect because its wrapper div is only as tall as the sidebar. On a 6,000 px doc the sidebar scrolls away (measured top −3866).
3. **P1, DV3, long docs:** Handoff, Operating guide and Glossary have no section index, and their headings have no ids, so no section can be linked or jumped to (13 sections and 5,984 px on Handoff).
4. **P1, DV4, Glossary State words table:** 68 rows with no grouping. The same word appears 2–4 times (Unverified ×4, Corroborated ×4, Verified ×3), and the machine name repeats on every row.
5. **P1, DV5, docs at 390 px:** the page scrolls sideways (scrollWidth 505). The nav doesn't wrap and the article runs out to 425 px.

---

# Docs — visual critique — 2026-11-04

Surface: `#docs/<slug>` (http://localhost:3610). States: How it works (overview), Operating guide, Glossary, Handoff (long doc). Viewports 1600×1000 and 1280×800, plus spot checks at 390×844 and in dark mode. GET only (non-GET requests aborted). Decisions in `docs/ux-flow/report.md` (item 12, DI3, DI4, DI9, HI7) are taken as given.

Evidence is in `/Users/kennygeiler/ai-capex-ledger/docs/ux-visual/pages/docs/`:
- `shots/{viewport}-{state}.png` and `-full.png`.
- Extra shots: `1600-handoff-codeblocks.png`, `1600-handoff-scrolled.png`, `1600-overview-focus-12.png`, `1600-overview-dark.png`, `390-overview.png`, `390-handoff.png`.
- `audit.json`: layout-audit, geometry-audit and a docs probe, keyed by viewport/state.
- `interact.json`: focus order, sticky sidebar, scroll after Back, narrow overflow.
- Scripts: `/Users/kennygeiler/ai-capex-ledger/docs/ux-visual/tmp/docs/`.

## Verdicts

**1600 · How it works.** The strongest of the four pages. It has a clear H1, a six-box flow, a step table with page and package per step, and a short "where to go next" list. It runs to 1.7 screens (docH 1707). Where it falls short:
- The diagram is 960 px wide in a 992 px column.
- Sub-labels are 10.9 px.
- The boxes are links but show no link cue.
- Lines run 112 ch.

Shots: `1600-overview.png`, `-full.png`, `1600-overview-focus-12.png`.

**1280 · How it works.** Same layout in an 880 px column, 100 ch lines. The global nav wraps "Known gaps" onto two lines and the header grows to 64 px. Shot: `1280-overview.png`.

**1600 · Operating guide.** Sound structure, 2,920 px tall. The "When a Release line is red" table is the best component on the surface. Where it falls short: 63 inline code chips in 1,243 words, a 112 ch line length, and a sidebar that scrolls away. Shots: `1600-operations.png`, `-full.png`.

**1280 · Operating guide.** 3,130 px tall, same issues. Shot: `1280-operations-full.png`.

**1600 · Glossary.** A State words table of 68 rows and a Terms table of 49 rows, 5,813 px in all. Where it falls short:
- Words repeat across machines with no grouping.
- "row (M1)" repeats 14 times.
- 14 code values break mid-word ("corroborate|d").
- There is no in-page navigation.

Shots: `1600-glossary.png`, `-full.png`.

**1280 · Glossary.** 6,291 px, same issues. Shot: `1280-glossary-full.png`.

**1600 · Handoff.** Broken. Both code blocks show as empty bands (169 and 300 px; contrast 1.0). Beyond that:
- 3,350 words and 253 inline code chips.
- No section index, and headings have no ids.
- The sidebar scrolls away.
- The H1 says "Start here" but the sidebar says "Handoff".

Shots: `1600-handoff.png`, `-full.png`, `-codeblocks.png`, `-scrolled.png`.

**1280 · Handoff.** 6,470 px. The blank bands are 183 and 315 px, the second one 26% of the viewport. Shot: `1280-handoff-full.png`.

**Spot checks.**
- Dark mode: code blocks are readable, so the P0 affects light mode only (`1600-overview-dark.png`).
- 390 px: the page scrolls sideways by 115 px. The flow diagram stacks correctly (`390-overview.png`, `390-handoff.png`).

## Findings

| id | level | element | problem | norm | evidence | sev | verified |
|---|---|---|---|---|---|---|---|
| DV1 | component | `.md pre.raw` | Light mode: text colour = background colour, so the commands can't be seen | A1, I8 | `1600-handoff-codeblocks.png`; lowContrast ratio 1 ×2; deadSpace 169 + 300 px, fill 0%; pre colour and background both rgb(249,250,251) | P0 | measured |
| DV2 | layout | `.docs .viewlist` | Sticky has no effect because the wrapper is only as tall as the nav; the sidebar scrolls away | L7, I6 | interact `handoffScrolledSide.top` −3866; `1600-handoff-scrolled.png` | P1 | measured |
| DV3 | page | Handoff, Operating guide, Glossary | No section index; headings have no id | I6, P1 | 13 headings, all ids empty; docH 5,984 / 6,470 | P1 | measured |
| DV4 | component | Glossary State words table | Words repeat (Unverified ×4, Corroborated ×4, Verified ×3) in an ungrouped 68-row list; machine name repeats per row | D5, C1 | probe `dups`; `1600-glossary-full.png` | P1 | measured |
| DV5 | layout | Docs ≤ 700 px | Sideways scroll: nav set to nowrap, article runs to 425 px | L6 | scrollWidth 505 at 390 px; `390-overview.png` | P1 | measured |
| DV6 | component | Code values in tables | Break mid-word (`overflow-wrap: anywhere`) | H6, C4 | 14 wrapped values; `1600-glossary.png` | P2 | measured |
| DV7 | page | `.md` prose | Lines 112 / 100 ch at 14 px | D1 | measureCh 112 / 100 | P2 | measured |
| DV8 | page | Inline code chips | 253 chips in Handoff, 63 in Operating guide; paragraphs read as rows of tags | Owner rule (no tags/pills), H2 | codes 253 / 63; chip bg #f3f4f6, radius 6 px | P2 | measured |
| DV9 | component | Handoff H1 vs sidebar | "Start here" vs "Handoff" | H5, C1 | `1600-handoff.png` | P2 | observed |
| DV10 | component | Flow diagram | 960 px wide in a 992 px column; right edge 32 px short of the table | L4, H6 | flow.rect.w 960 vs article.w 992 | P2 | measured |
| DV11 | component | Flow sub-labels | 10.9 px grey text | H3, A1 | subFsPx 10.93 | P2 | measured |
| DV12 | component | Flow boxes as links | No link cue; repeats the PAGE column links | I1, C2 | focus order rows 10–15; `1600-overview-focus-12.png` | P2 | observed |
| DV13 | layout | Global header at 1280 | "Known gaps" wraps; bar grows to 64 px | L6 | wrappedControls 8; `1280-overview.png` | P2 | measured |
| DV14 | page | Page top | 58 px gap between the "6 companies · Data as of" line and the H1 | D2, D4 | y 68 → 126 | P3 | measured |
| DV15 | component | "PACKAGE (MAP)" header link | 27×14 px target | I4, I1 | smallTargets | P3 | measured |
| DV16 | layout | Spacing | Off-scale 6/10/11 px; near-duplicates 10/11, 11/12 | D3 | spacing.offScale | P3 | measured |
| DV17 | component | Sidebar focus ring | 1 px outline, vs 5 px on flow boxes | I7, H5 | sideFocus outline auto 1px | P3 | measured |
| DV18 | component | Header "Signer" label | Contrast 1.43 | A1 | lowContrast | P3 | measured |

## Excellent as is

- **"When a Release line is red" table:** line / meaning / what to do.
- **How it works step table:** step / what happens / page / package.
- **Sidebar active state:** one tinted row with `aria-current`, no badges.
- **Flow diagram at narrow widths:** stacks vertically below 700 px.
- **Dark mode:** tokens carry through tables, diagram and code.
- **Type scale:** 5–6 sizes, headings step 20 → 16.8 → 15.2 px.
- **Tab order:** follows reading order.
- **Source / "Written from code on every request" footer:** provenance in one line.