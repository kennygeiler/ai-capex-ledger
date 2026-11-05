# STORY-014 — Full provenance audit of one company (APLD)

Evidence: live app `http://localhost:3610`, captured 2026-11-04 with headless Chromium at 1600×1000, read-only (0 non-GET requests logged across all three capture scripts). Screens in `STORY-014-screens/`. Scripts in `docs/ux-flow/tmp/s014*.py`.

Drift from the catalog text: the local copy is not the hosted read-only copy (no "· Read-only" in the scope line, `02-trail-top.png`); "Changes since release" reads "None" with no **Details** link (`02-trail-top.png`), so catalog step 4 cannot be taken; Statement figures "Unverified" rows show their reason inline ("Unverified · Definition differs from SEC XBRL", `07-calc-row.png`), so step 9's extra click is not needed.

## Friction Scorecard

| Measure | Value | Basis |
|---|---|---|
| Steps, catalog | 23 | STORY-014 Steps 1–23 |
| Steps, Ideal path | ~15 | catalog "Ideal path" |
| Steps, measured walk | 21 | steps 1–3, 5–8, 10–23; step 4 unavailable (no Details link), step 9 click unnecessary |
| Page height at load | 5,279 px | measured, `document.body.scrollHeight` |
| Page height with three tallies expanded | 24,181 px | measured after opening Statement figures, AI disclosures, Guidance and projects |
| Re-entry | 2 | Back from Compare filings lands at `scrollY 0` with tallies collapsed (measured, `13-after-back.png`); Reconcile round trip repeats it (catalog step 20) |
| Confirmations guarding nothing | 0 | none met on the read-only walk |
| Dead ends | 1 | Release card "Release gate · Done · No blocking items" (`11-release-card.png`) has no link to the packet or the Release page |
| Decisions a default could carry | 3 | which tallies to expand (all three are the same answer for an audit); which "Open" vs "sec.gov ↗" per row; Note figures open rows vs tally |

Hesitations (measured unless marked):

1. Counts disagree across screens for the same company. Trail header "17 to review" and summary "To review 17" (`02-trail-top.png`); Reconcile header "Needs review 9 · Proposed 8 · Unverified 2" (`14-reconcile.png`); Release page "APLD … G6 8 Fail" (`15-release.png` / `release.txt`) while the trail's Release card reads "Done · No blocking items" (`11-release-card.png`). An auditor reconciling step 23 meets three totals.
2. "Changes since release: None" on the trail (`02-trail-top.png`) vs Release page "Rows changed since v1.8.0 · 174" and "values.csv · 10 added" (`release.txt`). Suspected: the trail scopes to APLD and the Release page is all companies, but neither label says so.
3. Proof board legend has four keys ("Checked · Located/Done · Unverified · To review") over three-number cells such as "21 · 2 · 0" and "8 · 0 · 8" (`01-proof-board.png`); the trail legend has eight keys (`02-trail-top.png`). Which number is which is not stated on the cell.
4. AI disclosures tally opens to repeated identical rows "Revenue · FY2025 · Actual · — · — · Unverified · Part-year amount" (`09-ai-disclosures.png`), at least seven in a row with no value, no source and no distinguishing label. The catalog expects quotes in this card (step 17).
5. Statement figures lists "Opex · FY2026" and "Opex · FY2026 · Large year-over-year change" as two rows with the same value, formula and four sources (`statement.txt`). A check flag renders as a second figure.
6. "Citation only 7" in the trail summary (`02-trail-top.png`) vs "Citation only 174" for APLD in the Proof board's Verification source table (`01-proof-board.png`). Suspected: figures vs rows; the unit is not labelled.

## Take-away Pass

**Proof board (`01-proof-board.png`)**
- Removable: "Verification source" table repeats the trail summary per company with a different unit (hesitation 6). Collapse below the main table or drop.
- One primary action: no. Every company name is a link of equal weight with the orange "N to review" cell; acceptable for a hub.
- Stated more than once: "N to review" also appears on the trail header, trail summary, stage headers and Reconcile.

**Company trail, header and summary (`02-trail-top.png`)**
- Removable: the eight-key legend sits above the summary on two lines and is needed only when reading rows; move it to the first table header or hover.
- Removable: "To review 17" in the Verification block duplicates "17 to review" in the header, five lines above.
- Three links to Reconcile on one screen: header "Reconcile", summary "Review in Reconcile →", and per-card "Decide in Reconcile →". Keep one per context.
- One primary action: none dominant. For an audit, the primary path is reading down; acceptable.

**Filings card (`02-trail-top.png`)**
- Collapsible: five identical "Done · Statements located" rows with an empty Value column ("—"). Collapse to "5 filings · Statements located" with the rows behind a disclosure, like the other complete stages.
- Each row offers both "Open" and "sec.gov ↗"; the coverage line already links sec.gov. No simplification found for the pair, since one is the stored copy and one is the SEC copy, but the difference is not labelled.

**Statement figures (`07-calc-row.png`, `08-lightbox.png`)**
- Calculated rows show formula, arithmetic, "Filing's own total", SEC XBRL comparison, and one crop per input (up to four crops per row). Collapsible: the input crops behind the row; keep formula and the comparison line.
- Duplicate row for the check flag (hesitation 5): fold "Large year-over-year change" into the Opex FY2026 row as a status.

**Note figures (`04-trail-scroll-1.png`)**
- Open rows first, tally collapsed: matches the ideal. No simplification found for the restated rows; the two crops side by side carry the comparison already, so "Compare filings" adds a page that shows the same two crops larger (`12-compare.png`). Suspected removable: open the compare view inline instead of navigating away, which also removes the scroll-reset re-entry.
- Seven "Parts vs total" rows have Value "—" and a single source link; the gap amount sits in Verification. Move the gap to Value.

**AI disclosures (`09-ai-disclosures.png`)**
- Rows with no value and no source carry no evidence for an audit. Either show the quote and source or group them as one line "7 part-year amounts · Unverified".

**Category mapping (`04-trail-scroll-2.png`, `10-guidance.png`)**
- Each of 8 cards is roughly 480 px tall (estimated from the screenshot) with Company line, Proposed, full FASB definition, Company's own tag with definition, Basis, Alternatives, Affects. The same eight items appear on Reconcile as one row each (`14-reconcile.png`). For a reader on the trail, collapse each card to one row "Company line → Proposed · To confirm · Affects", definitions behind a disclosure. This is the single largest block on the page.
- "Decide in Reconcile →" repeated 8 times with the same target `#reconcile?scope=APLD&cause=asset_types` (`controls.txt`). One link at the card header is enough.

**Guidance and projects (`10-guidance.png`, `11-release-card.png`)**
- 109 quoted rows, no search or filter (catalog edge case, confirmed). Collapsed by default: correct. Missing a find box once open.

**Release card (`11-release-card.png`)**
- One row "Release gate · — · — · Done · No blocking items" in a full table with four column headers. Collapse into the summary's Last release block, and link it to the Release page.

**Reconcile (`14-reconcile.png`)**
- Outside the read path for this journey; the trail already shows everything Reconcile shows for the 8 mappings. No change proposed for this story.

## The Simpler Version

Fewest-steps journey (target 10):

1. Open `#proof/APLD` from the Proof board or the ticker box.
2. Read the summary: coverage, verification counts, last release, changes since release (scoped label "APLD changes since v1.8.0"), and one open-items total that equals Reconcile's.
3. Read Note figures open rows (9): restated rows show both crops; parts-vs-total rows show the gap in Value.
4. Open one restated row's comparison inline (no navigation, no scroll reset).
5. Read Category mapping as 8 one-line rows; expand one to see definitions.
6. Expand Statement figures; spot-check a calculated row and a capex crop (lightbox, Open in filing).
7. Expand AI disclosures; read quotes with sources, part-year rows grouped as one line.
8. Expand Guidance and projects; use a find box to sample.
9. Open a quote's source on sec.gov.
10. Record open items from the one total, which matches the Release page's per-company count.

Changes to get there:

1. One open-items number per company, computed once, shown in the trail header only, and equal on Reconcile and the Release page "Release checks by company" (fixes hesitation 1).
2. Label scope on "Changes since release" ("APLD · since v1.8.0") and link it to the Release page diff (hesitation 2).
3. Collapse Filings and Release cards to one line each when complete; Release links to the Release page.
4. Category mapping cards to one row each on the trail; definitions and alternatives behind a disclosure; one "Decide in Reconcile →" per card header.
5. Inline compare for restated rows, or keep scroll position and expanded tallies on Back (`13-after-back.png`).
6. Merge check-flag rows into their figure row (Opex FY2026).
7. Group or fill the AI disclosures rows that have no value and no source.
8. Find box on any stage over 12 rows.
9. Move the eight-key legend out of the header block.

## Clarity Issues

| Label | Where | Issue | Fix |
|---|---|---|---|
| "17 to review" / "Needs review 9 · Proposed 8" / "G6 8 Fail" | trail header, Reconcile, Release (`02`, `14`, `release.txt`) | one concept, three names and three numbers | one name ("Open items") and one number |
| "To confirm" vs "Proposed" | trail Category mapping cards vs trail legend and Reconcile (`04-trail-scroll-2.png`, `14-reconcile.png`) | same state named twice | use "Proposed" everywhere |
| "Checked · Located/Done · Unverified · To review" vs "Verified · Corroborated · Matches company tag · Done · Unverified · Proposed · Needs review · Blocks release" | Proof board vs trail legend (`01`, `02`) | two vocabularies for one status set; "Checked" exists only on the board | use the trail's names on the board |
| "Citation only 7" vs "CITATION ONLY 174" | trail vs Proof board Verification source | unit missing (figures vs rows, suspected) | add the unit to the column header |
| "Changes since release · None" | trail summary | scope unstated; Release page shows 174 changed rows | "APLD changes since v1.8.0" |
| "Open" vs "sec.gov ↗" | every source line | difference between stored copy and SEC copy not stated | "Stored filing" / "sec.gov ↗" |
| "G1 G4 G5 G6" | Release page per-company table (`release.txt`) | codes with no names | use the check names from the table above it |
| "Parts vs total" + Value "—" | Note figures (`04-trail-scroll-1.png`) | the measured gap sits in Verification, Value is empty | Value = gap amount |
| "Revenue · FY2025 · Actual" ×7 | AI disclosures (`09-ai-disclosures.png`) | identical labels, no way to tell rows apart | add source or quarter to the label |
| "Claude Fable 5.1 · 2026-11-01" under Basis | Category mapping cards | model name with no role label | "Proposed by Claude Fable 5.1 · 2026-11-01" |
| `BuildingAndBuildingImprovementsMember` monospace beside the human name | Category mapping cards, alternatives | tag shown twice per line (name + member id) | show the member id on hover or in the expanded detail |
| "Kenny's Data Emporium" | app title on every screen | not a product label; the browser title reads "Kenny's Data Emporium, Company trail APLD" | product name |

Rule checks: no gradients, italics or decorative pills seen. Bordered boxes: every stage is a bordered card and Category mapping nests labelled blocks inside each card (`04-trail-scroll-2.png`); acceptable for stages, heavy for the mapping cards. Wall of text: FASB and company-tag definitions printed in full on all 8 mapping cards, twice per card.

Verdict: convoluted. Steps measured 21 vs ideal ~15.
