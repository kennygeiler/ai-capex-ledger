# STORY-039 — Work down the 29 Proposed asset-type mappings

Evidence: local app http://localhost:3610, captured 2026-11-04 at 1600×1000, read-only (no non-GET request fired; checked in the capture script).
Screens: `STORY-039-screens/` — 01 Release, 02 Release with "Proposed" expanded, 03 `#reconcile?cause=asset_types`, 04 same scoped to AMD, 05 AMD with "Construction in progress" expanded, 06 grouped by company, 07 `#reconcile` unfiltered, 08 `#proof/AMD`. Script: `docs/ux-flow/tmp/story039.py`.

## Friction Scorecard

| Measure | Value | Basis |
|---|---|---|
| Ideal path | ~33 | catalog: open list once, 29 decisions, navigation |
| Actual, catalog path (scope per ticker, expand then Approve) | ~68 | 1 Release + 1 expand "Proposed" + 1 Fix in + 6 Scope changes + 29 expands + 29 Approve + 1 back to Release |
| Actual, shortest available path | 32 | Release → Fix in "Reconcile" → 29 row-level **Approve** → navbar Release. Measured: screen 03 and 05 show Approve/Reject/Choose another on every collapsed row, so neither expanding nor scoping is required |

The floor already meets the ideal. The extra ~35 steps in the catalog walk come from the screen not signalling that the row-level Approve is enough and that one unscoped page holds all 29.

Decisions a default could carry
- Scope per ticker (catalog steps 4, 8, 9): unnecessary. `#reconcile?cause=asset_types` (screen 03) already lists all 29 Proposed rows on one page, ordered by company. Measured.
- "Choose another" dropdown is prefilled with "Technology Equipment" on the AMD "Construction in progress" card (screen 05), unrelated to the proposal "Construction in Progress". A blank or nearest-alternative default would avoid a wrong pick on a fast Choose another. Measured (value shown); cause of the default not traced.

Re-entry / recall
- Release "Proposed" detail LINK column (screen 02) prints `reconcile?scope=AMD&cause=asset_types` as plain text, 29 times. Not clickable. Measured.
- The 409 "Changed since loaded. Reloading." path (catalog step 10) drops the reviewer's place. Suspected (not triggered; read-only walk).

Hesitations
- Screen 03 card header: "29 proposed · 0 unmapped · 6 differ from company tag · 18 match company tag". Below the 29 Proposed rows sit 18 rows marked "Matches company's own tag" with the same blue **Approve** button. Only the 29 count toward the Release "Proposed" line (screen 02 lists 29 keys, none of the 18). The page shows 47 Approve buttons for a 29-item job, with no line between them. Measured.
- Header "Unverified 6" next to the toggle "Show 6 settled" (screen 07): same number, two names; unclear whether they are the same 6. Suspected.
- Release header reads "10 of 13 required checks pass" (screen 01); catalog STORY-040 and the long story assume 15. Measured on screen; catalog is stale.

Confirmations guarding nothing: none found in this journey (Approve fires without a dialog, which fits an undoable-by-reconcile decision).

Dead ends
- Plain-text LINK column (above).
- After the last Approve, Reconcile shows no "Proposed 0 · Back to Release" cue; return is via navbar. Suspected (state not reachable read-only).

## Take-away Pass

Screen 01/02 — Release, "Proposed" expanded
- Removable: LINK column (29 identical non-links per ticker). Replace with one "Open in Reconcile" link per ticker, or make the KEY a link.
- Collapsible: the 29-row detail itself. The by-company table below ("Release checks by company", G6 column: MSFT 6, GOOGL 4, AMZN 4, NVDA 2, APLD 8, AMD 5) already says where the work is. The detail repeats each count line by line.
- Stated more than once: STATE "to confirm" on all 29 rows (column carries no information inside a line named Proposed); "proposed by Claude Fable 5.1" on all 29 REASON cells; the `asset_types|` prefix on every KEY.
- Primary action: "Sign v1.9.0" (disabled) is the only primary; correct.

Screen 03/04 — Reconcile, Category mapping
- Removable for mapping rows: DATASET, SEC XBRL, GAP, DIFFERENCE columns are "—" on every row (screens 03, 05).
- Deferrable: the 18 "Matches company's own tag" rows; they belong behind the settled toggle or in a second section after the 29.
- Stated more than once: company name and ticker stacked ("AMD / AMD", "Amazon / AMZN") in one cell; "Proposed" tag on all 29 rows of a card already headed "29 proposed".
- Primary action: three buttons per row × 47 rows; Approve is blue on every row. Per row there is one primary, which is right; per page the 18 extra blue buttons dilute it.

Screen 05 — expanded card
- Stated more than once: Approve / Choose another / Reject appear both in the row and in the card footer (two sets of the same three actions, 80 px apart).
- Removable: "Note wording — Note text unavailable" panel when there is no text; keep only the "Company trail" link.
- Kept: COMPANY LINE, PROPOSED definition, COMPANY'S OWN TAG, BASIS, AFFECTS: this is the evidence a decision needs.

Screen 08 — Proof AMD trail
- "Decide in Reconcile →" repeats per mapping item (4+ times). One link at the stage level would do. Accelerator of the canonical route, not a parallel implementation; acceptable.

## The Simpler Version

1. On Release, click "Reconcile" in the Fix in column of "Proposed" → `#reconcile?cause=asset_types` showing only the 29 Proposed rows.
2. For each row, read the inline proposal + basis; click **Approve** (or Choose another for the few disagreements). 29 decisions.
3. When the count reaches 0, click "Back to Release" in the card header → "Proposed Pass 0".

Total: 31 steps (1 + 29 + 1) against ideal ~33.

Changes to get there
- Release detail: make LINK a real link, or drop it and link each ticker in the G6 by-company table to `#reconcile?cause=asset_types&scope=<T>`.
- Reconcile Category mapping: split the card into "Proposed 29" (shown) and "Match company tag 18" (behind the settled toggle, or listed after under its own header with no blue button).
- Hide DATASET / SEC XBRL / GAP / DIFFERENCE columns when the card is Category mapping.
- Keep one action set per row: drop the row buttons when the card is expanded, or drop the card footer buttons.
- Leave the "Choose another" select empty until opened.
- After the last Proposed decision, replace the card body with "Proposed 0 · Release" link.
- On a 409 reload, restore scroll and focus to the row that was acted on.

## Clarity Issues

- One concept, three names: Release line "Proposed" + STATE "to confirm" (screen 02); Reconcile row tag "Proposed" (screen 03); expanded card status "To confirm" (screen 05). Pick one (Proposed).
- "Category mapping" (Reconcile cause filter, card title, Proof stage) vs `asset_types` (Release KEY, URL `cause=asset_types`) vs G6 (gate column header). Show "Category mapping" in Release keys and column headers; keep G6 out of the UI or label it.
- Release "Proposed" Details note (screen 02): "No decision left by a run for a person to confirm (decisions/resolutions.jsonl, 'to confirm'), and no asset-type mapping without a person's confirmed_by (taxonomy/asset_types.yaml, T63)". File paths, field names and rule IDs in a product label; long sentence. Suggested: "Run decisions and category mappings awaiting confirmation".
- "Matches company's own tag" (row) vs "match company tag" (card header) vs "Matches company tag" (Proof legend, screen 08): three spellings.
- Member names shown as both words and code: "Construction in Progress" + `ConstructionInProgressMember` (screen 05) and `BuildingAndBuildingImprovementsMember proposed by Claude Fable 5.1` (screen 02). Release detail should use the words form used in Reconcile.
- BASIS quotes like "the note's own category name" (screens 03, 05) assume knowledge of what "the note" is; label "Source: 10-K PP&E note category" would be clearer. Suspected.
- "Not tagged" under the proposal (screen 03) vs "COMPANY'S OWN TAG — Not tagged" (screen 05): the row form lacks the field name.
- Design-rule check: orange "Proposed" text tag on each of 29 rows under a header that already says "29 proposed" is a decorative status repeat; the 1.5px blue left bar on the focused row is fine. No italics, gradients or dividers seen.
