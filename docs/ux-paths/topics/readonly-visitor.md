# Hosted read-only visitor (LEDGER_READONLY=1)

Stories for someone on the hosted copy (claim `hosted_copy`, `https://datahq-production.up.railway.app`), where the server
was started with `LEDGER_READONLY=1`. Written from code (`ledger/web/app.py` `READONLY`, `Handler.do_POST`, `_hq`;
`pages/_router.js` scope line; `pages/_shared.js` `me`; write handlers in `proof.js`, `reconcile.js`, `release.js`,
`explore.js`) plus read-only GETs against the local copy on 2026-11-04 (which runs `readonly: false`, so read-only
behaviour below is traced through the code, not observed).

Behaviour that every story relies on:

- `GET /api/hq` returns `readonly: true`. When it resolves, `_router.js` replaces the header span "Signer [input]" with a
  plain azure "Read-only" and appends " · Read-only" to the scope line ("<n> companies · Data as of <date> · Read-only").
  Until that request resolves the Signer box is visible; if it fails (`.catch(() => {})`) the Signer box stays and no
  label appears.
- The `me` variable is set before the box is removed: `localStorage.datahq-me` or the default "Kenny Geiler". So on the
  read-only copy `me` is always non-empty, every `needsMe` / gold / Sign button is **enabled**, and tooltips read as if
  the action will work ("Approve this category", "Signs and publishes v1.9.0"). Nothing on a page disables or hides a
  write control in read-only mode.
- Every POST is refused first, before the Content-Type, Origin and `by` guards, with 403
  `{"error": "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository"}`.
  Below this is written READONLY_MSG.
- Every GET still works: all pages, `/api/v1/<list>` and `.csv`, `/packet/<v>.zip`, `/filing/<accession>`,
  `/evidence/crops/<f>.png`, `/docs/<NAME>.md`, `/api/v1/views/<id>/data`.

---

## STORY-001: Recognise that this copy is read-only
**Type**: short
**Topic**: readonly-visitor
**Persona**: Priya, a data journalist sent the hosted link by Kenny; first visit, never seen the local app
**Goal**: Know, before trying anything, whether she can change anything here
**Preconditions**: Hosted copy, `LEDGER_READONLY=1`; empty localStorage; `/api/hq` healthy
**Ideal path**: 1 — a read-only marker visible on landing, next to where a writer's controls would be, answers it without a click
**Alternate paths**: the scope line under the nav ("· Read-only"); the header span "Read-only" that replaces Signer; Known gaps claim row "Hosted copy" (status Out of date) for what the hosted copy is; Docs (no page found that explains the hosted copy to a visitor)
### Steps
1. Opens the hosted URL -> `#proof` loads ("Loading…" then the Proof board: "Proof", "0 of 6 proven", company table MSFT, GOOGL, AMZN, NVDA, APLD, AMD, each "<n> to review"). For a beat the header shows "Signer [Kenny Geiler]" because `/api/hq` has not returned yet.
2. `/api/hq` resolves -> the Signer box is swapped for a small azure "Read-only"; a line appears under the nav: "6 companies · Data as of <date> · Read-only". Priya glances at it; "Read-only" is small, at the far right of the dark navbar, after the "Ticker or company…" box.
3. Scrolls the Proof board to Hand check -> sees per-item **Right / Wrong / Can't say** buttons, enabled, with a note box. She hesitates: "it said read-only, but these look clickable."
### Variations
- Arrives on a deep link (`#reconcile?scope=NVDA`, `#explore/capex-by-group`) instead of the root: the same header swap and scope line happen on every route, because they run once from `_router.js` regardless of page.
- Has visited before on the same origin and once typed a name: irrelevant, the Signer box is gone either way; the stored name still becomes `me`.
### Edge Cases
- `/api/hq` errors or times out: the `.catch` is silent, so the Signer box stays (pre-filled "Kenny Geiler") and no "Read-only" appears anywhere; the visitor has no signal until a write is refused.
- Same "read-only" fact appears in two places (header span, scope line) and nowhere near the write controls themselves (Proof hand check, Reconcile decision form, Release Sign, Explore Save) — redundant at the top, absent where it matters.
- The flash of the Signer box before `/api/hq` resolves briefly suggests the opposite.

## STORY-002: Try to grade a hand-check item and get refused
**Type**: short
**Topic**: readonly-visitor
**Persona**: Priya (as above), curious whether she can mark something as wrong
**Goal**: Record a Wrong verdict on an AMZN gold item she disagrees with
**Preconditions**: Hosted read-only copy; Proof page; AMZN 20/20 checked
**Ideal path**: 0 — on a read-only copy the verdict controls should not be offered (or be visibly disabled with the reason), so there is no path
**Alternate paths**: none found (gold verdicts are only on Proof's Hand check; `POST /api/gold/verdict` has no other UI)
### Steps
1. Clicks "Hand check: <state>" in the Proof header -> page scrolls to `#gold`: "20 items per company · random sample · Unchecked never passes", company picker buttons "MSFT 20/20 … APLD 19/20".
2. Clicks "AMZN 20/20" -> table Item · Value · Source · Check, hard groups first (No SEC counterpart, Definition differs …), each item with crop thumbnail, "Open", "sec.gov ↗", value "In millions · $…", verdict status "Right · Kenny Geiler · <date>".
3. Clicks **Wrong** with the note empty -> inline red "Note required"; focus moves to the note box. No request sent (client check first).
4. Types "Capex here looks like it includes finance leases" in "Note (required for Wrong / Can't say)" and clicks **Wrong** -> all three buttons disable briefly, POST goes out, 403; the status line under the buttons turns red with READONLY_MSG; buttons re-enable; the verdict stays "Right · Kenny Geiler · <date>". Priya: "so why did it let me type a note?"
### Variations
- **Can't say** follows the same path (note required, then 403). **Right** skips the note check and goes straight to the 403.
- On APLD's one unchecked item, the status stays "Unchecked" after the refusal.
### Edge Cases
- READONLY_MSG names "decisions, views and prompts" but not verdicts; she has to infer it covers gold too.
- Her note text stays in the box after the refusal; nothing tells her it is not saved anywhere.
- The button tooltip says the verdict's help text (GOLD_HELP), not "read-only".

## STORY-003: Download the latest signed release packet
**Type**: short
**Topic**: readonly-visitor
**Persona**: Marcus, an analyst at a fund evaluating the dataset; wants the files, not the UI
**Goal**: Get the newest signed release as a zip
**Preconditions**: Hosted read-only copy; releases through v1.8.0 signed with packets; v1.9.0 unsigned
**Ideal path**: 2 — open the page that lists releases, click the newest packet download
**Alternate paths**: direct URL `/packet/v1.8.0.zip`; Release page (`#release`) shows "Packet v1.9.0" contents for the *unsigned* next version (File, Rows, Bytes, "Fingerprint <hash8>") but has no download link; Dataset Rows **CSV** / **JSON** per list as a substitute
### Steps
1. Lands on Proof (default route), scrolls to "Releases" -> table Version, Signed, Values, To review at signing, Unmapped at signing, Companies, Packet; newest six rows, latest first; v1.8.0 "Signed … · Kenny Geiler", Packet "Download".
2. Clicks "Download" on v1.8.0 -> browser saves `capex-ledger-v1.8.0.zip` (`Content-Disposition: attachment`); no read-only interference, it is a GET.
### Variations
- Wants an older one (v1.3.0): visible because the table shows the last six; v1.1.0 and earlier are cut off by `.slice(0, 6)` — only reachable by typing `/packet/v1.1.0.zip`.
- Clicks "Next release" under the table -> `#release`, sees v1.9.0's checklist and packet table, no download.
### Edge Cases
- Releases v0.1.0–v1.0.1 and v1.2.0 have `packet: false`: empty Packet cell, no explanation.
- A typed version without a packet returns an error JSON in the browser tab rather than a page.
- Packet contents described on Release ("Packet v1.9.0") and downloadable on Proof ("Releases") — two surfaces for one concept, split by signed/unsigned.

## STORY-004: Export NVDA's capex rows as CSV
**Type**: medium
**Topic**: readonly-visitor
**Persona**: Marcus (as above), building his own model in a spreadsheet
**Goal**: A CSV of NVDA statement figures, then a grid export across buyers
**Preconditions**: Hosted read-only copy
**Ideal path**: 3 — jump to NVDA, pick the list, click CSV
**Alternate paths**: Dataset Rows **CSV** link (server `/api/v1/<list>.csv?ticker=NVDA`); Dataset Grid **Export CSV** (client-side Blob, `capex-ledger-<field>.csv`); Explore "CSV" link next to the chart (`/api/v1/<measure>?…&format=csv`); Explore saved view data `/api/v1/views/<id>/data?format=csv` (no UI link found); Packet zip on Proof
### Steps
1. Types "NVDA" in "Ticker or company…" and presses Enter -> `#data?ticker=NVDA`; Dataset tab active; Rows view, "All rows" list, Company select "NVIDIA".
2. Clicks "Values" in the list sidebar -> `#data?list=values&ticker=NVDA`; "<n> rows of <m>"; columns sortable.
3. Types "capex" in "Find in rows" -> rows filter after 150 ms; count updates. Marcus wonders whether the CSV respects the search box.
4. Clicks **CSV** -> downloads `/api/v1/values.csv?ticker=NVDA` — the server list filtered by ticker only; the in-page "Find in rows" text is **not** applied (search is client-side). He notices the CSV has more rows than the screen.
5. Clicks **JSON** -> new tab with `{"list": "values", "count": …, "filters": {"ticker": "NVDA"}, "rows": [...]}`.
6. Switches to **Grid** -> `#data?view=grid…`; Field select "Capex", Companies group "Buyers", Kind "Spent".
7. Clicks a cell (NVDA FY2025) -> provenance: sources, crop, "Open in 10-K ↗", decision badge (e.g. "Accepted") or "Not checked".
8. Clicks **Export CSV** -> client-side file `capex-ledger-capex.csv` with ticker, company, field, dimension, period, kind, value, check, basis, source_url, provenance.
### Variations
- Uses Companies "Custom…" -> drawer with checkboxes (MSFT, GOOGL, AMZN, NVDA), **Apply**; works on the read-only copy (pure client state in the URL).
- Uses Explore instead: Measure "Statement figures", Tickers "NVDA", then the "CSV" link beside the row count.
### Edge Cases
- Rows CSV ignores "Find in rows" while Grid Export CSV exports exactly what the grid shows: two export buttons, two meanings.
- Four routes to the same rows (Rows CSV, Grid Export CSV, Explore CSV, packet) — redundancy candidate.
- Nothing about read-only affects this story; exports are GETs or client blobs.

## STORY-005: Save an Explore chart as a view, then try to delete one
**Type**: medium
**Topic**: readonly-visitor
**Persona**: Dana, a strategy associate who wants to bookmark a chart for her team
**Goal**: Keep "Capex by layer" filtered to hyperscalers so she can come back to it
**Preconditions**: Hosted read-only copy; 4 saved views (Capex by layer, by year; Technology equipment, gross balance by company; What companies state about AI, in dollars; Committed: purchase obligations and finance leases)
**Ideal path**: 2 — set the chart, copy the URL (every control writes to the hash); a "Save as view" that cannot work should not be offered here
**Alternate paths**: copy the `#explore?<state>` URL from the address bar (works, linkable); open an existing saved view `#explore/<id>` or legacy `#views/<id>`; JSON/CSV links capture the data but not the chart
### Steps
1. Clicks the "Explore" tab -> left list "4 saved views" + "New"; Plotly chart.
2. Clicks "Capex by layer, by year" -> `#explore/capex-by-group`; stacked bars by fiscal_year × layer; buttons **Save changes** and **Delete**.
3. Types "MSFT,GOOGL,AMZN" in Tickers -> chart redraws; URL hash updates.
4. Clicks **Save changes** -> drawer: "Save changes", Name "Capex by layer, by year", Note prefilled.
5. Edits Name to "Hyperscaler capex by layer" and clicks **Save** -> POST `/api/v1/views`, 403; the drawer's message line turns red with READONLY_MSG ("…decisions, views and prompts change in a checkout…"). Drawer stays open. Dana closes it (Close or Escape).
6. Copies the browser URL instead and pastes it to her team -> the hash carries tickers, measure and chart, so the link reproduces the chart for anyone.
7. Out of curiosity clicks **Delete** -> label becomes "Confirm delete".
8. Clicks "Confirm delete" -> POST 403; **nothing visible happens** (no try/catch: unhandled promise rejection); after ~5 s the label reverts to "Delete". Dana: "did it delete it or not?" Reloads; the view is still there.
### Variations
- From a fresh `#explore` (no view): button reads **Save as view**; same 403 in the drawer.
- On a local copy the same Save/Delete are refused for a different reason (missing `Content-Type`, 403 "a write needs Content-Type: application/json"); on the hosted copy the read-only guard runs first and masks that defect.
### Edge Cases
- Delete gives zero feedback on refusal — broken flow (also broken locally).
- Name/Note typed into the drawer are lost on close.
- The "save" need is fully met by the URL hash, so Save as view duplicates linkability for a visitor.

## STORY-006: Try to accept an NVDA "Differs from SEC XBRL" item in Reconcile
**Type**: medium
**Topic**: readonly-visitor
**Persona**: Leo, a sell-side analyst who covers NVDA and thinks a flagged gap is fine
**Goal**: Mark NVDA's capex difference as Explained with his reason
**Preconditions**: Hosted read-only copy; Reconcile live with ~69 rows; an NVDA row under "Differs from SEC XBRL"
**Ideal path**: 0 — a visitor cannot decide; the form should be read-only or absent. To *read* the item: 3 (Reconcile, scope NVDA, expand)
**Alternate paths**: Company trail `#proof/NVDA` → stage card → "Review in Reconcile →" / "Reconcile" link; keyboard e on a focused row; Proof board row click → trail → Reconcile
### Steps
1. Clicks "Reconcile" -> header counts (Needs review / Blocks release / Proposed / Unverified), "Last run …", "Keyboard" hint.
2. Sets Scope to "NVDA" -> `#reconcile?scope=NVDA`; cards by cause.
3. Clicks the NVDA capex row under "Differs from SEC XBRL" -> evidence expands: aligned tables (This year, By year …), "Company trail", "Open in Dataset", "Open in EDGAR ↗", and the decision form **Accept / Explain / Fix / Block release**, Reason input, **Save**.
4. Clicks **Explain** -> button active (tooltip "Right, with the reason kept").
5. Clicks **Save** with no reason -> "Reason required"; focus to Reason.
6. Types "Includes intangibles purchases; XBRL tag is PP&E only" and presses Enter -> "Saving…", then red "Couldn’t save: this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository. Try again." Leo clicks Save again; same message.
7. Clicks "Open in EDGAR ↗" -> sec.gov in a new tab; reading still works.
### Variations
- Keyboard: focuses the row, presses `e` -> row expands with Explain pre-selected and focus in Reason; same 403 on Enter.
- Selects several rows (checkbox or space) -> "<n> selected: …" card, "Why, for all <n>…", **Save for <n>** -> same 403 text from `/api/resolve/bulk`.
- A Proposed row: **Confirm Explain** -> "Saving…" then "Couldn’t save: …(READONLY_MSG)." ; **Overturn** just opens the form (no request).
### Edge Cases
- "Try again." is appended to a permanent refusal — misleading; Leo retries.
- "Saved. Apply to every company?" and **Make this a rule / Make this a definition** are unreachable on the read-only copy (they appear only after a successful save).
- Writes are attributed to `me` = "Kenny Geiler" even though the visitor never typed a name; if the read-only guard were ever off, a visitor's click would land under Kenny's name (related finding F18).

## STORY-007: Try to approve a category mapping for AMD
**Type**: short
**Topic**: readonly-visitor
**Persona**: Leo (as above)
**Goal**: Approve the proposed standard category for an AMD reported asset line
**Preconditions**: Hosted read-only copy; Reconcile "Category mapping" card has AMD rows to confirm
**Ideal path**: 0 — not a visitor action
**Alternate paths**: Company trail `#proof/AMD` → Category mapping stage card → "Decide in Reconcile →" / "Confirm or override in Reconcile →"; Release checklist "Proposed" row → "Fix in" Reconcile (`reconcile?cause=asset_types`)
### Steps
1. Opens `#reconcile?cause=asset_types&scope=AMD` (or Cause "Category mapping") -> mapping rows with **Approve** / **Reject** / **Choose another**.
2. Clicks **Approve** -> button disables, "Saving…", then red "Couldn’t save: READONLY_MSG." Button re-enables (still titled "Approve this category").
3. Expands the row, picks a different "Standard category" and clicks **Choose another** -> same refusal. Clicks **Reject** -> same.
### Variations
- A row with no proposal shows **Map** instead of Approve; same refusal.
### Edge Cases
- The 409 "Changed since loaded. Reloading." path can never fire here; the read-only 403 comes first.
- The refusal text says "decisions, views and prompts", not mappings.

## STORY-008: Check whether v1.9.0 can be signed, and what blocks it
**Type**: medium
**Topic**: readonly-visitor
**Persona**: Marcus, wants to know if a new release is imminent before he builds on v1.8.0
**Goal**: Understand v1.9.0's status and the blocking checks
**Preconditions**: Hosted read-only copy; v1.9.0 vs v1.8.0; required lines failing: Proposed, Needs review, Golden test
**Ideal path**: 2 — open Release, read the failing required lines
**Alternate paths**: Proof "Releases" table note "Next release" → `#release`; Proof header "<k> of 6 proven" and each company's "<n> to review"; Known gaps "Release" claims; checklist via `GET /api/v1/release/checklist` (no UI link)
### Steps
1. Clicks "Release" -> "Release", "v1.9.0 · Compared with v1.8.0 · 6 companies · <k of m> required checks pass".
2. Reads the **Sign v1.9.0** button -> disabled; status "3 required checks failing" (title the same). Read-only plays no part: it is disabled because checks fail.
3. Reads the checklist -> Fail rows: "Proposed", "Needs review", "Golden test" (note "gold unverified 1 of 120: give the verdicts on Proof"); Pass rows G1, G4, G5, Blocks release, Test run, Packet v1.9.0; Info rows "Rows with no value", "Rows changed since v1.8.0", "Known gaps: 0 stub · 3 stale · 37 open findings".
4. Clicks the "Golden test" row -> detail table expands.
5. Clicks its "Fix in" link (Proof) -> `#proof`; Hand check shows "APLD 19/20". Marcus realises the fix is a grader's job he cannot do here (STORY-002).
6. Back; clicks "Fix in" on "Proposed" -> `#reconcile?cause=asset_types`; the mapping rows (STORY-007).
7. Scrolls Release to "Changes since v1.8.0" -> List, Rows, Added, Removed, Changed, Columns.
### Variations
- `#release?version=v1.8.0` -> the signed release's checklist; Sign button reads "Sign v1.8.0", disabled or not depending on lines.
### Edge Cases
- If every required line passed on the hosted copy, Sign would be **enabled** with title "Signs and publishes v1.9.0"; clicking shows `confirm("Sign and publish v1.9.0 as Kenny Geiler?")` — a visitor asked to sign as Kenny — then red READONLY_MSG. Broken-flow risk.
- Hosted copy may lag the checkout (findings F6 "not redeployed since v1.8.0", F19), so the checklist a visitor reads may not be the one Kenny signs.
- "To review" counts appear on Proof (per company), Reconcile header, trail summary and Release lines — same numbers, four surfaces.

## STORY-009: Verify one AMZN figure all the way to the filing
**Type**: long
**Topic**: readonly-visitor
**Persona**: Priya, fact-checking a "$83B capex" claim before publishing
**Goal**: Confirm AMZN's latest capex value, see the exact 10-K cell, and keep the evidence
**Preconditions**: Hosted read-only copy; AMZN in scope; crops located for the cited cell
**Ideal path**: 4 — jump to AMZN, open trail, open the capex item's crop, Open in filing
**Alternate paths**: Proof board row → trail; jump box → Dataset → ticker cell → trail; Dataset Grid cell provenance → "Open in 10-K ↗"; Hand check item crop (if sampled); Reconcile expanded row → "Company trail" / "Open in EDGAR ↗"; Explore click bar → rows → trail; `#evidence/<id>` from a trail item; sec.gov links
### Steps
1. Types "Amazon" in "Ticker or company…" -> datalist offers "Amazon.com"; picks it -> `#data?ticker=AMZN` (the jump box goes to Dataset, not the trail).
2. Hesitates: she wanted "the proof". Clicks the AMZN ticker cell in a row -> `#proof/AMZN` (Company trail).
3. Reads the summary card -> "Before release", "As of …"; Coverage "Through 10-K · FY ending …", "Filed …", "SEC checked <h>h ago" or "out of date"; Verification tiles (Figures, Match SEC XBRL, Tie to totals …); Last release "Signed … · Kenny Geiler".
4. Scrolls to the Statement figures stage card -> "<n> items · <k> to review"; open items first, the rest under a tally ("12 verified · 3 corroborated …").
5. Expands the tally, finds Capex FY2024 -> Value $…; Verification "Verified" with reason.
6. Clicks the crop thumbnail -> lightbox with the cropped cell, caption, "Open in filing", "sec.gov ↗". Escape closes.
7. Clicks "Open" on the item -> new tab `/filing/<accession>`: the stored 10-K with the cell outlined (strict CSP; GET, unaffected by read-only).
8. Back on the trail, opens the row's detail (Enter) -> `details.why`; if restated, "Restated" line + "Compare filings".
9. Clicks "Compare filings" -> `#evidence/compare?a=…&b=…`: "Filing A · 10-K filed …" vs "Filing B …", "Readings agree" / "Readings differ".
10. Clicks "sec.gov ↗" -> EDGAR in a new tab.
11. Wants to keep it: right-clicks the crop image and saves it (`/evidence/crops/<f>.png`); copies the `#proof/AMZN` URL into her notes.
12. Clicks "Reconcile" in the trail header -> `#reconcile?scope=AMZN`; sees any open AMZN items, does not touch the decision form after STORY-006.
13. Clicks "Dataset" -> `#data?ticker=AMZN`; switches to **Grid**, Field Capex -> the same FY2024 cell with ✓ mark; clicks it -> provenance with "Open in 10-K ↗" (same filing link as step 7).
14. Clicks **Export CSV** -> keeps the numbers alongside the screenshot.
### Variations
- Crop state "Crop out of date" / "Cell not located" / "Crop file missing": no lightbox; she falls back to "sec.gov ↗"; `/evidence/crops/<f>.png` returns 404 JSON.
- Filing viewer refusals: 409 "the stored copy of this filing differs from its fingerprint" or 410 "…missing" as raw JSON in the new tab.
### Edge Cases
- The same value + filing link shows on trail, Dataset Grid provenance, Evidence page, Reconcile evidence and Hand check — five surfaces for "where did this number come from".
- The jump box lands on Dataset while the "proof" lives on the trail; one extra hop for a fact-checker.
- Hosted copy's "Data as of" may trail the local run (F6); the scope-line date is the only hint.

## STORY-010: A day on the hosted copy: evaluate the whole dataset before licensing it
**Type**: long
**Topic**: readonly-visitor
**Persona**: Sam, head of data at a buyer, assessing trustworthiness; skeptical, reads everything, clicks every button "to see"
**Goal**: Decide whether the dataset is trustworthy enough to license, leaving with files and a list of caveats
**Preconditions**: Hosted read-only copy; fresh browser; v1.8.0 latest signed; v1.9.0 unsigned
**Ideal path**: 8 — Proof board, one trail, Rules scores, Known gaps, Release, Docs Known limitations, packet download, done
**Alternate paths**: Docs "How it works" flow diagram boxes jump to Proof / Rules / Reconcile / Release / Dataset; Release "Fix in" links into each page; `/docs/<NAME>.md` plain text; read API `/api/v1/...`
### Steps
1. Opens the hosted root -> Proof; notices "· Read-only" in the scope line and "Read-only" top right.
2. Reads "0 of 6 proven" and each row's "<n> to review" -> frowns; hovers a stage cell for the breakdown (checked · done · explained · open).
3. Reads the Legend and "Verification source" table (SEC XBRL, Other company document, Ties to total, Later actual …, "All").
4. Opens Failure types card -> pareto charts and the Type · Cause class · Origin · Check · Companies seen table.
5. Opens "Regression test" -> Steps Pass/Fail, Differences.
6. Scrolls to Hand check -> "x right · y wrong · z can't say · n unchecked · error rate a% (95% CI …)" per group; picks "MSFT 20/20"; reads a few items.
7. Clicks **Right** on one item "to see" -> red READONLY_MSG under it. Notes: "buttons live, refused after the fact."
8. Clicks the MSFT row in the board -> `#proof/MSFT` trail; opens one crop and "Open" in filing (STORY-009 path).
9. Clicks "Rules" -> "Agents · <n>" cards: Model, Prompt version, Charter + "Full charter", Score (SEC XBRL match "x of y · p% (95% CI …)", Planted errors "Caught x of y · Missed z"); "Runs per company"; "Prompt and model history". No write controls here (good for a visitor).
10. Reads the "Rules" table (Kind, Rule, Description, Severity, Hits, Failure type) and "To review · <n>".
11. Clicks "Reconcile" -> reads counts and cards; expands a GOOGL row to see the evidence tables; types a test reason, clicks **Save** -> "Couldn’t save: … Try again." Ignores the form from now on.
12. Clicks "Dataset" -> Rows; sidebar Values, Facts, Statements, Projects, Companies; downloads **CSV** for Values (all companies).
13. Switches to **Grid**, Companies "Sellers", Field "Capex" -> marks ✓ ○ ≠; counts how many ≠ (Differs from SEC XBRL).
14. Clicks "Explore" -> opens "What companies state about AI, in dollars"; drags to zoom, double-clicks to reset; opens the "Data" disclosure; clicks a bar -> its rows; clicks a ticker -> trail.
15. Clicks **Save changes** to tweak the title -> drawer, **Save** -> red READONLY_MSG in the drawer; closes it.
16. Clicks "Release" -> v1.9.0 not signable, "3 required checks failing"; reads Fail lines (Proposed, Needs review, Golden test) and "Release checks by company" (G1/G4/G5/G6 Pass/Fail).
17. Clicks "Known gaps" -> counts "Holds / Partial / Not built / Out of date / Planned", "<n> open issues"; finds claim "Hosted copy" with status "Out of date"; in Open issues reads F6 "The hosted copy has not been redeployed since v1.8.0." and F3 "About 11 page tests fail when the app runs as the read-only copy."
18. Pauses: the copy he is looking at is admittedly stale. Rechecks the scope line "Data as of <date>".
19. Clicks "Docs" -> sidebar: How it works (flow boxes), Operating guide, Glossary, Map, States, Rules and checks, Evaluation, Known limitations, Handoff. Reads "Evaluation" and "Known limitations".
20. Clicks the "Release" box in the How it works diagram -> `#release` (same page as step 16).
21. Returns to Proof -> Releases -> **Download** v1.8.0 packet.
22. Writes his caveat list: staleness (F6), 0 of 6 proven, 1 unchecked gold item, Proposed mappings outstanding.
### Variations
- Reads docs as plain text in a new tab via the footer "Source: docs/<file>.md" link -> `/docs/<NAME>.md`.
- Uses the read API directly (`/api/v1/values?ticker=MSFT`, `/api/v1/proof`) instead of the pages.
### Edge Cases
- Three refusals in one session (steps 7, 11, 15), each in a different style: plain red text (gold), "Couldn’t save: … Try again." (Reconcile), drawer message (Explore); Delete would add a silent one.
- Staleness of the hosted copy is only discoverable on Known gaps; nothing on Proof or the scope line says "this copy is behind".
- Trust signals repeat across Proof board, trail summary, Rules scores, Release checklist and Known gaps — high redundancy, but each phrased differently ("to review", "Needs review", "open").
- Docs explain the owner's workflow; no page addresses a visitor's "what can I do here".

## STORY-011: Look up an unknown ticker from the jump box
**Type**: short
**Topic**: readonly-visitor
**Persona**: Dana, wants Oracle, assumes it is covered
**Goal**: See ORCL's capex
**Preconditions**: Hosted read-only copy; ORCL not in scope
**Ideal path**: 2 — type ticker, learn it is not covered
**Alternate paths**: Dataset Company select ("Every company" + in-scope list); Proof board (only the 6 proven); Dataset Companies list
### Steps
1. Types "ORCL" in "Ticker or company…" (no datalist match) and presses Enter -> matches `/^[A-Z.\-]{1,6}$/`, navigates to `#data?ticker=ORCL`.
2. Sees "No rows." (or "0 rows of <m>") -> unsure whether ORCL is missing or filtered; checks Dataset "Companies" list to confirm it is not there.
### Variations
- Types "Oracle" (a name, not on the list, longer than 6 letters) -> nothing happens at all; the box keeps the text.
- `#proof/ORCL` typed by hand -> trail header with "Not in scope".
### Edge Cases
- No "not covered" message on Dataset; the trail says "Not in scope" but the jump box never goes there.

## STORY-012: Read-only copy where the health request fails
**Type**: short
**Topic**: readonly-visitor
**Persona**: Leo on a slow hotel connection
**Goal**: Browse, unaware the copy is read-only
**Preconditions**: Hosted read-only copy; `/api/hq` fails or is very slow
**Ideal path**: 1 — the read-only state should come with the page shell (server-rendered), not depend on a second request
**Alternate paths**: none found (`/api/hq` is the only source of `readonly` in the UI)
### Steps
1. Opens `#proof` -> page renders from `/api/v1/proof`; `/api/hq` errors; the header keeps "Signer [Kenny Geiler]"; no scope line.
2. Edits the Signer box to "Leo" thinking it identifies him -> stored to `localStorage.datahq-me`; buttons stay enabled.
3. Clicks **Right** on a hand-check item -> red READONLY_MSG. The first sign the copy is read-only.
### Variations
- `/api/hq` succeeds late: the Signer box vanishes mid-session under his cursor and is replaced with "Read-only".
### Edge Cases
- `.catch(() => {})` swallows the error; no scope line ("<n> companies · Data as of …") either.
- The "Leo" he typed persists in this origin's localStorage and is used as `by` on every refused request.
