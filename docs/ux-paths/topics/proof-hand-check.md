# Proof overview and hand-check grading

Topic: `proof-hand-check`. Code read: `ledger/web/pages/proof.js` (proofPage, goldSet, verdict), `_shared.js` (citeCell, cropBox,
calcBlock, restatedLine, `me`), `_router.js`, `app.py` (`gold_view`, `/api/v1/golden`, `POST /api/gold/verdict`),
`ledger/review/gold.py` (`record`, `group_note`), `ledger/core/states.py` (GOLD, GOLD_GROUP), `ledger/release/checklist.py`
(`golden_line`). Live data 2026-11-04 (GET only): 0 of 6 proven (MSFT 6, GOOGL 11, AMZN 4, NVDA 2, APLD 17, AMD 5 to review);
hand check 119 of 120 checked, all Right; the one unchecked item is APLD Opex FY2026 (Definition differs).

Facts that shape every story:
- The header link "Hand check: 119 of 120 checked", the Regression test summary and the Release "Golden test" line all read
  `reports/golden.json`, a snapshot written only by the CLI (`ledger golden --check` / `ledger test`). The Hand check section
  itself reads `/api/v1/gold` live. A verdict given in the page updates the section, not the header or the Release line.
- The company picker selection lives only in memory: not in the hash, so not linkable, lost on reload, and Back does not restore it.
- A verdict redraws the whole Hand check section (`goldSet.draw(t)`): the clicked button is replaced (focus drops to body) and any
  unsaved note typed into another row is discarded.
- No row in the hand check links to the Company trail or to Reconcile; the only outbound links are the crop lightbox,
  "Open" (filing viewer, new tab), "sec.gov ↗" and, for a restated fact, "Compare filings".

---

## STORY-001: Check whether anything is proven yet
**Type**: short
**Topic**: proof-hand-check
**Persona**: Kenny, owner, opening the app on a Monday morning
**Goal**: Know in one glance how many proven companies are clean and what blocks them
**Preconditions**: Local checkout running on :3610; live state 0 of 6 proven
**Ideal path**: 1 — the landing page should answer "how many proven, what's left" without a click
**Alternate paths**: Navbar brand "Kenny's Data Emporium" → `#proof`; navbar tab "Proof"; any unknown hash (e.g. `#gold` typed into the address bar) falls back to Proof; Docs "How it works" flow box "Filings"/"Check" → `#proof`; Release checklist "Fix in: Proof"
### Steps
1. Open `http://localhost:3610/` -> Router defaults to `#proof`; "Loading…" then header "Proof", bold "0 of 6 proven"; right side "Tables unchanged · <date>" (grey) and orange link "Hand check: 119 of 120 checked".
2. Scan the company table -> Six rows (Microsoft MSFT, Alphabet GOOGL, Amazon AMZN, NVIDIA NVDA, Applied Digital APLD, AMD) with stage columns Filings · Statement figures · Note figures · AI disclosures · Category mapping · Guidance and projects · Release; last column orange "6 to review", "11 to review", "4 to review", "2 to review", "17 to review", "5 to review". Kenny thinks: "APLD is the long pole again."
3. Hover a red open count in APLD's Statement figures cell -> Tooltip names the open group; hovering the blue explained count shows "Citation only ×n · Restated in a later 10-K ×n…".
4. Read the legend under the table -> "● Checked · ● Done · ● Unverified · ● To review" in state colours.
### Variations
- NVDA at "2 to review" is closest to Proven; Kenny may jump straight there (STORY-004).
- When a company reaches zero open items its last cell turns green "Proven" and the header count rises.
### Edge Cases
- `/api/v1/proof` fails -> whole view replaced by a red `msg bad` line with the error text; no partial board.
- `reports/golden.json` missing -> "Tables: not compared" with tooltip "Nothing changed since the freeze; not a correctness check"; hand link reads "Hand check: not run".
- Redundancy: "<n> to review" per company appears here, on the Company trail header, and as per-company counts in Reconcile (`#reconcile?scope=T`) — three surfaces for one number.

## STORY-002: Grade the last unchecked APLD item (a calculated Opex that differs from SEC XBRL)
**Type**: medium
**Topic**: proof-hand-check
**Persona**: Kenny, owner/signer, finishing the hand check before trying to sign v1.9.0
**Goal**: Give a verdict on APLD's one unchecked gold item so the hand check reaches 120 of 120
**Preconditions**: Signer box holds "Kenny Geiler"; APLD shows 19/20; the open item is Opex · FY2026, group "Definition differs"
**Ideal path**: 4 — open Proof, pick APLD (or deep-link to it), inspect the item, click a verdict (+ note if not Right)
**Alternate paths**: Header link "Hand check: 119 of 120 checked" scrolls to `#gold`; scrolling down manually; Release checklist "Golden test" row "Fix in: Proof" (lands at top of Proof, then scroll or the Hand check link). CLI outside the UI (gold files) — not a UI route. No deep link to a company's hand check exists.
### Steps
1. On `#proof`, click "Hand check: 119 of 120 checked" -> Page scrolls to the Hand check section (link prevents the hash change). Heading "Hand check", "20 items per company · random sample · Unchecked never passes".
2. Read the group lines -> Bold headline "No SEC counterpart: 36 right · 0 wrong · 0 can't say · 0 unchecked · error rate 0.0% (95% CI 0.0–9.6%)", then "Definition differs: 0 right · 0 wrong · 0 can't say · 1 unchecked", "Calculated: 19 right…", "Matches SEC XBRL: 64 right…", "All: 119 right · … · 1 unchecked · error rate 0.0% (95% CI …)". Kenny notes the Definition differs line has no error rate — n is 0.
3. Look at the picker -> Buttons "AMD 20/20 · AMZN 20/20 · APLD 19/20 · GOOGL 20/20 · MSFT 20/20 · NVDA 20/20"; hovering APLD shows its rate line. Click "APLD" -> Button turns primary; card "APLD · 20 items" with APLD's rate on the right.
4. First group header row "No SEC counterpart" (six Right items), then "Definition differs · 0 right … 1 unchecked" -> The unchecked item sits second because items are ordered hard first. Kenny hesitates: he expected the unchecked one at the very top.
5. Read the Item cell -> "Opex · FY2026", "Statement figure · SEC XBRL $450,915,000".
6. Read the Value cell -> "$394,144,000" (no "In thousands" line, because a calculated figure is shown in dollars only). No "Now $…" line, so the dataset still holds this value.
7. Read the Source cell -> Calc block: "Calculated: revenue − cost of revenue − operating income = $394.1M", "$611.3M − ($56.8M + $396.9M) − (−$236.5M) = $394.1M", "Filing's own total: No total to compare", red "SEC XBRL: $450.9M · differs by $56.8M · Data center rental and other cost of revenue line". Four crops labelled Revenue, Cost of revenue, Cost of revenue, Operating income.
8. Click the "Cost of revenue" crop for "Data center rental and other cost of revenue" -> Lightbox with caption, "Open in filing", "sec.gov ↗", close ×. Kenny reads 56,771 boxed in red. Escape -> lightbox closes, focus returns to the thumbnail.
9. Decide: the arithmetic matches the filing; the gap is XBRL classifying the rental line differently. Kenny wavers between Right and Can't say — the help text on Right is "The filing shows this number at this cell", which does not quite fit a calculated figure.
10. Type into "Note (required for Wrong / Can't say)": "Arithmetic matches 10-K; XBRL Opex counts data-center rental cost as opex" then click "Right" -> Buttons disable, POST `/api/gold/verdict`, section redraws: APLD button "20/20", item status green "Right · Kenny Geiler · <today>", Definition differs line "1 right · 0 wrong · 0 can't say · 0 unchecked · error rate 0.0% (95% CI …)".
11. Scroll up to the header -> Still "Hand check: 119 of 120 checked" (orange). Kenny is confused — the section says 120.
### Variations
- Kenny picks "Can't say" with the same note -> status "Can't say · Kenny Geiler · <date>" in grey; counts move to "1 can't say"; the error rate's n includes it.
- He clicks "Right" with the note empty -> allowed (note optional for Right); the note is saved empty.
### Edge Cases
- Broken flow: the header link, the "Regression test" summary ("· Hand check: 119 of 120 checked") and Release's "Golden test" line ("gold unverified 1 of 120: give the verdicts on Proof") keep the old count until `ledger golden --check` or `ledger test` is rerun from the CLI; nothing in the UI says so.
- Focus is lost after the redraw (the clicked button no longer exists); a keyboard user restarts tabbing from the top.
- The live row behind the item changed since the draw -> the row is tinted red (`table-danger`) and the Value cell shows "Now $…"; grading the old number is then a judgement about a superseded figure.

## STORY-003: Mark a figure Wrong and get blocked by the note rule
**Type**: short
**Topic**: proof-hand-check
**Persona**: Kenny, regrading MSFT after a re-extraction
**Goal**: Record that an MSFT PP&E figure does not match the cell
**Preconditions**: MSFT picked in the hand check; item "PP&E by category · Servers, network equipment, and software · FY2026" shows 215,874 "In millions · $215,874,000,000", currently Right
**Ideal path**: 2 — type note, click Wrong
**Alternate paths**: none found (the gold set is the only verdict surface; Reconcile decisions are a different record)
### Steps
1. Click "Wrong" with the note box empty -> Status line turns red "Note required"; focus jumps to the note input; nothing is sent.
2. Type "Cell is 2025 column; FY2026 figure is in the next column" and click "Wrong" -> POST succeeds; section redraws; status red "Wrong · Kenny Geiler · <date>"; MSFT picker "20/20" unchanged (Wrong still counts as checked); MSFT rate line "19 right · 1 wrong · 0 can't say · 0 unchecked · error rate 5.0% (95% CI …)"; "No SEC counterpart" headline gets a non-zero error rate.
3. Kenny wonders where the fix happens -> the row has no "Company trail" or "Reconcile" link; he must go to the trail via the board (`#proof/MSFT`) or navbar Reconcile with `scope=MSFT` himself.
### Variations
- Re-vote: clicking "Right" later is allowed (any verdict → any verdict); "Unchecked" can never be restored.
### Edge Cases
- Server-side guard mirrors the client: a Wrong / Can't say without a note returns 400 ("a 'Wrong' verdict needs a note…") shown inline.
- A Wrong verdict does not open a Reconcile item or change the dataset; the gold failure surfaces only after the CLI golden run, as "Hand check: 1 failing" (red) and the Release "Golden test … gold FAILS".

## STORY-004: Signer box emptied by accident
**Type**: short
**Topic**: proof-hand-check
**Persona**: Kenny, after clearing the header Signer box while tidying the page
**Goal**: Understand why verdict buttons are greyed out and restore them
**Preconditions**: Signer box empty (localStorage `datahq-me` = "")
**Ideal path**: 2 — notice the disabled reason, type the name
**Alternate paths**: none found
### Steps
1. Pick "NVDA" in the picker -> 20 items render; every Right / Wrong / Can't say button is disabled. Hovering shows "Enter a signer name".
2. Type "Kenny Geiler" in the header "Signer" box -> Buttons enable live (global input listener) without a redraw; tooltips switch to the verdict help ("The filing shows this number at this cell"…).
### Variations
- Typing "Kenny" (not on `config.PEOPLE`) enables the buttons, but a click returns 400 "'Kenny' is not on config.PEOPLE…" inline in that item's status line.
### Edge Cases
- The same "Enter a signer name" gate appears on Reconcile Approve / Choose another / Make this a rule and on Release Sign — one header field gates four pages.

## STORY-005: Spot-check NVDA's sample by eye using crops only
**Type**: medium
**Topic**: proof-hand-check
**Persona**: Kenny, doing a periodic re-audit of already-Right items to guard against rubber-stamping
**Goal**: Confirm a handful of NVDA items still match their cells without opening the filings
**Preconditions**: NVDA 20/20 Right
**Ideal path**: 6 — pick company, then one lightbox open/close per checked item
**Alternate paths**: Company trail `#proof/NVDA` shows the same crops per stage item (same `citeCell`), with verification words instead of verdicts; Evidence page `#evidence/<id>` shows one cited cell larger with Extracted vs Filing columns; Dataset Grid cell provenance has a crop and "Open in 10-K ↗"
### Steps
1. On `#proof`, scroll to Hand check, click "NVDA" -> Card "NVDA · 20 items"; group rows No SEC counterpart, Calculated, Matches SEC XBRL.
2. For a "Matches SEC XBRL" item, read Item "Capex · FY2025 · Statement figure · SEC XBRL $…" next to Value -> Kenny compares the two figures; identical, so he skims.
3. For a "No SEC counterpart" item (Purchase commitments), click the crop -> Lightbox with the cell boxed in red, column header in blue; caption "Purchase commitments · FY… · <row> · <column> · <cell>".
4. Escape, next item -> Focus returns to the thumbnail he opened.
5. One crop shows "Crop out of date" text instead of a thumbnail -> He clicks "Open" (new tab, `/filing/<accession>` with the cell outlined).
6. Satisfied, he leaves every verdict as is -> nothing written.
### Variations
- Item with a restatement shows an orange "Restated…" line with "Compare filings" -> `#evidence/compare?a=&b=` (leaves Proof; Back returns to Proof but the picker resets to no company).
### Edge Cases
- Evidence missing for a cite -> "Crop unavailable · sec.gov ↗" only.
- Redundancy: the same crop of the same cell appears on Hand check, Company trail, Evidence and the Dataset grid provenance popup — four surfaces.
- Observation from data: MSFT verdicts carry timestamps ~1.5 s apart (19:13:10, :11, :13 …); the UI has no signal that grading was fast.

## STORY-006: Read-only visitor tries to grade
**Type**: short
**Topic**: proof-hand-check
**Persona**: A partner at Arctal viewing the hosted read-only copy
**Goal**: See the hand-check evidence; discover whether they can contribute a verdict
**Preconditions**: Server started with `LEDGER_READONLY=1`
**Ideal path**: 2 — pick company, read; ideally no write buttons at all
**Alternate paths**: `/api/v1/gold?t=AMZN` JSON directly
### Steps
1. Open `#proof` -> Header Signer box replaced by "Read-only"; scope line ends "· Read-only".
2. Scroll to Hand check, click "AMZN" -> Items render; verdict buttons are enabled because `me` still defaults to "Kenny Geiler" in this browser (or whatever localStorage held).
3. Click "Can't say" with a note -> 403 "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository" in the item's status line; buttons re-enable.
### Variations
- Without a note, "Note required" appears first — client validation runs before the read-only refusal.
### Edge Cases
- Write affordances render on a copy where they can never succeed; the refusal is only learned by clicking.

## STORY-007: From a failing Release line to a finished hand check and back
**Type**: long
**Topic**: proof-hand-check
**Persona**: Kenny, trying to sign v1.9.0
**Goal**: Clear the "Golden test" release blocker by completing the hand check, then confirm Release sees it
**Preconditions**: Release shows "Golden test" Fail: "tables equal; gold unverified 1 of 120: give the verdicts on Proof; <at>"
**Ideal path**: 6 — Release → Fix in (landing on the hand check) → pick APLD → grade → Release shows pass
**Alternate paths**: Navbar Proof → "Hand check" header link; Proof → scroll. For refreshing the Release line there is no UI path: only CLI `ledger golden --check` / `ledger test`.
### Steps
1. Navbar "Release" -> "Release", "v1.9.0 · Compared with v1.8.0 · 6 companies · <k of m> required checks pass"; "Sign v1.9.0" disabled with "<n> required checks failing".
2. Find row "Golden test", state Fail, Required -> Expand it: detail table (gold failures, if any) — for unverified there are no detail rows, "No items".
3. Click "Fix in: Proof" -> `#proof`, scrolled to top (router `scrollTo(0,0)`); Kenny has to find the hand check himself.
4. Click "Hand check: 119 of 120 checked" -> Scrolls to `#gold`.
5. Click "APLD 19/20" -> APLD items.
6. Grade Opex · FY2026 as in STORY-002 -> APLD "20/20", All line "120 right… 0 unchecked".
7. Navbar "Release" -> Golden test still Fail "gold unverified 1 of 120". Sign still disabled.
8. Kenny goes back to Proof -> header still "Hand check: 119 of 120 checked", Regression test summary the same. Two snapshot surfaces disagree with the live section.
9. Opens Docs → "Operating guide" / Glossary "Golden test" -> learns `ledger golden --check` rebuilds and compares; runs it in a terminal.
10. Reload Release -> Golden test Pass "tables equal; gold pass, 120 verdicts hold"; remaining failures (Proposed, Needs review) still keep Sign disabled.
11. Back to Proof -> header green "Hand check: all 120 hold".
12. Kenny clicks "Next release" link under Releases -> `#release` again; to clear Proposed / Needs review he follows "Fix in: Reconcile".
### Variations
- If a verdict is Wrong, step 10 shows "gold FAILS, 1 verdicts" with a detail row per failure, and the header turns red "Hand check: 1 failing" with the failure ids in its tooltip (first 5).
- If `ledger test` is run instead, `reports/golden.json` is also rewritten (same outcome).
### Edge Cases
- Broken flow: the UI never tells Kenny that his in-page verdict needs a CLI run before Release counts it; the Release note text "give the verdicts on Proof" stays true-looking after he has given them.
- "Fix in: Proof" lands on the board, not on `#gold` or on the company with unchecked items.
- Redundancy: gold state shown in four places — Proof header link, Regression test summary, Hand check section (live), Release "Golden test" line — two sources (snapshot vs live).

## STORY-008: Full regrade of one company after a new 10-K (AMD)
**Type**: long
**Topic**: proof-hand-check
**Persona**: Kenny, after AMD's new 10-K was ingested and a fresh sample drawn by CLI (verdicts kept for re-drawn items, others Unchecked)
**Goal**: Grade all AMD items, prioritising the groups no machine checks
**Preconditions**: AMD gold file redrawn: e.g. "AMD 8/20"; `co.note` "mixes draws: …; items with a verdict keep the…"
**Ideal path**: 22 — pick company + ~1 click per item (20) + a final read; notes only where Wrong / Can't say
**Alternate paths**: Company trail `#proof/AMD` for the same figures with stage context (no verdicts there); Reconcile `scope=AMD` for machine-open items (separate decisions)
### Steps
1. `#proof` → Hand check link -> section; AMD picker "8/20", hover shows "8 right · 0 wrong · 0 can't say · 12 unchecked · error rate 0.0% (95% CI …)".
2. Click "AMD" -> grey note paragraph under the picker: "mixes draws: …". Kenny reads it as "some of these were graded against an older draw".
3. Group "No SEC counterpart" first -> e.g. "Segment revenue · Data Center · FY2026", "Note figure · Not in SEC XBRL", value "12,579 · In millions · $12,579,000,000".
4. Open each crop, compare the figure, click "Right" -> section redraws after every click; Kenny scrolls back to his place each time (the card rebuilds in place, so scroll usually holds, but focus is lost).
5. An item shows orange "Group changed since draw: was Matches SEC XBRL, now No SEC counterpart" -> Kenny pauses: the XBRL counterpart disappeared; he checks the crop more carefully.
6. Item shows "Now $…" in red and a red-tinted row -> the dataset moved since the draw; Kenny decides the sampled number is stale and picks "Can't say" with note "value changed after redraw; regrade after next draw".
7. He starts typing a note on item 9, then clicks "Right" on item 8 above it -> redraw wipes item 9's draft note. He retypes.
8. "Calculated" group -> calc block per item with formula, arithmetic and cross-checks; four crops each.
9. "Matches SEC XBRL" group -> quick by-eye compare of Value vs "SEC XBRL $…" in the Item cell; clicks Right on each.
10. Final: picker "AMD 20/20"; card header rate "19 right · 0 wrong · 1 can't say · 0 unchecked · error rate …".
11. Kenny leaves for the trail via the board row "AMD" (no link from the hand-check card) -> `#proof/AMD`; Back -> Proof with no company picked; he must click AMD again to review his work.
### Variations
- `groups_live` false (database busy) -> orange "Groups as drawn · live tables unavailable"; "Current value unavailable" under every value; grading continues on the drawn groups.
- A gold file fails validation -> red "Hand-check files with errors: …" above the picker; that company is absent.
### Edge Cases
- No keyboard shortcuts in the hand check (Reconcile has j/k/a/e/f/b); 20 items × mouse clicks.
- Draft notes on other rows are lost on every verdict redraw.
- Picker state is not in the URL; reload or Back loses the selected company.

## STORY-009: Read the verification-source and failure-type evidence before trusting the hand check
**Type**: medium
**Topic**: proof-hand-check
**Persona**: A new operator taking over, deciding how much the 0.0% error rate means
**Goal**: Understand what machine checks already vouch for, and how wide the hand-check uncertainty is
**Preconditions**: Read-only or local copy
**Ideal path**: 3 — read Verification source, read Hand check All line, read Failure types
**Alternate paths**: Docs "Evaluation" and Glossary ("Hand check", "Golden test"); Rules page agent Score datagrid (SEC XBRL match with 95% CI); Company trail Verification tile per company
### Steps
1. On `#proof`, read "Verification source" (note "Strongest first") -> per company and "All": SEC XBRL, Other company document, Ties to total, Later actual, Later filing, Citation only, Rows; header tooltips explain each grade.
2. Note "Citation only" is the column no key vouches for -> matches the hand check headline group "No SEC counterpart" ("the person is the only check").
3. Read Failure types -> "<n> known failure types · bars count types, not occurrences"; two bar charts "Types per cause class" and "Types per check" with tables; "No automated check: x of n"; expand "All <n> types".
4. Scroll to Hand check -> "No SEC counterpart … error rate 0.0% (95% CI 0.0–9.6%)" and "All … (95% CI 0.0–…%)". Operator concludes: zero errors seen, but up to ~10% plausible on the human-only group.
5. Expand "Regression test" -> Steps table (Pass / Fail (exit)) and, if any, Differences (Table, Added, Missing); summary with tooltip "Nothing changed since the freeze; not a correctness check".
### Variations
- Plotly fails to load -> each chart reads "Chart unavailable"; tables still carry the numbers.
### Edge Cases
- `/api/v1/failures` fails -> "Failure types unavailable".
- Redundancy: per-company verification counts appear in Verification source here and in the trail's Verification tile; the hand-check rate appears on the picker tooltip, the card header and the group header rows (same numbers, three places).

## STORY-010: Download the last signed packet from Proof
**Type**: short
**Topic**: proof-hand-check
**Persona**: An analyst wanting the release that carried the hand check
**Goal**: Get v1.8.0's packet zip
**Preconditions**: v1.8.0 signed with a packet
**Ideal path**: 1 — click Download
**Alternate paths**: Release page "Packet <v>" card (current candidate only); direct `/packet/v1.8.0.zip`
### Steps
1. On `#proof`, find "Releases" -> rows newest first (max 6): Version, Signed "Kenny Geiler, <date>" (or "Not signed", red "· not published"), Values, To review at signing, Unmapped at signing, Companies "6: MSFT, GOOGL, …".
2. Click "Download" on v1.8.0 -> browser downloads `/packet/v1.8.0.zip`.
### Variations
- A release signed before the checklist existed shows "—" in the at-signing columns.
### Edge Cases
- Hand-check state at signing is not one of the Releases columns; the release record does not show whether gold passed when it was signed.
