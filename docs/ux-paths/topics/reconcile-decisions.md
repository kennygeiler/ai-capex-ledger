# Reconcile: deciding open items

Topic `reconcile-decisions`. Source: `ledger/web/pages/reconcile.js` (`reconcilePage`, `resolutionForm`, `confirmCell`,
`keys`, `paint`, `evidence`, `encodePanel`), `ledger/web/app.py` (`_flow`, POST `/api/resolve`, `/api/resolve/bulk`),
`ledger/review/resolutions.py` (`_line`, `resolve_many`, `is_live`), `ledger/review/workbench.py` (causes, `to_confirm`).
Live data read 2026-11-04 from `GET /api/v1/reconcile?scope=all`.

Live queue as of writing: header "Needs review 16 · Proposed 29 · Unverified 6", "Last run Nov 1", "Last release v1.8.0".
Cards by cause: **Rule findings** (16 to review of 16: APLD and GOOGL tie failures and "Readings differ across filings"),
**Category mapping** (29 proposed · 18 match company tag; covered in `reconcile-mapping-encode`). "Show 6 settled" reveals
**Differs from SEC XBRL** (AMZN Equipment FY2024, GOOGL Office space / Technical infrastructure / Corporate and other
assets FY2024, APLD Construction in Progress FY2023) and APLD opex FY2026 ("Large year-over-year change", explained by
definition `cost_lines`). No **To confirm** or **Blocks release** rows exist today; stories that use them follow the code.
No live item is encodable (every `encode.rule` / `encode.definition` carries `why_not`), so "Apply everywhere" and
"Saved. Apply to every company?" never appear on today's data.

---

## STORY-001: Accept one rule finding with a reason
**Type**: short
**Topic**: reconcile-decisions
**Persona**: Kenny Geiler, owner and signer, on the local checkout with Signer "Kenny Geiler"
**Goal**: Close GOOGL segment_revenue FY2025 "Does not tie to reported total" after deciding the $127M gap is explained
**Preconditions**: `#reconcile` loaded, default Grouped by cause; the row is in the Rule findings card, state "Needs review"
**Ideal path**: 3 — open the row, type the reason, press Save (Accept is the form's default state)
**Alternate paths**: keyboard: focus row, `a` (opens and pre-selects Accept, focuses Reason), type, Enter; bulk: tick the checkbox → bulk card → Save for 1; Company trail `#proof/GOOGL` "Review in Reconcile →" lands on the same page scoped to GOOGL
### Steps
1. Click Reconcile in the navbar -> `#reconcile`; header counts "Needs review 16 · Proposed 29 · Unverified 6"; Rule findings card first.
2. Click the GOOGL row "segment_revenue FY2025" (Dataset, SEC XBRL, Gap, Difference all "—") -> evidence row opens below: "Details" disclosure with "3 parts in 0001652044-26-000018 sum to $402,963M; the filing tags Revenues $402,836M for 2025-12-31 (gap $127M, tolerance on the sum ±$2M)", link "Open in Dataset", and a **Decision** card.
3. Kenny thinks: "$127M on $403B, the segments include hedging gains Alphabet reports outside segments." He hesitates over Accept vs Explain: both tooltips read "Right as it stands" / "Right, with the reason kept"; both need a reason anyway. Leaves **Accept** (pre-pressed).
4. Types "segment total includes hedging gains reported in Alphabet-level activities" in the Reason box (placeholder "e.g. includes finance leases, note 7") and clicks **Save** -> "Saving…" then "Saved."; after 250 ms the page re-renders.
5. Row is gone from the default list (no longer open); header now "Needs review 15"; "Show 7 settled". Focus lands on the first row of the page (the saved row no longer exists, so `FOCUS_KEY` falls back to index 0) and scrolls it to centre.
### Variations
- Explain instead of Accept: identical server effect (both map to state explained / word "Unverified"); only the badge colour and label differ (`bg-azure-lt` vs `bg-green-lt`).
- Press Enter in the Reason box instead of clicking Save (Reason `onkeydown` Enter clicks Save).
- Arriving from Release: "Fix in" Reconcile on the "Needs review" line → `#reconcile` unfiltered; the user has to find GOOGL themselves.
### Edge Cases
- Empty reason -> Reason focused, status "Reason required"; nothing posted.
- The decision is shown afterwards in three places: the row's Decision cell ("Accept · Kenny Geiler · Nov 4", only with Show settled), the Decision card header ("Accept · Kenny Geiler · Nov 4 · <reason>"), and the Company trail / Dataset grid badge ("Accepted"). Redundancy candidate.
- No undo. Reversing means re-opening the settled row (Show settled) and saving a new decision, which appends a new line.

## STORY-002: Triage APLD findings fast with the keyboard
**Type**: medium
**Topic**: reconcile-decisions
**Persona**: Kenny, keyboard-first, clearing the queue before a release
**Goal**: Decide all nine APLD rule findings without the mouse
**Preconditions**: `#reconcile?scope=APLD`; Signer filled
**Ideal path**: 4 per item (j to move, letter to decide, type reason, Enter) — about 36 keystroke-groups for nine items; a well-designed UI could auto-advance after Save
**Alternate paths**: mouse click per row + Save; bulk select (space) + Save for n when the reason is shared (STORY-004); the "Keyboard" hint in the header is the only discoverability for keys (tooltip "j k move · Enter opens · a e f b decide · space selects")
### Steps
1. Choose Scope "Applied Digital (APLD)" -> URL `#reconcile?scope=APLD`; Rule findings card "9 to review of 9" (settled opex FY2026 hidden), Category mapping card for APLD below.
2. Hover "Keyboard" in the header -> tooltip lists the keys. Kenny had forgotten `o` also opens.
3. Click (or Tab to) the first row "segment_capex FY2026" -> row gets the `cur` highlight.
4. Press Enter -> evidence opens: Details "2 parts in 0001144879-26-000048 sum to $2,989.9M; the filing tags PaymentsToAcquireProductiveAssets $2,865.8M for 2026-05-31 (gap $124.2M, tolerance on the sum ±$1,500)".
5. Kenny thinks the segment table double counts a transfer. Presses `f` -> Fix is pressed, cursor in Reason.
6. Types "segment table double-counts intersegment transfer; re-read" and Enter -> "Saved."; page re-renders; row stays (Fix keeps it open, now "Needs review" with "Fix · Kenny Geiler · Nov 4" under it); focus returns to the same row (FOCUS_KEY found).
7. Press `j` -> next row "segment_revenue FY2026". He has to press Enter or a letter again: nothing auto-opens.
8. Press `e`, type "revenue split restated by the FY2026 10-K", Enter -> row leaves the list; focus jumps to the first row on the page (index 0), not the next item. Kenny presses `j` several times to get back to where he was.
9. Next row "ppe_category FY2025" -> `o` opens it; evidence starts with the orange restated line "Restated: 2,126 (10-K 2025-07-30) → 12,447 (10-K 2026-07-29) · dataset uses 12,447 (10-K 2026-07-29) · Compare filings".
10. Kenny clicks "Compare filings" -> `#evidence/compare?a=…&b=…` ("Readings differ"); checks both crops; presses Back -> Reconcile re-renders from the URL with nothing expanded and focus on the first row.
11. Finds the row again, `e`, "later 10-K reclassified fixtures; dataset uses the later reading", Enter.
12. Two rows read "segment_capex FY2024" and two read "segment_capex FY2023" (different filings, subject in the key only). He opens each to tell them apart by the accession in Details before deciding.
13. Repeats `j` / letter / reason / Enter for the rest; Rule findings card for APLD ends "n to review of 9" counting only the Fix rows.
### Variations
- `k` / ArrowUp to go back; Escape collapses the open evidence row (only while focus is on the row, not inside the Reason input).
- Grouped by company (`group=company`): APLD card mixes rule findings and mapping rows; `a e f b` are ignored on mapping rows (`isAsset` guard).
### Edge Cases
- Keys are ignored while focus is in an input, select or button, and with Cmd/Ctrl/Alt held: after typing a reason and clicking elsewhere in the form, `j` does nothing until focus is back on a row.
- After Save the page fully re-renders (`route`), so every other expanded row closes.
- Focus after Save: same row if it is still listed (Fix), else first row of the page — breaks a top-to-bottom keyboard rhythm when deciding mid-list.
- Duplicate-looking rows (same "segment_capex FY2024" twice) are a scanning hazard: the Item column cannot distinguish them.

## STORY-003: Bulk-explain GOOGL segment revenue ties for five years
**Type**: medium
**Topic**: reconcile-decisions
**Persona**: Kenny, who already knows the cause is the same every year
**Goal**: One reason for GOOGL segment_revenue FY2020–FY2025 "Does not tie to reported total"
**Preconditions**: `#reconcile?scope=GOOGL&field=segment_revenue`
**Ideal path**: 4 — filter, Select all, type reason, Save for n
**Alternate paths**: tick each checkbox; keyboard space on each row; from the unfiltered page use "Select all 16" then untick non-GOOGL rows; or decide each row singly (6× STORY-001)
### Steps
1. From `#reconcile`, choose Scope "Alphabet (GOOGL)" -> `#reconcile?scope=GOOGL`.
2. Choose Field "Segment revenue" -> `#reconcile?scope=GOOGL&field=segment_revenue`; Rule findings card "6 to review of 6", button "Select all 6".
3. Opens FY2023 to confirm the pattern ("…sum to …; the filing tags Revenues … (gap …)"), then FY2021. Same shape, small gaps.
4. Clicks **Select all 6** -> all checkboxes ticked; a bulk card appears above the cards: "**6** selected: GOOGL segment_revenue FY2025; GOOGL segment_revenue FY2024; …" with the Decision btn-group (Accept pressed), Reason placeholder "Why, for all 6, e.g. accrual capex, cash basis differs", **Save for 6**, **Clear**.
5. Clicks **Explain**, types "segments include hedging gains reported outside segments", clicks **Save for 6** -> the bulk card hides immediately (selection cleared before the status can be read), page re-renders 250 ms later; the six rows leave the list.
6. Header "Needs review 10"; with field filter still on, the page shows "No items to review" (no Rule findings card, Category mapping not shown because mappings have no field).
### Variations
- Untick one row inside the selection: the bulk card text and button update ("Save for 5").
- Space on a focused row toggles selection the same way.
### Edge Cases
- Server checks every item before writing (`resolve_many`): one bad key refuses all, nothing written; status "Couldn't save: … Try again."
- No "Saved." feedback survives a successful bulk save; the user infers success from the rows disappearing.
- Bulk never offers "Apply to every company?" (encode is single-item only).
- Field filter persists in the URL after the work is done; "No items to review" can read as "queue empty" while 10 items remain under other fields.

## STORY-004: Bulk select in "Grouped by company" sweeps in mapping rows and fails
**Type**: medium
**Topic**: reconcile-decisions
**Persona**: Kenny, trying to clear everything for APLD in one go
**Goal**: Explain all open APLD items at once
**Preconditions**: `#reconcile?scope=APLD&group=company`
**Ideal path**: 3 — Select all, reason, Save for n (if the selection only took decidable rows)
**Alternate paths**: Grouped by cause + "Select all 9" on the Rule findings card (works); per-row checkboxes (mapping rows have none)
### Steps
1. Choose Group by "Grouped by company" -> one card "Applied Digital APLD", header "17 to review of 25" (9 rule findings + 8 Proposed mappings open; 8 "Matches company tag" mappings listed too); button "Select all 17".
2. Kenny assumes it selects the nine rule findings. Clicks **Select all 17** -> bulk card lists "APLD segment_capex FY2026; …; APLD Building; APLD Electrical infrastructure; …" — open Category mapping rows (Proposed) are included, though mapping rows have no checkbox.
3. Picks Explain, types "tie gaps reviewed", clicks **Save for 17** -> "Couldn't save: not a queue item's key (kind|ticker|field|period|dimension|rule_id|subject, a live kind): 'asset_types|APLD|Building'. Try again." Nothing is written.
4. Kenny is confused (mapping rows are "never bulk-selected"); clicks **Clear**, switches back to Grouped by cause, uses "Select all 9" on Rule findings, saves.
### Variations
- Space on a focused mapping row also adds it to the selection (the `keys` handler has no `isAsset` guard for space), with the same failure.
### Edge Cases
- BROKEN FLOW: `Select all` is hidden only for the cause-grouped Category mapping card (`assetGroup` is false when grouped by company), and keyboard space has no mapping guard. The server refuses the whole batch (400), so no partial write, but the error text is developer wording.

## STORY-005: Confirm a run's proposed decision
**Type**: short
**Topic**: reconcile-decisions
**Persona**: Kenny, after a pipeline run wrote decisions for a person to confirm
**Goal**: Make a run's "explain" on APLD segment_capex FY2025 his own so release gate G6 passes
**Preconditions**: a run line exists (not live today); Release checklist line "Proposed" failing with "Fix in" Reconcile → `#reconcile?cause=to_confirm`
**Ideal path**: 2 — read the proposal, click Confirm
**Alternate paths**: Overturn → Save with the same state (writes the user's own reason instead of "confirmed"); keyboard letter on the row then Save; Release "Fix in" link vs navbar Reconcile
### Steps
1. On `#release`, the row "Proposed" fails; clicks "Fix in" Reconcile -> `#reconcile?cause=to_confirm`.
2. **To confirm** card first, "1 proposed"; row Item "finding unconfirmed: segment_capex FY2025 (segment_capex_tie)", Dataset/SEC XBRL/Difference "—"; Decision cell **Confirm Explain** and **Overturn**, under them "<run name> · Nov 1".
3. Kenny opens the row to read why -> card "Proposed: Explain" with the run's message, "Company trail" link, and a **Change decision** card (form pre-set to Explain, Reason pre-filled with the run's reason).
4. Satisfied, clicks **Confirm Explain** -> "Saving…" then "Confirmed."; reload after 250 ms; the To confirm card disappears; header "Proposed" count drops by one.
### Variations
- Confirm straight from the row without opening it (button stops propagation); fastest but decides unseen.
### Edge Cases
- Empty Signer: Confirm is not disabled (no `needsMe`), the POST fails: "Couldn't save: a resolution needs a state (accept, explain, fix, blocks), a reason and a name." Inconsistent with Approve/Sign which disable with "Enter a signer name".
- `cause=to_confirm` with no proposed rows (today): the Cause select has no "To confirm" option so it shows "Every cause" while the list says "No items to review" — the filter is invisible and the empty state misleads.
- The reason written is the literal "confirmed"; the run's own reasoning stays only on the run line.

## STORY-006: Overturn a proposed Accept and block the release
**Type**: medium
**Topic**: reconcile-decisions
**Persona**: Kenny, sceptical of an agent's call
**Goal**: Replace a run's "Accept" on GOOGL ppe_category FY2023 (4 parts sum to $201,803M vs tagged $166,667M, gap $35,136M) with Block release
**Preconditions**: a run line proposes accept for that item (code path; not live today)
**Ideal path**: 4 — Overturn, choose Block release, write reason, Save
**Alternate paths**: open the row and use the Change decision card directly; keyboard `b` on the focused row
### Steps
1. In the To confirm card, row "finding unconfirmed: ppe_category FY2023 (ppe_categories_tie)" shows **Confirm Accept**.
2. A $35B gap does not look acceptable. Clicks **Overturn** (tooltip "Change decision") -> evidence opens, cursor in the Reason box of **Change decision**; Accept is pressed and the Reason holds the run's text.
3. Hesitates: the pre-filled reason is the agent's, not his. Selects all and deletes it.
4. Clicks **Block release** (tooltip "Blocks release until settled"), types "construction in progress counted twice; do not publish until re-read", **Save** -> "Saved."; reload.
5. The To confirm row is gone; the GOOGL ppe_category FY2023 item now reads "Blocks release" in Rule findings, and the header gains "Blocks release 1".
6. Goes to `#release`: the "Blocks release" line fails; Sign stays disabled ("<n> required checks failing").
### Variations
- Overturn to Fix: item stays "Needs review" with "Fix · Kenny Geiler · …".
### Edge Cases
- The same item may appear twice (its own Rule findings row and the To confirm row); deciding either settles the key. Redundant surfaces for one decision.
- Saving the overturn with the pre-filled reason untouched records the agent's words under Kenny's name.

## STORY-007: Revisit a settled SEC XBRL difference and change the decision
**Type**: medium
**Topic**: reconcile-decisions
**Persona**: Kenny, after an analyst asks why AMZN Equipment FY2024 shows $218.9B against SEC XBRL $53.5B
**Goal**: Look at the evidence for the settled row and record Explain with a clear reason
**Preconditions**: row is settled (Unverified, explained by a definition), hidden by default
**Ideal path**: 5 — Show settled, filter, open, Explain + reason, Save
**Alternate paths**: Dataset grid cell (≠ mark) → provenance → no decide control there, so the user must come to Reconcile; Company trail `#proof/AMZN` "Review in Reconcile →" (`#reconcile?scope=AMZN`, still needs Show settled)
### Steps
1. On `#reconcile`, toggles **Show 6 settled** -> URL gains `resolved=1`; new card **Differs from SEC XBRL** "0 to review of 5".
2. Chooses Cause "Differs from SEC XBRL" -> `#reconcile?cause=fact_differs&resolved=1`.
3. AMZN "Equipment FY2024" row: Dataset $218,893,000,000, SEC XBRL $53,509,000,000, red gap bar, Difference "+$165.4B" / "+309%", Decision "Unverified" (no by-line: settled by a definition, not a person).
4. Opens it -> "FY2024 · Cited vs SEC XBRL" table (Cited "“Equipment”", SEC XBRL "Property plant and equipment gross · Equipment · 2024-12-31" with "Restated in a later 10-K", "In v1.8.0" Last release, Difference), a large gap bar, **Source** card (Value 218,893 · Line Equipment · Column December 31, 2024), crop thumbnail with "Open"/"sec.gov ↗", "Company trail", and "By year" (FY2021–FY2023 "Unverified · citation only", FY2024 "Differs from SEC XBRL").
5. Clicks the crop -> lightbox shows the 10-K cell; "Open in filing" opens `/filing/0001018724-25-000004` in a new tab with the cell outlined. Kenny sees Amazon's "Equipment" line is gross servers + networking while the XBRL member is narrower.
6. Back on Reconcile, Decision card shows no header text (no person decision); Accept is pre-pressed. Clicks **Explain**, types "AMZN Equipment includes servers and networking; EquipmentMember tag is narrower", **Save** -> "Saved."
7. Row stays visible (resolved=1); Decision cell now "Unverified" + "Explain · Kenny Geiler · Nov 4".
### Variations
- Same check from Dataset grid: provenance shows the decision badge (Explained) but offers no write; Reconcile is the only write surface.
### Edge Cases
- Gap bar, Difference column, the evidence table and the large gap bar all repeat the same Cited-vs-XBRL number four ways on one screen.
- The save posts the hash the page loaded; if a run changed the item meanwhile, `/api/resolve` does not refuse (no Stale check on resolutions), the line is written against the old hash and the row silently stays open after reload.

## STORY-008: Read-only visitor tries to decide
**Type**: short
**Topic**: reconcile-decisions
**Persona**: an Arctal analyst on the hosted copy (`LEDGER_READONLY=1`)
**Goal**: See whether they can mark APLD opex FY2026 as accepted
**Preconditions**: hosted copy; header shows "Read-only" in place of Signer
**Ideal path**: 1 — the form should be absent or disabled with a reason
**Alternate paths**: none found (no read-only branch in reconcile.js)
### Steps
1. Opens `#reconcile?resolved=1`, opens APLD opex FY2026 -> "Large year-over-year change" table (Prior year $83,985,000, This year $394,144,000, "+$310.2M 4.7×"), "opex by year", Details "opex moves 4.69× from FY2025 …", "Open in Dataset".
2. The Decision form renders fully; picks Accept, types "looks right", **Save** -> "Couldn't save: this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository. Try again."
### Edge Cases
- "Try again." invites a retry that can never succeed.
- Keyboard `a e f b` and Select all / Save for n render and fail the same way.

## STORY-009: Wrong signer name
**Type**: short
**Topic**: reconcile-decisions
**Persona**: a colleague at Kenny's machine who types their own name in Signer
**Goal**: Accept one finding
**Preconditions**: local copy; Signer changed to "Dana Ruiz" (not on `config.PEOPLE`)
**Ideal path**: 1 — Save should be disabled with "Enter a signer name"-style guidance
**Alternate paths**: none found
### Steps
1. Types "Dana Ruiz" in **Signer** (saved to localStorage).
2. Opens a GOOGL segment_revenue row, Accept, reason, **Save** -> "Couldn't save: 'Dana Ruiz' is not on config.PEOPLE, the people whose resolutions count as a person's; a run writes author_kind run. Try again."
### Edge Cases
- Empty Signer: Save is enabled; error "a resolution needs a state (accept, explain, fix, blocks), a reason and a name". Approve, Make this a rule and Sign disable instead — inconsistent gating.
- The Signer persists in localStorage, so Kenny's next session also fails until he retypes his name.

## STORY-010: Clear the whole Rule findings queue before signing v1.9.0
**Type**: long
**Topic**: reconcile-decisions
**Persona**: Kenny, end of the week, wants a signable v1.9.0
**Goal**: Leave zero "Needs review" items so the Release "Needs review" line passes
**Preconditions**: 16 open rule findings (APLD 9, GOOGL 7); Signer "Kenny Geiler"
**Ideal path**: ~12 — two filtered bulk saves (GOOGL segment revenue, APLD segment capex) plus per-item decisions for the three "Readings differ" / ppe items with distinct reasons
**Alternate paths**: Release "Fix in" Reconcile; Proof row "<n> to review" → trail → "Review in Reconcile →" per company; keyboard-only (STORY-002); one big Select all 16 with a generic reason (fast, poor audit trail)
### Steps
1. On `#release` sees "v1.9.0 · Compared with v1.8.0 · …" with "Needs review" failing (16); clicks "Fix in" Reconcile -> `#reconcile`.
2. Header "Needs review 16"; Rule findings "16 to review of 16". Decides to work by company.
3. Scope "Alphabet (GOOGL)", Field "Segment revenue" -> 6 rows; opens two to sample; **Select all 6**; Explain; "segments include hedging gains reported outside segments"; **Save for 6**.
4. Field "Every field" -> remaining GOOGL row "ppe_category FY2023" ($35,136M gap). Opens it; Details only, no numbers in Dataset/SEC XBRL columns.
5. Clicks "Open in Dataset" -> `#data?view=grid&t=GOOGL&f=ppe_category,capex`; looks at the FY2023 category cells; Back.
6. Back on Reconcile the filters survive in the URL; row collapsed again. Opens it, `f`, "categories include CIP twice; re-read note 7", Enter -> stays open as Fix.
7. Scope "Applied Digital (APLD)" -> 9 rows. Field "Segment capex" -> 6 rows (FY2023 ×2, FY2024 ×2, FY2025, FY2026).
8. Opens FY2026 and FY2025: gaps $124.2M and similar against PaymentsToAcquireProductiveAssets. Kenny decides the segment table includes financed equipment.
9. **Select all 6**, Explain, "segment capex includes financed equipment not in cash capex", **Save for 6**.
10. Field "Segment revenue" -> 1 row FY2026; opens, Accept, reason, Save.
11. Field "PP&E by category" -> 2 rows "Readings differ across filings" FY2025 and FY2024; each opens with the orange "Restated: …" line and "Compare filings".
12. Uses "Compare filings" for FY2024 (9,552 → 1,760): crops agree the later 10-K reclassified. Back; Explain "later 10-K reclassification; dataset uses later reading"; Save.
13. FY2025 (2,126 → 12,447): same reason; Save.
14. Clears Field and Scope to All companies -> header "Needs review 1" (the GOOGL Fix row). Fix keeps it open by design.
15. Kenny realises Fix will keep the release red; options: re-run extraction from the CLI (not in the UI), or change the decision. Leaves it.
16. Goes to `#release` via navbar -> "Needs review" still fails (1), "Proposed" fails (29 mappings, separate topic), "Golden test" fails; Sign stays disabled.
### Variations
- Do it all with "Grouped by company" -> trips STORY-004's mapping-row bulk failure.
- Use the Proof board instead of Release to start: row "APLD 9 to review" → `#proof/APLD` → "Review in Reconcile →" → `#reconcile?scope=APLD`.
### Edge Cases
- The open-count lives on four surfaces (Reconcile header, Release "Needs review" line, Proof "<n> to review" column, trail summary "<k> to review") — redundant but consistent only after a reload of each page.
- Fix has no way to close from the UI: the item stays "Needs review" until a re-read; the tooltip "Wrong; stays open until re-read" is the only hint, so a release blocked by Fix needs CLI work.
- Each single save reloads the whole page and resets expansion; with filters in the URL the context survives, but scroll position and focus move to the first row.
- Filter selects show only causes/fields/kinds present in the loaded rows; after the last GOOGL segment_revenue row is settled, reloading `field=segment_revenue` still filters but the select falls back to its first option, hiding the active filter.

## STORY-011: Filter by check type to review year-over-year jumps
**Type**: short
**Topic**: reconcile-decisions
**Persona**: Kenny, checking whether any large jump is still unexplained
**Goal**: See every "Large year-over-year change" item including settled ones
**Preconditions**: `#reconcile`
**Ideal path**: 2 — pick Check, toggle Show settled
**Alternate paths**: Rules page "To review" list (read-only); typing `#reconcile?kind=jump&resolved=1`
### Steps
1. Check select (shown because kinds exist) -> choose "Large year-over-year change" -> `#reconcile?kind=jump`; "No items to review".
2. Kenny is unsure whether that means none exist; toggles **Show 6 settled** -> `#reconcile?kind=jump&resolved=1`; one row: APLD opex FY2026, "Unverified", Difference "+$310.2M" "+369%".
3. Opens it: Details "opex moves 4.69× …", table "Prior year / This year / Difference 4.7×", "opex by year" with FY2026 "Unverified · definition". Satisfied, no decision.
### Edge Cases
- The other kind in the Check select is shown raw as "other" (tie and readings-differ findings carry `kind: other`), so it does not match the card's cause labels ("Does not tie to reported total", "Readings differ across filings").
- "Show 6 settled" counts settled rows across all filters, not within the current filter.
