# Company trail and evidence drill-down

Topic: `company-trail-evidence`. Written 2026-11-04 from `ledger/web/pages/trail.js`, `pages/evidence.js`, `pages/_shared.js`
(`citeCell`, `cropBox`, `calcBlock`, `restatedLine`, `mappingDecision`), `ledger/web/viewer.py` and `app.py`
(`/filing/`, `/evidence/crops/`, `/api/v1/evidence/`, `/api/v1/proof/<T>`), checked against read-only GETs on :3610.

Live facts used below: all six proven companies show "<n> to review" (MSFT 6, GOOGL 11, AMZN 4, NVDA 2, APLD 17, AMD 5);
SEC check is stale everywhere (179 h → "7d ago · out of date"); every trail crop is in state located; MSFT has 10
restated Intelligent Cloud segment facts with a "Compare filings" pair; GOOGL has 7 open note figures (PP&E parts don't
tie, no crop); last release v1.8.0 for all six.

---

## STORY-001: Check where one MSFT capex figure came from
**Type**: short
**Topic**: company-trail-evidence
**Persona**: Analyst at a fund reading the ledger, wants to trust one number before quoting it
**Goal**: See the cited 10-K cell behind Microsoft's FY2026 capex figure
**Preconditions**: Local or hosted copy; MSFT trail loads; Statement figures stage has 15 items, 0 open
**Ideal path**: 3 — open trail, find the capex row, click the thumbnail; the crop is the proof
**Alternate paths**: Proof board row MSFT → trail; Dataset grid (`#data?view=grid`) capex cell → provenance drawer shows the same crop via `sources()`; Hand check (if the item was sampled) shows the same `citeCell`; Reconcile expand (only if the item is open) shows the crop; `#evidence/<extraction_id>` typed by hand shows it with the Extracted/Filing split
### Steps
1. Click **Proof** tab, then the **Microsoft MSFT** row -> `#proof/MSFT` loads: header "Microsoft MSFT", legend, "6 to review", links "Reconcile" and "Dataset"; summary card "Before release".
2. Scroll to the **Statement figures** card ("15 items · Complete") -> Because 15 > 12 and nothing is open, the table is collapsed under a summary line "15 verified". User hesitates: the card looks empty until they notice the grey summary.
3. Click the "15 verified" summary -> Table Item · Value · Source · Verification opens; rows like "Capex · FY2026", value `$…M`, Source shows a crop thumbnail with "10-K 2026-07-29 · Open · sec.gov ↗", Verification "Verified · Matches SEC XBRL: $…M".
4. Click the crop thumbnail -> Lightbox opens full-size crop, caption "Capex · FY2026 · <row> · <column> · <cell>", links "Open in filing" and "sec.gov ↗", close button focused.
5. Press Escape -> Lightbox closes, focus returns to the thumbnail.
### Variations
- Uses the jump box "Ticker or company…" and types MSFT -> lands on `#data?ticker=MSFT` (Dataset), not the trail; must click the ticker cell or use the trail link from there. Extra step.
- Arrives from Explore: click a bar → "Data" rows → Company link → `#proof/MSFT`.
- A figure computed from several cells (e.g. "Opex · FY2022") shows a calc block above several thumbnails, each with a role label ("Revenue", "Cost of revenue", "Operating income").
### Edge Cases
- The thumbnail is a folded canvas (`focusCell`): label column + boxed cell only. If the image can't be read by canvas, the whole crop shows contained.
- Crop not located/stale/missing: no thumbnail, instead the crop-state word ("Cell not located · <reason>", "Crop out of date", "Crop file missing", "No crop").
- Redundancy: the same crop+Open+sec.gov trio appears on trail, Hand check, Reconcile evidence row, Dataset grid drawer, and `#evidence/<id>`.

---

## STORY-002: Open the cited cell inside the stored filing
**Type**: short
**Topic**: company-trail-evidence
**Persona**: Skeptical reviewer who wants to see the number in context, not a crop
**Goal**: See NVDA's revenue cell outlined in the actual 10-K
**Preconditions**: NVDA trail; Statement figures "18 items · Complete"; stored filing present and fingerprint matches
**Ideal path**: 3 — trail, expand stage, click Open
**Alternate paths**: lightbox "Open in filing"; `#evidence/<id>` "Open in filing" button or clicking its crop image; Hand check row "Open"; Reconcile evidence row "Open"; Dataset grid drawer "Open"; "sec.gov ↗" (the SEC copy, with a text fragment `#:~:text=`, no outline)
### Steps
1. Go to `#proof/NVDA` -> Trail loads ("2 to review": the two Proposed category mappings).
2. Expand "18 verified" under **Statement figures** -> rows visible.
3. On "Revenue · FY2026" click **Open** (tooltip "Open in filing, the cell outlined") -> New tab `/filing/0001045810-26-000021?t=…&row=…&col=…&cell=…`.
4. Filing loads (multi-MB, may take a moment) -> fixed dark banner "Found on this page · Revenue · 2026 · 130,497"-style text; the cell outlined red, its row tinted yellow and scrolled to centre.
### Variations
- User clicks "sec.gov ↗" instead: lands on sec.gov with a text fragment highlight; no outline, depends on the browser supporting text fragments.
- From the lightbox "Open in filing": same tab target.
### Edge Cases
- Locator can't confirm the cell: banner turns red "Not found on this page", with " · Column ambiguous" or " · Page shows X · cited Y". The banner is the live find, not the crop state, so a "Cell located" crop can still show "Not found on this page" if the page shifted.
- Filing is sandboxed (strict CSP): links inside the 10-K do nothing; there is no way back to the app from the tab except closing it.

---

## STORY-003: Why does Intelligent Cloud FY2021 have two values? (Compare filings)
**Type**: medium
**Topic**: company-trail-evidence
**Persona**: Equity analyst who saw 60,080 in an old model and 59,728 in the ledger
**Goal**: Understand Microsoft's segment restatement and which reading the dataset uses
**Preconditions**: MSFT trail; Note figures "63 items · Complete" (27 verified · 31 corroborated · 5 unverified); 10 items carry a restatement
**Ideal path**: 4 — trail, expand Note figures, read the Restated line, click Compare filings
**Alternate paths**: Hand check item (if sampled) shows `restatedLine(…, true)` with its own "Compare filings" link; `#evidence/<A id>` single page shows the Restated line + "Compare filings"; Reconcile expand when a restatement is open; typing `#evidence/compare?a=…&b=…`
### Steps
1. Open `#proof/MSFT` -> Summary shows Verification tile "Figures 78 · Match SEC XBRL 42 · Tie to totals 31 · Citation only 5 · To review 6 · Quotes verified 25".
2. Scroll to **Note figures** -> collapsed "27 verified · 31 corroborated · 5 unverified" (63 > 12 items). User wonders whether restated figures are hidden in "verified".
3. Expand -> 63 rows; user scans for "Segment revenue · Intelligent Cloud · FY2021".
4. Read the row -> Value "$59,728M"; Source shows two crops side by side: the 10-K 2022-07-28 crop with orange mark "Superseded" and the 10-K 2023-07-27 crop; Verification "Verified · Matches SEC XBRL: $59,728M".
5. Below it, orange line "Restated: 60,080 (10-K 2022-07-28) → 59,728 (10-K 2023-07-27) · dataset uses 59,728 (10-K 2023-07-27)" and a link **Compare filings**.
6. Click **Compare filings** -> `#evidence/compare?a=0001564590-22-026876|…&b=0000950170-23-035122|…`; Proof tab stays highlighted.
7. Read header -> "Segment revenue · Intelligent Cloud MSFT", orange "Readings differ · Intelligent Cloud · 12 months to Jun 30, 2021", Restated line repeated.
8. Compare the two columns -> "Filing A · 10-K filed Jul 28, 2022" `$60,080M` "cited 60,080" with "Superseded" mark, vs "Filing B · 10-K filed Jul 27, 2023" `$59,728M`; each with "Cell located", crop, "Page shows 60,080 · cropped Nov 3, …", **Open in filing**, "sec.gov ↗".
9. Click **Open in filing** under Filing B -> new tab, banner "Found on this page", cell outlined.
10. Close tab, press browser Back -> returns to `#proof/MSFT`; the Note figures disclosure is collapsed again (page re-rendered), user has to re-expand.
### Variations
- FY2023 pair: "Restated: 87,907 (10-K 2023-07-27, 10-K 2024-07-30) → 72,944 (10-K 2025-07-30)" — a $15B swing (segment re-org), the compare page makes the re-org obvious.
- Readings agree: header shows green "Readings agree".
- Two readings that round to the same `usd()` print with `usdExact` so they never look identical.
### Edge Cases
- Compare page has no "Company trail" link (single evidence page does); only Back returns.
- Missing `a` or `b` in URL -> page error "Two readings are needed: #evidence/compare?a=<id>&b=<id>".
- One id unknown -> page error "no cited cell '<id>'" (whole page, no partial render).
- Redundancy: the Restated line appears in the trail Verification cell, the compare header, the single evidence header, and Hand check.

---

## STORY-004: Investigate why GOOGL has 7 open note figures
**Type**: medium
**Topic**: company-trail-evidence
**Persona**: Kenny (owner) preparing to clear GOOGL before signing v1.9.0
**Goal**: Understand the open Note figures items and get to the place to decide them
**Preconditions**: GOOGL trail "11 to review" (7 Note figures + 4 Category mapping)
**Ideal path**: 4 — trail, read the open row's reason, open the filing, jump to Reconcile scoped
**Alternate paths**: Proof board stage cell for GOOGL (hover breakdown) → row → trail; `#reconcile?scope=GOOGL` directly (header link "Reconcile", summary link "Review in Reconcile →"); Rules page "To review" list grouped by need; Release checklist "Fix in" → Reconcile
### Steps
1. From Proof click **Alphabet GOOGL** -> trail, header "11 to review"; summary "Before release", "Review in Reconcile →".
2. Read the Coverage tile -> "Through 10-K · FY ending 2025-12-31" (link to sec.gov), "Filed 2026-02-05", "Next 10-K expected ~2027-02-05", "SEC checked 7d ago · out of date" in warning colour. User hesitates: is "out of date" why things are open? (It isn't; it's the EDGAR freshness check.)
3. Scroll to **Note figures** "55 items · 7 to review" -> the 7 open rows show uncollapsed first; the other 48 sit under a tally summary.
4. Read row "PP&E by category · FY2023 · Parts vs total"-style item -> Value "—"; Source: no crop, a line "10-K 2025-02-05 · Open · sec.gov ↗"; Verification red "Needs review · Does not tie · gap $35,136M".
5. Click the Verification line (it is a `<details>` summary) -> detail "Parts $201,803M · total $166,667M (SEC XBRL) · 4 parts · tolerance ±$2.5M".
6. Click **Open** -> new tab `/filing/0001652044-25-000014` with no row/cell params: the whole 10-K, no banner, no outline. User must Cmd-F for the PP&E note themselves.
7. Close tab; click **Review in Reconcile →** -> `#reconcile?scope=GOOGL`, cards per cause, where the decision form (Accept / Explain / Fix / Block release) lives.
### Variations
- Uses header "Reconcile" link instead of the summary link: same URL. Two links to the same place within one screen.
- Uses header "Dataset" -> `#data?ticker=GOOGL`, Rows view filtered to GOOGL.
### Edge Cases
- Rule-finding rows have no cited cell, so "Open" opens the bare filing: a weak evidence step compared to figure rows.
- The trail is read-only: no decision controls here even for the owner; every fix is one hop away in Reconcile.

---

## STORY-005: Category mapping on the trail, decided elsewhere
**Type**: short
**Topic**: company-trail-evidence
**Persona**: Kenny checking AMD's 5 Proposed mappings
**Goal**: See what Claude proposed for each AMD asset category and get to the decision
**Preconditions**: AMD trail "5 to review", all in Category mapping (wait)
**Ideal path**: 3 — trail, read mapping card, click "Decide in Reconcile →"
**Alternate paths**: `#reconcile?scope=AMD&cause=asset_types` directly; Reconcile with Cause "Category mapping"; Proof board Category mapping cell
### Steps
1. Open `#proof/AMD` -> "5 to review", Category mapping card "5 items · 5 to review".
2. Read a decision card -> name + orange state label, datagrid Company line (latest value + period, "Open ↗", series), Proposed (label, member e.g. `BuildingAndBuildingImprovementsMember`, definition, "Source: …"), Company's own tag, Basis "“…”" with "Claude Fable 5.1 · <date>", Alternatives (expandable definitions), Affects.
3. Click **Decide in Reconcile →** -> `#reconcile?scope=AMD&cause=asset_types`, the same card with Approve / Reject / Choose another.
### Variations
- Items already settled by the company's own XBRL tag ("Matches company tag", e.g. GOOGL 5 of 9) sit under the tally summary with link "Confirm or override in Reconcile →".
- NVDA: 2 Proposed + 2 Matches company tag.
### Edge Cases
- Redundancy: the mapping decision card is rendered identically (`mappingDecision`) on trail and Reconcile; the trail copy has no actions.

---

## STORY-006: Full provenance audit of one company before a release
**Type**: long
**Topic**: company-trail-evidence
**Persona**: Outside auditor given the hosted read-only copy, asked to sample APLD (Applied Digital) evidence
**Goal**: Walk every stage for APLD, spot-check figures, quotes, guidance and restatements, and note what's still open
**Preconditions**: Hosted copy (`LEDGER_READONLY=1`, scope line ends "· Read-only"); APLD "17 to review" (9 Note figures, 8 Category mapping)
**Ideal path**: ~15 — one page holds everything; the cost is expanding collapsed stages and opening filings
**Alternate paths**: Dataset Rows filtered `#data?ticker=APLD` (values/facts/statements/projects lists with CSV/JSON); Release page "Packet" for the signed v1.8.0 files; Hand check APLD (20 sampled items with crops, 1 unchecked); API `/api/v1/proof/APLD`
### Steps
1. Open the hosted URL -> Proof board, scope line "<n> companies · Data as of … · Read-only".
2. Click **Applied Digital APLD** -> trail; header "17 to review"; legend dots Verified (SEC XBRL or the quoted source), Corroborated, Matches company tag (hover title), Done (hover), Unverified (citation only), Proposed, Needs review (open item), Blocks release.
3. Read summary -> Coverage "Through 10-K · FY ending 2026-05-31", "Filed 2026-07-29", "Next 10-K expected ~2027-07-29", "SEC checked 7d ago · out of date"; Verification Figures 87, Match SEC XBRL 65, Tie to totals 7, Confirmed in 2 filings 6, Citation only 7, To review 17, Quotes verified 129; Last release "v1.8.0", "Signed … · Kenny Geiler"; Changes since release counts + "Details".
4. Click **Details** under Changes since release -> list of "+ … / ~ … / − …" lines. Auditor notes which figures moved since v1.8.0.
5. Click the Coverage link "Through 10-K · FY ending 2026-05-31" -> sec.gov filing index in a new tab (the SEC copy, not the stored one).
6. **Filings** card "5 items · Complete" -> five rows "10-K · FY ending …", each "Done · Statements located"; Source "10-K filed … · Open · sec.gov ↗".
7. Click **Open** on the newest -> `/filing/0001144879-26-000048` whole filing, no banner (no cell asked). Close.
8. **Statement figures** "23 items · Complete" -> collapsed "21 verified · 2 unverified". Expand.
9. Find the 2 "Unverified" rows -> Verification "Unverified · <reason>"; click the line to read the long `details.why` text.
10. On a verified capex row, click the thumbnail -> lightbox; click **Open in filing** -> banner "Found on this page …". Close tab, Escape lightbox.
11. On a calculated row (6 in this stage), read the calc block -> formula line, arithmetic, cross-checks "matches"/"differs by"; if not holding, "Stored value $…".
12. **Note figures** "71 items · 9 to review" -> 9 open rows first.
13. Read each open row -> Verification "Needs review · …"; open the detail; some have no crop (7 citations without a crop) so Source is "10-K … · Open · sec.gov ↗".
14. Expand the tally "39 verified · 13 corroborated · 5 match company tag · 5 unverified".
15. Find a row with a Restated line (6 exist) -> click **Compare filings** -> `#evidence/compare?…` "Readings differ"; inspect both crops.
16. Back -> trail re-renders, collapsed again; re-expand Note figures.
17. **AI disclosures** "35 items · Complete" -> rows are quotes (value column wraps the quote in “…”); "Verified · Quote matches source" or "Unverified"; Source line "Earnings release · <date> · Open ↗" (sec.gov text fragment).
18. Click a quote's **Open ↗** -> sec.gov with the quote highlighted by text fragment.
19. **Category mapping** "16 items · 8 to review" -> 8 decision cards with "Decide in Reconcile →"; 8 more under the tally with "Confirm or override in Reconcile →".
20. Click **Decide in Reconcile →** -> `#reconcile?scope=APLD&cause=asset_types`; on the read-only copy any Approve click would return 403 inline. Auditor only reads. Back.
21. **Guidance and projects** "109 items · Complete" -> collapsed tally (>12); expand to a long list "Guidance · revenue guidance · FY2024" / "Project · <name> · …", each a verbatim quote, "Source · Open ↗".
22. **Release** "1 item · Complete" card -> "Release gate", "Done · No blocking items".
23. Auditor records: 9 open note figures + 8 Proposed mappings = 17, matching the header.
### Variations
- Auditor uses the Dataset Rows view and CSV instead of trail for bulk checking, losing crops and verification words.
- Auditor downloads `/packet/v1.8.0.zip` from Proof "Releases" to compare against the trail's "Changes since release".
### Edge Cases
- Stage card count uses `plural(st.items, 'item')` so "1 item" singular on Release; "0 items · Complete" shows for an empty Guidance and projects card (MSFT).
- Very long stage (109 rows) has no search or filter on the trail.
- Redundancy: "17 to review" appears in header, summary "To review 17", stage tallies, Proof board last column and Reconcile counts.

---

## STORY-007: Jump straight to one cited cell by its id
**Type**: short
**Topic**: company-trail-evidence
**Persona**: Developer debugging a value reported via the API, holding an `extraction_id`
**Goal**: See the Extracted vs Filing view for one reading
**Preconditions**: Has id `0001564590-22-026876|segment_revenue|Intelligent Cloud|2021-06-30` (from `/api/v1/proof/MSFT` or a CSV)
**Ideal path**: 1 — paste `#evidence/<id>`; no UI link exists so this is also the only path
**Alternate paths**: none found in the UI — no page links to the single `#evidence/<id>` route (trail/gold/compare all link the compare form only); API `/api/v1/evidence/<id>` for JSON
### Steps
1. Paste `http://localhost:3610/#evidence/0001564590-22-026876%7Csegment_revenue%7CIntelligent%20Cloud%7C2021-06-30` -> Proof tab highlighted; title "Segment revenue · Intelligent Cloud MSFT", period "12 months to Jun 30, 2021", orange Restated line with **Compare filings**, link **Company trail**.
2. Read **Extracted** -> `$60,080,000,000`, Cited cell `60,080`, Row "Intelligent Cloud", Column "2021", Units "stated × 1,000,000", Period, Filing "10-K · 0001564590-22-026876 · filed Jul 28, 2022", Source "Notes to the financial statements".
3. Read **Filing** -> "Cell located", orange "Superseded", crop image, "Page shows 60,080 · cropped Nov 3, …", **Open in filing**, "sec.gov ↗".
4. Click **Company trail** -> `#proof/MSFT`.
### Variations
- Click the crop image itself -> same as Open in filing (new tab viewer).
### Edge Cases
- Unknown id -> page shows red error "no cited cell '<id>'".
- Broken flow: this richest single-reading view (exact dollar value, units, scale) is orphaned — reachable only by typed URL.

---

## STORY-008: Viewer refusals when the stored copy is wrong
**Type**: medium
**Topic**: company-trail-evidence
**Persona**: New operator after a partial `data/raw` restore on a fresh checkout
**Goal**: Open a cited cell and understand why the filing won't load
**Preconditions**: A filing file missing or edited on disk; or a hand-edited URL
**Ideal path**: 2 — click Open, read the refusal; recovery happens in the CLI
**Alternate paths**: "sec.gov ↗" next to every Open link (SEC copy, always available); lightbox crop (independent of the stored filing, served from `reports/evidence/crops`)
### Steps
1. On `#proof/AMZN`, expand Statement figures, click **Open** on a row -> new tab.
2. Stored file deleted -> tab shows raw JSON `{"error": "the stored copy of this filing is missing"}` (HTTP 410), no styling, no link back.
3. Operator tries another row whose file was re-downloaded but differs -> `{"error": "the stored copy of this filing differs from its fingerprint"}` (409).
4. Operator edits the URL to `/filing/abc` -> `{"error": "not a filing"}` (404); to a well-formed unknown accession `/filing/0000000000-00-000000` -> `{"error": "no stored filing with that accession"}` (404).
5. Falls back to **sec.gov ↗** on the trail row -> SEC's copy with text fragment.
6. Re-runs ingest from a checkout (CLI, outside the UI), reloads -> banner "Found on this page".
### Variations
- Crop PNG requested directly when its state isn't located (`/evidence/crops/<f>.png`) -> 404 `{"error": "not found"}`; in the UI that crop never shows as a thumbnail, only the state word.
### Edge Cases
- The trail gives no hint beforehand that a filing is missing/changed; crop state ("Cell located") is computed separately and can still say located.
- Refusals are JSON under a sandbox CSP: a non-technical reader sees a code blob, not a page.

---

## STORY-009: Odd tickers on the trail route
**Type**: short
**Topic**: company-trail-evidence
**Persona**: Curious visitor editing the URL, or someone following a Dataset link for an in-scope but unproven company
**Goal**: See the trail for Oracle, then for a typo
**Preconditions**: ORCL is in scope but not in the proven six; ZZZZ doesn't exist
**Ideal path**: 1 — type `#proof/ORCL`
**Alternate paths**: Dataset Rows ticker cell for ORCL → `#proof/ORCL`; Explore data table Company link; Reconcile "Company trail" link on an ORCL row
### Steps
1. Go to `#proof/ORCL` -> "Oracle ORCL", legend plus grey "Not in scope", "5 to review" (5 Proposed mappings); stages Filings 5, Statement figures 18, Note figures 55, AI disclosures 5, Category mapping 5, Guidance and projects 10; Last release "None".
2. Go to `#proof/ZZZZ` -> "ZZZZ ZZZZ", "Not in scope", but green **Proven**, summary "Ready for release", Coverage "No filings", "SEC checked 7d ago · out of date", every stage "0 items · Complete", Release "1 item · Complete".
### Variations
- Jump box with "ZZZZ" -> goes to `#data?ticker=ZZZZ` (empty rows), not the trail.
### Edge Cases
- Broken flow: an unknown ticker reads as "Proven" and "Ready for release" — the server returns `proven: true, open: 0` for nothing.
- Trail for an unproven company is complete and useful, but nothing on Proof links to it (Proof lists only the six).

---

## STORY-010: Compare a crop across every surface for one sampled item
**Type**: long
**Topic**: company-trail-evidence
**Persona**: Kenny auditing his own UI for consistency before showing it to Arctal
**Goal**: Confirm the same AMZN figure shows the same value, crop and verdict everywhere it appears
**Preconditions**: AMZN has 20 Hand check items; one sampled item is a capex figure also in Statement figures
**Ideal path**: n/a (consistency audit) — the redundancy is the subject
**Alternate paths**: every surface below is itself an alternate path to the same cited cell
### Steps
1. `#proof` -> scroll to **Hand check**, click **AMZN 20/20** -> table Item · Value · Source · Check.
2. Find the capex item -> value "In millions · $…", crop thumbnail, "Open" / "sec.gov ↗", verdict "Right · Kenny Geiler · <date>".
3. Click the thumbnail -> lightbox; note the caption; Escape.
4. Click **Amazon AMZN** row on the board -> `#proof/AMZN`.
5. Look at **Statement figures** "12 items · Complete" -> with 12 items and none open the table shows uncollapsed (no tally summary) -> find the same capex row.
6. Compare: value, crop, "Verified · Matches SEC XBRL" vs the gold "Right" (gold verdict doesn't appear on the trail).
7. Click header **Dataset** -> `#data?ticker=AMZN` Rows view.
8. Switch **Grid**, Field Capex, Companies including AMZN -> click the AMZN FY cell -> provenance shows "Capex: <cell> · Line “…” · Column “…”", "10-K filed …", same crop via `citeCell`, decision if any.
9. Go to `#reconcile?scope=AMZN` -> only if the capex item is open would it show; it isn't, so the item is absent unless "Show <n> settled" is switched on; switch it on and expand -> crop again, "Company trail" link.
10. Paste `#evidence/<extraction_id>` -> Extracted (exact dollars) vs Filing.
11. Click **Open in filing** from three surfaces -> each opens the identical `/filing/…?t=&row=&col=&cell=` URL.
### Variations
- Item drifted since sampling: Hand check shows red "Now $…" or "Removed from dataset", trail shows the new value only.
### Edge Cases
- Five surfaces render the same cell; only `#evidence/<id>` shows the exact dollar figure and scale; only Hand check shows the human verdict; only the trail shows verification ladder words. Candidate for consolidation: one evidence view linked from all.
- Stage tally thresholds differ: Statement figures collapse only when >12 items or something is open, so AMZN (12) shows open while MSFT (15) is collapsed — inconsistent first impression across companies.
