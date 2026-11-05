# STORY-006: From a failing Release line to a finished hand check and back

Verdict: **convoluted** · Steps: **10 actual / 6 ideal** (measured to step 7; steps 8–10 from code, not walked: the walk was read-only)

Evidence: live app on http://localhost:3610, 2026-11-04, headless Chrome 1600x1000. Screens in `STORY-006-screens/`.
Code read: `ledger/release/checklist.py:315-331` (`golden_line`), `ledger/cli/golden.py:57`.

## Friction Scorecard

| # | Step (walked) | Screen | Ideal? | Note |
|---|---|---|---|---|
| 1 | Navbar Release | 01-release.png | yes | "Golden test · Fail · 1 · Required", note truncated at "give the verdicts on Proof; 2…" |
| 2 | Expand "Golden test" row | 02-golden-expanded.png | no | Body is "No items". Dead end: the one item is not named. Measured |
| 3 | Fix in "Proof" | 03-proof-landing.png | yes | Href `#proof`, lands at scrollY 0 on the stage table. Hand check is ~4 screens down. Measured |
| 4 | Header link "Hand check: 119 of 120 checked" | 04-gold-section.png | no | Scrolls to `#gold`. Extra step because step 3 does not use the `#gold` anchor. Measured |
| 5 | Picker "APLD 19/20" | 05-apld-items.png | yes | Six equal-weight buttons; the one with an open item is not marked beyond "19/20". Measured |
| 6 | Scroll to the Unchecked item | 05b-gold-card.png, 06-apld-unchecked-item.png | no | "Opex · FY2026" is item 7 of 20, under "Definition differs". No jump to the unchecked item. Measured |
| 7 | Grade Right / Wrong / Can't say | 06-apld-unchecked-item.png | yes | Not clicked (read-only walk) |
| 8 | Navbar Release | — | yes | Line still Fail: it reads `reports/golden.json`, rewritten only by `ledger golden --check` / `ledger test` (checklist.py:38, 315). From code, not walked |
| 9 | Terminal: `ledger golden --check` | — | no | No UI path. The Release note "give the verdicts on Proof" stays as written after the verdict is given. Suspected confusion, code-confirmed cause |
| 10 | Reload Release | — | no | Only now can the line turn Pass |

- Steps: 10 actual vs 6 ideal. Extra: 2 (dead-end expand), 4 (missed anchor), 6 (manual scan), 9–10 (CLI rerun outside the app).
- Decisions a default could carry: which company (step 5) and which item (step 6). Release already knows `unverified` = 1 and the gold file knows which item; the link could carry both.
- Re-entry: none of data. Context re-entry: the user must remember "APLD, one item" is not stated anywhere on Release; it is recovered by scanning the picker.
- Confirmations guarding nothing: none found.
- Dead ends: step 2 ("No items" with a non-zero Count of 1); step 8 (Fail with no in-app way to refresh).
- Hesitations: step 2 (which item?), step 8 (verdict given, line unchanged), and the "Test run" line on the same screen reads "golden ok" Pass while "Golden test" reads Fail (01-release.png). `cli/golden.py:57` exits 0 when gold is only unverified, so both lines are true by their own rules and contradict each other on screen. Measured.

## Take-away Pass

Release (`#release`, 01/02)
- Primary action: "Sign v1.9.0", disabled, with "3 required checks failing" under it. Exactly one primary. Fine.
- Removable: the expanded detail body "No items" for this line. When detail is empty, the row should not expand at all, or the expand should list the unverified item(s).
- Collapsible: Details column truncates every note at ~26rem; the one actionable clause ("give the verdicts on Proof") is the part that survives, the date is cut. Drop the ISO timestamp from the note (it repeats the "Test run" timestamp) so the note fits.
- Stated more than once: gold state appears in "Golden test" (Fail) and "Test run" ("golden ok") with opposite tone.
- Top whitespace: ~80px blank band between the scope line and the "Release" heading (01-release.png). Removable.

Proof landing (`#proof`, 03)
- Nothing on the first screen serves this journey except the orange header link "Hand check: 119 of 120 checked". The stage table, legend, Verification source, Failure types and Releases all sit between landing and the hand check (04). Not removable from Proof, but the Fix in link should skip them.

Hand check (`#gold`, 04/05/06)
- Gold state stated four times on one page: header link "Hand check: 119 of 120 checked", "Regression test … Hand check: 119 of 120 checked", "All: 119 right · … · 1 unchecked", picker "APLD 19/20" (04-gold-section.png). Plus a fifth in the APLD card head "19 right · 0 wrong · 0 can't say · 1 unchecked". Keep the picker and the All line; the Regression test summary can drop its hand-check clause (it links to the same section).
- Per-group error lines with 95% CI ("error rate 0.0% (95% CI 0.0–39.0%)") are shown before any item; useful for audit, not for finishing one verdict. Deferrable behind the All line.
- One primary action per item: graded items show "Right" filled blue, the unchecked item shows all three outlined (06). Correct: the only unfilled control on screen is the one to act on. But with 20 items × 3 buttons + a note box each, 60 buttons compete; graded rows could collapse to their status line.
- Units shown twice per row: "9,320 / In thousands · $9,320,000" (05b). One form is enough.

## The Simpler Version

1. Release → "Golden test" Fail, note "gold: 1 of 120 unchecked · APLD".
2. Fix in "Proof" → `#gold?ticker=APLD`, scrolled to the first Unchecked item.
3. Grade it (Right / Wrong / Can't say).
4. Return to Release (link under the hand check: "Back to Release").
5. Golden test reads live gold state → Pass (or a "Rerun golden test" control replaces the CLI step).

5 steps, one fewer than the catalog's Ideal path, because the Ideal path still counts a separate "pick APLD".

Concrete changes:
- `golden_line` fix target: `"proof"` → `"proof/gold"` route or `#gold` anchor, with the first unverified ticker (checklist.py:331). Removes steps 3–4 and 5.
- Golden test detail: emit one detail row per unverified item (ticker, field, year) instead of an empty list. Removes the "No items" dead end.
- Split the line: tables equal/differ stays snapshot-based (needs the CLI run); the gold verdict half reads `gold/*.json` live, the same source the Hand check uses. Removes steps 9–10 for the verdict-only case. Suspected safe: gold verdicts are already live on Proof; needs a code check against the signing invariants in docs/HANDOFF.md.
- Until that split lands: when gold files are newer than `reports/golden.json`, the line note reads "Stale · rerun `ledger golden --check`" instead of "give the verdicts on Proof".
- "Test run" note: replace "golden ok" with "golden exit 0" or drop the gold clause, so it stops contradicting "Golden test".
- In the picker, mark companies with unchecked items (e.g. order them first); in the APLD card, put Unchecked items first.

## Clarity Issues

- One concept, four names: "Golden test" (Release), "gold" (Release note), "Hand check" (Proof header, section title), "Regression test" (Proof collapsible), plus "verdicts" (Release note) vs "Right/Wrong/Can't say" (buttons). Glossary separates Golden test (table rebuild) from Gold set (verdicts), but the Release line merges both under "Golden test". Proposed: Release line splits into "Regression test" (tables) and "Hand check" (verdicts), matching Proof.
- Same count, three framings: "gold unverified 1 of 120" (Release), "119 of 120 checked" (Proof header), "1 unchecked" (All line). Pick "unchecked" everywhere: "Hand check: 1 of 120 unchecked".
- "give the verdicts on Proof" is a conversational instruction inside a status note; the app rule is labels/values/statuses. Replace with "1 unchecked · APLD".
- "Count 1" plus "No items" on the same row reads as an error.
- Note column carries a raw ISO timestamp "2026-11-03T21:12:16+00:00" while the rest of the app shows "Nov 3, 4:12 PM".
- Picker buttons render as boxed segments with borders on each (04): reads close to the banned tag/pill pattern; a plain list with counts would do.
- "Definition differs" group label (06) is the reason this item is open, but on Release nothing connects "Golden test" to "Definition differs". Suspected the item stayed unchecked because it is the hard one; the fix link landing on it addresses that.

No simplification found for: confirmation dialogs (none exist on this path), and the Sign button's disabled state copy ("3 required checks failing" is clear).
