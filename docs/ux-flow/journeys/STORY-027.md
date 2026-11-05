# STORY-027: Clear the whole Rule findings queue before signing v1.9.0

Verdict: **convoluted**. Steps: 16 story steps (about 38 inputs) actual vs ~12 ideal (6 in the merged release-sign variant). The journey also ends short of its goal: one "Fix" decision leaves "Needs review" at 1 and Sign stays disabled.

Evidence: live app at http://localhost:3610, captured 2026-11-04 headless, 1600x1000, POST blocked at the network layer. Screens in `STORY-027-screens/`. Nothing was saved. Steps after a Save (page reload, filter fall-back, the Fix row staying open) come from the catalog text and are marked **suspected**.

| Screen | Route |
|---|---|
| 01-release, 01b-release-needs-review | `#release`, "Needs review" row expanded |
| 02-reconcile | `#reconcile` |
| 03-reconcile-googl, 04-reconcile-apld | `#reconcile?scope=GOOGL`, `?scope=APLD` |
| 07-googl-segrev, 08-googl-row-open, 09-googl-selected | `?scope=GOOGL&field=segment_revenue`, first row open, Select all 6 |
| 10-apld-ppe-open | `?scope=APLD&field=ppe_category`, FY2024 open |
| 11-googl-ppe-open | `?scope=GOOGL&field=ppe_category`, FY2023 open |
| 05-proof, 06-proof-apld | `#proof`, `#proof/APLD` |

## Friction Scorecard

| Measure | Finding | Basis |
|---|---|---|
| Steps actual vs ideal | 16 story steps / about 38 inputs vs ~12. Each batch costs about 9 inputs: Scope, Field, open a sample row, Select all, choose a decision, type, Save, then Field again. This runs 4 times (GOOGL segment revenue, APLD segment capex, APLD segment revenue, APLD PP&E). | measured: filter bar 02, bulk card 09 |
| Re-entry from Release | "Fix in → Reconcile" on the Needs review row opens `#reconcile` unscoped: 16 rule findings plus 29 Category mapping rows below (02). The expanded detail lists `GOOGL 7`, `APLD 9` as plain text, with no link (01b). The scope must be re-picked by hand even though `?scope=` works (03). | measured |
| Decisions a default could carry | (a) The Field filter: grouping by company + field would show "Segment revenue · 6" as one selectable group, with no filter to set. (b) "Readings differ across filings" rows: the row already says "dataset uses 1,760 (10-K 2025-07-30)" (10). The reason "later reading used" could be prefilled. (c) Industry filter once a company is chosen: "Hyperscaler" is the only option left (03), so it decides nothing. | measured (options present); defaults suspected |
| Dead ends | (1) "Fix" saves a decision but the item stays "Needs review" until a re-read. Release stays Fail with no UI path forward (catalog step 14–16; label "Fix" in 08/09 gives no warning). (2) The Release Needs review detail has counts with no links (01b). | (1) suspected (not saved); (2) measured |
| Hesitations | Every rule-finding row shows "—" in Dataset, SEC XBRL, Gap and Difference (02, 07). The numbers are only in the "Details" prose after expanding (08: "sum to $402,963M … tags Revenues $402,836M … gap $127M"). Each batch needs at least one expand just to see the size of the gap. | measured |
| Confirmations guarding nothing | None found. Save writes directly. | measured |
| Count drift | One company's open work has four numbers: Reconcile header GOOGL "Needs review 7" (03); Proof "11 to review" (05, which is 7 + 4 proposed); Release detail "GOOGL 7" (01b); Release checks by company "G6 4" (01b). For APLD: 9 / 17 / 9 / 8. | measured |

## Take-away Pass

**Release (01, 01b)**
- Remove: the Details column's file paths and codes (`decisions/resolutions.jsonl`, `golden/stage<N>-handcheck.json`, `T63`, `has_value false`). They are truncated at 1600px anyway and add nothing for the person signing. Collapse the full text behind the row expander.
- Collapse: the 7 Pass rows and 4 Info rows under a "10 passing" disclosure. The 3 Fail rows are what the signer acts on.
- Replace: the expanded "Needs review" ticker table gets row links to `#reconcile?scope=<T>`. Or remove the expander and make the Count itself the link.
- Remove or rename: the "Release checks by company" G1/G4/G5/G6 codes (01b). The column headers need product names, and G6 disagrees with the Needs review counts (see Count drift).
- One primary action: yes. "Sign v1.9.0" is the only filled button, disabled with "3 required checks failing" (01). Correct.

**Reconcile, filtered (02, 03, 07)**
- Remove: the Dataset, SEC XBRL, Gap and Difference columns for rule findings, or fill them. All four are "—" on every one of the 16 rows (02).
- Remove: the Industry filter when a company is scoped (03).
- Defer: the Category mapping table (29 rows below the findings, 02) when the entry point is "Needs review". It belongs to the "Proposed" check.
- Stated more than once: the header "Needs review 16" and "Rule findings 16 to review of 16" sit 110px apart. "Show 6 settled" adds a third count.

**Reconcile, bulk selection (09)**
- Two primaries on screen: the bulk card shows "Save for 6" and an Accept/Explain/Fix/Block release group, while the expanded row below shows a second Decision panel with its own "Save" and the same four choices. Both Saves are filled blue. When a selection exists, the row panel should hide.
- Remove: the selected-item list "GOOGL segment_revenue FY2025; GOOGL segment_revenue FY2024; …" repeats the table rows just below it. "6 selected" is enough.
- "Accept" comes preselected in both panels (09). A bulk save with no deliberate choice records Accept.

**Reconcile, row open (08, 10, 11)**
- Details text leads with accession numbers (`0001652044-26-000018`) and raw field ids (`ppe_category Other equipment and fixtures`). The numbers belong in the empty columns. The accession number fits as a link label.
- The "Decision" sub-card is a bordered box inside a bordered table inside a bordered card (08). Drop one level.
- The restatement line (10) carries the decision-relevant fact ("dataset uses 1,760") in orange above "Details". It is the best-placed element on this screen. Keep it.

## The Simpler Version

Target: 7 steps.

1. `#release`: in the Needs review row, click **GOOGL 7** → `#reconcile?scope=GOOGL&status=open`.
2. The rows come grouped by field + check, with numbers in the columns: "Segment revenue · Does not tie · 6 · gaps $127M…". Tick the group, choose **Explain**, type the reason, **Save for 6**.
3. "PP&E by category FY2023 · gap $35,136M": **Fix**. The Fix button reads "Fix (stays open until re-read; release stays failing)". Choose **Block release** or **Explain** if the release must go out.
4. Back via the persistent link "Release · Needs review 1 left" (or the next ticker link) → **APLD 9**.
5. Group "Segment capex · 6": tick, Explain, reason, Save for 6. Group "Segment revenue · 1": same.
6. Group "PP&E by category · Readings differ · 2": reason prefilled "later 10-K reading used (dataset uses later filing)"; **Save for 2**. "Compare filings" stays available per row.
7. Return to Release: Needs review Pass.

Changes to get there:
- Link each ticker in Release "Needs review" detail to `#reconcile?scope=<T>`. Make "Fix in → Reconcile" carry the filter for its check (rule findings, open only, mapping table hidden).
- Add group rows keyed on company + field + check, each with one checkbox. This removes the Field filter step from every batch (4 × 2 inputs).
- Fill Dataset / SEC XBRL / Gap from the finding detail for "Does not tie" and "Readings differ" rows. This removes the sampling expand.
- Hide the per-row Decision panel while a bulk selection exists. Start with no decision preselected, so Save stays disabled until one is chosen.
- Prefill the reason for "Readings differ" rows where the dataset already uses the later filing.
- Show Fix's consequence on the control. Add a "Needs review N left · Release" link after each save, so the journey does not end at a reloaded list.
- Use one open-count definition across Reconcile header, Proof "to review", Release detail and Release-by-company. Or name the different ones differently ("to review" = needs review + proposed).

## Clarity Issues

| Label / text | Where | Problem | Suggested |
|---|---|---|---|
| "to review" vs "Needs review" | Proof 05 ("11 to review") vs Reconcile 03 ("Needs review 7") | Same words, different counts (Proof adds Proposed) | "11 open (7 review · 4 proposed)" |
| "G1 G4 G5 G6" | Release checks by company, 01b | Internal check codes | Check names, e.g. "Needs review", "Proposed" |
| "Fix" | Decision control, 08/09 | Reads as "fixed". The item actually stays open and the release stays failing (catalog edge case) | "Re-read needed" |
| "Accept" | Decision control, 08/09 | Accept what: the dataset value or the gap? | "Value correct" |
| "segment_revenue", "ppe_category" | bulk card 09, Details 10 | Raw field ids next to "Segment revenue", "PP&E by category" in the filter and rows | Use the display labels |
| "Does not tie to reported total" | rows 02 | Clear, but "tie" is accounting jargon. Acceptable for the persona. | keep |
| "Rule findings" vs "Needs review" | Reconcile 02 vs Release 01 | Two names for one queue across screens | "Needs review" on both |
| "Proposed" (check) vs "Category mapping … proposed" | Release 01 vs Reconcile 02 | Matches. No issue. | — |
| "Fix in" | Release column header 01 | Every row has it, Pass rows included. Reads as an instruction on rows that need nothing | Link on Fail rows only, header "Open" |
| Details column text | Release 01 | File paths and task ids (`decisions/resolutions.jsonl`, `T63`, `has_value false`) | Product wording; paths in Docs |
| "Grouped by cause" / "Every cause" / "Every check" | filter bar 02 | Cause and check are two filters with overlapping meaning ("Differs from SEC XBRL" is a cause, "Large year-over-year change" is a check) | Merge into one "Check" filter |
| Placeholders | bulk "Why, for all 6, e.g. accrual capex, cash basis differs" vs row "e.g. includes finance leases, note 7" (09) | Two example styles for one field | One placeholder: "Reason" |

App style rules: no italics, gradients or decorative pills were seen on these screens. Nested bordered boxes appear in the Decision sub-card (08, 10). The orange "Restated:" line (10) is a status, not a tag. No issue there.
