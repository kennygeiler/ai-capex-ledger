# UX Flow Critique — 2026-11-04

App: Kenny's Data Emporium (Capex Ledger), local copy http://localhost:3610, data as of Nov 1, 2026. Sources: `journeys/STORY-*.md` (8), `redundancy.md`, screens in `journeys/STORY-*-screens/` and `redundancy-screens/`. Story numbers refer to `docs/ux-paths/catalog.md`.

## Run Summary

| Item | Value |
|---|---|
| Journeys critiqued | 8: STORY-006, 014, 027, 039, 045, 055, 064, 068 |
| Evidence source | Live pass, headless Chrome 1600×1000, GET only. Steps after a write (save, verdict, sign) come from code or the catalog and are marked suspected. |
| Owner mode only | Local copy runs in owner mode. Read-only refusals (064) are cited from the catalog, not reproduced. |
| Verdicts | Convoluted 7 · Acceptable 1 (039) · Minimal 0 |
| Redundancy findings | 28: Duplicate paths 7 · Duplicate information 9 · Overlapping features 5 · Hierarchy & IA 7 · 6 passed, 1 moved (O7 → HI3) |
| Catalog drift | Release "10 of 13 required checks" (catalog: 12 of 15); rows with no value 118 (catalog: 125); STORY-014 step 4 "Details" link absent |

## Friction Scorecard

| Journey | Steps actual/ideal | Needless decisions | Re-entry | Dead ends | Verdict |
|---|---|---|---|---|---|
| 045 Pre-release pass to published | ~55 / ~45 | 1 (18 tag-matching mappings approved one by one) | 3 round trips to Release; Proof for Download | 2 (Fix in → Release self-links; post-publish redirect, no Download) | Convoluted |
| 006 Golden test → hand check → back | 10 / 6 (5 proposed) | 2 (company, item) | Context: "APLD, 1 item" not on Release | 2 ("No items" under Count 1; Fail, no in-app refresh) | Convoluted |
| 027 Clear Rule findings | 16 steps / ~38 inputs vs ~12 (7 proposed) | 3 (Field filter per batch, prefillable reason, Industry after scope) | 1 (unscoped Reconcile; unlinked ticker counts) | 2 (Fix leaves item open, Release stays Fail; unlinked counts) | Convoluted |
| 039 29 Proposed mappings | 32 shortest, ~68 catalog / ~33 | 1 ("Choose another" prefilled wrong) | 1 (LINK column is plain text, 29×) | 2 (plain-text LINK; no "Proposed 0 · Release" cue, suspected) | Acceptable |
| 014 Provenance audit, one company | 21 / ~15 (10 proposed) | 3 (which tallies, Open vs sec.gov, rows vs tally) | 2 (Back resets scroll + tallies) | 1 (trail Release card, no link) | Convoluted |
| 055 Dataset vs release audit | 18 / 8 (6 proposed) | 1 per list (which column holds the verdict) | 2 (Find clears; Grid filters dropped) | 2 ("0 rows of 81", no route; ai_spend.csv has no list) | Convoluted |
| 064 Buyer evaluates dataset | 22 / 8 (6 proposed) | 2 (which trust page; which of 6 packets) | 2 (Release ×2, Proof ×2) | 2 (Fix in → owner queues; refusals after click, suspected) | Convoluted |
| 068 Handoff + links | 18 / 6 (5 proposed) | 1 (start point: Handoff last, `#docs` → How it works) | 1 (Back from Map → top of 5,984 px page) | 2 (6 `docs/*.md` refs as text, README 404; docs promise Edit button) | Convoluted |

Confirmations guarding nothing: none. Sign's single confirmation guards an irreversible publish.

## Redundancy Map

| ID | Redundancy | Recommendation |
|---|---|---|
| DP1 | Five routes to one figure's provenance; `#evidence/<id>` is unlinked | Make `#evidence/<id>` the canonical view; every crop links to it |
| DP2 | Three CSV export shapes (Rows server, Grid client, Explore lossy) | One export of the on-screen filtered rows with the same columns; the packet stays |
| DP3 | Jump box lands on Dataset | Jump box → `#proof/<T>` |
| DP4 | Trail → Reconcile: header link + "Review in Reconcile →" 60 px apart | Remove the header link; "6 to review" becomes the link; keep per-item links |
| DP5 | Two entry points to the encode panel | Keep both, one visible at a time (not captured) |
| DP6 | Three ways to confirm a proposed mapping | Approve is the canonical confirm; Choose another excludes the proposal |
| DP7 | Save as view (403) vs URL | Hide Save as view until it works; add "Copy link" |
| DI1 | Open-item count on 7 surfaces; G6 disagrees (GOOGL 4 vs 11) | Reconcile is the canonical count; rename or drop G6 |
| DI2 | Hand check: CLI snapshot vs live section | Live is canonical; snapshots read "as of last CLI run" |
| DI3 | Claims register: 3 breakdowns, 2 vocabularies, Docs counts differ | Known gaps is canonical; Release uses its words; Docs embeds the live table or dates its snapshot |
| DI4 | Rules on the Rules page and in Docs, unlinked | Rules page is canonical; Docs links each rule id |
| DI5 | Mapping card on both trail and Reconcile | Keep both; trail copy becomes one line |
| DI6 | Verification counts twice on Proof, once on the trail | Keep the trail tile; fold Proof's "Verification source" |
| DI7 | Release info lines repeat their own cards | Remove; each line links to its card |
| DI8 | Saved decision shown 3× | Keep badge + card header; row cell shows the word only |
| DI9 | State words defined in 4 places | Glossary is canonical; legends stay |
| OF1 | Five readers of a company's figures | Differentiate by job; Explore "Show rows" opens Dataset |
| OF2 | Hand check and trail show the same crops, unlinked | Merge a verdict chip onto the trail row; link both ways |
| OF3 | Rules "To review · 45" duplicates Reconcile with stale instructions | Remove; replace with one link |
| OF4 | "Fix in" lands at page tops; links to Release from Release | Open the filtered target; drop self-links |
| OF5 | Accept vs Explain do the same thing | Merge into one action with a reason type |
| HI1 | "Rules" page leads with Agents | Rename or split |
| HI2 | Category mapping has 4 names | One noun, one state word, one action set |
| HI3 | Same filter, different words | Display labels in tables; rename Explore controls |
| HI4 | Proof carries 4 jobs; Hand check last | Failure types → Rules, Releases → Release |
| HI5 | Download on Proof, packet contents on Release | Downloads move to Release |
| HI6 | Two primary-looking trail links | Covered by DP4 |
| HI7 | Known gaps vs Docs → Known limitations | Drop Known limitations |

Passed: P7, P9, I7, I8, I12, I13.

## Simplification Proposals

Ranked by journeys improved × steps or elements removed ÷ effort, weighted toward the owner loop: review → grade → decide → sign (045, 006, 027, 039, 014).

1. **Fix-in links carry the exact scope.**
   - Now: Golden test → `#proof` top; Needs review → bare `#reconcile`; Release detail prints `reconcile?scope=…` as text 29×; Fix in on passing rows and links back to Release.
   - Proposed: `#gold?ticker=<first unchecked>` scrolled to the item; Needs review → rule findings, open only; ticker links; Fix in on failing rows only.
   - Saves: 2–3 steps per failing check and 3 round trips in 045.
   - Journeys: 006, 027, 039, 045, 064.
   - Effort: S (`ledger/release/checklist.py:331`).
   - Evidence: 006 steps 3–6; 027 re-entry; 039 screen 02; 045 controls; OF4.
2. **Release shows only what blocks signing.**
   - Now: failing rows at positions 4/5/14 of 16; G-code card; Details full of file paths, truncated; count stated twice; info lines repeat cards.
   - Proposed: Fail → Info → Pass order with passing rows collapsed; drop the G card or replace it with all three failing counts per company; product labels; one count; info lines link to cards.
   - Saves: ~15 rows and one card off the first screen.
   - Journeys: 006, 027, 039, 045, 064.
   - Effort: S.
   - Evidence: 045, 027, 064 Release; DI7.
3. **Golden test reads live hand-check state.**
   - Now: the Release line reads `reports/golden.json` until a CLI rerun; the note says "give the verdicts on Proof"; "golden ok" Pass sits next to Golden test Fail; "No items" under Count 1.
   - Proposed: split into Hand check (live) and Regression test (snapshot); list unchecked items; show a "Stale · rerun" note meanwhile.
   - Saves: 2 steps and a terminal trip per verdict.
   - Journeys: 006, 045.
   - Effort: M (check against HANDOFF signing invariants).
   - Evidence: 006 steps 8–10, `cli/golden.py:57`; DI2.
4. **One open-items number per company.**
   - Now: GOOGL 7/11/7/4 and APLD 9/17/9/8 across Reconcile, Proof, Release detail and Release by company; trail says "No blocking items" while Release says Fail.
   - Proposed: one definition, "11 open (7 review · 4 proposed)", linked; Reconcile header shows the release's failing counts and drops or explains "Unverified 6".
   - Journeys: 014, 027, 039, 045, 064.
   - Effort: M.
   - Evidence: 027 count drift; 014 hesitation 1; DI1.
5. **Category mapping: approve the obvious at once.**
   - Now: 47 blue Approve buttons for a 29-item job; 4 empty columns; two action sets when a row is expanded; wrong "Choose another" default.
   - Proposed: split Proposed 29 from Matches company tag 18 with "Approve all matching"; hide empty columns; one action set per row; empty default; "Proposed 0 · Release" when done.
   - Saves: up to 17 clicks; ~87 → ~33 buttons.
   - Journeys: 039, 045.
   - Effort: M.
   - Evidence: 039 screens 03–05; DP6.
6. **Rule findings: group, show numbers, deliberate Save.**
   - Now: ~9 inputs per batch; gap only in expanded prose; two Save buttons; Accept preselected; Fix silently leaves the item open.
   - Proposed: group by company + field + check; fill the gap columns; hide the row panel during a selection; no preselected decision; prefill the "Readings differ" reason; Fix states its consequence; "N left · Release" link after each save.
   - Saves: ~38 → ~15 inputs.
   - Journeys: 027, 045.
   - Effort: M.
   - Evidence: 027 screens 07–11.
7. **Hand check puts the open item first.**
   - Now: unchecked item is 7th–8th of 20; 60 live buttons; CI lines above the picker.
   - Proposed: unchecked companies and items first; decided items collapse; CI lines deferred.
   - Saves: 2 decisions and a scan.
   - Journeys: 006, 045.
   - Effort: S.
8. **Packet download lives on Release.**
   - Now: after Sign, redirect to Proof with no Download; six equal Download links on Proof.
   - Proposed: stay on Release with "Download v1.9.0"; Releases table on Release; one "latest signed" primary; file names link to Dataset lists.
   - Saves: 1–2 page visits.
   - Journeys: 045, 055, 064.
   - Effort: S.
   - Evidence: `release.js:43-44`; HI5.
9. **One vocabulary.**
   - Category mapping/Proposed/Approve·Reject·Choose another; "Hand check"; Known gaps words everywhere ("Holds 6", not "proven 6"); Glossary state set on Proof and trail; display labels instead of snake_case.
   - Removes hesitations, not steps.
   - Journeys: 7 of 8.
   - Effort: M.
   - Evidence: HI2, HI3, DI3, DI9.
10. **Company trail condensed.**
    - Now: 8 mapping cards ~480 px each; "Decide in Reconcile →" 8×; identical Filings rows; check flags shown as duplicate figures; 7 identical AI-disclosure rows; Back resets.
    - Proposed: one-row mapping cards; one link per stage; complete stages collapse; flags fold into their row; group empty rows; inline compare or keep scroll on Back.
    - Saves: 21 → 10 steps.
    - Journeys: 014, 064.
    - Effort: M.
11. **Proof does one job.** Stage table + to-review + Hand check progress; Failure types → Rules; Releases → Release; drop the repeated Regression test line.
    - Saves: ~4 screens of scroll.
    - Journeys: 006, 045, 064.
    - Effort: M.
    - Evidence: HI4, DI2, DI6.
12. **Docs start at Start here and stay true.** Start here first in the sidebar and the default route; reading order; `docs/*.md` references become links; docs match UI labels (Category mapping, Choose another); scroll restore on Back; drop Known limitations.
    - Saves: 18 → 5 steps.
    - Journeys: 068, 064.
    - Effort: S.
13. **Dataset: one Verification filter, persistent filters, one export.** Verification control bound to `check`; one verdict vocabulary; filters kept across switches; Grid export uses the server endpoint; add an AI spend list; an empty result names the list that matches.
    - Saves: 18 → 6 steps.
    - Journeys: 055.
    - Effort: M.
14. **Read-only copy hides owner controls.** Hide write controls and Signer; show hosted-copy staleness in the scope line.
    - Saves: 3 failed actions.
    - Journeys: 064.
    - Effort: M.
    - Suspected; needs a read-only capture.

## Already Minimal

- Sign v1.9.0: the single primary on Release, disabled with a clear reason, with one justified confirmation (006, 045).
- Row-level Approve: no dialog, and the shortest path (32 steps) already meets the ideal (039).
- Hand check: the unchecked item's unfilled buttons are the only controls left to act on (006).
- Note figures: open rows first, both restated crops side by side (014).
- Reconcile restatement line "dataset uses 1,760": the deciding fact sits above the details (027).
- Grid: Export CSV is the single primary; the drawer has one action (055).
- Release ↔ Dataset counts agree for all six lists (055).
- Rules agent Score and Known gaps give the strongest trust evidence (064).
- Docs Map links; diagram + step table (P9); Restated line (I7); three handoff audiences (I13).
