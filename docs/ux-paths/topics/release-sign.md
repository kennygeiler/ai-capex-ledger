# Release checklist and signing — UX path stories

Topic: release-sign. Sources: `ledger/web/pages/release.js`, `ledger/release/checklist.py` (`checklist`, `sign`,
`golden_line`, `tests_line`, `claims_lines`, `folder_state`, `next_version`), `ledger/web/app.py` (`/api/v1/release/checklist`,
`/api/release/sign`, `/packet/<v>.zip`, `outputs()`), `ledger/web/pages/proof.js` (Releases table), `_shared.js` (`me`,
`table`, `dtable`, `api`), `_router.js` (read-only label). Live state read 2026-11-04 by GET only: `v1.9.0 · Compared with
v1.8.0 · 6 companies · 12 of 15 required checks pass`, red lines Proposed (29), Needs review (16: GOOGL 7, APLD 9), Golden
test (gold unverified 1 of 120); packet fingerprint `5c50eaf3`; releases v0.1.0–v1.8.0 on disk, v1.2.0 unsigned.

Code facts the stories lean on:
- The Sign button's state and the status text are computed once at render from `cl.ok` and the `me` variable. The Signer box's
  `input` listener only updates `me` and localStorage; nothing re-renders the Release page.
- `sign()` refuses an empty name ("a signature needs a name") but does **not** check `config.PEOPLE`, unlike every other write.
- "Fix in" links are page-level only (`#proof`, `#reconcile`, `#reconcile?cause=asset_types`, `#data…`, `#gaps`, `#release`);
  a line's detail table may carry a `link` column, rendered as plain text, not a link.
- Proof's Releases table shows the 6 newest releases; "Download" only when signed **and** README.md exists; `/packet/<v>.zip`
  itself only needs SIGNOFF.json.

---

## STORY-001: Why can't I sign v1.9.0 today?
**Type**: short
**Topic**: release-sign
**Persona**: Kenny Geiler, owner/signer, at the local checkout
**Goal**: Find out in one glance whether v1.9.0 is signable and what is stopping it
**Preconditions**: Local copy, Signer "Kenny Geiler"; checklist red on Proposed, Needs review, Golden test
**Ideal path**: 2 — open Release, read the header count and the disabled button's status line
**Alternate paths**: Proof → Releases card note "Next release" → `#release`; Docs flow diagram box "Release" → `#release`; read `/api/v1/release/checklist` (`red` array) directly; CLI `ledger release` prints `checklist_table`
### Steps
1. Click the navbar tab **Release** -> Page header "Release", subtitle "**v1.9.0** · Compared with v1.8.0 · 6 companies · **12 of 15** required checks pass".
2. Look at the right of the header -> Button **Sign v1.9.0** is greyed out; under it "3 required checks failing"; hovering the button shows the same words as a tooltip.
3. Scan the checklist table (sorted fail first by the State column's sort key, though the table opens in server order) -> Three red "Fail" rows: "Proposed" 29, "Needs review" 16, "Golden test" 1. Kenny thinks: "two of these are Reconcile work, the golden one is the last APLD hand-check item."
### Variations
- Kenny clicks the **State** header to sort; fails go first (fail 0, stale 1, not run 2, info 3, pass 4).
- If only the Test run line were "Stale", the count would still say "1 required check failing" with no hint it is a re-run, not a data fix; he has to read Details ("stale (HEAD is …): run `ledger test`").
### Edge Cases
- The status text never names which lines fail; the user has to scan the table. The JSON `red` array (`gate_G6, open, golden`) is not shown.
- Redundancy: the same three numbers appear on Proof (company rows "<n> to review", Hand check "119 of 120"), Reconcile header (Needs review / Proposed counts) and here.

## STORY-002: Clear the Golden test line from its Fix in link
**Type**: medium
**Topic**: release-sign
**Persona**: Kenny, signer
**Goal**: Turn "Golden test" green by grading the one unchecked APLD gold item
**Preconditions**: Golden test Fail, note "tables equal; gold unverified 1 of 120: give the verdicts on Proof; 2026-11-03T21:12:16+00:00"
**Ideal path**: 5 — Fix in lands directly on the APLD hand-check group, one verdict, back to Release (plus the out-of-band `ledger test`)
**Alternate paths**: Proof header "Hand check: <state>" link scrolls to `#gold`; navbar Proof then scroll; brand "Kenny's Data Emporium" → `#proof`
### Steps
1. On `#release`, click the "Golden test" row -> Row expands; detail table shows "No items" (detail is empty when only gold is unverified). Kenny hesitates: "which item?"
2. Read the Details cell (truncated at ~26rem; hover shows the full note) -> "gold unverified 1 of 120: give the verdicts on Proof".
3. Click **Proof** in the "Fix in" column -> Navigates to `#proof` top (not `#gold`); the row does not toggle (click stops propagation).
4. Click the header link "Hand check: …" -> Page scrolls to the Hand check card.
5. Scan the company picker -> "APLD 19/20"; click it -> APLD items table opens.
6. Find the one item with status "Unchecked", open its crop thumbnail -> Lightbox with the cell; Kenny checks the value against the filing.
7. Click **Right** -> Status becomes "Right · Kenny Geiler · <date>"; picker shows "APLD 20/20".
8. Click navbar **Release** -> Golden test still "Fail": the line reads `reports/golden.json`, written by `ledger test`/the golden run, not live gold files. Kenny is confused.
9. In a terminal run the golden/test command, then reload `#release` -> Golden test "Pass"; "13 of 15 required checks pass".
### Variations
- Kenny marks **Wrong** instead: must fill "Note (required for Wrong / Can't say)"; after the rerun the line note becomes "gold FAILS, 1 verdicts" and stays red.
- Proof's own "Regression test" collapsible (Hand check state) shows the same gold state as the Release line.
### Edge Cases
- Broken flow: Fix in → `#proof` lands at the top of a long page; the gold section has its own anchor that the link does not use.
- No UI tells the user the line only refreshes after a CLI run; the note's timestamp is the only clue.
- If `reports/golden.json` is missing, the line reads "not run", count 1, Fail.

## STORY-003: Work down the 29 Proposed asset-type mappings
**Type**: long
**Topic**: release-sign
**Persona**: Kenny, signer and reviewer
**Goal**: Clear the "Proposed" line (G6) by approving or correcting Claude's asset-type proposals for all six companies
**Preconditions**: Proposed Fail, 29; detail rows like `asset_types|AMD|Construction in progress` · to confirm · "ConstructionInProgressMember proposed by Claude Fable 5.1" · `reconcile?scope=AMD&cause=asset_types`
**Ideal path**: ~33 — open the list once, then one decision per mapping (29) plus navigation; bulk is not allowed for mappings by design
**Alternate paths**: Reconcile navbar tab → Cause "Category mapping"; Proof → company trail → Category mapping stage "Decide in Reconcile →"; the "Release checks by company" G6 column shows per-ticker counts; Reconcile header "Proposed" count
### Steps
1. On `#release`, click the "Proposed" row -> Detail table with columns key · state · reason · link, 29 rows.
2. Kenny tries to click a `reconcile?scope=AMD&cause=asset_types` value -> Nothing happens; it is plain text. He copies the ticker mentally.
3. Click **Reconcile** in Fix in -> `#reconcile?cause=asset_types`; Category mapping card(s), all six tickers mixed.
4. Set Scope to "AMD" -> URL becomes `#reconcile?cause=asset_types&scope=AMD`; AMD's mappings only.
5. Expand "Construction in progress" -> Decision card: Proposed ConstructionInProgressMember, Source, Company's own tag, Basis, Alternatives.
6. Click **Approve** -> "Confirmed."; row settles.
7. Repeat steps 5–6 for each AMD row; on "Building and leasehold improvements" Kenny disagrees and clicks **Choose another**, picks from "Standard category", saves -> "Mapped."
8. Switch Scope to MSFT -> six rows ("Buildings and improvements", "Computer equipment and software", "Furniture and equipment", "Land", "Leasehold improvements", "Servers, network equipment…"). Approve each.
9. Repeat for GOOGL, AMZN, NVDA, APLD (~29 decisions in all).
10. One Approve returns 409 "Changed since loaded. Reloading." -> page reloads; Kenny re-finds his place.
11. Click navbar **Release** -> "Proposed" now Pass, 0; "Release checks by company" G6 column shows "·" for every ticker, all "Pass".
### Variations
- Use Group by "Grouped by company" instead of Scope to walk all tickers on one page.
- Start from the "Release checks by company" table: click ticker "AMD" -> `#proof/AMD` trail, Category mapping stage → "Decide in Reconcile →".
- Keyboard: j/k to move, Enter to expand; a/e/f/b do not apply to mapping rows.
### Edge Cases
- "Select all <n>" never includes mappings, so 29 single clicks is the floor.
- Rejecting a mapping (**Reject**) moves it to Unmapped, which then counts under "Needs review" (note "…asset types with no entry (Reconcile, asset types)"): one red line turns into another.
- Redundancy: G6 count appears in the Proposed line, its detail, the by-company gate table, the Reconcile header "Proposed", and Proof board cells.
- If a run's to-confirm decisions also exist, the Fix in link becomes plain `#reconcile` (both causes) instead of `cause=asset_types`.

## STORY-004: Clear "Needs review" for GOOGL and APLD
**Type**: medium
**Topic**: release-sign
**Persona**: Kenny, reviewer
**Goal**: Decide the 16 open items (GOOGL 7, APLD 9) so the line passes
**Preconditions**: Needs review Fail 16, detail rows `ticker GOOGL · open 7`, `APLD · open 9`
**Ideal path**: 6 — Fix in scoped to the ticker, select all, one reason, Save for n, repeat for second ticker, back
**Alternate paths**: Proof board row → trail "Review in Reconcile →"; trail header "Reconcile" link (`#reconcile?scope=T`); Reconcile tab + Scope filter; "Release checks by company" ticker link → trail
### Steps
1. Expand "Needs review" -> detail: GOOGL 7, APLD 9.
2. Click **Reconcile** -> `#reconcile` with every company and cause (69 rows live), not scoped to GOOGL/APLD. Kenny sighs.
3. Set Scope "GOOGL" -> 7 open rows (e.g. "Differs from SEC XBRL" capex rows).
4. Expand the first, read SEC XBRL vs Dataset and the Gap bar -> decides it is a definition difference.
5. Select the rows that share the reason (space / checkboxes) -> "<n> selected" card.
6. Type reason "Google reports purchases of property and equipment net of …" and click **Save for <n>** -> "Saved.".
7. For the odd ones, use **Fix** (stays open until re-read) or **Explain** individually.
8. Set Scope "APLD" and repeat for 9 items; Kenny uses **Block release** on one he cannot settle.
9. Back on **Release** -> "Needs review" Pass but "Blocks release" Fail 1 (detail `APLD · blocked 1`).
### Variations
- Kenny uses keyboard: j/k, `a` then type reason, Enter.
- After an Accept, "Saved. Apply to every company?" offers **Make this a rule** — writing a rule clears the item on the next run, not now.
### Edge Cases
- Fix keeps the item "Needs review" until a re-read; the Release line stays red despite a saved decision.
- Detail counts are by ticker only; no link per ticker even though Reconcile supports `scope=`.

## STORY-005: Sign and publish v1.9.0 (happy path)
**Type**: short
**Topic**: release-sign
**Persona**: Kenny, signer
**Goal**: Sign and publish once every required line is green
**Preconditions**: All 15 required lines Pass; Signer "Kenny Geiler"; Postgres reachable
**Ideal path**: 3 — open Release, click Sign, confirm
**Alternate paths**: CLI signoff/publish commands (no UI); no other page has a Sign control
### Steps
1. Open **Release** -> "15 of 15 required checks pass"; status "Signs and publishes v1.9.0"; button **Sign v1.9.0** enabled.
2. Glance at "Packet v1.9.0" card (File · Rows · Bytes, note "Fingerprint 5c50eaf3") and "Changes since v1.8.0" (taxonomy.csv 164 changed, values.csv +10 …) -> Kenny sanity-checks the diff.
3. Click **Sign v1.9.0** -> Browser dialog "Sign and publish v1.9.0 as Kenny Geiler?"
4. Click OK -> Button disables; status "Signing v1.9.0…".
5. Wait -> green "v1.9.0 signed by Kenny Geiler · <time> · 5c50eaf3 · Published: <n> values, …"; after 2.5 s the page moves to `#proof`.
6. On Proof, Releases card -> top row "v1.9.0 · Kenny Geiler, <date> · 81 values · To review at signing 0 · Unmapped at signing 0 · 6: MSFT, GOOGL, AMZN, NVDA, APLD, AMD · Download".
### Variations
- Kenny clicks Cancel in the confirm dialog -> nothing happens, button stays enabled.
### Edge Cases
- Data changed between checklist and sign -> red "the data changed while the checklist was built; reload and sign again"; button re-enabled but the page is stale — he must reload.
- A required line turns red during the write -> "v1.9.0 not signed: … is red on the checklist"; releases/v1.9.0/ stays on disk unsigned and becomes the next version to sign.
- Two quick clicks: server lock serializes; the button is disabled after the first.
- The 2.5 s redirect gives little time to read or copy the hash; the same hash is not shown on Proof (only the Release page's "Fingerprint").

## STORY-006: Signed, not published — and what now?
**Type**: medium
**Topic**: release-sign
**Persona**: Kenny, signer
**Goal**: Understand and recover from a publish failure after signing
**Preconditions**: All required lines green; Postgres down
**Ideal path**: 4 — sign, read the error, retry publish from the page, verify on Proof (today the retry has no UI)
**Alternate paths**: CLI `ledger publish` (the only retry); Proof Releases "Signed" cell shows " · not published"
### Steps
1. Click **Sign v1.9.0**, OK -> "Signing v1.9.0…".
2. Result -> green "v1.9.0 signed by Kenny Geiler · <time> · 5c50eaf3" then red "Signed, not published: <psycopg error>". Page stays (no redirect).
3. Kenny looks for a Retry/Publish button -> none; button re-enable logic does not run on success, it stays disabled.
4. Reload `#release` -> The page now shows the **next** version (v1.10.0, minor bump), compared with v1.9.0; nothing on Release mentions the unpublished v1.9.0.
5. Go to **Proof** → Releases -> "v1.9.0 · Kenny Geiler, <date> · not published" (red) with **Download**.
6. In a terminal, run `ledger publish` once Postgres is back -> SIGNOFF.json records published true; Proof drops the red marker.
### Variations
- Kenny downloads the packet anyway from Proof's **Download** — it works because packet only needs SIGNOFF.json.
### Edge Cases
- Broken flow: recovery is CLI-only and the Release page forgets the state after reload; only Proof's red " · not published" remains.
- Releases v1.1.0–v1.7.0 have `published` null (signed before it was recorded) and show no marker either way — indistinguishable from published.
- A `record_error` (SIGNOFF note failed to land) is returned in the JSON but never displayed.

## STORY-007: Signer box empty or changed while on the Release page
**Type**: short
**Topic**: release-sign
**Persona**: Kenny on a shared laptop where a colleague cleared the Signer box
**Goal**: Get the Sign button enabled
**Preconditions**: Every required line green; the Signer box was cleared on another page in this tab (an empty stored value falls back to "Kenny Geiler" on a page load, so the empty state only exists in memory)
**Ideal path**: 2 — type name, click Sign (should enable live)
**Alternate paths**: none found (the Signer box in the header is the only place to set the name)
### Steps
1. Click navbar **Release** with the Signer box empty -> Button disabled, status "Enter a signer name".
2. Type "Kenny Geiler" in **Signer** -> Button stays disabled; status unchanged (the page computed it at render).
3. Click navbar **Release** again -> Nothing happens (same hash, no hashchange).
4. Go to Proof and back, or reload (a reload also restores "Kenny Geiler" by default) -> Button enabled, "Signs and publishes v1.9.0".
### Variations
- Reverse: page rendered enabled, then Kenny clears the Signer box -> button stays enabled; clicking shows "Sign and publish v1.9.0 as ?" and the server answers 400 "a signature needs a name", shown red; button re-enabled.
### Edge Cases
- Broken flow: unlike Reconcile/Proof write buttons, which read `me` at click, the Release button's disabled state is frozen at render.
- Signer "Pat Lee" (not in `config.PEOPLE`) can sign: `sign()` only refuses an empty name, so SIGNOFF.json records any name typed — inconsistent with every other write (400 for names off PEOPLE).

## STORY-008: Download a release packet for an analyst
**Type**: short
**Topic**: release-sign
**Persona**: A data consumer (or Kenny sending a packet to Arctal)
**Goal**: Get the v1.8.0 packet zip
**Preconditions**: v1.8.0 signed and published
**Ideal path**: 2 — open Proof Releases, click Download
**Alternate paths**: direct URL `/packet/v1.8.0.zip`; per-list CSV via Dataset **CSV** links or `/api/v1/<list>.csv` (current data, not the frozen release)
### Steps
1. Click navbar **Proof**, scroll to **Releases** -> table of the 6 newest: v1.8.0, v1.7.0, v1.6.0, v1.5.0, v1.4.0, v1.3.0.
2. Click **Download** on v1.8.0 -> Browser saves `capex-ledger-v1.8.0.zip` (~93 KB) holding `capex-ledger-v1.8.0/` values.csv, taxonomy.csv, DIFF.md, LIMITATIONS.md, README.md, manifest.json, SIGNOFF.json…
### Variations
- Visitor first opens **Release** expecting downloads -> only the unsigned next version's "Packet v1.9.0" file list; no download link there. They must go to Proof.
### Edge Cases
- Older releases (v1.2.0 and earlier) are not in the table (slice of 6); v1.0.0 has no README so even in the table it would show no Download, yet `/packet/v1.0.0.zip` serves it.
- v1.2.0 is unsigned: `/packet/v1.2.0.zip` → 404 `{"error": "not found"}` (raw JSON in the tab).
- Read-only hosted copy: download works (GET).
- Redundancy: the packet's file list appears twice on Release (expanded "Packet v1.9.0" line detail and the "Packet v1.9.0" card).

## STORY-009: Read an old release's checklist via ?version=
**Type**: short
**Topic**: release-sign
**Persona**: Kenny auditing what v1.8.0's signature meant
**Goal**: See the checklist for a past version
**Preconditions**: v1.8.0 signed
**Ideal path**: 2 — from Proof's Releases row to that release's checklist at signing
**Alternate paths**: Proof Releases columns "To review at signing", "Unmapped at signing", "Companies" (summary of SIGNOFF.json's checklist); SIGNOFF.json inside the packet zip
### Steps
1. Type `#release?version=v1.8.0` in the address bar (no UI link exists) -> Page "v1.8.0 · Compared with v1.7.0 …" built from **today's** data, not as signed.
2. "Packet v1.8.0" line -> Fail, "v1.8.0 is already signed; a shipped release is never edited. Use a new version." Button **Sign v1.8.0** disabled.
3. Kenny realizes this is a re-computation; he goes to Proof → Releases to read the at-signing counts (0 · 0 · 6 companies).
### Variations
- `#release?version=v2` -> page error "not a version: 'v2' (vMAJOR.MINOR.PATCH)".
- `#release?version=v1.2.0` (unsigned, older than a signed release) -> checklist runs; Packet line compares folder hash ("…built before this release's checks; delete and rebuild" if different).
### Edge Cases
- The query param is undocumented in the UI and the page title gives no "as signed" vs "now" cue; easy to misread as historical.

## STORY-010: Read-only visitor presses Sign
**Type**: short
**Topic**: release-sign
**Persona**: An outside reviewer on the hosted copy (`LEDGER_READONLY=1`)
**Goal**: See whether the release would pass, and (curious) try Sign
**Preconditions**: Hosted copy; header shows "Read-only"; suppose every required line is green there
**Ideal path**: 1 — open Release; a read-only copy should show no Sign button
**Alternate paths**: none found
### Steps
1. Open **Release** -> checklist renders; "Test run" line reads Info "commit not compared: no git; …" (hosted copy ships no .git) — which is not required-pass, so Sign stays disabled ("1 required check failing").
2. If it were enabled (the `me` variable still holds "Kenny Geiler" from the default even though the Signer box was replaced by "Read-only"), clicking → confirm "…as Kenny Geiler?" → red "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository".
### Edge Cases
- The button renders on a read-only copy at all; the status text never says "Read-only".
- On the hosted copy the Test run line can never pass, so the read-only Release page always looks "not signable" — a visitor may read that as a data problem.

## STORY-011: Full pre-release pass from Proof to published
**Type**: long
**Topic**: release-sign
**Persona**: Kenny on release day, wanting v1.9.0 out before sending the dataset to Arctal
**Goal**: Go from "3 required checks failing" to a published v1.9.0 and a packet in hand
**Preconditions**: Live state (Proposed 29, Needs review 16, gold 1 unchecked)
**Ideal path**: ~45 — 29 mapping decisions + ~4 grouped review saves + 1 gold verdict + test rerun + sign/confirm + download
**Alternate paths**: Start at Reconcile instead of Release; start at Proof board rows; per-company via trails; CLI `ledger release` to read the checklist as text
### Steps
1. Proof -> header "0 of 6 proven"; every company "<n> to review". Kenny clicks "Next release" in the Releases card note -> `#release`.
2. Read "12 of 15 required checks pass", button disabled "3 required checks failing".
3. Expand "Release checks by company" view (no expansion needed: G1/G4/G5 "·", G6 counts per ticker, Result Fail for each with proposals).
4. Fix in **Reconcile** on "Proposed" -> do STORY-003 (≈29 Approve/Choose another clicks).
5. Back to Release (navbar) -> Proposed Pass; "13 of 15".
6. Fix in **Reconcile** on "Needs review" -> scope GOOGL then APLD, bulk Accept/Explain with reasons (STORY-004).
7. Back to Release -> Needs review Pass; check "Blocks release" still Pass and "Answer-key values missing from the dataset" still 0 (an Accept that blanks a value could trip it).
8. Fix in **Proof** on "Golden test" -> header "Hand check" link -> APLD -> **Right** on the last item.
9. Terminal: rerun tests/golden -> reload Release: Golden test Pass, Test run Pass (fresh commit, clean tree — if he committed the gold verdict; a dirty tree makes Test run "Stale").
10. Review info lines: "Rows with no value 118" (Fix in **Dataset** → `#data?list=taxonomy&has_value=false`), "Rows changed since v1.8.0 174", "Limitations with no mitigation 2" (Fix in **Release** — links to itself), "Known gaps: 0 stub · 3 stale · 37 open findings" (Fix in **Known gaps**).
11. Check "Claims register" and "Claims doc current" Pass; if Claims doc fails he runs `ledger claims` and commits, then reruns tests (commit moves HEAD → Test run stale).
12. Click **Sign v1.9.0** → OK -> "Signing…" → signed · Published → redirect to Proof.
13. Proof → Releases → v1.9.0 **Download** -> zip saved for Arctal.
### Variations
- He works from Reconcile's own header counts and never visits Release until the end; same result, fewer back-and-forths but no single "what's left" view outside Release.
### Edge Cases
- Ordering trap: committing the gold verdict or claims doc after the test run makes "Test run" Stale; tests must be the last step before Sign.
- "Fix in" for Limitations and Previous releases points to Release itself — a dead end.
- Redundancy: "Known gaps" line duplicates the Known gaps page header counts; "Rows changed" line detail duplicates the "Changes since v1.8.0" card.
