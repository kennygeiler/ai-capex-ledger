# Reconcile: category mapping and apply-everywhere

Topic `reconcile-mapping-encode`. Written 2026-11-04 from `ledger/web/pages/reconcile.js` (`mappingCell`, `mappingActions`,
`postMapping`, `expectedOf`, `encodePanel`, `canEncode`, `resolutionForm`, `keys`), `pages/_shared.js` (`mappingDecision`),
`pages/trail.js` (mapping stage), `ledger/web/app.py` (`/api/mapping`, `/api/mapping/reject`, `/api/judgement`),
`ledger/review/mapper.py` (`approve`, `reject`, `Stale`, `person`) and `ledger/review/judgement.py` (`offers`), plus a
read-only GET of `/api/v1/reconcile?scope=all`.

Live state used in the stories: 47 "Category mapping" rows (29 Proposed = to_confirm, 18 "Matches company's own tag"),
0 unmapped (so no live row shows **Map** today), and 0 rows that can be encoded (every `encode.rule` / `encode.definition`
carries a `why_not`, and the 5 "Differs from SEC XBRL" rows carry no `encode` at all), so **Apply everywhere** and
"Saved. Apply to every company?" cannot appear on the current data.

## STORY-001: Approve a proposed category from the row
**Type**: short
**Topic**: reconcile-mapping-encode
**Persona**: Kenny Geiler, owner/reviewer, Signer box filled with "Kenny Geiler"
**Goal**: Confirm the mapper's proposal that MSFT's "Land" line is `LandMember`
**Preconditions**: Local copy (not read-only); MSFT "Land" is Proposed (to_confirm), no company tag ("Not tagged"), proposal by "Claude Fable 5.1"
**Ideal path**: 2 — filter to the company's mappings, press Approve on an obvious one-word match
**Alternate paths**: (a) Expand the row and press **Approve** in the decision card (`mappingActions`); (b) from `#proof/MSFT`, Category mapping stage card → "Decide in Reconcile →" (lands on `#reconcile?scope=MSFT&cause=asset_types`); (c) choose `LandMember` explicitly via the card's "Standard category" select + **Choose another** (writes the same member as a confirm, not a replace)
### Steps
1. Open `#reconcile`, set Scope to "Microsoft (MSFT)" and Cause to "Category mapping" -> URL becomes `#reconcile?scope=MSFT&cause=asset_types`; one card "Category mapping" with header tally "6 proposed · 0 unmapped · 0 differ from company tag · 0 match company tag"
2. Scan the "Land" row: Dataset column shows "Land" + orange "Proposed", the quoted evidence "the note's own category name …" and "Not tagged" -> Kenny thinks: "Land is Land, no need to open it"
3. Press **Approve** in the Decision column -> status "Saving…", then "Confirmed." (the row is an existing entry, so the word is Confirmed, not Mapped), page reloads after 250 ms
4. The row stays listed (asset rows are always listed) but leaves Proposed; the header Proposed count and the card tally each drop by 1
### Variations
- Approve on a row whose proposal came from nothing on file (mapping `unmapped` with a proposal) shows "Mapped." instead of "Confirmed."
- Grouped by company (`group=company`) shows the same row under "Microsoft MSFT" with Cause column "Category mapping".
### Edge Cases
- Signer box empty -> **Approve** is disabled with tooltip "Enter a signer name"; **Reject** and the row's **Choose another** are not disabled (they are not wrapped in `needsMe`).
- Double-click: the button disables itself on the first click; a second POST cannot fire.
- Read-only copy: **Approve** renders enabled; click -> "Couldn’t save: this copy of Kenny's Data Emporium is read-only; …." inline in red.
- Redundancy: the same proposal (member, evidence, company tag) is shown on the row, in the expanded decision card, and on the trail's Category mapping stage card.

## STORY-002: Stale Approve gets "Changed since loaded. Reloading."
**Type**: short
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, with Reconcile open in two browser tabs
**Goal**: Confirm GOOGL "Office space" → `BuildingAndBuildingImprovementsMember`
**Preconditions**: Tab A and tab B both loaded `#reconcile?scope=GOOGL&cause=asset_types`; in tab B he already rejected the proposal (line removed from `taxonomy/asset_types.yaml`)
**Ideal path**: 1 — a stale click should explain itself and refresh without data loss
**Alternate paths**: The same 409 is reachable from the decision card's **Approve** and **Choose another** (both send `expected`); **Reject** never 409s (it sends no `expected`)
### Steps
1. In tab A press **Approve** on "Office space" -> "Saving…"
2. Server compares `expected` {standard_type: BuildingAndBuildingImprovementsMember, at: 2026-11-01} with the file (now no entry) -> 409 -> status turns red "Changed since loaded. Reloading."
3. After 800 ms the page re-routes -> the row now shows "No proposal" and a primary **Map** button; the expanded card would show "Rejected: Building and building improvements"
4. Kenny thinks: "Fine, it was me in the other tab" — but the message does not say what changed or who changed it
### Variations
- Mapper rerun between load and click (proposal `at` date changed) -> same 409, page reloads showing the new proposal.
### Edge Cases
- If the other tab *confirmed* it instead, `expected` still matches (same member and `at`), so no 409; the server raises "… is already mapped to … and confirmed by Kenny Geiler" -> 400 shown as "Couldn’t save: …." with no reload. The two "someone else got there first" cases surface differently.
- Any text typed nowhere is lost on reload, but mapping has no free-text field, so nothing is lost.

## STORY-003: Reject a wrong proposal and pick the right member
**Type**: medium
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, cautious about AI-proposed buckets for AI capex
**Goal**: Fix APLD "Information Systems and Software", proposed as `TechnologyEquipmentMember` while APLD's own XBRL tag says Software
**Preconditions**: Row shows red "Company tags SoftwareAndSoftwareDevelopmentCostsMember" under the proposal; header tally includes "differ from company tag"
**Ideal path**: 3 — open the row, pick the company's member, Choose another (one write replaces the proposal)
**Alternate paths**: (a) Row **Choose another** → expands the row and focuses the select (same as clicking the row); (b) **Reject** first, wait for re-render, then **Map** with the select (two writes, leaves a "Rejected" log line); (c) arrive from `#proof/APLD` "Decide in Reconcile →"
### Steps
1. `#reconcile?scope=APLD&cause=asset_types` -> card header "11 proposed · 0 unmapped · 3 differ from company tag · 8 match company tag" (counts as live)
2. Kenny notices the red "Company tags SoftwareAndSoftwareDevelopmentCostsMember" under "Technology equipment · Proposed" -> hesitates: "Is the line hardware or software? The FY2023 number is only $21.2M"
3. Click the row (or Enter) -> evidence opens: decision card (name, state "To confirm", Company line "$21.2M FY2023" + "Open ↗", Proposed with definition and "Source: …", Company’s own tag "Differs: Software and Software Development Costs …" with the definition, Basis, Alternatives "Software and Software Development Costs · … · why", Affects "2 figures · $21.2M FY2023") and a "Note wording" card
4. Expand the "Alternatives" disclosure to read the Software definition -> satisfied it matches
5. In the "Standard category" select (the proposed Technology Equipment is filtered out, so the list starts at "Computer Equipment") choose "Software and Software Development Costs"
6. Press **Choose another** -> "Saving…" -> "Mapped." -> reload; the entry is replaced, confirmed by Kenny today
### Variations
- Path (b): **Reject** -> "Rejected." -> reload -> row now "No proposal" with **Map**; the select now also omits the rejected member; **Map** writes the new entry -> "Mapped.". Next mapper run will not re-propose the rejected member; if it does, the card shows orange "Proposed again after rejection: …".
### Edge Cases
- The select defaults to its first option, not to the company's tagged member; pressing **Choose another** without touching the select maps to whatever is first (e.g. "Computer Equipment"). No confirmation step.
- Choose another on the row does not write anything — it only opens the card. Two controls with the same label do different things (row = open, card = write).
- Escape does not collapse the row while focus is in the select (`keys` ignores events from inputs/selects/buttons).
- Reject's reason is fixed text "rejected on Reconcile"; there is no field to say why.

## STORY-004: Override a "Matches company's own tag" mapping
**Type**: medium
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, second-guessing AMZN "Heavy equipment"
**Goal**: Decide whether "Heavy equipment" belongs in `MachineryAndEquipmentMember` or something narrower
**Preconditions**: Row state "Matches company's own tag" (verification `company`, mapping `verified`, by `mapping:filer_tag`); not open, but still listed after the open rows
**Ideal path**: 2 — open and approve or choose; the row is already settled, so confirming should be optional
**Alternate paths**: `#proof/AMZN` Category mapping stage → collapsed tally → expand → "Confirm or override in Reconcile →"
### Steps
1. `#reconcile?scope=AMZN&cause=asset_types` -> asset rows sorted open first; "Heavy equipment" sits below the 4 Proposed rows with green "Matches company’s own tag"
2. Kenny wonders why a settled row still has **Approve / Reject / Choose another** -> the code keeps them "so a person can override it"
3. Open the row -> decision card: Company’s own tag "Same as proposed", Affects "2 figures · $65,545M FY2025"
4. Press **Approve** -> "Confirmed." (adds confirmed_by/at) or **Reject** -> server refuses only if already person-confirmed; a filer-tag line is removed and the category becomes unmapped
### Variations
- Choose "Equipment" from the select -> **Choose another** replaces the filer-tag line with Kenny's entry.
### Edge Cases
- Rejecting a filer-tag match throws away the strongest evidence class (company's own XBRL) with one click and no confirm dialog.
- The header "Proposed" counter does not include these 18 rows, but the card header tally does ("18 match company tag" across companies) — two counts of the same group on one page.

## STORY-005: Work through all MSFT mappings by keyboard
**Type**: long
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, doing the "five times a company" pass the code comment describes, keyboard first
**Goal**: Settle all 6 Proposed MSFT categories (Buildings and improvements, Computer equipment and software, Furniture and equipment, Land, Leasehold improvements, Servers, network equipment, and software)
**Preconditions**: Signer "Kenny Geiler"; all 6 to_confirm, none tagged by the company
**Ideal path**: 12 — 6 rows × (move + decide), no reload jumps
**Alternate paths**: Mouse on row buttons; via the decision card; arrive from `#proof/MSFT` → "Review in Reconcile →" (lands unfiltered by cause) or the stage's "Decide in Reconcile →"
### Steps
1. Hover "Keyboard" in the header -> tooltip "j k move · Enter opens · a e f b decide · space selects"
2. `#reconcile?scope=MSFT&cause=asset_types`, Tab into the first row -> row highlighted (`cur`)
3. Press `a` hoping to approve -> nothing happens (a/e/f/b are disabled on mapping rows); Kenny thinks: "so the keyboard hint lies for this card"
4. Press Enter -> evidence opens; Tab to **Approve** in the card, press Enter -> "Confirmed." -> reload after 250 ms
5. After reload focus returns to row 0 (no FOCUS_KEY is set by mapping writes) -> he must press `j` to reach the next undecided row each time
6. "Computer equipment and software" → proposal Technology Equipment; Alternatives list "Computer Equipment" -> hesitation: Microsoft lumps software in; he opens "Note wording" to read the note text, then approves Technology Equipment
7. "Furniture and equipment" → proposed Furniture and Fixtures; Alternatives "Equipment …" -> he looks for "Furniture and Fixtures" in the select, but it is filtered out because it is the proposal, so he presses **Approve** instead
8. "Servers, network equipment, and software" → Affects "2 figures · $215,874M FY2026" -> the biggest dollar line; he opens Company line "Open ↗" (SEC link) to double-check, then **Approve**
9. Remaining two rows: **Approve** each (j, Enter, Tab ×n, Enter)
10. Card header tally reaches "0 proposed"; Reconcile header Proposed count drops by 6
11. Open `#proof/MSFT` -> Category mapping stage card shows the confirmed cards with Basis "… · confirmed Kenny Geiler 2026-11-04", no "Decide in Reconcile →" links
12. Check `#proof` board -> MSFT Category mapping cell no longer counts open items
### Variations
- Mouse-only: row **Approve** is 1 click per row, faster than the keyboard route.
### Edge Cases
- Pressing space on a mapping row adds it to the selection (the space handler does not check `isAsset`), showing the "<n> selected: …" bulk card even though mapping rows have no checkbox; **Save for n** then posts mapping keys to `/api/resolve/bulk`, which appears to refuse the whole batch (key names no dataset row) — likely broken flow.
- Every write reloads the whole page and resets focus to the first row; long lists mean repeated scrolling.
- Same Affects / Company line facts appear on the trail card and the Reconcile card (redundant by design: shared `mappingDecision`).

## STORY-006: Map an unmapped category with no proposal
**Type**: short
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, after a new AMD 10-K adds a line the mapper did not propose for
**Goal**: Give AMD "Data center equipment" a standard member
**Preconditions**: Row with mapping `unmapped`, no proposal (not live today: 0 unmapped rows); Dataset column "No proposal"
**Ideal path**: 3 — open, select member, Map
**Alternate paths**: Row **Map** (primary button, opens the card and focuses the select); clicking the row
### Steps
1. Row shows "No proposal" and a blue **Map** button (no Approve/Reject) -> click **Map** -> card opens, "Standard category" select focused; card Proposed reads "None"
2. Choose "Technology Equipment" -> press card **Map** -> "Mapped." -> reload
### Variations
- `expected` is null for an unmapped row; if the mapper wrote a proposal meanwhile, 409 "Changed since loaded. Reloading."
### Edge Cases
- Empty Signer: card **Map** disabled ("Enter a signer name") but the row **Map** still opens the card — the user can go one step before finding the block.
- Server refuses a member off the list (400) — not reachable from the select.

## STORY-007: A different name in the Signer box
**Type**: short
**Topic**: reconcile-mapping-encode
**Persona**: A colleague "Priya" at Kenny's local checkout, not on `config.PEOPLE`
**Goal**: Approve NVDA "Land" (actually it is already Matches company's own tag) and reject AMD "Equipment"
**Preconditions**: Signer box reads "Priya"
**Ideal path**: 1 — the UI should say before the click that this name cannot write
**Alternate paths**: none found (every mapping write goes through the same two routes)
### Steps
1. Press **Approve** on AMD "Equipment" -> "Couldn’t save: 'Priya' is not on config.PEOPLE, the people who may confirm a mapping." (400)
2. Press **Reject** on the same row -> appears to succeed "Rejected." (`mapper.reject` only checks the name is non-empty, not `config.PEOPLE`) -> the proposal line is removed under Priya's name
### Edge Cases
- Asymmetric guard: Reject accepts any name, Approve/Choose another/Map refuse; contradicts the discovery note that every write refuses a `by` off PEOPLE. Flag for verification.
- With an empty Signer, Reject is enabled and the server answers 400 "a rejection needs the ticker, the reported name, the member rejected and a name".

## STORY-008: Explain a renamed line once and make it a rule
**Type**: medium
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, tired of explaining the same "Line renamed" finding every year
**Goal**: Explain a `row_label_switch` finding on GOOGL capex and write it as a rule for every company reading those lines
**Preconditions**: A finding_unconfirmed row of rule `row_label_switch` with a field the company reads from at least one line (not present on live data; all live findings are tie/jump rules whose `encode.rule.why_not` hides the panel)
**Ideal path**: 3 — decide Explain with a reason, then one click on Make this a rule reusing that reason
**Alternate paths**: (a) Expand the row → **Apply everywhere** card at the bottom (`once`) → **Make this a rule** without saving a decision first; (b) after Save on Accept or Explain → "Saved. Apply to every company?" panel (same `encodePanel`); (c) keyboard `e` opens the row with Explain pre-pressed
### Steps
1. `#reconcile?scope=GOOGL&kind=row_label_switch` (Check select "Line renamed") -> row under "Rule findings"
2. Press `e` on the row -> evidence opens, Decision card with **Explain** active and Reason focused
3. Type "Google renamed 'Purchases of property and equipment' to 'Capital expenditures'; same line" -> **Save** -> status "Saved. Apply to every company?" with the encode panel and a **Done** button (the page does not reload yet)
4. Panel line "Applies to: every company reading “Purchases of property and equipment”, “Capital expenditures”"; Reason input pre-filled with his reason, placeholder "Reason (applies to every company)"
5. Kenny hesitates: "every company" — the labels are specific, so it is narrow enough -> press **Make this a rule** -> "Writing…" -> "Saved to rules/<id>.yaml. Applies on the next run."
6. Press **Done** -> page reloads; the row stays until the next `ledger rules` run
### Variations
- Pressing **Done** without writing skips the rule; the Explain decision is kept.
- Reason cleared -> "Reason required" and focus to the input.
### Edge Cases
- After writing, the same rule offer reappears on reload with `why_not` "already on file … rerun ledger rules", so the panel silently disappears — no on-page sign a rule was written until the run.
- Bulk **Save for n** never offers the encode panel; Fix and Block release never offer it.
- Redundancy: the same panel appears both as the "Apply everywhere" card in the expanded row and inside the post-save status; a user can write from the card, then Save, then see it again.
- Encode failures read "Couldn’t write: …." (different verb from decisions' "Couldn’t save: …. Try again.").

## STORY-009: Write a company definition for a blocked revenue disagreement
**Type**: medium
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, NVDA FY2025 revenue blocks release because the SEC tag counts something different
**Goal**: Explain once in `definitions/companies.yaml` that NVDA's revenue definition differs
**Preconditions**: A "blocked" item of `xbrl_reconcile` on revenue FY2025 for NVDA, no NVDA revenue definition on file (none live today)
**Ideal path**: 2 — expand, Make this a definition with reason
**Alternate paths**: Save Explain first → "Saved. Apply to every company?" → **Make this a definition**; `b` key opens with Block release pre-pressed (wrong default for this goal)
### Steps
1. `#reconcile?cause=blocked&scope=NVDA` -> the Blocks release card
2. Open the row -> **Apply everywhere** card: "Applies to: NVDA · FY2025", placeholder "Reason (this company)"
3. Kenny notes the card title says "Apply everywhere" while the line says this company only -> mild confusion
4. Type "SEC Revenues tag includes … ; the 10-K line is net revenue" -> **Make this a definition** -> "Saved to definitions/companies.yaml. Applies on the next run."
### Variations
- Cost-lines definition (`cost_lines_summed`): "Applies to: NVDA · “Cost of revenue — products” + “Cost of revenue — services”".
### Edge Cases
- NVDA already has a revenue definition -> `why_not` "edit it by hand" -> the panel just does not render; the reason is never shown in the UI.
- Signer empty -> button disabled, tooltip "Enter a signer name".

## STORY-010: Full company: trail → mapping → decision → encode → Proof
**Type**: long
**Topic**: reconcile-mapping-encode
**Persona**: Kenny, trying to get APLD from "to review" toward "Proven" in one sitting
**Goal**: Clear APLD's 11 Proposed mappings and settle its findings, writing a rule where the code allows
**Preconditions**: Live APLD state: 11 Proposed mappings (5 company extension tags, 3 differ), 16 findings mostly tie rules (none encodable)
**Ideal path**: ~25 — 11 mapping decisions + ~10 finding decisions + navigation
**Alternate paths**: Start at `#proof` board row APLD; or the jump box "APLD" → `#data?ticker=APLD` → ticker cell → trail; or `#release` "Fix in" → Reconcile (unscoped)
### Steps
1. `#proof` -> APLD row "<n> to review" -> click -> `#proof/APLD`
2. Category mapping stage card "<n> items · 11 to review": cards show Company’s own tag "Company-specific tag: apld:ElectricGenerationAndTransformersMember" etc. -> click "Decide in Reconcile →" -> `#reconcile?scope=APLD&cause=asset_types`
3. "Electric Generation and Transformers" (FY2023) and "Electric generation and transformers" (FY2026) appear as two rows — the reported name changed case between filings -> Kenny thinks: "same line, two decisions" -> **Approve** each (ElectricGenerationEquipmentMember)
4. "Electrical infrastructure" → ElectricGeneration proposed, no alternatives -> **Approve**
5. "Mechanical infrastructure" → MachineryAndEquipment, $71.9M -> **Approve**
6. "Building" (tag says BuildingMember) and "Building improvements" (tag says BuildingImprovementsMember) proposed as BuildingAndBuildingImprovements -> open each, select the tagged member, **Choose another** -> "Mapped."
7. "Information Systems and Software" and "Networking equipment, electrical equipment, and software" (tag differs: Software) -> one to Software via **Choose another**, the mixed line he **Approve**s as Technology Equipment after reading "Note wording"
8. Card tally "0 proposed"
9. Change Cause select to "Every cause" -> "Rule findings" card shows segment_capex/segment_revenue tie findings
10. Open "segment_capex FY2026" -> no "Apply everywhere" card (rule why_not); Kenny expected one after reading the Docs -> chooses **Explain**, reason "segments exclude corporate", **Save** -> "Saved." (no encode prompt) -> reload
11. Select the remaining segment_capex rows with checkboxes / "Select all <n>" -> bulk card "<n> selected: …" -> **Explain**, "Why, for all n…" -> **Save for n**
12. "ppe_category FY2024 / FY2025" (fact_readings_differ) -> **Fix** with reason "re-read note 7"
13. Back to `#proof/APLD` -> mapping stage "Complete"; findings explained
14. `#release` -> "Proposed" line still fails for other companies; APLD row in "Release checks by company" improves
### Variations
- Grouped by company (`group=company`) shows mappings and findings for APLD in one card, avoiding the Cause switch.
### Edge Cases
- No live item offers encoding, so the "write it once" promise is unreachable on this data; the user cannot tell why (why_not never shown).
- "Select all <n>" is hidden on the mapping card (mappings are never bulk), so 11 separate decisions are required.
- Each mapping write reloads and returns focus to the first row.

## STORY-011: Read-only visitor tries the mapping buttons
**Type**: short
**Topic**: reconcile-mapping-encode
**Persona**: Analyst on the hosted copy (`LEDGER_READONLY=1`)
**Goal**: Understand how GOOGL "Technical infrastructure" was categorised
**Preconditions**: Header shows "Read-only"; no Signer box
**Ideal path**: 2 — open the row and read the decision card; buttons should be hidden
**Alternate paths**: `#proof/GOOGL` Category mapping stage card (same `mappingDecision` card, no buttons)
### Steps
1. `#reconcile?scope=GOOGL&cause=asset_types` -> rows with **Approve / Reject / Choose another**
2. Open "Technical infrastructure" -> Proposed Technology Equipment, Company’s own tag "Company-specific tag: goog:TechnicalInfrastructureMember · not every extracted year", Affects "3 figures · $203,679M FY2025"
3. Clicks **Reject** out of curiosity -> "Couldn’t save: this copy … is read-only; …."
### Edge Cases
- `me` is unset on the read-only copy, so Approve/Choose another are disabled with "Enter a signer name" (misleading there) while Reject is enabled and fails on click.
- The trail card shows the same facts with no buttons — the better read surface for this persona.
