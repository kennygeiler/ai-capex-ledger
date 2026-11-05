# UX Path Catalog: Kenny's Data Emporium

Generated: 2026-11-04
Total Stories: 76 (85 written across 8 topic passes; 9 duplicates merged into the story they repeat)
Coverage: 12 of 12 feature areas from `discovery.md` (100%); 8 of 8 recommended topics

Sources: `docs/ux-paths/discovery.md` and `docs/ux-paths/topics/*.md` (proof-hand-check, company-trail-evidence,
reconcile-decisions, reconcile-mapping-encode, release-sign, dataset-explore, readonly-visitor, operator-onboarding).
Every story is renumbered STORY-001 to STORY-076 in topic order. Each story keeps a **Source** line naming its topic file
and original number. Cross-references inside story text point at the new numbers. A merged duplicate keeps its full text
under "Merged duplicate" inside the story it repeats.

## Summary

| Type | Stories | Share |
|---|---|---|
| Short (1–3 steps, one feature) | 32 | 42% |
| Medium (4–8 steps, a few features) | 29 | 38% |
| Long (end to end, many features) | 15 | 20% |
| **Total** | **76** | |

Before merging: 85 stories (39 short, 31 medium, 15 long). The merged duplicates are 7 short and 2 medium stories.

| Topic | Short | Medium | Long | Total | Story numbers |
|---|---|---|---|---|---|
| Proof overview and hand-check grading | 3 | 3 | 2 | 8 | 001–008 |
| Company trail and evidence drill-down | 5 | 3 | 2 | 10 | 009–018 |
| Reconcile: deciding open items | 4 | 5 | 1 | 10 | 019–028 |
| Reconcile: category mapping and apply-everywhere | 3 | 4 | 2 | 9 | 029–037 |
| Release checklist and signing | 5 | 1 | 2 | 8 | 038–045 |
| Dataset and Explore | 3 | 5 | 2 | 10 | 046–055 |
| Hosted read-only visitor | 5 | 4 | 2 | 11 | 056–066 |
| New operator: Docs, Rules, Known gaps | 4 | 4 | 2 | 10 | 067–076 |

Merged duplicates (absorbed → kept):

| Absorbed (topic, old number) | Kept as |
|---|---|
| release-sign 002 "Clear the Golden test line from its Fix in link" | STORY-006 |
| proof-hand-check 010 "Download the last signed packet from Proof" | STORY-043 |
| readonly-visitor 003 "Download the latest signed release packet" | STORY-043 |
| proof-hand-check 006 "Read-only visitor tries to grade" | STORY-057 |
| reconcile-decisions 008 "Read-only visitor tries to decide" | STORY-060 |
| reconcile-mapping-encode 011 "Read-only visitor tries the mapping buttons" | STORY-061 |
| release-sign 010 "Read-only visitor presses Sign" | STORY-062 |
| reconcile-mapping-encode 007 "A different name in the Signer box" | STORY-026 |
| release-sign 004 "Clear Needs review for GOOGL and APLD" | STORY-027 |

Disagreements between topic passes that the merge exposed (left as written, need a code check):
- STORY-061: the mapping pass says `me` is unset on the read-only copy, so Approve and Choose another are disabled with
  "Enter a signer name". The read-only pass says `me` is always set (from localStorage, or "Kenny Geiler" by default),
  so every write button is enabled. STORY-057 and STORY-062 follow the read-only pass.
- STORY-027: the release pass describes GOOGL's 7 open items as "Differs from SEC XBRL" capex rows and says a bulk save
  shows "Saved.". The reconcile pass reads them as 6 segment_revenue tie findings and 1 ppe_category tie finding, and
  says no "Saved." survives a bulk save (STORY-021).
- STORY-026: every write is supposed to refuse a `by` that is not on `config.PEOPLE`. Mapping Reject (STORY-026 merged
  part) and Sign (STORY-042) accept any non-empty name.

## Coverage Matrix

| Feature area (discovery.md) | Stories | Gaps |
|---|---|---|
| Global shell: navbar, jump box, Signer, scope line, drawer, lightbox, sortable tables, route errors | 001, 004, 009, 026, 042, 046, 049, 056, 065, 066, 074 | "Skip to content" and hidden h1 never exercised; no keyboard-only pass of the navbar; phone width only noted in passing (067, 074); route-error page only appears as edge cases |
| Proof board: stage table, legend, Verification source, Failure types, Releases, Regression test | 001, 008, 038, 043, 045, 064 | "Tables changed" state and Regression test Differences only seen when empty; Failure types table not explored in depth |
| Proof → Hand check (gold) | 002, 003, 004, 005, 006, 007, 018, 057 | Gold file validation errors and `groups_live` false are variations only; no story with the picker reached by Back |
| Company trail `#proof/<T>` | 009, 010, 011, 012, 013, 014, 017, 018, 037, 063 | SEC check "never checked" / "check failed" tiles; "<n> new filings not read"; Changes since release "Details" only in 014 |
| Evidence `#evidence/<id>`, `#evidence/compare` | 011, 015, 018, 020, 063 | Single-reading route has no UI link (015), so it is only reached by typed URL |
| Filing viewer `/filing/<accession>` | 010, 014, 016, 063 | None found; refusals covered |
| Rules: agents, scores, runs, history, rules table, To review | 064, 069, 070, 071, 072, 075 | Agent prompt / model / use POST routes have no UI, so no story can exercise them; retired agents not visible |
| Reconcile: decisions (Accept / Explain / Fix / Block release, Confirm / Overturn, bulk, keyboard, filters) | 019, 020, 021, 022, 023, 024, 025, 026, 027, 028, 060 | Causes `new_filing`, `value_missing`, `fact_changed` have no story; Blocks release card and To confirm rows exist only as code paths (no live rows); "Release vs Now" and "Before/After" diff tables not shown |
| Reconcile: category mapping and apply-everywhere | 013, 029, 030, 031, 032, 033, 034, 035, 036, 037, 039, 061 | Map (no proposal) and Make this a rule / definition are code paths with no live data; "Proposed again after rejection" only a variation |
| Dataset: Rows / Grid, lists, search, CSV / JSON, grid drawer, provenance | 046, 047, 048, 049, 055, 058, 063, 065 | API `as_of` point-in-time reads have no story; Projects list only skimmed (055); `#tables/<list>` redirect only a variation |
| Explore: chart controls, saved views, Save / Delete, JSON / CSV | 050, 051, 052, 053, 054, 059, 064 | Layer filter, "share of total" and >8-series folding only as variations; no story where a save succeeds (it cannot today) |
| Release: checklist, Fix in, Sign, publish, packet, `?version=` | 006, 038, 039, 040, 041, 042, 043, 044, 045, 062, 075 | "Stale" and "Not run" states only as variations; "Release checks by company" ticker links only a variation (039) |
| Known gaps: claims, open issues, warnings | 064, 073, 074, 075 | "Unregistered claims" alert and "Issue log edited" warning never shown with live data |
| Docs: sidebar, markdown, flow diagram, raw `/docs/*.md` | 064, 067, 068, 069, 076 | None found beyond the label-drift findings |

Roles: owner/signer (most stories), read-only visitor (056–066 plus 014, 076), new operator (008, 016, 067–076), unnamed
local user (026). Every role in discovery.md has at least one story.

## Story Dependency Graph

Arrows read "needs, or is a step inside". Stories marked (code path) depend on data that does not exist on the live copy
today and can only be walked with a fixture.

```
Setup: local checkout on :3610, Signer = "Kenny Geiler"
├── Signer edge cases ............ 004 (gold), 026 (Reconcile + mapping), 042 (Sign)
│
├── 045 Full pre-release pass (Proof → published)
│   ├── 038 Why can't I sign v1.9.0?
│   ├── 039 Work down the 29 Proposed mappings
│   │   ├── 029 Approve from the row
│   │   ├── 030 Stale Approve (409)
│   │   ├── 031 Reject / Choose another
│   │   ├── 032 Override a "Matches company's own tag" mapping
│   │   └── 033 All MSFT mappings by keyboard
│   ├── 027 Clear the Rule findings queue (Needs review)
│   │   ├── 019 Accept one finding
│   │   ├── 020 Keyboard triage
│   │   ├── 021 Bulk explain ── 022 Bulk in "Grouped by company" fails
│   │   └── 011 Compare filings (for "Readings differ" rows)
│   ├── 006 Golden test line → hand check → CLI rerun
│   │   └── 002 Grade the last APLD item ── 003 Wrong needs a note
│   ├── 040 Sign and publish
│   │   └── 041 Signed, not published (Postgres down)
│   └── 043 Download the packet
│
├── 037 Full company: trail → mapping → decision → encode → Proof
│   ├── 013 Mapping on the trail → "Decide in Reconcile"
│   ├── 029 / 031 mapping decisions
│   ├── 019 / 021 finding decisions
│   └── 035 Make this a rule (code path) ── 036 Make this a definition (code path)
│
├── Run-written proposals (code path)
│   ├── 023 Confirm a proposed decision
│   └── 024 Overturn and Block release ── feeds 038 ("Blocks release" line)
├── 034 Map an unmapped category (code path)
├── 025 Revisit a settled SEC XBRL difference ── 028 Filter by check type
├── 007 Full regrade after a new 10-K ── 005 Spot-check by crops
└── 044 Old release checklist via ?version=

Evidence (any copy)
├── 009 Where one figure came from
│   ├── 010 Open the cited cell in the stored filing ── 016 Viewer refusals
│   ├── 011 Compare filings ── 015 Jump to one cited cell by id
│   └── 012 Why GOOGL has open note figures → Reconcile (019)
├── 014 Full provenance audit (009 + 010 + 011 + 013 + 016)
├── 017 Odd tickers on the trail route
└── 018 Same crop on every surface (005 + 009 + 048 + 025 + 015)

Consumers (any copy)
├── 046 Find one figure in Rows ── 047 CSV for two companies
├── 048 Grid comparison ── 049 Custom company set
├── 050 Chart and export ── 051 Saved views ── 052 Save a view (broken) ── 053 Edit / delete a view (broken)
├── 054 Research pass (046 + 048 + 049 + 050 + 052 + 009)
└── 055 Dataset audit before a client send (046 + 047 + 048 + 043)

Hosted read-only copy (LEDGER_READONLY=1)
├── 056 Recognise read-only ── 066 /api/hq fails, so no read-only marker
├── 057 Grade (refused) · 060 Decide (refused) · 061 Map (refused) · 059 Save view (refused) · 062 Release / Sign
├── 058 Export NVDA rows · 063 Verify one figure to the filing (009 + 010 + 011) · 065 Unknown ticker
└── 064 A day on the hosted copy (056 + 057 + 063 + 060 + 059 + 062 + 043 + 070 + 073)

New operator
├── 067 Flow diagram ── 068 Handoff end to end ── 069 Glossary lookup
├── 070 Audit one agent · 071 Is this rule doing anything? · 072 Rules "To review"
├── 073 Claims register ── 074 Triage high-severity issues (uses 009 / 038)
├── 075 Release "Fix in → Known gaps / Rules" (from 038)
└── 076 Docs on the hosted copy and raw links
```

## All Stories

### Topic: Proof overview and hand-check grading (`proof-hand-check`)

<details><summary>Topic notes (as written by the topic pass)</summary>

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

</details>

#### STORY-001: Check whether anything is proven yet
**Type**: short
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-001
**Persona**: Kenny, owner, opening the app on a Monday morning
**Goal**: Know in one glance how many proven companies are clean and what blocks them
**Preconditions**: Local checkout running on :3610; live state 0 of 6 proven
**Ideal path**: 1 — the landing page should answer "how many proven, what's left" without a click
**Alternate paths**: Navbar brand "Kenny's Data Emporium" → `#proof`; navbar tab "Proof"; any unknown hash (e.g. `#gold` typed into the address bar) falls back to Proof; Docs "How it works" flow box "Filings"/"Check" → `#proof`; Release checklist "Fix in: Proof"
##### Steps
1. Open `http://localhost:3610/` -> Router defaults to `#proof`; "Loading…" then header "Proof", bold "0 of 6 proven"; right side "Tables unchanged · <date>" (grey) and orange link "Hand check: 119 of 120 checked".
2. Scan the company table -> Six rows (Microsoft MSFT, Alphabet GOOGL, Amazon AMZN, NVIDIA NVDA, Applied Digital APLD, AMD) with stage columns Filings · Statement figures · Note figures · AI disclosures · Category mapping · Guidance and projects · Release; last column orange "6 to review", "11 to review", "4 to review", "2 to review", "17 to review", "5 to review". Kenny thinks: "APLD is the long pole again."
3. Hover a red open count in APLD's Statement figures cell -> Tooltip names the open group; hovering the blue explained count shows "Citation only ×n · Restated in a later 10-K ×n…".
4. Read the legend under the table -> "● Checked · ● Done · ● Unverified · ● To review" in state colours.
##### Variations
- NVDA at "2 to review" is closest to Proven; Kenny may jump straight there (STORY-004).
- When a company reaches zero open items its last cell turns green "Proven" and the header count rises.
##### Edge Cases
- `/api/v1/proof` fails -> whole view replaced by a red `msg bad` line with the error text; no partial board.
- `reports/golden.json` missing -> "Tables: not compared" with tooltip "Nothing changed since the freeze; not a correctness check"; hand link reads "Hand check: not run".
- Redundancy: "<n> to review" per company appears here, on the Company trail header, and as per-company counts in Reconcile (`#reconcile?scope=T`) — three surfaces for one number.

#### STORY-002: Grade the last unchecked APLD item (a calculated Opex that differs from SEC XBRL)
**Type**: medium
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-002
**Persona**: Kenny, owner/signer, finishing the hand check before trying to sign v1.9.0
**Goal**: Give a verdict on APLD's one unchecked gold item so the hand check reaches 120 of 120
**Preconditions**: Signer box holds "Kenny Geiler"; APLD shows 19/20; the open item is Opex · FY2026, group "Definition differs"
**Ideal path**: 4 — open Proof, pick APLD (or deep-link to it), inspect the item, click a verdict (+ note if not Right)
**Alternate paths**: Header link "Hand check: 119 of 120 checked" scrolls to `#gold`; scrolling down manually; Release checklist "Golden test" row "Fix in: Proof" (lands at top of Proof, then scroll or the Hand check link). CLI outside the UI (gold files) — not a UI route. No deep link to a company's hand check exists.
##### Steps
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
##### Variations
- Kenny picks "Can't say" with the same note -> status "Can't say · Kenny Geiler · <date>" in grey; counts move to "1 can't say"; the error rate's n includes it.
- He clicks "Right" with the note empty -> allowed (note optional for Right); the note is saved empty.
##### Edge Cases
- Broken flow: the header link, the "Regression test" summary ("· Hand check: 119 of 120 checked") and Release's "Golden test" line ("gold unverified 1 of 120: give the verdicts on Proof") keep the old count until `ledger golden --check` or `ledger test` is rerun from the CLI; nothing in the UI says so.
- Focus is lost after the redraw (the clicked button no longer exists); a keyboard user restarts tabbing from the top.
- The live row behind the item changed since the draw -> the row is tinted red (`table-danger`) and the Value cell shows "Now $…"; grading the old number is then a judgement about a superseded figure.

#### STORY-003: Mark a figure Wrong and get blocked by the note rule
**Type**: short
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-003
**Persona**: Kenny, regrading MSFT after a re-extraction
**Goal**: Record that an MSFT PP&E figure does not match the cell
**Preconditions**: MSFT picked in the hand check; item "PP&E by category · Servers, network equipment, and software · FY2026" shows 215,874 "In millions · $215,874,000,000", currently Right
**Ideal path**: 2 — type note, click Wrong
**Alternate paths**: none found (the gold set is the only verdict surface; Reconcile decisions are a different record)
##### Steps
1. Click "Wrong" with the note box empty -> Status line turns red "Note required"; focus jumps to the note input; nothing is sent.
2. Type "Cell is 2025 column; FY2026 figure is in the next column" and click "Wrong" -> POST succeeds; section redraws; status red "Wrong · Kenny Geiler · <date>"; MSFT picker "20/20" unchanged (Wrong still counts as checked); MSFT rate line "19 right · 1 wrong · 0 can't say · 0 unchecked · error rate 5.0% (95% CI …)"; "No SEC counterpart" headline gets a non-zero error rate.
3. Kenny wonders where the fix happens -> the row has no "Company trail" or "Reconcile" link; he must go to the trail via the board (`#proof/MSFT`) or navbar Reconcile with `scope=MSFT` himself.
##### Variations
- Re-vote: clicking "Right" later is allowed (any verdict → any verdict); "Unchecked" can never be restored.
##### Edge Cases
- Server-side guard mirrors the client: a Wrong / Can't say without a note returns 400 ("a 'Wrong' verdict needs a note…") shown inline.
- A Wrong verdict does not open a Reconcile item or change the dataset; the gold failure surfaces only after the CLI golden run, as "Hand check: 1 failing" (red) and the Release "Golden test … gold FAILS".

#### STORY-004: Signer box emptied by accident
**Type**: short
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-004
**Persona**: Kenny, after clearing the header Signer box while tidying the page
**Goal**: Understand why verdict buttons are greyed out and restore them
**Preconditions**: Signer box empty (localStorage `datahq-me` = "")
**Ideal path**: 2 — notice the disabled reason, type the name
**Alternate paths**: none found
##### Steps
1. Pick "NVDA" in the picker -> 20 items render; every Right / Wrong / Can't say button is disabled. Hovering shows "Enter a signer name".
2. Type "Kenny Geiler" in the header "Signer" box -> Buttons enable live (global input listener) without a redraw; tooltips switch to the verdict help ("The filing shows this number at this cell"…).
##### Variations
- Typing "Kenny" (not on `config.PEOPLE`) enables the buttons, but a click returns 400 "'Kenny' is not on config.PEOPLE…" inline in that item's status line.
##### Edge Cases
- The same "Enter a signer name" gate appears on Reconcile Approve / Choose another / Make this a rule and on Release Sign — one header field gates four pages.

#### STORY-005: Spot-check NVDA's sample by eye using crops only
**Type**: medium
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-005
**Persona**: Kenny, doing a periodic re-audit of already-Right items to guard against rubber-stamping
**Goal**: Confirm a handful of NVDA items still match their cells without opening the filings
**Preconditions**: NVDA 20/20 Right
**Ideal path**: 6 — pick company, then one lightbox open/close per checked item
**Alternate paths**: Company trail `#proof/NVDA` shows the same crops per stage item (same `citeCell`), with verification words instead of verdicts; Evidence page `#evidence/<id>` shows one cited cell larger with Extracted vs Filing columns; Dataset Grid cell provenance has a crop and "Open in 10-K ↗"
##### Steps
1. On `#proof`, scroll to Hand check, click "NVDA" -> Card "NVDA · 20 items"; group rows No SEC counterpart, Calculated, Matches SEC XBRL.
2. For a "Matches SEC XBRL" item, read Item "Capex · FY2025 · Statement figure · SEC XBRL $…" next to Value -> Kenny compares the two figures; identical, so he skims.
3. For a "No SEC counterpart" item (Purchase commitments), click the crop -> Lightbox with the cell boxed in red, column header in blue; caption "Purchase commitments · FY… · <row> · <column> · <cell>".
4. Escape, next item -> Focus returns to the thumbnail he opened.
5. One crop shows "Crop out of date" text instead of a thumbnail -> He clicks "Open" (new tab, `/filing/<accession>` with the cell outlined).
6. Satisfied, he leaves every verdict as is -> nothing written.
##### Variations
- Item with a restatement shows an orange "Restated…" line with "Compare filings" -> `#evidence/compare?a=&b=` (leaves Proof; Back returns to Proof but the picker resets to no company).
##### Edge Cases
- Evidence missing for a cite -> "Crop unavailable · sec.gov ↗" only.
- Redundancy: the same crop of the same cell appears on Hand check, Company trail, Evidence and the Dataset grid provenance popup — four surfaces.
- Observation from data: MSFT verdicts carry timestamps ~1.5 s apart (19:13:10, :11, :13 …); the UI has no signal that grading was fast.

#### STORY-006: From a failing Release line to a finished hand check and back
**Type**: long
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-007; merged with `release-sign` STORY-002 (Clear the Golden test line from its Fix in link)
**Persona**: Kenny, trying to sign v1.9.0
**Goal**: Clear the "Golden test" release blocker by completing the hand check, then confirm Release sees it
**Preconditions**: Release shows "Golden test" Fail: "tables equal; gold unverified 1 of 120: give the verdicts on Proof; <at>"
**Ideal path**: 6 — Release → Fix in (landing on the hand check) → pick APLD → grade → Release shows pass
**Alternate paths**: Navbar Proof → "Hand check" header link; Proof → scroll. For refreshing the Release line there is no UI path: only CLI `ledger golden --check` / `ledger test`.
##### Steps
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
##### Variations
- If a verdict is Wrong, step 10 shows "gold FAILS, 1 verdicts" with a detail row per failure, and the header turns red "Hand check: 1 failing" with the failure ids in its tooltip (first 5).
- If `ledger test` is run instead, `reports/golden.json` is also rewritten (same outcome).
##### Edge Cases
- Broken flow: the UI never tells Kenny that his in-page verdict needs a CLI run before Release counts it; the Release note text "give the verdicts on Proof" stays true-looking after he has given them.
- "Fix in: Proof" lands on the board, not on `#gold` or on the company with unchecked items.
- Redundancy: gold state shown in four places — Proof header link, Regression test summary, Hand check section (live), Release "Golden test" line — two sources (snapshot vs live).

##### Merged duplicate: `release-sign` STORY-002: Clear the Golden test line from its Fix in link

**Type**: medium
**Topic**: release-sign
**Persona**: Kenny, signer
**Goal**: Turn "Golden test" green by grading the one unchecked APLD gold item
**Preconditions**: Golden test Fail, note "tables equal; gold unverified 1 of 120: give the verdicts on Proof; 2026-11-03T21:12:16+00:00"
**Ideal path**: 5 — Fix in lands directly on the APLD hand-check group, one verdict, back to Release (plus the out-of-band `ledger test`)
**Alternate paths**: Proof header "Hand check: <state>" link scrolls to `#gold`; navbar Proof then scroll; brand "Kenny's Data Emporium" → `#proof`
###### Steps
1. On `#release`, click the "Golden test" row -> Row expands; detail table shows "No items" (detail is empty when only gold is unverified). Kenny hesitates: "which item?"
2. Read the Details cell (truncated at ~26rem; hover shows the full note) -> "gold unverified 1 of 120: give the verdicts on Proof".
3. Click **Proof** in the "Fix in" column -> Navigates to `#proof` top (not `#gold`); the row does not toggle (click stops propagation).
4. Click the header link "Hand check: …" -> Page scrolls to the Hand check card.
5. Scan the company picker -> "APLD 19/20"; click it -> APLD items table opens.
6. Find the one item with status "Unchecked", open its crop thumbnail -> Lightbox with the cell; Kenny checks the value against the filing.
7. Click **Right** -> Status becomes "Right · Kenny Geiler · <date>"; picker shows "APLD 20/20".
8. Click navbar **Release** -> Golden test still "Fail": the line reads `reports/golden.json`, written by `ledger test`/the golden run, not live gold files. Kenny is confused.
9. In a terminal run the golden/test command, then reload `#release` -> Golden test "Pass"; "13 of 15 required checks pass".
###### Variations
- Kenny marks **Wrong** instead: must fill "Note (required for Wrong / Can't say)"; after the rerun the line note becomes "gold FAILS, 1 verdicts" and stays red.
- Proof's own "Regression test" collapsible (Hand check state) shows the same gold state as the Release line.
###### Edge Cases
- Broken flow: Fix in → `#proof` lands at the top of a long page; the gold section has its own anchor that the link does not use.
- No UI tells the user the line only refreshes after a CLI run; the note's timestamp is the only clue.
- If `reports/golden.json` is missing, the line reads "not run", count 1, Fail.

#### STORY-007: Full regrade of one company after a new 10-K (AMD)
**Type**: long
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-008
**Persona**: Kenny, after AMD's new 10-K was ingested and a fresh sample drawn by CLI (verdicts kept for re-drawn items, others Unchecked)
**Goal**: Grade all AMD items, prioritising the groups no machine checks
**Preconditions**: AMD gold file redrawn: e.g. "AMD 8/20"; `co.note` "mixes draws: …; items with a verdict keep the…"
**Ideal path**: 22 — pick company + ~1 click per item (20) + a final read; notes only where Wrong / Can't say
**Alternate paths**: Company trail `#proof/AMD` for the same figures with stage context (no verdicts there); Reconcile `scope=AMD` for machine-open items (separate decisions)
##### Steps
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
##### Variations
- `groups_live` false (database busy) -> orange "Groups as drawn · live tables unavailable"; "Current value unavailable" under every value; grading continues on the drawn groups.
- A gold file fails validation -> red "Hand-check files with errors: …" above the picker; that company is absent.
##### Edge Cases
- No keyboard shortcuts in the hand check (Reconcile has j/k/a/e/f/b); 20 items × mouse clicks.
- Draft notes on other rows are lost on every verdict redraw.
- Picker state is not in the URL; reload or Back loses the selected company.

#### STORY-008: Read the verification-source and failure-type evidence before trusting the hand check
**Type**: medium
**Topic**: proof-hand-check
**Source**: `proof-hand-check` STORY-009
**Persona**: A new operator taking over, deciding how much the 0.0% error rate means
**Goal**: Understand what machine checks already vouch for, and how wide the hand-check uncertainty is
**Preconditions**: Read-only or local copy
**Ideal path**: 3 — read Verification source, read Hand check All line, read Failure types
**Alternate paths**: Docs "Evaluation" and Glossary ("Hand check", "Golden test"); Rules page agent Score datagrid (SEC XBRL match with 95% CI); Company trail Verification tile per company
##### Steps
1. On `#proof`, read "Verification source" (note "Strongest first") -> per company and "All": SEC XBRL, Other company document, Ties to total, Later actual, Later filing, Citation only, Rows; header tooltips explain each grade.
2. Note "Citation only" is the column no key vouches for -> matches the hand check headline group "No SEC counterpart" ("the person is the only check").
3. Read Failure types -> "<n> known failure types · bars count types, not occurrences"; two bar charts "Types per cause class" and "Types per check" with tables; "No automated check: x of n"; expand "All <n> types".
4. Scroll to Hand check -> "No SEC counterpart … error rate 0.0% (95% CI 0.0–9.6%)" and "All … (95% CI 0.0–…%)". Operator concludes: zero errors seen, but up to ~10% plausible on the human-only group.
5. Expand "Regression test" -> Steps table (Pass / Fail (exit)) and, if any, Differences (Table, Added, Missing); summary with tooltip "Nothing changed since the freeze; not a correctness check".
##### Variations
- Plotly fails to load -> each chart reads "Chart unavailable"; tables still carry the numbers.
##### Edge Cases
- `/api/v1/failures` fails -> "Failure types unavailable".
- Redundancy: per-company verification counts appear in Verification source here and in the trail's Verification tile; the hand-check rate appears on the picker tooltip, the card header and the group header rows (same numbers, three places).

### Topic: Company trail and evidence drill-down (`company-trail-evidence`)

<details><summary>Topic notes (as written by the topic pass)</summary>

Topic: `company-trail-evidence`. Written 2026-11-04 from `ledger/web/pages/trail.js`, `pages/evidence.js`, `pages/_shared.js`
(`citeCell`, `cropBox`, `calcBlock`, `restatedLine`, `mappingDecision`), `ledger/web/viewer.py` and `app.py`
(`/filing/`, `/evidence/crops/`, `/api/v1/evidence/`, `/api/v1/proof/<T>`), checked against read-only GETs on :3610.

Live facts used below: all six proven companies show "<n> to review" (MSFT 6, GOOGL 11, AMZN 4, NVDA 2, APLD 17, AMD 5);
SEC check is stale everywhere (179 h → "7d ago · out of date"); every trail crop is in state located; MSFT has 10
restated Intelligent Cloud segment facts with a "Compare filings" pair; GOOGL has 7 open note figures (PP&E parts don't
tie, no crop); last release v1.8.0 for all six.

</details>

#### STORY-009: Check where one MSFT capex figure came from
**Type**: short
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-001
**Persona**: Analyst at a fund reading the ledger, wants to trust one number before quoting it
**Goal**: See the cited 10-K cell behind Microsoft's FY2026 capex figure
**Preconditions**: Local or hosted copy; MSFT trail loads; Statement figures stage has 15 items, 0 open
**Ideal path**: 3 — open trail, find the capex row, click the thumbnail; the crop is the proof
**Alternate paths**: Proof board row MSFT → trail; Dataset grid (`#data?view=grid`) capex cell → provenance drawer shows the same crop via `sources()`; Hand check (if the item was sampled) shows the same `citeCell`; Reconcile expand (only if the item is open) shows the crop; `#evidence/<extraction_id>` typed by hand shows it with the Extracted/Filing split
##### Steps
1. Click **Proof** tab, then the **Microsoft MSFT** row -> `#proof/MSFT` loads: header "Microsoft MSFT", legend, "6 to review", links "Reconcile" and "Dataset"; summary card "Before release".
2. Scroll to the **Statement figures** card ("15 items · Complete") -> Because 15 > 12 and nothing is open, the table is collapsed under a summary line "15 verified". User hesitates: the card looks empty until they notice the grey summary.
3. Click the "15 verified" summary -> Table Item · Value · Source · Verification opens; rows like "Capex · FY2026", value `$…M`, Source shows a crop thumbnail with "10-K 2026-07-29 · Open · sec.gov ↗", Verification "Verified · Matches SEC XBRL: $…M".
4. Click the crop thumbnail -> Lightbox opens full-size crop, caption "Capex · FY2026 · <row> · <column> · <cell>", links "Open in filing" and "sec.gov ↗", close button focused.
5. Press Escape -> Lightbox closes, focus returns to the thumbnail.
##### Variations
- Uses the jump box "Ticker or company…" and types MSFT -> lands on `#data?ticker=MSFT` (Dataset), not the trail; must click the ticker cell or use the trail link from there. Extra step.
- Arrives from Explore: click a bar → "Data" rows → Company link → `#proof/MSFT`.
- A figure computed from several cells (e.g. "Opex · FY2022") shows a calc block above several thumbnails, each with a role label ("Revenue", "Cost of revenue", "Operating income").
##### Edge Cases
- The thumbnail is a folded canvas (`focusCell`): label column + boxed cell only. If the image can't be read by canvas, the whole crop shows contained.
- Crop not located/stale/missing: no thumbnail, instead the crop-state word ("Cell not located · <reason>", "Crop out of date", "Crop file missing", "No crop").
- Redundancy: the same crop+Open+sec.gov trio appears on trail, Hand check, Reconcile evidence row, Dataset grid drawer, and `#evidence/<id>`.

#### STORY-010: Open the cited cell inside the stored filing
**Type**: short
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-002
**Persona**: Skeptical reviewer who wants to see the number in context, not a crop
**Goal**: See NVDA's revenue cell outlined in the actual 10-K
**Preconditions**: NVDA trail; Statement figures "18 items · Complete"; stored filing present and fingerprint matches
**Ideal path**: 3 — trail, expand stage, click Open
**Alternate paths**: lightbox "Open in filing"; `#evidence/<id>` "Open in filing" button or clicking its crop image; Hand check row "Open"; Reconcile evidence row "Open"; Dataset grid drawer "Open"; "sec.gov ↗" (the SEC copy, with a text fragment `#:~:text=`, no outline)
##### Steps
1. Go to `#proof/NVDA` -> Trail loads ("2 to review": the two Proposed category mappings).
2. Expand "18 verified" under **Statement figures** -> rows visible.
3. On "Revenue · FY2026" click **Open** (tooltip "Open in filing, the cell outlined") -> New tab `/filing/0001045810-26-000021?t=…&row=…&col=…&cell=…`.
4. Filing loads (multi-MB, may take a moment) -> fixed dark banner "Found on this page · Revenue · 2026 · 130,497"-style text; the cell outlined red, its row tinted yellow and scrolled to centre.
##### Variations
- User clicks "sec.gov ↗" instead: lands on sec.gov with a text fragment highlight; no outline, depends on the browser supporting text fragments.
- From the lightbox "Open in filing": same tab target.
##### Edge Cases
- Locator can't confirm the cell: banner turns red "Not found on this page", with " · Column ambiguous" or " · Page shows X · cited Y". The banner is the live find, not the crop state, so a "Cell located" crop can still show "Not found on this page" if the page shifted.
- Filing is sandboxed (strict CSP): links inside the 10-K do nothing; there is no way back to the app from the tab except closing it.

#### STORY-011: Why does Intelligent Cloud FY2021 have two values? (Compare filings)
**Type**: medium
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-003
**Persona**: Equity analyst who saw 60,080 in an old model and 59,728 in the ledger
**Goal**: Understand Microsoft's segment restatement and which reading the dataset uses
**Preconditions**: MSFT trail; Note figures "63 items · Complete" (27 verified · 31 corroborated · 5 unverified); 10 items carry a restatement
**Ideal path**: 4 — trail, expand Note figures, read the Restated line, click Compare filings
**Alternate paths**: Hand check item (if sampled) shows `restatedLine(…, true)` with its own "Compare filings" link; `#evidence/<A id>` single page shows the Restated line + "Compare filings"; Reconcile expand when a restatement is open; typing `#evidence/compare?a=…&b=…`
##### Steps
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
##### Variations
- FY2023 pair: "Restated: 87,907 (10-K 2023-07-27, 10-K 2024-07-30) → 72,944 (10-K 2025-07-30)" — a $15B swing (segment re-org), the compare page makes the re-org obvious.
- Readings agree: header shows green "Readings agree".
- Two readings that round to the same `usd()` print with `usdExact` so they never look identical.
##### Edge Cases
- Compare page has no "Company trail" link (single evidence page does); only Back returns.
- Missing `a` or `b` in URL -> page error "Two readings are needed: #evidence/compare?a=<id>&b=<id>".
- One id unknown -> page error "no cited cell '<id>'" (whole page, no partial render).
- Redundancy: the Restated line appears in the trail Verification cell, the compare header, the single evidence header, and Hand check.

#### STORY-012: Investigate why GOOGL has 7 open note figures
**Type**: medium
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-004
**Persona**: Kenny (owner) preparing to clear GOOGL before signing v1.9.0
**Goal**: Understand the open Note figures items and get to the place to decide them
**Preconditions**: GOOGL trail "11 to review" (7 Note figures + 4 Category mapping)
**Ideal path**: 4 — trail, read the open row's reason, open the filing, jump to Reconcile scoped
**Alternate paths**: Proof board stage cell for GOOGL (hover breakdown) → row → trail; `#reconcile?scope=GOOGL` directly (header link "Reconcile", summary link "Review in Reconcile →"); Rules page "To review" list grouped by need; Release checklist "Fix in" → Reconcile
##### Steps
1. From Proof click **Alphabet GOOGL** -> trail, header "11 to review"; summary "Before release", "Review in Reconcile →".
2. Read the Coverage tile -> "Through 10-K · FY ending 2025-12-31" (link to sec.gov), "Filed 2026-02-05", "Next 10-K expected ~2027-02-05", "SEC checked 7d ago · out of date" in warning colour. User hesitates: is "out of date" why things are open? (It isn't; it's the EDGAR freshness check.)
3. Scroll to **Note figures** "55 items · 7 to review" -> the 7 open rows show uncollapsed first; the other 48 sit under a tally summary.
4. Read row "PP&E by category · FY2023 · Parts vs total"-style item -> Value "—"; Source: no crop, a line "10-K 2025-02-05 · Open · sec.gov ↗"; Verification red "Needs review · Does not tie · gap $35,136M".
5. Click the Verification line (it is a `<details>` summary) -> detail "Parts $201,803M · total $166,667M (SEC XBRL) · 4 parts · tolerance ±$2.5M".
6. Click **Open** -> new tab `/filing/0001652044-25-000014` with no row/cell params: the whole 10-K, no banner, no outline. User must Cmd-F for the PP&E note themselves.
7. Close tab; click **Review in Reconcile →** -> `#reconcile?scope=GOOGL`, cards per cause, where the decision form (Accept / Explain / Fix / Block release) lives.
##### Variations
- Uses header "Reconcile" link instead of the summary link: same URL. Two links to the same place within one screen.
- Uses header "Dataset" -> `#data?ticker=GOOGL`, Rows view filtered to GOOGL.
##### Edge Cases
- Rule-finding rows have no cited cell, so "Open" opens the bare filing: a weak evidence step compared to figure rows.
- The trail is read-only: no decision controls here even for the owner; every fix is one hop away in Reconcile.

#### STORY-013: Category mapping on the trail, decided elsewhere
**Type**: short
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-005
**Persona**: Kenny checking AMD's 5 Proposed mappings
**Goal**: See what Claude proposed for each AMD asset category and get to the decision
**Preconditions**: AMD trail "5 to review", all in Category mapping (wait)
**Ideal path**: 3 — trail, read mapping card, click "Decide in Reconcile →"
**Alternate paths**: `#reconcile?scope=AMD&cause=asset_types` directly; Reconcile with Cause "Category mapping"; Proof board Category mapping cell
##### Steps
1. Open `#proof/AMD` -> "5 to review", Category mapping card "5 items · 5 to review".
2. Read a decision card -> name + orange state label, datagrid Company line (latest value + period, "Open ↗", series), Proposed (label, member e.g. `BuildingAndBuildingImprovementsMember`, definition, "Source: …"), Company's own tag, Basis "“…”" with "Claude Fable 5.1 · <date>", Alternatives (expandable definitions), Affects.
3. Click **Decide in Reconcile →** -> `#reconcile?scope=AMD&cause=asset_types`, the same card with Approve / Reject / Choose another.
##### Variations
- Items already settled by the company's own XBRL tag ("Matches company tag", e.g. GOOGL 5 of 9) sit under the tally summary with link "Confirm or override in Reconcile →".
- NVDA: 2 Proposed + 2 Matches company tag.
##### Edge Cases
- Redundancy: the mapping decision card is rendered identically (`mappingDecision`) on trail and Reconcile; the trail copy has no actions.

#### STORY-014: Full provenance audit of one company before a release
**Type**: long
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-006
**Persona**: Outside auditor given the hosted read-only copy, asked to sample APLD (Applied Digital) evidence
**Goal**: Walk every stage for APLD, spot-check figures, quotes, guidance and restatements, and note what's still open
**Preconditions**: Hosted copy (`LEDGER_READONLY=1`, scope line ends "· Read-only"); APLD "17 to review" (9 Note figures, 8 Category mapping)
**Ideal path**: ~15 — one page holds everything; the cost is expanding collapsed stages and opening filings
**Alternate paths**: Dataset Rows filtered `#data?ticker=APLD` (values/facts/statements/projects lists with CSV/JSON); Release page "Packet" for the signed v1.8.0 files; Hand check APLD (20 sampled items with crops, 1 unchecked); API `/api/v1/proof/APLD`
##### Steps
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
##### Variations
- Auditor uses the Dataset Rows view and CSV instead of trail for bulk checking, losing crops and verification words.
- Auditor downloads `/packet/v1.8.0.zip` from Proof "Releases" to compare against the trail's "Changes since release".
##### Edge Cases
- Stage card count uses `plural(st.items, 'item')` so "1 item" singular on Release; "0 items · Complete" shows for an empty Guidance and projects card (MSFT).
- Very long stage (109 rows) has no search or filter on the trail.
- Redundancy: "17 to review" appears in header, summary "To review 17", stage tallies, Proof board last column and Reconcile counts.

#### STORY-015: Jump straight to one cited cell by its id
**Type**: short
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-007
**Persona**: Developer debugging a value reported via the API, holding an `extraction_id`
**Goal**: See the Extracted vs Filing view for one reading
**Preconditions**: Has id `0001564590-22-026876|segment_revenue|Intelligent Cloud|2021-06-30` (from `/api/v1/proof/MSFT` or a CSV)
**Ideal path**: 1 — paste `#evidence/<id>`; no UI link exists so this is also the only path
**Alternate paths**: none found in the UI — no page links to the single `#evidence/<id>` route (trail/gold/compare all link the compare form only); API `/api/v1/evidence/<id>` for JSON
##### Steps
1. Paste `http://localhost:3610/#evidence/0001564590-22-026876%7Csegment_revenue%7CIntelligent%20Cloud%7C2021-06-30` -> Proof tab highlighted; title "Segment revenue · Intelligent Cloud MSFT", period "12 months to Jun 30, 2021", orange Restated line with **Compare filings**, link **Company trail**.
2. Read **Extracted** -> `$60,080,000,000`, Cited cell `60,080`, Row "Intelligent Cloud", Column "2021", Units "stated × 1,000,000", Period, Filing "10-K · 0001564590-22-026876 · filed Jul 28, 2022", Source "Notes to the financial statements".
3. Read **Filing** -> "Cell located", orange "Superseded", crop image, "Page shows 60,080 · cropped Nov 3, …", **Open in filing**, "sec.gov ↗".
4. Click **Company trail** -> `#proof/MSFT`.
##### Variations
- Click the crop image itself -> same as Open in filing (new tab viewer).
##### Edge Cases
- Unknown id -> page shows red error "no cited cell '<id>'".
- Broken flow: this richest single-reading view (exact dollar value, units, scale) is orphaned — reachable only by typed URL.

#### STORY-016: Viewer refusals when the stored copy is wrong
**Type**: medium
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-008
**Persona**: New operator after a partial `data/raw` restore on a fresh checkout
**Goal**: Open a cited cell and understand why the filing won't load
**Preconditions**: A filing file missing or edited on disk; or a hand-edited URL
**Ideal path**: 2 — click Open, read the refusal; recovery happens in the CLI
**Alternate paths**: "sec.gov ↗" next to every Open link (SEC copy, always available); lightbox crop (independent of the stored filing, served from `reports/evidence/crops`)
##### Steps
1. On `#proof/AMZN`, expand Statement figures, click **Open** on a row -> new tab.
2. Stored file deleted -> tab shows raw JSON `{"error": "the stored copy of this filing is missing"}` (HTTP 410), no styling, no link back.
3. Operator tries another row whose file was re-downloaded but differs -> `{"error": "the stored copy of this filing differs from its fingerprint"}` (409).
4. Operator edits the URL to `/filing/abc` -> `{"error": "not a filing"}` (404); to a well-formed unknown accession `/filing/0000000000-00-000000` -> `{"error": "no stored filing with that accession"}` (404).
5. Falls back to **sec.gov ↗** on the trail row -> SEC's copy with text fragment.
6. Re-runs ingest from a checkout (CLI, outside the UI), reloads -> banner "Found on this page".
##### Variations
- Crop PNG requested directly when its state isn't located (`/evidence/crops/<f>.png`) -> 404 `{"error": "not found"}`; in the UI that crop never shows as a thumbnail, only the state word.
##### Edge Cases
- The trail gives no hint beforehand that a filing is missing/changed; crop state ("Cell located") is computed separately and can still say located.
- Refusals are JSON under a sandbox CSP: a non-technical reader sees a code blob, not a page.

#### STORY-017: Odd tickers on the trail route
**Type**: short
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-009
**Persona**: Curious visitor editing the URL, or someone following a Dataset link for an in-scope but unproven company
**Goal**: See the trail for Oracle, then for a typo
**Preconditions**: ORCL is in scope but not in the proven six; ZZZZ doesn't exist
**Ideal path**: 1 — type `#proof/ORCL`
**Alternate paths**: Dataset Rows ticker cell for ORCL → `#proof/ORCL`; Explore data table Company link; Reconcile "Company trail" link on an ORCL row
##### Steps
1. Go to `#proof/ORCL` -> "Oracle ORCL", legend plus grey "Not in scope", "5 to review" (5 Proposed mappings); stages Filings 5, Statement figures 18, Note figures 55, AI disclosures 5, Category mapping 5, Guidance and projects 10; Last release "None".
2. Go to `#proof/ZZZZ` -> "ZZZZ ZZZZ", "Not in scope", but green **Proven**, summary "Ready for release", Coverage "No filings", "SEC checked 7d ago · out of date", every stage "0 items · Complete", Release "1 item · Complete".
##### Variations
- Jump box with "ZZZZ" -> goes to `#data?ticker=ZZZZ` (empty rows), not the trail.
##### Edge Cases
- Broken flow: an unknown ticker reads as "Proven" and "Ready for release" — the server returns `proven: true, open: 0` for nothing.
- Trail for an unproven company is complete and useful, but nothing on Proof links to it (Proof lists only the six).

#### STORY-018: Compare a crop across every surface for one sampled item
**Type**: long
**Topic**: company-trail-evidence
**Source**: `company-trail-evidence` STORY-010
**Persona**: Kenny auditing his own UI for consistency before showing it to Arctal
**Goal**: Confirm the same AMZN figure shows the same value, crop and verdict everywhere it appears
**Preconditions**: AMZN has 20 Hand check items; one sampled item is a capex figure also in Statement figures
**Ideal path**: n/a (consistency audit) — the redundancy is the subject
**Alternate paths**: every surface below is itself an alternate path to the same cited cell
##### Steps
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
##### Variations
- Item drifted since sampling: Hand check shows red "Now $…" or "Removed from dataset", trail shows the new value only.
##### Edge Cases
- Five surfaces render the same cell; only `#evidence/<id>` shows the exact dollar figure and scale; only Hand check shows the human verdict; only the trail shows verification ladder words. Candidate for consolidation: one evidence view linked from all.
- Stage tally thresholds differ: Statement figures collapse only when >12 items or something is open, so AMZN (12) shows open while MSFT (15) is collapsed — inconsistent first impression across companies.

### Topic: Reconcile: deciding open items (`reconcile-decisions`)

<details><summary>Topic notes (as written by the topic pass)</summary>

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

</details>

#### STORY-019: Accept one rule finding with a reason
**Type**: short
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-001
**Persona**: Kenny Geiler, owner and signer, on the local checkout with Signer "Kenny Geiler"
**Goal**: Close GOOGL segment_revenue FY2025 "Does not tie to reported total" after deciding the $127M gap is explained
**Preconditions**: `#reconcile` loaded, default Grouped by cause; the row is in the Rule findings card, state "Needs review"
**Ideal path**: 3 — open the row, type the reason, press Save (Accept is the form's default state)
**Alternate paths**: keyboard: focus row, `a` (opens and pre-selects Accept, focuses Reason), type, Enter; bulk: tick the checkbox → bulk card → Save for 1; Company trail `#proof/GOOGL` "Review in Reconcile →" lands on the same page scoped to GOOGL
##### Steps
1. Click Reconcile in the navbar -> `#reconcile`; header counts "Needs review 16 · Proposed 29 · Unverified 6"; Rule findings card first.
2. Click the GOOGL row "segment_revenue FY2025" (Dataset, SEC XBRL, Gap, Difference all "—") -> evidence row opens below: "Details" disclosure with "3 parts in 0001652044-26-000018 sum to $402,963M; the filing tags Revenues $402,836M for 2025-12-31 (gap $127M, tolerance on the sum ±$2M)", link "Open in Dataset", and a **Decision** card.
3. Kenny thinks: "$127M on $403B, the segments include hedging gains Alphabet reports outside segments." He hesitates over Accept vs Explain: both tooltips read "Right as it stands" / "Right, with the reason kept"; both need a reason anyway. Leaves **Accept** (pre-pressed).
4. Types "segment total includes hedging gains reported in Alphabet-level activities" in the Reason box (placeholder "e.g. includes finance leases, note 7") and clicks **Save** -> "Saving…" then "Saved."; after 250 ms the page re-renders.
5. Row is gone from the default list (no longer open); header now "Needs review 15"; "Show 7 settled". Focus lands on the first row of the page (the saved row no longer exists, so `FOCUS_KEY` falls back to index 0) and scrolls it to centre.
##### Variations
- Explain instead of Accept: identical server effect (both map to state explained / word "Unverified"); only the badge colour and label differ (`bg-azure-lt` vs `bg-green-lt`).
- Press Enter in the Reason box instead of clicking Save (Reason `onkeydown` Enter clicks Save).
- Arriving from Release: "Fix in" Reconcile on the "Needs review" line → `#reconcile` unfiltered; the user has to find GOOGL themselves.
##### Edge Cases
- Empty reason -> Reason focused, status "Reason required"; nothing posted.
- The decision is shown afterwards in three places: the row's Decision cell ("Accept · Kenny Geiler · Nov 4", only with Show settled), the Decision card header ("Accept · Kenny Geiler · Nov 4 · <reason>"), and the Company trail / Dataset grid badge ("Accepted"). Redundancy candidate.
- No undo. Reversing means re-opening the settled row (Show settled) and saving a new decision, which appends a new line.

#### STORY-020: Triage APLD findings fast with the keyboard
**Type**: medium
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-002
**Persona**: Kenny, keyboard-first, clearing the queue before a release
**Goal**: Decide all nine APLD rule findings without the mouse
**Preconditions**: `#reconcile?scope=APLD`; Signer filled
**Ideal path**: 4 per item (j to move, letter to decide, type reason, Enter) — about 36 keystroke-groups for nine items; a well-designed UI could auto-advance after Save
**Alternate paths**: mouse click per row + Save; bulk select (space) + Save for n when the reason is shared (STORY-022); the "Keyboard" hint in the header is the only discoverability for keys (tooltip "j k move · Enter opens · a e f b decide · space selects")
##### Steps
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
##### Variations
- `k` / ArrowUp to go back; Escape collapses the open evidence row (only while focus is on the row, not inside the Reason input).
- Grouped by company (`group=company`): APLD card mixes rule findings and mapping rows; `a e f b` are ignored on mapping rows (`isAsset` guard).
##### Edge Cases
- Keys are ignored while focus is in an input, select or button, and with Cmd/Ctrl/Alt held: after typing a reason and clicking elsewhere in the form, `j` does nothing until focus is back on a row.
- After Save the page fully re-renders (`route`), so every other expanded row closes.
- Focus after Save: same row if it is still listed (Fix), else first row of the page — breaks a top-to-bottom keyboard rhythm when deciding mid-list.
- Duplicate-looking rows (same "segment_capex FY2024" twice) are a scanning hazard: the Item column cannot distinguish them.

#### STORY-021: Bulk-explain GOOGL segment revenue ties for five years
**Type**: medium
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-003
**Persona**: Kenny, who already knows the cause is the same every year
**Goal**: One reason for GOOGL segment_revenue FY2020–FY2025 "Does not tie to reported total"
**Preconditions**: `#reconcile?scope=GOOGL&field=segment_revenue`
**Ideal path**: 4 — filter, Select all, type reason, Save for n
**Alternate paths**: tick each checkbox; keyboard space on each row; from the unfiltered page use "Select all 16" then untick non-GOOGL rows; or decide each row singly (6× STORY-019)
##### Steps
1. From `#reconcile`, choose Scope "Alphabet (GOOGL)" -> `#reconcile?scope=GOOGL`.
2. Choose Field "Segment revenue" -> `#reconcile?scope=GOOGL&field=segment_revenue`; Rule findings card "6 to review of 6", button "Select all 6".
3. Opens FY2023 to confirm the pattern ("…sum to …; the filing tags Revenues … (gap …)"), then FY2021. Same shape, small gaps.
4. Clicks **Select all 6** -> all checkboxes ticked; a bulk card appears above the cards: "**6** selected: GOOGL segment_revenue FY2025; GOOGL segment_revenue FY2024; …" with the Decision btn-group (Accept pressed), Reason placeholder "Why, for all 6, e.g. accrual capex, cash basis differs", **Save for 6**, **Clear**.
5. Clicks **Explain**, types "segments include hedging gains reported outside segments", clicks **Save for 6** -> the bulk card hides immediately (selection cleared before the status can be read), page re-renders 250 ms later; the six rows leave the list.
6. Header "Needs review 10"; with field filter still on, the page shows "No items to review" (no Rule findings card, Category mapping not shown because mappings have no field).
##### Variations
- Untick one row inside the selection: the bulk card text and button update ("Save for 5").
- Space on a focused row toggles selection the same way.
##### Edge Cases
- Server checks every item before writing (`resolve_many`): one bad key refuses all, nothing written; status "Couldn't save: … Try again."
- No "Saved." feedback survives a successful bulk save; the user infers success from the rows disappearing.
- Bulk never offers "Apply to every company?" (encode is single-item only).
- Field filter persists in the URL after the work is done; "No items to review" can read as "queue empty" while 10 items remain under other fields.

#### STORY-022: Bulk select in "Grouped by company" sweeps in mapping rows and fails
**Type**: medium
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-004
**Persona**: Kenny, trying to clear everything for APLD in one go
**Goal**: Explain all open APLD items at once
**Preconditions**: `#reconcile?scope=APLD&group=company`
**Ideal path**: 3 — Select all, reason, Save for n (if the selection only took decidable rows)
**Alternate paths**: Grouped by cause + "Select all 9" on the Rule findings card (works); per-row checkboxes (mapping rows have none)
##### Steps
1. Choose Group by "Grouped by company" -> one card "Applied Digital APLD", header "17 to review of 25" (9 rule findings + 8 Proposed mappings open; 8 "Matches company tag" mappings listed too); button "Select all 17".
2. Kenny assumes it selects the nine rule findings. Clicks **Select all 17** -> bulk card lists "APLD segment_capex FY2026; …; APLD Building; APLD Electrical infrastructure; …" — open Category mapping rows (Proposed) are included, though mapping rows have no checkbox.
3. Picks Explain, types "tie gaps reviewed", clicks **Save for 17** -> "Couldn't save: not a queue item's key (kind|ticker|field|period|dimension|rule_id|subject, a live kind): 'asset_types|APLD|Building'. Try again." Nothing is written.
4. Kenny is confused (mapping rows are "never bulk-selected"); clicks **Clear**, switches back to Grouped by cause, uses "Select all 9" on Rule findings, saves.
##### Variations
- Space on a focused mapping row also adds it to the selection (the `keys` handler has no `isAsset` guard for space), with the same failure.
##### Edge Cases
- BROKEN FLOW: `Select all` is hidden only for the cause-grouped Category mapping card (`assetGroup` is false when grouped by company), and keyboard space has no mapping guard. The server refuses the whole batch (400), so no partial write, but the error text is developer wording.

#### STORY-023: Confirm a run's proposed decision
**Type**: short
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-005
**Persona**: Kenny, after a pipeline run wrote decisions for a person to confirm
**Goal**: Make a run's "explain" on APLD segment_capex FY2025 his own so release gate G6 passes
**Preconditions**: a run line exists (not live today); Release checklist line "Proposed" failing with "Fix in" Reconcile → `#reconcile?cause=to_confirm`
**Ideal path**: 2 — read the proposal, click Confirm
**Alternate paths**: Overturn → Save with the same state (writes the user's own reason instead of "confirmed"); keyboard letter on the row then Save; Release "Fix in" link vs navbar Reconcile
##### Steps
1. On `#release`, the row "Proposed" fails; clicks "Fix in" Reconcile -> `#reconcile?cause=to_confirm`.
2. **To confirm** card first, "1 proposed"; row Item "finding unconfirmed: segment_capex FY2025 (segment_capex_tie)", Dataset/SEC XBRL/Difference "—"; Decision cell **Confirm Explain** and **Overturn**, under them "<run name> · Nov 1".
3. Kenny opens the row to read why -> card "Proposed: Explain" with the run's message, "Company trail" link, and a **Change decision** card (form pre-set to Explain, Reason pre-filled with the run's reason).
4. Satisfied, clicks **Confirm Explain** -> "Saving…" then "Confirmed."; reload after 250 ms; the To confirm card disappears; header "Proposed" count drops by one.
##### Variations
- Confirm straight from the row without opening it (button stops propagation); fastest but decides unseen.
##### Edge Cases
- Empty Signer: Confirm is not disabled (no `needsMe`), the POST fails: "Couldn't save: a resolution needs a state (accept, explain, fix, blocks), a reason and a name." Inconsistent with Approve/Sign which disable with "Enter a signer name".
- `cause=to_confirm` with no proposed rows (today): the Cause select has no "To confirm" option so it shows "Every cause" while the list says "No items to review" — the filter is invisible and the empty state misleads.
- The reason written is the literal "confirmed"; the run's own reasoning stays only on the run line.

#### STORY-024: Overturn a proposed Accept and block the release
**Type**: medium
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-006
**Persona**: Kenny, sceptical of an agent's call
**Goal**: Replace a run's "Accept" on GOOGL ppe_category FY2023 (4 parts sum to $201,803M vs tagged $166,667M, gap $35,136M) with Block release
**Preconditions**: a run line proposes accept for that item (code path; not live today)
**Ideal path**: 4 — Overturn, choose Block release, write reason, Save
**Alternate paths**: open the row and use the Change decision card directly; keyboard `b` on the focused row
##### Steps
1. In the To confirm card, row "finding unconfirmed: ppe_category FY2023 (ppe_categories_tie)" shows **Confirm Accept**.
2. A $35B gap does not look acceptable. Clicks **Overturn** (tooltip "Change decision") -> evidence opens, cursor in the Reason box of **Change decision**; Accept is pressed and the Reason holds the run's text.
3. Hesitates: the pre-filled reason is the agent's, not his. Selects all and deletes it.
4. Clicks **Block release** (tooltip "Blocks release until settled"), types "construction in progress counted twice; do not publish until re-read", **Save** -> "Saved."; reload.
5. The To confirm row is gone; the GOOGL ppe_category FY2023 item now reads "Blocks release" in Rule findings, and the header gains "Blocks release 1".
6. Goes to `#release`: the "Blocks release" line fails; Sign stays disabled ("<n> required checks failing").
##### Variations
- Overturn to Fix: item stays "Needs review" with "Fix · Kenny Geiler · …".
##### Edge Cases
- The same item may appear twice (its own Rule findings row and the To confirm row); deciding either settles the key. Redundant surfaces for one decision.
- Saving the overturn with the pre-filled reason untouched records the agent's words under Kenny's name.

#### STORY-025: Revisit a settled SEC XBRL difference and change the decision
**Type**: medium
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-007
**Persona**: Kenny, after an analyst asks why AMZN Equipment FY2024 shows $218.9B against SEC XBRL $53.5B
**Goal**: Look at the evidence for the settled row and record Explain with a clear reason
**Preconditions**: row is settled (Unverified, explained by a definition), hidden by default
**Ideal path**: 5 — Show settled, filter, open, Explain + reason, Save
**Alternate paths**: Dataset grid cell (≠ mark) → provenance → no decide control there, so the user must come to Reconcile; Company trail `#proof/AMZN` "Review in Reconcile →" (`#reconcile?scope=AMZN`, still needs Show settled)
##### Steps
1. On `#reconcile`, toggles **Show 6 settled** -> URL gains `resolved=1`; new card **Differs from SEC XBRL** "0 to review of 5".
2. Chooses Cause "Differs from SEC XBRL" -> `#reconcile?cause=fact_differs&resolved=1`.
3. AMZN "Equipment FY2024" row: Dataset $218,893,000,000, SEC XBRL $53,509,000,000, red gap bar, Difference "+$165.4B" / "+309%", Decision "Unverified" (no by-line: settled by a definition, not a person).
4. Opens it -> "FY2024 · Cited vs SEC XBRL" table (Cited "“Equipment”", SEC XBRL "Property plant and equipment gross · Equipment · 2024-12-31" with "Restated in a later 10-K", "In v1.8.0" Last release, Difference), a large gap bar, **Source** card (Value 218,893 · Line Equipment · Column December 31, 2024), crop thumbnail with "Open"/"sec.gov ↗", "Company trail", and "By year" (FY2021–FY2023 "Unverified · citation only", FY2024 "Differs from SEC XBRL").
5. Clicks the crop -> lightbox shows the 10-K cell; "Open in filing" opens `/filing/0001018724-25-000004` in a new tab with the cell outlined. Kenny sees Amazon's "Equipment" line is gross servers + networking while the XBRL member is narrower.
6. Back on Reconcile, Decision card shows no header text (no person decision); Accept is pre-pressed. Clicks **Explain**, types "AMZN Equipment includes servers and networking; EquipmentMember tag is narrower", **Save** -> "Saved."
7. Row stays visible (resolved=1); Decision cell now "Unverified" + "Explain · Kenny Geiler · Nov 4".
##### Variations
- Same check from Dataset grid: provenance shows the decision badge (Explained) but offers no write; Reconcile is the only write surface.
##### Edge Cases
- Gap bar, Difference column, the evidence table and the large gap bar all repeat the same Cited-vs-XBRL number four ways on one screen.
- The save posts the hash the page loaded; if a run changed the item meanwhile, `/api/resolve` does not refuse (no Stale check on resolutions), the line is written against the old hash and the row silently stays open after reload.

#### STORY-026: Wrong signer name
**Type**: short
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-009; merged with `reconcile-mapping-encode` STORY-007 (A different name in the Signer box)
**Persona**: a colleague at Kenny's machine who types their own name in Signer
**Goal**: Accept one finding
**Preconditions**: local copy; Signer changed to "Dana Ruiz" (not on `config.PEOPLE`)
**Ideal path**: 1 — Save should be disabled with "Enter a signer name"-style guidance
**Alternate paths**: none found
##### Steps
1. Types "Dana Ruiz" in **Signer** (saved to localStorage).
2. Opens a GOOGL segment_revenue row, Accept, reason, **Save** -> "Couldn't save: 'Dana Ruiz' is not on config.PEOPLE, the people whose resolutions count as a person's; a run writes author_kind run. Try again."
##### Edge Cases
- Empty Signer: Save is enabled; error "a resolution needs a state (accept, explain, fix, blocks), a reason and a name". Approve, Make this a rule and Sign disable instead — inconsistent gating.
- The Signer persists in localStorage, so Kenny's next session also fails until he retypes his name.

##### Merged duplicate: `reconcile-mapping-encode` STORY-007: A different name in the Signer box

**Type**: short
**Topic**: reconcile-mapping-encode
**Persona**: A colleague "Priya" at Kenny's local checkout, not on `config.PEOPLE`
**Goal**: Approve NVDA "Land" (actually it is already Matches company's own tag) and reject AMD "Equipment"
**Preconditions**: Signer box reads "Priya"
**Ideal path**: 1 — the UI should say before the click that this name cannot write
**Alternate paths**: none found (every mapping write goes through the same two routes)
###### Steps
1. Press **Approve** on AMD "Equipment" -> "Couldn’t save: 'Priya' is not on config.PEOPLE, the people who may confirm a mapping." (400)
2. Press **Reject** on the same row -> appears to succeed "Rejected." (`mapper.reject` only checks the name is non-empty, not `config.PEOPLE`) -> the proposal line is removed under Priya's name
###### Edge Cases
- Asymmetric guard: Reject accepts any name, Approve/Choose another/Map refuse; contradicts the discovery note that every write refuses a `by` off PEOPLE. Flag for verification.
- With an empty Signer, Reject is enabled and the server answers 400 "a rejection needs the ticker, the reported name, the member rejected and a name".

#### STORY-027: Clear the whole Rule findings queue before signing v1.9.0
**Type**: long
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-010; merged with `release-sign` STORY-004 (Clear "Needs review" for GOOGL and APLD)
**Persona**: Kenny, end of the week, wants a signable v1.9.0
**Goal**: Leave zero "Needs review" items so the Release "Needs review" line passes
**Preconditions**: 16 open rule findings (APLD 9, GOOGL 7); Signer "Kenny Geiler"
**Ideal path**: ~12 — two filtered bulk saves (GOOGL segment revenue, APLD segment capex) plus per-item decisions for the three "Readings differ" / ppe items with distinct reasons
**Alternate paths**: Release "Fix in" Reconcile; Proof row "<n> to review" → trail → "Review in Reconcile →" per company; keyboard-only (STORY-020); one big Select all 16 with a generic reason (fast, poor audit trail)
##### Steps
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
##### Variations
- Do it all with "Grouped by company" -> trips STORY-022's mapping-row bulk failure.
- Use the Proof board instead of Release to start: row "APLD 9 to review" → `#proof/APLD` → "Review in Reconcile →" → `#reconcile?scope=APLD`.
##### Edge Cases
- The open-count lives on four surfaces (Reconcile header, Release "Needs review" line, Proof "<n> to review" column, trail summary "<k> to review") — redundant but consistent only after a reload of each page.
- Fix has no way to close from the UI: the item stays "Needs review" until a re-read; the tooltip "Wrong; stays open until re-read" is the only hint, so a release blocked by Fix needs CLI work.
- Each single save reloads the whole page and resets expansion; with filters in the URL the context survives, but scroll position and focus move to the first row.
- Filter selects show only causes/fields/kinds present in the loaded rows; after the last GOOGL segment_revenue row is settled, reloading `field=segment_revenue` still filters but the select falls back to its first option, hiding the active filter.

##### Merged duplicate: `release-sign` STORY-004: Clear "Needs review" for GOOGL and APLD

**Type**: medium
**Topic**: release-sign
**Persona**: Kenny, reviewer
**Goal**: Decide the 16 open items (GOOGL 7, APLD 9) so the line passes
**Preconditions**: Needs review Fail 16, detail rows `ticker GOOGL · open 7`, `APLD · open 9`
**Ideal path**: 6 — Fix in scoped to the ticker, select all, one reason, Save for n, repeat for second ticker, back
**Alternate paths**: Proof board row → trail "Review in Reconcile →"; trail header "Reconcile" link (`#reconcile?scope=T`); Reconcile tab + Scope filter; "Release checks by company" ticker link → trail
###### Steps
1. Expand "Needs review" -> detail: GOOGL 7, APLD 9.
2. Click **Reconcile** -> `#reconcile` with every company and cause (69 rows live), not scoped to GOOGL/APLD. Kenny sighs.
3. Set Scope "GOOGL" -> 7 open rows (e.g. "Differs from SEC XBRL" capex rows).
4. Expand the first, read SEC XBRL vs Dataset and the Gap bar -> decides it is a definition difference.
5. Select the rows that share the reason (space / checkboxes) -> "<n> selected" card.
6. Type reason "Google reports purchases of property and equipment net of …" and click **Save for <n>** -> "Saved.".
7. For the odd ones, use **Fix** (stays open until re-read) or **Explain** individually.
8. Set Scope "APLD" and repeat for 9 items; Kenny uses **Block release** on one he cannot settle.
9. Back on **Release** -> "Needs review" Pass but "Blocks release" Fail 1 (detail `APLD · blocked 1`).
###### Variations
- Kenny uses keyboard: j/k, `a` then type reason, Enter.
- After an Accept, "Saved. Apply to every company?" offers **Make this a rule** — writing a rule clears the item on the next run, not now.
###### Edge Cases
- Fix keeps the item "Needs review" until a re-read; the Release line stays red despite a saved decision.
- Detail counts are by ticker only; no link per ticker even though Reconcile supports `scope=`.

#### STORY-028: Filter by check type to review year-over-year jumps
**Type**: short
**Topic**: reconcile-decisions
**Source**: `reconcile-decisions` STORY-011
**Persona**: Kenny, checking whether any large jump is still unexplained
**Goal**: See every "Large year-over-year change" item including settled ones
**Preconditions**: `#reconcile`
**Ideal path**: 2 — pick Check, toggle Show settled
**Alternate paths**: Rules page "To review" list (read-only); typing `#reconcile?kind=jump&resolved=1`
##### Steps
1. Check select (shown because kinds exist) -> choose "Large year-over-year change" -> `#reconcile?kind=jump`; "No items to review".
2. Kenny is unsure whether that means none exist; toggles **Show 6 settled** -> `#reconcile?kind=jump&resolved=1`; one row: APLD opex FY2026, "Unverified", Difference "+$310.2M" "+369%".
3. Opens it: Details "opex moves 4.69× …", table "Prior year / This year / Difference 4.7×", "opex by year" with FY2026 "Unverified · definition". Satisfied, no decision.
##### Edge Cases
- The other kind in the Check select is shown raw as "other" (tie and readings-differ findings carry `kind: other`), so it does not match the card's cause labels ("Does not tie to reported total", "Readings differ across filings").
- "Show 6 settled" counts settled rows across all filters, not within the current filter.

### Topic: Reconcile: category mapping and apply-everywhere (`reconcile-mapping-encode`)

<details><summary>Topic notes (as written by the topic pass)</summary>

Topic `reconcile-mapping-encode`. Written 2026-11-04 from `ledger/web/pages/reconcile.js` (`mappingCell`, `mappingActions`,
`postMapping`, `expectedOf`, `encodePanel`, `canEncode`, `resolutionForm`, `keys`), `pages/_shared.js` (`mappingDecision`),
`pages/trail.js` (mapping stage), `ledger/web/app.py` (`/api/mapping`, `/api/mapping/reject`, `/api/judgement`),
`ledger/review/mapper.py` (`approve`, `reject`, `Stale`, `person`) and `ledger/review/judgement.py` (`offers`), plus a
read-only GET of `/api/v1/reconcile?scope=all`.

Live state used in the stories: 47 "Category mapping" rows (29 Proposed = to_confirm, 18 "Matches company's own tag"),
0 unmapped (so no live row shows **Map** today), and 0 rows that can be encoded (every `encode.rule` / `encode.definition`
carries a `why_not`, and the 5 "Differs from SEC XBRL" rows carry no `encode` at all), so **Apply everywhere** and
"Saved. Apply to every company?" cannot appear on the current data.

</details>

#### STORY-029: Approve a proposed category from the row
**Type**: short
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-001
**Persona**: Kenny Geiler, owner/reviewer, Signer box filled with "Kenny Geiler"
**Goal**: Confirm the mapper's proposal that MSFT's "Land" line is `LandMember`
**Preconditions**: Local copy (not read-only); MSFT "Land" is Proposed (to_confirm), no company tag ("Not tagged"), proposal by "Claude Fable 5.1"
**Ideal path**: 2 — filter to the company's mappings, press Approve on an obvious one-word match
**Alternate paths**: (a) Expand the row and press **Approve** in the decision card (`mappingActions`); (b) from `#proof/MSFT`, Category mapping stage card → "Decide in Reconcile →" (lands on `#reconcile?scope=MSFT&cause=asset_types`); (c) choose `LandMember` explicitly via the card's "Standard category" select + **Choose another** (writes the same member as a confirm, not a replace)
##### Steps
1. Open `#reconcile`, set Scope to "Microsoft (MSFT)" and Cause to "Category mapping" -> URL becomes `#reconcile?scope=MSFT&cause=asset_types`; one card "Category mapping" with header tally "6 proposed · 0 unmapped · 0 differ from company tag · 0 match company tag"
2. Scan the "Land" row: Dataset column shows "Land" + orange "Proposed", the quoted evidence "the note's own category name …" and "Not tagged" -> Kenny thinks: "Land is Land, no need to open it"
3. Press **Approve** in the Decision column -> status "Saving…", then "Confirmed." (the row is an existing entry, so the word is Confirmed, not Mapped), page reloads after 250 ms
4. The row stays listed (asset rows are always listed) but leaves Proposed; the header Proposed count and the card tally each drop by 1
##### Variations
- Approve on a row whose proposal came from nothing on file (mapping `unmapped` with a proposal) shows "Mapped." instead of "Confirmed."
- Grouped by company (`group=company`) shows the same row under "Microsoft MSFT" with Cause column "Category mapping".
##### Edge Cases
- Signer box empty -> **Approve** is disabled with tooltip "Enter a signer name"; **Reject** and the row's **Choose another** are not disabled (they are not wrapped in `needsMe`).
- Double-click: the button disables itself on the first click; a second POST cannot fire.
- Read-only copy: **Approve** renders enabled; click -> "Couldn’t save: this copy of Kenny's Data Emporium is read-only; …." inline in red.
- Redundancy: the same proposal (member, evidence, company tag) is shown on the row, in the expanded decision card, and on the trail's Category mapping stage card.

#### STORY-030: Stale Approve gets "Changed since loaded. Reloading."
**Type**: short
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-002
**Persona**: Kenny, with Reconcile open in two browser tabs
**Goal**: Confirm GOOGL "Office space" → `BuildingAndBuildingImprovementsMember`
**Preconditions**: Tab A and tab B both loaded `#reconcile?scope=GOOGL&cause=asset_types`; in tab B he already rejected the proposal (line removed from `taxonomy/asset_types.yaml`)
**Ideal path**: 1 — a stale click should explain itself and refresh without data loss
**Alternate paths**: The same 409 is reachable from the decision card's **Approve** and **Choose another** (both send `expected`); **Reject** never 409s (it sends no `expected`)
##### Steps
1. In tab A press **Approve** on "Office space" -> "Saving…"
2. Server compares `expected` {standard_type: BuildingAndBuildingImprovementsMember, at: 2026-11-01} with the file (now no entry) -> 409 -> status turns red "Changed since loaded. Reloading."
3. After 800 ms the page re-routes -> the row now shows "No proposal" and a primary **Map** button; the expanded card would show "Rejected: Building and building improvements"
4. Kenny thinks: "Fine, it was me in the other tab" — but the message does not say what changed or who changed it
##### Variations
- Mapper rerun between load and click (proposal `at` date changed) -> same 409, page reloads showing the new proposal.
##### Edge Cases
- If the other tab *confirmed* it instead, `expected` still matches (same member and `at`), so no 409; the server raises "… is already mapped to … and confirmed by Kenny Geiler" -> 400 shown as "Couldn’t save: …." with no reload. The two "someone else got there first" cases surface differently.
- Any text typed nowhere is lost on reload, but mapping has no free-text field, so nothing is lost.

#### STORY-031: Reject a wrong proposal and pick the right member
**Type**: medium
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-003
**Persona**: Kenny, cautious about AI-proposed buckets for AI capex
**Goal**: Fix APLD "Information Systems and Software", proposed as `TechnologyEquipmentMember` while APLD's own XBRL tag says Software
**Preconditions**: Row shows red "Company tags SoftwareAndSoftwareDevelopmentCostsMember" under the proposal; header tally includes "differ from company tag"
**Ideal path**: 3 — open the row, pick the company's member, Choose another (one write replaces the proposal)
**Alternate paths**: (a) Row **Choose another** → expands the row and focuses the select (same as clicking the row); (b) **Reject** first, wait for re-render, then **Map** with the select (two writes, leaves a "Rejected" log line); (c) arrive from `#proof/APLD` "Decide in Reconcile →"
##### Steps
1. `#reconcile?scope=APLD&cause=asset_types` -> card header "11 proposed · 0 unmapped · 3 differ from company tag · 8 match company tag" (counts as live)
2. Kenny notices the red "Company tags SoftwareAndSoftwareDevelopmentCostsMember" under "Technology equipment · Proposed" -> hesitates: "Is the line hardware or software? The FY2023 number is only $21.2M"
3. Click the row (or Enter) -> evidence opens: decision card (name, state "To confirm", Company line "$21.2M FY2023" + "Open ↗", Proposed with definition and "Source: …", Company’s own tag "Differs: Software and Software Development Costs …" with the definition, Basis, Alternatives "Software and Software Development Costs · … · why", Affects "2 figures · $21.2M FY2023") and a "Note wording" card
4. Expand the "Alternatives" disclosure to read the Software definition -> satisfied it matches
5. In the "Standard category" select (the proposed Technology Equipment is filtered out, so the list starts at "Computer Equipment") choose "Software and Software Development Costs"
6. Press **Choose another** -> "Saving…" -> "Mapped." -> reload; the entry is replaced, confirmed by Kenny today
##### Variations
- Path (b): **Reject** -> "Rejected." -> reload -> row now "No proposal" with **Map**; the select now also omits the rejected member; **Map** writes the new entry -> "Mapped.". Next mapper run will not re-propose the rejected member; if it does, the card shows orange "Proposed again after rejection: …".
##### Edge Cases
- The select defaults to its first option, not to the company's tagged member; pressing **Choose another** without touching the select maps to whatever is first (e.g. "Computer Equipment"). No confirmation step.
- Choose another on the row does not write anything — it only opens the card. Two controls with the same label do different things (row = open, card = write).
- Escape does not collapse the row while focus is in the select (`keys` ignores events from inputs/selects/buttons).
- Reject's reason is fixed text "rejected on Reconcile"; there is no field to say why.

#### STORY-032: Override a "Matches company's own tag" mapping
**Type**: medium
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-004
**Persona**: Kenny, second-guessing AMZN "Heavy equipment"
**Goal**: Decide whether "Heavy equipment" belongs in `MachineryAndEquipmentMember` or something narrower
**Preconditions**: Row state "Matches company's own tag" (verification `company`, mapping `verified`, by `mapping:filer_tag`); not open, but still listed after the open rows
**Ideal path**: 2 — open and approve or choose; the row is already settled, so confirming should be optional
**Alternate paths**: `#proof/AMZN` Category mapping stage → collapsed tally → expand → "Confirm or override in Reconcile →"
##### Steps
1. `#reconcile?scope=AMZN&cause=asset_types` -> asset rows sorted open first; "Heavy equipment" sits below the 4 Proposed rows with green "Matches company’s own tag"
2. Kenny wonders why a settled row still has **Approve / Reject / Choose another** -> the code keeps them "so a person can override it"
3. Open the row -> decision card: Company’s own tag "Same as proposed", Affects "2 figures · $65,545M FY2025"
4. Press **Approve** -> "Confirmed." (adds confirmed_by/at) or **Reject** -> server refuses only if already person-confirmed; a filer-tag line is removed and the category becomes unmapped
##### Variations
- Choose "Equipment" from the select -> **Choose another** replaces the filer-tag line with Kenny's entry.
##### Edge Cases
- Rejecting a filer-tag match throws away the strongest evidence class (company's own XBRL) with one click and no confirm dialog.
- The header "Proposed" counter does not include these 18 rows, but the card header tally does ("18 match company tag" across companies) — two counts of the same group on one page.

#### STORY-033: Work through all MSFT mappings by keyboard
**Type**: long
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-005
**Persona**: Kenny, doing the "five times a company" pass the code comment describes, keyboard first
**Goal**: Settle all 6 Proposed MSFT categories (Buildings and improvements, Computer equipment and software, Furniture and equipment, Land, Leasehold improvements, Servers, network equipment, and software)
**Preconditions**: Signer "Kenny Geiler"; all 6 to_confirm, none tagged by the company
**Ideal path**: 12 — 6 rows × (move + decide), no reload jumps
**Alternate paths**: Mouse on row buttons; via the decision card; arrive from `#proof/MSFT` → "Review in Reconcile →" (lands unfiltered by cause) or the stage's "Decide in Reconcile →"
##### Steps
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
##### Variations
- Mouse-only: row **Approve** is 1 click per row, faster than the keyboard route.
##### Edge Cases
- Pressing space on a mapping row adds it to the selection (the space handler does not check `isAsset`), showing the "<n> selected: …" bulk card even though mapping rows have no checkbox; **Save for n** then posts mapping keys to `/api/resolve/bulk`, which appears to refuse the whole batch (key names no dataset row) — likely broken flow.
- Every write reloads the whole page and resets focus to the first row; long lists mean repeated scrolling.
- Same Affects / Company line facts appear on the trail card and the Reconcile card (redundant by design: shared `mappingDecision`).

#### STORY-034: Map an unmapped category with no proposal
**Type**: short
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-006
**Persona**: Kenny, after a new AMD 10-K adds a line the mapper did not propose for
**Goal**: Give AMD "Data center equipment" a standard member
**Preconditions**: Row with mapping `unmapped`, no proposal (not live today: 0 unmapped rows); Dataset column "No proposal"
**Ideal path**: 3 — open, select member, Map
**Alternate paths**: Row **Map** (primary button, opens the card and focuses the select); clicking the row
##### Steps
1. Row shows "No proposal" and a blue **Map** button (no Approve/Reject) -> click **Map** -> card opens, "Standard category" select focused; card Proposed reads "None"
2. Choose "Technology Equipment" -> press card **Map** -> "Mapped." -> reload
##### Variations
- `expected` is null for an unmapped row; if the mapper wrote a proposal meanwhile, 409 "Changed since loaded. Reloading."
##### Edge Cases
- Empty Signer: card **Map** disabled ("Enter a signer name") but the row **Map** still opens the card — the user can go one step before finding the block.
- Server refuses a member off the list (400) — not reachable from the select.

#### STORY-035: Explain a renamed line once and make it a rule
**Type**: medium
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-008
**Persona**: Kenny, tired of explaining the same "Line renamed" finding every year
**Goal**: Explain a `row_label_switch` finding on GOOGL capex and write it as a rule for every company reading those lines
**Preconditions**: A finding_unconfirmed row of rule `row_label_switch` with a field the company reads from at least one line (not present on live data; all live findings are tie/jump rules whose `encode.rule.why_not` hides the panel)
**Ideal path**: 3 — decide Explain with a reason, then one click on Make this a rule reusing that reason
**Alternate paths**: (a) Expand the row → **Apply everywhere** card at the bottom (`once`) → **Make this a rule** without saving a decision first; (b) after Save on Accept or Explain → "Saved. Apply to every company?" panel (same `encodePanel`); (c) keyboard `e` opens the row with Explain pre-pressed
##### Steps
1. `#reconcile?scope=GOOGL&kind=row_label_switch` (Check select "Line renamed") -> row under "Rule findings"
2. Press `e` on the row -> evidence opens, Decision card with **Explain** active and Reason focused
3. Type "Google renamed 'Purchases of property and equipment' to 'Capital expenditures'; same line" -> **Save** -> status "Saved. Apply to every company?" with the encode panel and a **Done** button (the page does not reload yet)
4. Panel line "Applies to: every company reading “Purchases of property and equipment”, “Capital expenditures”"; Reason input pre-filled with his reason, placeholder "Reason (applies to every company)"
5. Kenny hesitates: "every company" — the labels are specific, so it is narrow enough -> press **Make this a rule** -> "Writing…" -> "Saved to rules/<id>.yaml. Applies on the next run."
6. Press **Done** -> page reloads; the row stays until the next `ledger rules` run
##### Variations
- Pressing **Done** without writing skips the rule; the Explain decision is kept.
- Reason cleared -> "Reason required" and focus to the input.
##### Edge Cases
- After writing, the same rule offer reappears on reload with `why_not` "already on file … rerun ledger rules", so the panel silently disappears — no on-page sign a rule was written until the run.
- Bulk **Save for n** never offers the encode panel; Fix and Block release never offer it.
- Redundancy: the same panel appears both as the "Apply everywhere" card in the expanded row and inside the post-save status; a user can write from the card, then Save, then see it again.
- Encode failures read "Couldn’t write: …." (different verb from decisions' "Couldn’t save: …. Try again.").

#### STORY-036: Write a company definition for a blocked revenue disagreement
**Type**: medium
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-009
**Persona**: Kenny, NVDA FY2025 revenue blocks release because the SEC tag counts something different
**Goal**: Explain once in `definitions/companies.yaml` that NVDA's revenue definition differs
**Preconditions**: A "blocked" item of `xbrl_reconcile` on revenue FY2025 for NVDA, no NVDA revenue definition on file (none live today)
**Ideal path**: 2 — expand, Make this a definition with reason
**Alternate paths**: Save Explain first → "Saved. Apply to every company?" → **Make this a definition**; `b` key opens with Block release pre-pressed (wrong default for this goal)
##### Steps
1. `#reconcile?cause=blocked&scope=NVDA` -> the Blocks release card
2. Open the row -> **Apply everywhere** card: "Applies to: NVDA · FY2025", placeholder "Reason (this company)"
3. Kenny notes the card title says "Apply everywhere" while the line says this company only -> mild confusion
4. Type "SEC Revenues tag includes … ; the 10-K line is net revenue" -> **Make this a definition** -> "Saved to definitions/companies.yaml. Applies on the next run."
##### Variations
- Cost-lines definition (`cost_lines_summed`): "Applies to: NVDA · “Cost of revenue — products” + “Cost of revenue — services”".
##### Edge Cases
- NVDA already has a revenue definition -> `why_not` "edit it by hand" -> the panel just does not render; the reason is never shown in the UI.
- Signer empty -> button disabled, tooltip "Enter a signer name".

#### STORY-037: Full company: trail → mapping → decision → encode → Proof
**Type**: long
**Topic**: reconcile-mapping-encode
**Source**: `reconcile-mapping-encode` STORY-010
**Persona**: Kenny, trying to get APLD from "to review" toward "Proven" in one sitting
**Goal**: Clear APLD's 11 Proposed mappings and settle its findings, writing a rule where the code allows
**Preconditions**: Live APLD state: 11 Proposed mappings (5 company extension tags, 3 differ), 16 findings mostly tie rules (none encodable)
**Ideal path**: ~25 — 11 mapping decisions + ~10 finding decisions + navigation
**Alternate paths**: Start at `#proof` board row APLD; or the jump box "APLD" → `#data?ticker=APLD` → ticker cell → trail; or `#release` "Fix in" → Reconcile (unscoped)
##### Steps
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
##### Variations
- Grouped by company (`group=company`) shows mappings and findings for APLD in one card, avoiding the Cause switch.
##### Edge Cases
- No live item offers encoding, so the "write it once" promise is unreachable on this data; the user cannot tell why (why_not never shown).
- "Select all <n>" is hidden on the mapping card (mappings are never bulk), so 11 separate decisions are required.
- Each mapping write reloads and returns focus to the first row.

### Topic: Release checklist and signing — UX path stories (`release-sign`)

<details><summary>Topic notes (as written by the topic pass)</summary>

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

</details>

#### STORY-038: Why can't I sign v1.9.0 today?
**Type**: short
**Topic**: release-sign
**Source**: `release-sign` STORY-001
**Persona**: Kenny Geiler, owner/signer, at the local checkout
**Goal**: Find out in one glance whether v1.9.0 is signable and what is stopping it
**Preconditions**: Local copy, Signer "Kenny Geiler"; checklist red on Proposed, Needs review, Golden test
**Ideal path**: 2 — open Release, read the header count and the disabled button's status line
**Alternate paths**: Proof → Releases card note "Next release" → `#release`; Docs flow diagram box "Release" → `#release`; read `/api/v1/release/checklist` (`red` array) directly; CLI `ledger release` prints `checklist_table`
##### Steps
1. Click the navbar tab **Release** -> Page header "Release", subtitle "**v1.9.0** · Compared with v1.8.0 · 6 companies · **12 of 15** required checks pass".
2. Look at the right of the header -> Button **Sign v1.9.0** is greyed out; under it "3 required checks failing"; hovering the button shows the same words as a tooltip.
3. Scan the checklist table (sorted fail first by the State column's sort key, though the table opens in server order) -> Three red "Fail" rows: "Proposed" 29, "Needs review" 16, "Golden test" 1. Kenny thinks: "two of these are Reconcile work, the golden one is the last APLD hand-check item."
##### Variations
- Kenny clicks the **State** header to sort; fails go first (fail 0, stale 1, not run 2, info 3, pass 4).
- If only the Test run line were "Stale", the count would still say "1 required check failing" with no hint it is a re-run, not a data fix; he has to read Details ("stale (HEAD is …): run `ledger test`").
##### Edge Cases
- The status text never names which lines fail; the user has to scan the table. The JSON `red` array (`gate_G6, open, golden`) is not shown.
- Redundancy: the same three numbers appear on Proof (company rows "<n> to review", Hand check "119 of 120"), Reconcile header (Needs review / Proposed counts) and here.

#### STORY-039: Work down the 29 Proposed asset-type mappings
**Type**: long
**Topic**: release-sign
**Source**: `release-sign` STORY-003
**Persona**: Kenny, signer and reviewer
**Goal**: Clear the "Proposed" line (G6) by approving or correcting Claude's asset-type proposals for all six companies
**Preconditions**: Proposed Fail, 29; detail rows like `asset_types|AMD|Construction in progress` · to confirm · "ConstructionInProgressMember proposed by Claude Fable 5.1" · `reconcile?scope=AMD&cause=asset_types`
**Ideal path**: ~33 — open the list once, then one decision per mapping (29) plus navigation; bulk is not allowed for mappings by design
**Alternate paths**: Reconcile navbar tab → Cause "Category mapping"; Proof → company trail → Category mapping stage "Decide in Reconcile →"; the "Release checks by company" G6 column shows per-ticker counts; Reconcile header "Proposed" count
##### Steps
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
##### Variations
- Use Group by "Grouped by company" instead of Scope to walk all tickers on one page.
- Start from the "Release checks by company" table: click ticker "AMD" -> `#proof/AMD` trail, Category mapping stage → "Decide in Reconcile →".
- Keyboard: j/k to move, Enter to expand; a/e/f/b do not apply to mapping rows.
##### Edge Cases
- "Select all <n>" never includes mappings, so 29 single clicks is the floor.
- Rejecting a mapping (**Reject**) moves it to Unmapped, which then counts under "Needs review" (note "…asset types with no entry (Reconcile, asset types)"): one red line turns into another.
- Redundancy: G6 count appears in the Proposed line, its detail, the by-company gate table, the Reconcile header "Proposed", and Proof board cells.
- If a run's to-confirm decisions also exist, the Fix in link becomes plain `#reconcile` (both causes) instead of `cause=asset_types`.

#### STORY-040: Sign and publish v1.9.0 (happy path)
**Type**: short
**Topic**: release-sign
**Source**: `release-sign` STORY-005
**Persona**: Kenny, signer
**Goal**: Sign and publish once every required line is green
**Preconditions**: All 15 required lines Pass; Signer "Kenny Geiler"; Postgres reachable
**Ideal path**: 3 — open Release, click Sign, confirm
**Alternate paths**: CLI signoff/publish commands (no UI); no other page has a Sign control
##### Steps
1. Open **Release** -> "15 of 15 required checks pass"; status "Signs and publishes v1.9.0"; button **Sign v1.9.0** enabled.
2. Glance at "Packet v1.9.0" card (File · Rows · Bytes, note "Fingerprint 5c50eaf3") and "Changes since v1.8.0" (taxonomy.csv 164 changed, values.csv +10 …) -> Kenny sanity-checks the diff.
3. Click **Sign v1.9.0** -> Browser dialog "Sign and publish v1.9.0 as Kenny Geiler?"
4. Click OK -> Button disables; status "Signing v1.9.0…".
5. Wait -> green "v1.9.0 signed by Kenny Geiler · <time> · 5c50eaf3 · Published: <n> values, …"; after 2.5 s the page moves to `#proof`.
6. On Proof, Releases card -> top row "v1.9.0 · Kenny Geiler, <date> · 81 values · To review at signing 0 · Unmapped at signing 0 · 6: MSFT, GOOGL, AMZN, NVDA, APLD, AMD · Download".
##### Variations
- Kenny clicks Cancel in the confirm dialog -> nothing happens, button stays enabled.
##### Edge Cases
- Data changed between checklist and sign -> red "the data changed while the checklist was built; reload and sign again"; button re-enabled but the page is stale — he must reload.
- A required line turns red during the write -> "v1.9.0 not signed: … is red on the checklist"; releases/v1.9.0/ stays on disk unsigned and becomes the next version to sign.
- Two quick clicks: server lock serializes; the button is disabled after the first.
- The 2.5 s redirect gives little time to read or copy the hash; the same hash is not shown on Proof (only the Release page's "Fingerprint").

#### STORY-041: Signed, not published — and what now?
**Type**: medium
**Topic**: release-sign
**Source**: `release-sign` STORY-006
**Persona**: Kenny, signer
**Goal**: Understand and recover from a publish failure after signing
**Preconditions**: All required lines green; Postgres down
**Ideal path**: 4 — sign, read the error, retry publish from the page, verify on Proof (today the retry has no UI)
**Alternate paths**: CLI `ledger publish` (the only retry); Proof Releases "Signed" cell shows " · not published"
##### Steps
1. Click **Sign v1.9.0**, OK -> "Signing v1.9.0…".
2. Result -> green "v1.9.0 signed by Kenny Geiler · <time> · 5c50eaf3" then red "Signed, not published: <psycopg error>". Page stays (no redirect).
3. Kenny looks for a Retry/Publish button -> none; button re-enable logic does not run on success, it stays disabled.
4. Reload `#release` -> The page now shows the **next** version (v1.10.0, minor bump), compared with v1.9.0; nothing on Release mentions the unpublished v1.9.0.
5. Go to **Proof** → Releases -> "v1.9.0 · Kenny Geiler, <date> · not published" (red) with **Download**.
6. In a terminal, run `ledger publish` once Postgres is back -> SIGNOFF.json records published true; Proof drops the red marker.
##### Variations
- Kenny downloads the packet anyway from Proof's **Download** — it works because packet only needs SIGNOFF.json.
##### Edge Cases
- Broken flow: recovery is CLI-only and the Release page forgets the state after reload; only Proof's red " · not published" remains.
- Releases v1.1.0–v1.7.0 have `published` null (signed before it was recorded) and show no marker either way — indistinguishable from published.
- A `record_error` (SIGNOFF note failed to land) is returned in the JSON but never displayed.

#### STORY-042: Signer box empty or changed while on the Release page
**Type**: short
**Topic**: release-sign
**Source**: `release-sign` STORY-007
**Persona**: Kenny on a shared laptop where a colleague cleared the Signer box
**Goal**: Get the Sign button enabled
**Preconditions**: Every required line green; the Signer box was cleared on another page in this tab (an empty stored value falls back to "Kenny Geiler" on a page load, so the empty state only exists in memory)
**Ideal path**: 2 — type name, click Sign (should enable live)
**Alternate paths**: none found (the Signer box in the header is the only place to set the name)
##### Steps
1. Click navbar **Release** with the Signer box empty -> Button disabled, status "Enter a signer name".
2. Type "Kenny Geiler" in **Signer** -> Button stays disabled; status unchanged (the page computed it at render).
3. Click navbar **Release** again -> Nothing happens (same hash, no hashchange).
4. Go to Proof and back, or reload (a reload also restores "Kenny Geiler" by default) -> Button enabled, "Signs and publishes v1.9.0".
##### Variations
- Reverse: page rendered enabled, then Kenny clears the Signer box -> button stays enabled; clicking shows "Sign and publish v1.9.0 as ?" and the server answers 400 "a signature needs a name", shown red; button re-enabled.
##### Edge Cases
- Broken flow: unlike Reconcile/Proof write buttons, which read `me` at click, the Release button's disabled state is frozen at render.
- Signer "Pat Lee" (not in `config.PEOPLE`) can sign: `sign()` only refuses an empty name, so SIGNOFF.json records any name typed — inconsistent with every other write (400 for names off PEOPLE).

#### STORY-043: Download a release packet for an analyst
**Type**: short
**Topic**: release-sign
**Source**: `release-sign` STORY-008; merged with `proof-hand-check` STORY-010 (Download the last signed packet from Proof), `readonly-visitor` STORY-003 (Download the latest signed release packet)
**Persona**: A data consumer (or Kenny sending a packet to Arctal)
**Goal**: Get the v1.8.0 packet zip
**Preconditions**: v1.8.0 signed and published
**Ideal path**: 2 — open Proof Releases, click Download
**Alternate paths**: direct URL `/packet/v1.8.0.zip`; per-list CSV via Dataset **CSV** links or `/api/v1/<list>.csv` (current data, not the frozen release)
##### Steps
1. Click navbar **Proof**, scroll to **Releases** -> table of the 6 newest: v1.8.0, v1.7.0, v1.6.0, v1.5.0, v1.4.0, v1.3.0.
2. Click **Download** on v1.8.0 -> Browser saves `capex-ledger-v1.8.0.zip` (~93 KB) holding `capex-ledger-v1.8.0/` values.csv, taxonomy.csv, DIFF.md, LIMITATIONS.md, README.md, manifest.json, SIGNOFF.json…
##### Variations
- Visitor first opens **Release** expecting downloads -> only the unsigned next version's "Packet v1.9.0" file list; no download link there. They must go to Proof.
##### Edge Cases
- Older releases (v1.2.0 and earlier) are not in the table (slice of 6); v1.0.0 has no README so even in the table it would show no Download, yet `/packet/v1.0.0.zip` serves it.
- v1.2.0 is unsigned: `/packet/v1.2.0.zip` → 404 `{"error": "not found"}` (raw JSON in the tab).
- Read-only hosted copy: download works (GET).
- Redundancy: the packet's file list appears twice on Release (expanded "Packet v1.9.0" line detail and the "Packet v1.9.0" card).

##### Merged duplicate: `proof-hand-check` STORY-010: Download the last signed packet from Proof

**Type**: short
**Topic**: proof-hand-check
**Persona**: An analyst wanting the release that carried the hand check
**Goal**: Get v1.8.0's packet zip
**Preconditions**: v1.8.0 signed with a packet
**Ideal path**: 1 — click Download
**Alternate paths**: Release page "Packet <v>" card (current candidate only); direct `/packet/v1.8.0.zip`
###### Steps
1. On `#proof`, find "Releases" -> rows newest first (max 6): Version, Signed "Kenny Geiler, <date>" (or "Not signed", red "· not published"), Values, To review at signing, Unmapped at signing, Companies "6: MSFT, GOOGL, …".
2. Click "Download" on v1.8.0 -> browser downloads `/packet/v1.8.0.zip`.
###### Variations
- A release signed before the checklist existed shows "—" in the at-signing columns.
###### Edge Cases
- Hand-check state at signing is not one of the Releases columns; the release record does not show whether gold passed when it was signed.

##### Merged duplicate: `readonly-visitor` STORY-003: Download the latest signed release packet

**Type**: short
**Topic**: readonly-visitor
**Persona**: Marcus, an analyst at a fund evaluating the dataset; wants the files, not the UI
**Goal**: Get the newest signed release as a zip
**Preconditions**: Hosted read-only copy; releases through v1.8.0 signed with packets; v1.9.0 unsigned
**Ideal path**: 2 — open the page that lists releases, click the newest packet download
**Alternate paths**: direct URL `/packet/v1.8.0.zip`; Release page (`#release`) shows "Packet v1.9.0" contents for the *unsigned* next version (File, Rows, Bytes, "Fingerprint <hash8>") but has no download link; Dataset Rows **CSV** / **JSON** per list as a substitute
###### Steps
1. Lands on Proof (default route), scrolls to "Releases" -> table Version, Signed, Values, To review at signing, Unmapped at signing, Companies, Packet; newest six rows, latest first; v1.8.0 "Signed … · Kenny Geiler", Packet "Download".
2. Clicks "Download" on v1.8.0 -> browser saves `capex-ledger-v1.8.0.zip` (`Content-Disposition: attachment`); no read-only interference, it is a GET.
###### Variations
- Wants an older one (v1.3.0): visible because the table shows the last six; v1.1.0 and earlier are cut off by `.slice(0, 6)` — only reachable by typing `/packet/v1.1.0.zip`.
- Clicks "Next release" under the table -> `#release`, sees v1.9.0's checklist and packet table, no download.
###### Edge Cases
- Releases v0.1.0–v1.0.1 and v1.2.0 have `packet: false`: empty Packet cell, no explanation.
- A typed version without a packet returns an error JSON in the browser tab rather than a page.
- Packet contents described on Release ("Packet v1.9.0") and downloadable on Proof ("Releases") — two surfaces for one concept, split by signed/unsigned.

#### STORY-044: Read an old release's checklist via ?version=
**Type**: short
**Topic**: release-sign
**Source**: `release-sign` STORY-009
**Persona**: Kenny auditing what v1.8.0's signature meant
**Goal**: See the checklist for a past version
**Preconditions**: v1.8.0 signed
**Ideal path**: 2 — from Proof's Releases row to that release's checklist at signing
**Alternate paths**: Proof Releases columns "To review at signing", "Unmapped at signing", "Companies" (summary of SIGNOFF.json's checklist); SIGNOFF.json inside the packet zip
##### Steps
1. Type `#release?version=v1.8.0` in the address bar (no UI link exists) -> Page "v1.8.0 · Compared with v1.7.0 …" built from **today's** data, not as signed.
2. "Packet v1.8.0" line -> Fail, "v1.8.0 is already signed; a shipped release is never edited. Use a new version." Button **Sign v1.8.0** disabled.
3. Kenny realizes this is a re-computation; he goes to Proof → Releases to read the at-signing counts (0 · 0 · 6 companies).
##### Variations
- `#release?version=v2` -> page error "not a version: 'v2' (vMAJOR.MINOR.PATCH)".
- `#release?version=v1.2.0` (unsigned, older than a signed release) -> checklist runs; Packet line compares folder hash ("…built before this release's checks; delete and rebuild" if different).
##### Edge Cases
- The query param is undocumented in the UI and the page title gives no "as signed" vs "now" cue; easy to misread as historical.

#### STORY-045: Full pre-release pass from Proof to published
**Type**: long
**Topic**: release-sign
**Source**: `release-sign` STORY-011
**Persona**: Kenny on release day, wanting v1.9.0 out before sending the dataset to Arctal
**Goal**: Go from "3 required checks failing" to a published v1.9.0 and a packet in hand
**Preconditions**: Live state (Proposed 29, Needs review 16, gold 1 unchecked)
**Ideal path**: ~45 — 29 mapping decisions + ~4 grouped review saves + 1 gold verdict + test rerun + sign/confirm + download
**Alternate paths**: Start at Reconcile instead of Release; start at Proof board rows; per-company via trails; CLI `ledger release` to read the checklist as text
##### Steps
1. Proof -> header "0 of 6 proven"; every company "<n> to review". Kenny clicks "Next release" in the Releases card note -> `#release`.
2. Read "12 of 15 required checks pass", button disabled "3 required checks failing".
3. Expand "Release checks by company" view (no expansion needed: G1/G4/G5 "·", G6 counts per ticker, Result Fail for each with proposals).
4. Fix in **Reconcile** on "Proposed" -> do STORY-039 (≈29 Approve/Choose another clicks).
5. Back to Release (navbar) -> Proposed Pass; "13 of 15".
6. Fix in **Reconcile** on "Needs review" -> scope GOOGL then APLD, bulk Accept/Explain with reasons (STORY-027).
7. Back to Release -> Needs review Pass; check "Blocks release" still Pass and "Answer-key values missing from the dataset" still 0 (an Accept that blanks a value could trip it).
8. Fix in **Proof** on "Golden test" -> header "Hand check" link -> APLD -> **Right** on the last item.
9. Terminal: rerun tests/golden -> reload Release: Golden test Pass, Test run Pass (fresh commit, clean tree — if he committed the gold verdict; a dirty tree makes Test run "Stale").
10. Review info lines: "Rows with no value 118" (Fix in **Dataset** → `#data?list=taxonomy&has_value=false`), "Rows changed since v1.8.0 174", "Limitations with no mitigation 2" (Fix in **Release** — links to itself), "Known gaps: 0 stub · 3 stale · 37 open findings" (Fix in **Known gaps**).
11. Check "Claims register" and "Claims doc current" Pass; if Claims doc fails he runs `ledger claims` and commits, then reruns tests (commit moves HEAD → Test run stale).
12. Click **Sign v1.9.0** → OK -> "Signing…" → signed · Published → redirect to Proof.
13. Proof → Releases → v1.9.0 **Download** -> zip saved for Arctal.
##### Variations
- He works from Reconcile's own header counts and never visits Release until the end; same result, fewer back-and-forths but no single "what's left" view outside Release.
##### Edge Cases
- Ordering trap: committing the gold verdict or claims doc after the test run makes "Test run" Stale; tests must be the last step before Sign.
- "Fix in" for Limitations and Previous releases points to Release itself — a dead end.
- Redundancy: "Known gaps" line duplicates the Known gaps page header counts; "Rows changed" line detail duplicates the "Changes since v1.8.0" card.

### Topic: Dataset and Explore: user journey stories (`dataset-explore`)

<details><summary>Topic notes (as written by the topic pass)</summary>

Topic: **dataset-explore**, the consumer read path. Written 2026-11-04 from `ledger/web/pages/data.js`,
`pages/explore.js`, `pages/_shared.js`, `pages/_router.js` and `app.py`, with read-only GETs against the local copy on
port 3610 (617 taxonomy rows, 81 values, 327 facts, 227 statements, 182 projects, 6 companies, 4 saved views).

Surfaces covered: `#data` (Rows view, list sidebar, Company select, "Every row / With a value / Without a value",
"Find in rows", **CSV** / **JSON**), `#data?view=grid` (Field, Companies incl. "Custom…" drawer, Kind, cells, provenance
drawer, **Export CSV**), `#company/<T>`, `#tables/<list>`, header jump box, `#explore` (controls, Plotly chart, "Data"
disclosure, "Show rows", bar click, **Save as view** / **Save changes** / **Delete**, JSON / CSV links), `#explore/<id>`,
`#views/<id>`, `/api/v1/<list>[.csv]`.

Findings recorded inside the stories (for the redundancy and friction passes):

- **Broken: Save as view / Save changes / Delete.** `api()` posts without `Content-Type: application/json`; the server
  answers 403 "a write needs Content-Type: application/json". Save shows that text in the drawer; Delete has no
  try/catch, so the rejection is unhandled and the page silently stays put (STORY-052, STORY-053).
- **Broken saved view:** "What companies state about AI, in dollars" (`company-stated-ai`) has `chart: null`,
  `show: grid`; Explore falls back to x = `period`, which taxonomy rows do not have, so it renders "No rows match" for
  118 rows that exist (STORY-051).
- **Explore JSON / CSV links drop filters:** they carry only field, kind, layer, ticker; the taxonomy Measure,
  Category, Standard type and From/To are left out, so the "Capex by layer, by year" CSV holds all 617 taxonomy rows
  instead of the 27 capex rows charted (STORY-050).
- **Grid "Custom…" cannot be reopened** once the selection is already custom (the select's `change` does not fire on
  the already-selected option); an empty Custom selection, or an industry with no companies in scope (e.g. "Power
  producer"), silently means every company (STORY-048, STORY-049).
- **"Find in rows" is not in the URL**: lost on Back, refresh or a list switch; it matches the whole row as JSON, so
  "capex" also hits URLs and concept names (STORY-046).
- **Redundancy:** a company's figures can be read in five places (Dataset Rows, Dataset Grid, Explore "Show rows",
  Company trail `#proof/<T>`, Reconcile evidence); CSV export exists three ways (Rows **CSV** = server
  `/api/v1/<list>.csv`, Grid **Export CSV** = client-side blob with different columns, Explore **CSV** =
  `?format=csv`); the header jump box, `#company/<T>` and the Rows Company select all land on the same Rows view.
  "Measure" names three different things (Explore's list select, the taxonomy measure select, and the Grid Kind
  option "Every measure").

</details>

#### STORY-046: Find Microsoft's FY2026 capex in the raw rows and copy it
**Type**: short
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-001
**Persona**: Equity analyst at a long-only fund, first visit, wants one number with a source
**Goal**: Read MSFT's FY2026 cash-flow capex and see where it came from
**Preconditions**: Local or hosted copy open on `#proof`; MSFT in scope
**Ideal path**: 3: type the ticker, filter to the line, read the row (a search scoped to a company should be enough)
**Alternate paths**: (a) navbar **Dataset** → Company select "Microsoft MSFT" → "Find in rows"; (b) type `#company/MSFT` (redirects to the same Rows view); (c) Dataset → **Values** list (81 rows) → Company select; (d) Dataset → **Grid** → Field "Capex" → MSFT row, FY26 cell → provenance drawer; (e) Company trail `#proof/MSFT` → "Statement figures" stage card; (f) Explore with Measure "Statement figures", Field "Capex", Tickers "MSFT", then **Show rows**; (g) `/api/v1/values?ticker=MSFT&field=capex` directly
##### Steps
1. Types "MSFT" in the header jump box "Ticker or company…" and picks Microsoft from the datalist -> Route `#data?ticker=MSFT`; tab **Dataset** highlighted; heading "All rows", "71 rows · USD", Company select shows "Microsoft MSFT", value select "Every row".
2. Hesitates: 71 rows across derived, planned and company-stated-AI measures; not sure which is "capex". Types "capex" in **Find in rows** -> After ~150 ms the count reads "<n> rows of 71"; the matches include the cash-flow line plus rows whose `standard_concept`/URL text happens to contain "capex".
3. Clicks the column header **fiscal_year** twice to put FY2026 on top -> Table re-sorts (first click ascending, second descending).
4. Clicks the FY2026 row with `reported_name` "capital expenditures (cash-flow line)" -> A detail row opens listing every column (`value` 115948000000, `standard_concept` PaymentsToAcquirePropertyPlantAndEquipment, `accession`, `source_url`, `check`).
5. Clicks the `source_url` "open" link in the table -> sec.gov 10-K opens in a new tab.
##### Variations
- Searches "Microsoft" instead of selecting the company: matches nothing in taxonomy rows (they carry `ticker`, not the name) unless the URL or a quote contains it; the jump box is the reliable route.
- Starts from the **Values** list: the same figure is `value` 115948000000 with `check_label` agree and a `citations` string ("… 'Purchases of property and equipment' …").
- Clicks the ticker cell "MSFT" in the table -> goes to the Company trail `#proof/MSFT` instead of expanding the row.
##### Edge Cases
- Jump box text "msft" (lowercase) works (uppercased); "Micro" does not navigate (needs the full company name or a 1–6 letter ticker); an out-of-scope ticker like "ORCL" navigates and shows "0 rows · USD" / "No rows.".
- Pressing Back after searching clears "Find in rows" (search is not in the hash); the count resets to "71 rows".
- Searching a number with separators ("115,948") fails: search runs over raw JSON (`115948000000`).

#### STORY-047: Download every Note figure for the chip sellers as CSV
**Type**: short
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-002
**Persona**: Data engineer loading the ledger into a warehouse
**Goal**: Get facts (note figures) for NVDA and AMD as a file
**Preconditions**: Any copy, including read-only
**Ideal path**: 3: pick the list, pick the companies, download (one multi-company filter would make it 3; the Rows view allows only one company)
**Alternate paths**: (a) Dataset Rows → **Facts** → **CSV** (all companies) and filter in a spreadsheet; (b) twice: Company "NVIDIA NVDA" → CSV, then "AMD" → CSV; (c) `/api/v1/facts.csv?ticker=NVDA,AMD` typed by hand (the API takes a comma list); (d) Explore Measure "Note figures", Tickers "NVDA, AMD", **CSV** link (`?format=csv`); (e) **JSON** button for the same list; (f) Release packet `/packet/<v>.zip` from Proof "Releases" (signed data only)
##### Steps
1. Clicks navbar **Dataset** -> `#data`, "All rows" (617 rows).
2. Clicks **Facts** ("Note figures") in the list sidebar -> `#data?list=facts`, "327 rows · USD".
3. Looks for a multi-select; finds only the Company select. Picks "NVIDIA NVDA" -> `#data?list=facts&ticker=NVDA`.
4. Clicks **CSV** -> Browser downloads `/api/v1/facts.csv?ticker=NVDA` (`text/csv`).
5. Switches Company to "AMD" and clicks **CSV** again -> second file; merges them by hand.
##### Variations
- Uses Explore instead: Measure "Note figures", Tickers "NVDA, AMD" (input uppercases and strips spaces → `NVDA,AMD`), then the small **CSV** link → one file; this is the only UI route to a two-company CSV.
- Clicks **JSON** -> opens `/api/v1/facts?ticker=NVDA` in a new tab with `{list, count, filters, rows}`.
##### Edge Cases
- On the **Companies** list the Company select still shows and filters the 6-row list down to one.
- The "Every row / With a value / Without a value" select only appears on **All rows** (taxonomy); switching lists drops `has_value` from the URL.
- Read-only copy: CSV and JSON still work (GET).

#### STORY-048: Compare hyperscaler capex year by year in the Grid
**Type**: medium
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-003
**Persona**: Sell-side analyst building an AI capex comp table
**Goal**: See MSFT, GOOGL, AMZN capex FY2022–FY2026 side by side, verified marks visible, then export
**Preconditions**: Any copy; values verified ("agree") for all three
**Ideal path**: 4: open Grid, pick field, pick group, export (Capex is already the default field)
**Alternate paths**: (a) `#data?view=grid&t=MSFT,GOOGL,AMZN&f=capex` typed or shared; (b) Companies "Custom…" drawer ticking the three; (c) Explore with Measure "Statement figures", Field "Capex", Layer "Hyperscaler", x: year, series: company, Chart type "bars", then "Data" disclosure; (d) saved view "Capex by layer, by year" (layer totals, not per company); (e) Rows view → **Values** → CSV and pivot by hand
##### Steps
1. Clicks navbar **Dataset**, then **Grid** -> `#data?view=grid`; Field "Capex", Companies "All companies", Kind "Every measure"; caption "6 rows · USD · ✓ Verified · ○ Unverified · ≠ Differs from SEC XBRL".
2. Reads rows sorted by largest value: Amazon AMZN, Microsoft MSFT, Alphabet GOOGL first; columns "2022"…"2026" -> AMZN FY2026 blank (not filed yet), MSFT 2026 $115.9B with ✓.
3. Hesitates over Companies: "Buyers" would include APLD (role buyer). Picks the industry group "Hyperscaler" -> `t=MSFT,GOOGL,AMZN`; caption "3 rows".
4. Sets Kind to "Spent" -> URL gains `k=spent`; same three rows (cash-flow capex is spent).
5. Hovers a ✓ mark -> tooltip "Verified · matches SEC XBRL" (word from `checkWord`).
6. Clicks GOOGL's 2025 cell ($91.4B) -> Drawer: "Alphabet, Capex, FY2025", figures Value / Verification ("values table"), SEC XBRL line, "Open in 10-K ↗", then the cited cell source (Line, Column, crop thumbnail).
7. Clicks the crop thumbnail -> lightbox with "Open in filing" and "sec.gov ↗"; Escape closes it, Escape again closes the drawer (focus returns to the cell).
8. Clicks **Export CSV** -> client-side download `capex-ledger-capex.csv` with columns ticker, company, field, dimension, period, kind, value, check, basis, source_url, provenance.
9. Copies the URL to a colleague -> the link reproduces the same grid (state lives in the hash).
##### Variations
- Arrives from Reconcile "Open in Dataset" -> `#data?view=grid&t=<T>&f=<field>,capex`: a **Field** column appears because two fields are selected; the Field select shows only the first.
- Clicks the company name in a row -> narrows the grid to that one company (`t=<T>`); switching to **Rows** then keeps `ticker=<T>`.
- Field "Segment capex": a "Segment or category" column appears (APLD "Data Center Hosting Business", "HPC Hosting Business").
##### Edge Cases
- Picking an industry with no companies in scope ("Power producer", "Neocloud") sets `t=` empty, which the page reads as every company; the select snaps back to "All companies" with no message.
- A cell whose value changed since the last release gets the `moved` highlight, but there is no legend for it.
- A `check` label the server does not declare shows ✗ "Not checked", never a pass.
- Grid **Export CSV** and Rows **CSV** produce different column sets for the same values (redundant exports, different shapes).

#### STORY-049: Build a custom company set in the Grid and then change it
**Type**: medium
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-004
**Persona**: Analyst comparing AI chip sellers against one buyer (NVDA, AMD, MSFT)
**Goal**: Show capex for an ad-hoc set, then add APLD
**Preconditions**: Grid open on "All companies"
**Ideal path**: 4: open picker, tick, apply; reopen, tick, apply
**Alternate paths**: (a) edit `t=` in the URL; (b) pick "Chip design" group, then edit URL to add MSFT; (c) Explore Tickers "NVDA, AMD, MSFT" (free text, no picker)
##### Steps
1. Selects Companies "Custom…" -> Drawer "Companies" with checkboxes grouped by industry (Hyperscaler: MSFT GOOGL AMZN; Chip design: NVDA AMD; Miner to HPC: APLD), all ticked.
2. Unticks GOOGL, AMZN, APLD -> nothing changes behind the drawer yet.
3. Clicks **Apply** -> `#data?view=grid&t=MSFT,NVDA,AMD&f=capex`; select shows "Custom…"; "3 rows".
4. Wants to add APLD; re-selects "Custom…" in the Companies select -> nothing happens (already selected, no change event).
5. Confused; picks "All companies" then "Custom…" again -> drawer opens with all six ticked (the previous custom set is gone).
6. Unticks GOOGL, AMZN, ticks nothing else, clicks **Apply** -> `t=MSFT,NVDA,AMD,APLD`.
##### Variations
- Edits the URL instead (`&t=MSFT,NVDA,AMD,APLD`): works first time, the select shows "Custom…".
- Closes the drawer with Escape or the close button instead of Apply: ticks are discarded, but the select still shows "Custom…" until the next render.
##### Edge Cases
- Unticking every company and pressing **Apply** shows all six companies (empty `t` means everyone).
- Ticks that exactly match a group (NVDA + AMD) render the select as "Chip design", not "Custom…".
- Lowercase tickers in a hand-typed `t=msft` find no data (Grid does not uppercase `t`, unlike Rows' `ticker`).

#### STORY-050: Chart capex by layer and export what the chart shows
**Type**: medium
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-005
**Persona**: Journalist writing about AI infrastructure spend
**Goal**: A stacked bar of capex by supply-chain layer per fiscal year, plus the numbers behind it
**Preconditions**: Explore defaults
**Ideal path**: 3: open Explore (defaults already chart this), open Data, export
**Alternate paths**: (a) saved view "Capex by layer, by year" (`#explore/capex-by-group` or `#views/capex-by-group`); (b) Grid Field "Capex" + Export CSV and sum by layer by hand; (c) Rows **All rows** with Find "capex" + CSV; (d) `/api/v1/taxonomy.csv?category=capex`
##### Steps
1. Clicks navbar **Explore** -> `#explore`; left "4 saved views" + "New"; controls Measure "All measures", Measure "spent", Category "capex", "every asset type", "every field", "every kind", Value "the value as reported", "every layer", tickers box, From/To, "then", "x: fiscal year", "series: layer", Chart type "stacked bars".
2. Reads "<n> rows" and the stacked chart (Hyperscaler, Chip design, Miner to HPC in fixed colours); y axis "capex, $billion".
3. Hovers FY2025's Hyperscaler segment -> "<b>$…</b> Hyperscaler, x% of the fiscal year · n row(s)".
4. Opens the **Data** disclosure -> table: layer × FY columns with dollar sums; copies it.
5. Clicks the **CSV** link expecting the charted rows -> downloads `/api/v1/taxonomy?&format=csv`: all 617 taxonomy rows (category and measure filters are not in the export link).
6. Notices the mismatch, goes back and opens the **JSON** link -> same, `filters: {}`.
7. Falls back to typing `/api/v1/taxonomy.csv?category=capex&measure=spent` or uses the Data table.
##### Variations
- Opens the saved view instead: identical chart, heading "Capex by layer, by year" with the view's note.
- Chart type "share of total" -> y axis "share of the total, %".
- Value "change from the prior year" -> plots `change_from_prior`; y title adds ", change from the prior year".
##### Edge Cases
- From "FY2024" To "FY2022" (inverted) -> "No rows match".
- More than 8 series (e.g. series: standard type) -> extras folded into "Other" (grey), caption ", n smaller series folded into Other".
- Plotly CDN blocked -> "Chart unavailable" and the row table shows directly.
- Same numbers appear in the Data disclosure, Show rows, the JSON link and Grid: four surfaces for one series.

#### STORY-051: Open each saved view to see what is already built
**Type**: medium
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-006
**Persona**: New team member told "the views are in Explore"
**Goal**: Browse the 4 saved views and pick one to reuse
**Preconditions**: 4 views in `data/views.json`
**Ideal path**: 4: one click per view
**Alternate paths**: (a) `#views/<id>` (same page, Explore tab highlighted); (b) `/api/v1/views` JSON listing; (c) `/api/v1/views/<id>/data` (rows only, API)
##### Steps
1. Navbar **Explore** -> left list: "Capex by layer, by year" (taxonomy · capex, fiscal year by layer), "Technology equipment, gross balance by company", "What companies state about AI, in dollars" (taxonomy · company stated ai), "Committed: purchase obligations and finance leases".
2. Clicks "Technology equipment, gross balance by company" -> `#explore/technology-equipment-gross`; lines per company over fiscal year; Category "ppe gross by type", Standard type "TechnologyEquipment".
3. Clicks a line point (MSFT FY2024) -> "Microsoft MSFT, FY2024" rows table below with Company link, Year, reported name, Value, Basis.
4. Clicks "What companies state about AI, in dollars" -> heading shows the view's name; chart area says "No rows match" although the measure has 118 rows.
5. Hesitates: checks the X axis select; no option matches (`period` is not a taxonomy column; the view was saved as `show: grid` with no chart). Changes X axis to "x: fiscal year" -> chart appears; URL becomes `#explore?…` (no longer the view).
6. Clicks "Committed: purchase obligations and finance leases" -> grouped bars by company per fiscal year.
7. Clicks **New** -> back to `#explore` defaults.
##### Variations
- Arrives via a shared `#views/committed` link: identical page.
##### Edge Cases
- Changing any control on a saved view leaves `#explore/<id>` for `#explore?<state>`; the heading reverts to "Explore" and the button becomes **Save as view** (there is no way to "Save changes" after tweaking, because tweaking drops the view id).
- Unknown id `#explore/nope` silently shows the default chart under "Explore".

#### STORY-052: Save a new view (fails on the Content-Type guard)
**Type**: short
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-007
**Persona**: Kenny (owner) on the local copy, Signer "Kenny Geiler"
**Goal**: Save "AI capex vs total, FY2023–FY2026" as a view
**Preconditions**: Local copy (not read-only), Signer set
**Ideal path**: 3: Save as view, name, Save
**Alternate paths**: none found in the UI (views are otherwise only editable in `data/views.json`)
##### Steps
1. Sets Category "ai capex", From "FY2023", To "FY2026", series: company -> chart redraws; URL `#explore?…`.
2. Clicks **Save as view** -> Drawer "Save as view", Name (placeholder "e.g. Capex by industry, FY2022–FY2026"), Note.
3. Types the name and "Company-stated AI capex", clicks **Save** -> red message under the button: "a write needs Content-Type: application/json"; drawer stays open.
4. Retries -> same error. Nothing saved; no other route exists.
##### Variations
- Read-only copy: the read-only guard runs first -> "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository".
##### Edge Cases
- Empty Name: server would reject, but the Content-Type refusal comes first, so the user never sees name validation.
- Signer box empty: the button is not disabled here (unlike Reconcile writes); `by: ''` would also be refused.

#### STORY-053: Edit and delete a saved view (both fail; Delete fails silently)
**Type**: medium
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-008
**Persona**: Kenny tidying views before sharing the hosted link
**Goal**: Rename "Committed: purchase obligations and finance leases", then delete "What companies state about AI, in dollars"
**Preconditions**: Local copy, Signer set
**Ideal path**: 5: open view, Save changes, rename, Save; open other view, Delete + confirm (6)
**Alternate paths**: none found in the UI
##### Steps
1. Clicks "Committed: purchase obligations and finance leases" -> `#explore/committed`, buttons **Save changes** and **Delete**.
2. Clicks **Save changes** without touching controls -> Drawer "Save changes" with Name and Note prefilled.
3. Edits Name to "Committed obligations", **Save** -> "a write needs Content-Type: application/json" in the drawer.
4. Closes the drawer (Escape) -> name unchanged in the list.
5. Clicks "What companies state about AI, in dollars" (already broken, STORY-051), clicks **Delete** -> button text becomes "Confirm delete" (armed for 5 s).
6. Clicks **Confirm delete** -> the POST is refused 403; no message, no navigation; the button keeps reading "Confirm delete" until the timer resets it to "Delete" (unhandled promise rejection in the console).
7. Unsure whether it worked, reloads -> the view is still listed (4 saved views).
##### Variations
- Waits more than 5 s between clicks -> the button disarms and the second click re-arms instead of deleting.
##### Edge Cases
- Read-only copy: Delete fails the same silent way (403 read-only), while Save shows the message.
- The `aria-live` on the Delete button announces "Confirm delete" but never an error.

#### STORY-054: Quarterly research pass: from a hunch on APLD to a shareable chart and a source check
**Type**: long
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-009
**Persona**: Buy-side analyst covering Applied Digital (APLD), comparing it with the hyperscalers' capex ramp
**Goal**: Quantify APLD's capex jump, check it against the filing, find the segment split, and send a colleague a chart link plus a CSV
**Preconditions**: Any copy; APLD capex FY2022 $55.0M → FY2026 $2.87B, all "agree"
**Ideal path**: 10: jump to APLD, Grid capex, open FY2026 cell + source, switch field to Segment capex, Explore with APLD + series, Data table, copy link, export CSV
**Alternate paths**: (a) Company trail `#proof/APLD` for the source of every figure (Statement figures and Note figures stages); (b) Rows view **Values** / **Facts** with Company "Applied Digital APLD"; (c) Reconcile `#reconcile?scope=APLD` evidence "Open in Dataset"; (d) Explore **Show rows** for every row; (e) API `/api/v1/facts?ticker=APLD&field=segment_capex`
##### Steps
1. Types "APLD" in the jump box -> `#data?ticker=APLD`, "All rows", "<n> rows · USD".
2. Selects "With a value" -> `has_value=true`; count drops (taxonomy rows without values hidden).
3. Clicks **Grid** -> `#data?view=grid&t=APLD`; Field "Capex"; one row "Applied Digital APLD": 2022 $55.0M … 2026 $2.9B, all ✓.
4. Clicks the 2026 cell -> drawer "Applied Digital, Capex, FY2026", Value $2.9B, Verification Verified, SEC XBRL $2.9B, "Open in 10-K ↗", source line and crop.
5. Clicks the crop -> lightbox; clicks "Open in filing" -> `/filing/<accession>` in a new tab with the cell outlined.
6. Returns, presses Escape to close the drawer; switches Field to "Segment capex" -> rows per segment ("Data Center Hosting Business", "HPC Hosting Business", "Cloud Services Business") under "Segment or category".
7. Hesitates: wants the hyperscalers next to APLD on one chart; Grid sorts by size, so APLD drops to the bottom. Switches Field back to "Capex", Companies "Custom…", ticks MSFT and APLD, **Apply**.
8. Values differ by 40×; the grid has no growth view. Opens navbar **Explore**.
9. Sets Measure "Statement figures" -> Field resets to "Capex", x: year.
10. Types "APLD, MSFT" in the tickers box, tabs out -> `ticker=APLD,MSFT`.
11. Sets Series "series: company", Chart type "lines" -> two lines, hover "x unified".
12. MSFT dwarfs APLD; switches Measure back to "All measures" to use Value "change from the prior year" -> Category resets to "capex", Measure "spent", tickers kept.
13. Sets Value "change from the prior year", series: company, lines -> change lines plotted; FY2022 has no prior and drops out.
14. Double-clicks the chart to reset after a drag-zoom; toggles MSFT off in the legend to read APLD alone.
15. Opens **Data** -> APLD and MSFT rows by fiscal year; copies the table.
16. Clicks a point -> rows table "Applied Digital APLD, FY2026" with Basis text.
17. Clicks the company link in the rows table -> Company trail `#proof/APLD` (now outside this topic; checks "Coverage" next 10-K date), then Back.
18. Tries **Save as view** to keep it -> fails (STORY-052); instead copies the `#explore?…` URL, which reproduces the chart.
19. Clicks the **CSV** link -> downloads rows filtered by ticker only (not category/measure), so gets every APLD and MSFT taxonomy row; filters in a spreadsheet.
20. Sends the link and the CSV.
##### Variations
- Uses Grid **Export CSV** at step 7 instead of Explore's CSV: exact charted rows, but no change-from-prior column.
- Uses Layer "Miner to HPC" instead of tickers: same APLD series (APLD is the only miner_to_hpc company).
##### Edge Cases
- The colour of APLD is stored per browser (`localStorage.datahq-colors`); the colleague may see different colours for the same link.
- Typing "APLD MSFT" (space, no comma) becomes `APLDMSFT` after whitespace stripping -> "No rows match".
- The Grid row link and the jump box both reset the Grid's field to capex unless `f` is carried.

#### STORY-055: Audit the Dataset against the release before a client send
**Type**: long
**Topic**: dataset-explore
**Source**: `dataset-explore` STORY-010
**Persona**: Kenny, owner, checking that what consumers will download matches what Proof says
**Goal**: Walk every list, spot unverified or flagged values, and confirm exports are consistent across the three CSV routes
**Preconditions**: Local copy; release v1.9.0 not yet signed
**Ideal path**: 8: one filter for "not verified" across lists, one export (the UI has no such filter; the Grid's `check` URL parameter is the closest)
**Alternate paths**: (a) Release checklist "Fix in" → Dataset; (b) Reconcile filters (Cause "Differs from SEC XBRL"); (c) Proof Company trail stage tallies; (d) hand-typed `#data?view=grid&check=unresolved,flag` (supported in code, no control for it)
##### Steps
1. Navbar **Dataset** -> "All rows" 617 rows.
2. Selects "Without a value" -> 125 rows; scans `measure` (planned, company_stated_ai) to confirm these are text-only statements, not missing numbers.
3. Selects "Every row", clicks **Values** -> 81 rows; sorts **check_label** to group anything other than agree.
4. Types "unresolved" in **Find in rows** -> count "0 rows of 81" (none differ today).
5. Clicks **Facts** -> search box clears (not kept across lists); 327 rows; sorts **check** column.
6. Clicks **Statements** -> 227 rows; expands a row to read `quote` (cut at 90 characters in the table, full in the detail).
7. Clicks **Projects** -> 182 rows; looks at `amount_low`/`amount_high`.
8. Clicks **Companies** -> 6 rows: MSFT, GOOGL, AMZN hyperscaler; NVDA, AMD chip_seller; APLD miner_to_hpc.
9. Switches to **Grid**, Field "Capex", All companies -> 6 rows, every cell ✓.
10. Field "Purchase commitments", Kind "Committed" -> rows for the companies that disclose them; looks for ≠ or ○ marks and Fix / Accepted / Explained / Blocks release badges.
11. Field "PP&E by category" -> wide table with "Segment or category"; clicks a ○ cell -> drawer: Verification "Unverified · citation only".
12. Hand-types `&check=unresolved,flag` on the Grid URL -> only differing or flagged rows remain.
13. Clicks **Export CSV** -> `capex-ledger-ppe_category.csv` (client-side).
14. Switches to **Rows** -> lands on `#data` (Rows switch keeps only list/ticker), All rows.
15. Clicks **Values** → **CSV** (server `/api/v1/values.csv`) and compares to Grid's export for capex: different columns (`check_label` vs `check`, `citations` vs `provenance`).
16. Opens Explore, Measure "Statement figures", Field "Capex" -> **CSV** (`?field=capex&format=csv`): same columns as the Rows CSV.
17. Notes three export shapes for one dataset; files a finding.
18. Opens **Release** to see "Packet v1.9.0" files and compares row counts with steps 3–8.
##### Variations
- Read-only copy: every step works (all GET).
- Uses `#tables/facts` from an old bookmark -> redirects to `#data?list=facts`.
##### Edge Cases
- Grid ignores `check` in its controls: the filter is invisible and survives only until a control is changed (`setQ` drops it).
- The table renders every row (no paging); on All rows (617) the page is long.
- A `#data?list=bogus` URL falls back to All rows silently.

### Topic: Hosted read-only visitor (LEDGER_READONLY=1) (`readonly-visitor`)

<details><summary>Topic notes (as written by the topic pass)</summary>

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

</details>

#### STORY-056: Recognise that this copy is read-only
**Type**: short
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-001
**Persona**: Priya, a data journalist sent the hosted link by Kenny; first visit, never seen the local app
**Goal**: Know, before trying anything, whether she can change anything here
**Preconditions**: Hosted copy, `LEDGER_READONLY=1`; empty localStorage; `/api/hq` healthy
**Ideal path**: 1 — a read-only marker visible on landing, next to where a writer's controls would be, answers it without a click
**Alternate paths**: the scope line under the nav ("· Read-only"); the header span "Read-only" that replaces Signer; Known gaps claim row "Hosted copy" (status Out of date) for what the hosted copy is; Docs (no page found that explains the hosted copy to a visitor)
##### Steps
1. Opens the hosted URL -> `#proof` loads ("Loading…" then the Proof board: "Proof", "0 of 6 proven", company table MSFT, GOOGL, AMZN, NVDA, APLD, AMD, each "<n> to review"). For a beat the header shows "Signer [Kenny Geiler]" because `/api/hq` has not returned yet.
2. `/api/hq` resolves -> the Signer box is swapped for a small azure "Read-only"; a line appears under the nav: "6 companies · Data as of <date> · Read-only". Priya glances at it; "Read-only" is small, at the far right of the dark navbar, after the "Ticker or company…" box.
3. Scrolls the Proof board to Hand check -> sees per-item **Right / Wrong / Can't say** buttons, enabled, with a note box. She hesitates: "it said read-only, but these look clickable."
##### Variations
- Arrives on a deep link (`#reconcile?scope=NVDA`, `#explore/capex-by-group`) instead of the root: the same header swap and scope line happen on every route, because they run once from `_router.js` regardless of page.
- Has visited before on the same origin and once typed a name: irrelevant, the Signer box is gone either way; the stored name still becomes `me`.
##### Edge Cases
- `/api/hq` errors or times out: the `.catch` is silent, so the Signer box stays (pre-filled "Kenny Geiler") and no "Read-only" appears anywhere; the visitor has no signal until a write is refused.
- Same "read-only" fact appears in two places (header span, scope line) and nowhere near the write controls themselves (Proof hand check, Reconcile decision form, Release Sign, Explore Save) — redundant at the top, absent where it matters.
- The flash of the Signer box before `/api/hq` resolves briefly suggests the opposite.

#### STORY-057: Try to grade a hand-check item and get refused
**Type**: short
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-002; merged with `proof-hand-check` STORY-006 (Read-only visitor tries to grade)
**Persona**: Priya (as above), curious whether she can mark something as wrong
**Goal**: Record a Wrong verdict on an AMZN gold item she disagrees with
**Preconditions**: Hosted read-only copy; Proof page; AMZN 20/20 checked
**Ideal path**: 0 — on a read-only copy the verdict controls should not be offered (or be visibly disabled with the reason), so there is no path
**Alternate paths**: none found (gold verdicts are only on Proof's Hand check; `POST /api/gold/verdict` has no other UI)
##### Steps
1. Clicks "Hand check: <state>" in the Proof header -> page scrolls to `#gold`: "20 items per company · random sample · Unchecked never passes", company picker buttons "MSFT 20/20 … APLD 19/20".
2. Clicks "AMZN 20/20" -> table Item · Value · Source · Check, hard groups first (No SEC counterpart, Definition differs …), each item with crop thumbnail, "Open", "sec.gov ↗", value "In millions · $…", verdict status "Right · Kenny Geiler · <date>".
3. Clicks **Wrong** with the note empty -> inline red "Note required"; focus moves to the note box. No request sent (client check first).
4. Types "Capex here looks like it includes finance leases" in "Note (required for Wrong / Can't say)" and clicks **Wrong** -> all three buttons disable briefly, POST goes out, 403; the status line under the buttons turns red with READONLY_MSG; buttons re-enable; the verdict stays "Right · Kenny Geiler · <date>". Priya: "so why did it let me type a note?"
##### Variations
- **Can't say** follows the same path (note required, then 403). **Right** skips the note check and goes straight to the 403.
- On APLD's one unchecked item, the status stays "Unchecked" after the refusal.
##### Edge Cases
- READONLY_MSG names "decisions, views and prompts" but not verdicts; she has to infer it covers gold too.
- Her note text stays in the box after the refusal; nothing tells her it is not saved anywhere.
- The button tooltip says the verdict's help text (GOLD_HELP), not "read-only".

##### Merged duplicate: `proof-hand-check` STORY-006: Read-only visitor tries to grade

**Type**: short
**Topic**: proof-hand-check
**Persona**: A partner at Arctal viewing the hosted read-only copy
**Goal**: See the hand-check evidence; discover whether they can contribute a verdict
**Preconditions**: Server started with `LEDGER_READONLY=1`
**Ideal path**: 2 — pick company, read; ideally no write buttons at all
**Alternate paths**: `/api/v1/gold?t=AMZN` JSON directly
###### Steps
1. Open `#proof` -> Header Signer box replaced by "Read-only"; scope line ends "· Read-only".
2. Scroll to Hand check, click "AMZN" -> Items render; verdict buttons are enabled because `me` still defaults to "Kenny Geiler" in this browser (or whatever localStorage held).
3. Click "Can't say" with a note -> 403 "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository" in the item's status line; buttons re-enable.
###### Variations
- Without a note, "Note required" appears first — client validation runs before the read-only refusal.
###### Edge Cases
- Write affordances render on a copy where they can never succeed; the refusal is only learned by clicking.

#### STORY-058: Export NVDA's capex rows as CSV
**Type**: medium
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-004
**Persona**: Marcus (as above), building his own model in a spreadsheet
**Goal**: A CSV of NVDA statement figures, then a grid export across buyers
**Preconditions**: Hosted read-only copy
**Ideal path**: 3 — jump to NVDA, pick the list, click CSV
**Alternate paths**: Dataset Rows **CSV** link (server `/api/v1/<list>.csv?ticker=NVDA`); Dataset Grid **Export CSV** (client-side Blob, `capex-ledger-<field>.csv`); Explore "CSV" link next to the chart (`/api/v1/<measure>?…&format=csv`); Explore saved view data `/api/v1/views/<id>/data?format=csv` (no UI link found); Packet zip on Proof
##### Steps
1. Types "NVDA" in "Ticker or company…" and presses Enter -> `#data?ticker=NVDA`; Dataset tab active; Rows view, "All rows" list, Company select "NVIDIA".
2. Clicks "Values" in the list sidebar -> `#data?list=values&ticker=NVDA`; "<n> rows of <m>"; columns sortable.
3. Types "capex" in "Find in rows" -> rows filter after 150 ms; count updates. Marcus wonders whether the CSV respects the search box.
4. Clicks **CSV** -> downloads `/api/v1/values.csv?ticker=NVDA` — the server list filtered by ticker only; the in-page "Find in rows" text is **not** applied (search is client-side). He notices the CSV has more rows than the screen.
5. Clicks **JSON** -> new tab with `{"list": "values", "count": …, "filters": {"ticker": "NVDA"}, "rows": [...]}`.
6. Switches to **Grid** -> `#data?view=grid…`; Field select "Capex", Companies group "Buyers", Kind "Spent".
7. Clicks a cell (NVDA FY2025) -> provenance: sources, crop, "Open in 10-K ↗", decision badge (e.g. "Accepted") or "Not checked".
8. Clicks **Export CSV** -> client-side file `capex-ledger-capex.csv` with ticker, company, field, dimension, period, kind, value, check, basis, source_url, provenance.
##### Variations
- Uses Companies "Custom…" -> drawer with checkboxes (MSFT, GOOGL, AMZN, NVDA), **Apply**; works on the read-only copy (pure client state in the URL).
- Uses Explore instead: Measure "Statement figures", Tickers "NVDA", then the "CSV" link beside the row count.
##### Edge Cases
- Rows CSV ignores "Find in rows" while Grid Export CSV exports exactly what the grid shows: two export buttons, two meanings.
- Four routes to the same rows (Rows CSV, Grid Export CSV, Explore CSV, packet) — redundancy candidate.
- Nothing about read-only affects this story; exports are GETs or client blobs.

#### STORY-059: Save an Explore chart as a view, then try to delete one
**Type**: medium
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-005
**Persona**: Dana, a strategy associate who wants to bookmark a chart for her team
**Goal**: Keep "Capex by layer" filtered to hyperscalers so she can come back to it
**Preconditions**: Hosted read-only copy; 4 saved views (Capex by layer, by year; Technology equipment, gross balance by company; What companies state about AI, in dollars; Committed: purchase obligations and finance leases)
**Ideal path**: 2 — set the chart, copy the URL (every control writes to the hash); a "Save as view" that cannot work should not be offered here
**Alternate paths**: copy the `#explore?<state>` URL from the address bar (works, linkable); open an existing saved view `#explore/<id>` or legacy `#views/<id>`; JSON/CSV links capture the data but not the chart
##### Steps
1. Clicks the "Explore" tab -> left list "4 saved views" + "New"; Plotly chart.
2. Clicks "Capex by layer, by year" -> `#explore/capex-by-group`; stacked bars by fiscal_year × layer; buttons **Save changes** and **Delete**.
3. Types "MSFT,GOOGL,AMZN" in Tickers -> chart redraws; URL hash updates.
4. Clicks **Save changes** -> drawer: "Save changes", Name "Capex by layer, by year", Note prefilled.
5. Edits Name to "Hyperscaler capex by layer" and clicks **Save** -> POST `/api/v1/views`, 403; the drawer's message line turns red with READONLY_MSG ("…decisions, views and prompts change in a checkout…"). Drawer stays open. Dana closes it (Close or Escape).
6. Copies the browser URL instead and pastes it to her team -> the hash carries tickers, measure and chart, so the link reproduces the chart for anyone.
7. Out of curiosity clicks **Delete** -> label becomes "Confirm delete".
8. Clicks "Confirm delete" -> POST 403; **nothing visible happens** (no try/catch: unhandled promise rejection); after ~5 s the label reverts to "Delete". Dana: "did it delete it or not?" Reloads; the view is still there.
##### Variations
- From a fresh `#explore` (no view): button reads **Save as view**; same 403 in the drawer.
- On a local copy the same Save/Delete are refused for a different reason (missing `Content-Type`, 403 "a write needs Content-Type: application/json"); on the hosted copy the read-only guard runs first and masks that defect.
##### Edge Cases
- Delete gives zero feedback on refusal — broken flow (also broken locally).
- Name/Note typed into the drawer are lost on close.
- The "save" need is fully met by the URL hash, so Save as view duplicates linkability for a visitor.

#### STORY-060: Try to accept an NVDA "Differs from SEC XBRL" item in Reconcile
**Type**: medium
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-006; merged with `reconcile-decisions` STORY-008 (Read-only visitor tries to decide)
**Persona**: Leo, a sell-side analyst who covers NVDA and thinks a flagged gap is fine
**Goal**: Mark NVDA's capex difference as Explained with his reason
**Preconditions**: Hosted read-only copy; Reconcile live with ~69 rows; an NVDA row under "Differs from SEC XBRL"
**Ideal path**: 0 — a visitor cannot decide; the form should be read-only or absent. To *read* the item: 3 (Reconcile, scope NVDA, expand)
**Alternate paths**: Company trail `#proof/NVDA` → stage card → "Review in Reconcile →" / "Reconcile" link; keyboard e on a focused row; Proof board row click → trail → Reconcile
##### Steps
1. Clicks "Reconcile" -> header counts (Needs review / Blocks release / Proposed / Unverified), "Last run …", "Keyboard" hint.
2. Sets Scope to "NVDA" -> `#reconcile?scope=NVDA`; cards by cause.
3. Clicks the NVDA capex row under "Differs from SEC XBRL" -> evidence expands: aligned tables (This year, By year …), "Company trail", "Open in Dataset", "Open in EDGAR ↗", and the decision form **Accept / Explain / Fix / Block release**, Reason input, **Save**.
4. Clicks **Explain** -> button active (tooltip "Right, with the reason kept").
5. Clicks **Save** with no reason -> "Reason required"; focus to Reason.
6. Types "Includes intangibles purchases; XBRL tag is PP&E only" and presses Enter -> "Saving…", then red "Couldn’t save: this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository. Try again." Leo clicks Save again; same message.
7. Clicks "Open in EDGAR ↗" -> sec.gov in a new tab; reading still works.
##### Variations
- Keyboard: focuses the row, presses `e` -> row expands with Explain pre-selected and focus in Reason; same 403 on Enter.
- Selects several rows (checkbox or space) -> "<n> selected: …" card, "Why, for all <n>…", **Save for <n>** -> same 403 text from `/api/resolve/bulk`.
- A Proposed row: **Confirm Explain** -> "Saving…" then "Couldn’t save: …(READONLY_MSG)." ; **Overturn** just opens the form (no request).
##### Edge Cases
- "Try again." is appended to a permanent refusal — misleading; Leo retries.
- "Saved. Apply to every company?" and **Make this a rule / Make this a definition** are unreachable on the read-only copy (they appear only after a successful save).
- Writes are attributed to `me` = "Kenny Geiler" even though the visitor never typed a name; if the read-only guard were ever off, a visitor's click would land under Kenny's name (related finding F18).

##### Merged duplicate: `reconcile-decisions` STORY-008: Read-only visitor tries to decide

**Type**: short
**Topic**: reconcile-decisions
**Persona**: an Arctal analyst on the hosted copy (`LEDGER_READONLY=1`)
**Goal**: See whether they can mark APLD opex FY2026 as accepted
**Preconditions**: hosted copy; header shows "Read-only" in place of Signer
**Ideal path**: 1 — the form should be absent or disabled with a reason
**Alternate paths**: none found (no read-only branch in reconcile.js)
###### Steps
1. Opens `#reconcile?resolved=1`, opens APLD opex FY2026 -> "Large year-over-year change" table (Prior year $83,985,000, This year $394,144,000, "+$310.2M 4.7×"), "opex by year", Details "opex moves 4.69× from FY2025 …", "Open in Dataset".
2. The Decision form renders fully; picks Accept, types "looks right", **Save** -> "Couldn't save: this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository. Try again."
###### Edge Cases
- "Try again." invites a retry that can never succeed.
- Keyboard `a e f b` and Select all / Save for n render and fail the same way.

#### STORY-061: Try to approve a category mapping for AMD
**Type**: short
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-007; merged with `reconcile-mapping-encode` STORY-011 (Read-only visitor tries the mapping buttons)
**Persona**: Leo (as above)
**Goal**: Approve the proposed standard category for an AMD reported asset line
**Preconditions**: Hosted read-only copy; Reconcile "Category mapping" card has AMD rows to confirm
**Ideal path**: 0 — not a visitor action
**Alternate paths**: Company trail `#proof/AMD` → Category mapping stage card → "Decide in Reconcile →" / "Confirm or override in Reconcile →"; Release checklist "Proposed" row → "Fix in" Reconcile (`reconcile?cause=asset_types`)
##### Steps
1. Opens `#reconcile?cause=asset_types&scope=AMD` (or Cause "Category mapping") -> mapping rows with **Approve** / **Reject** / **Choose another**.
2. Clicks **Approve** -> button disables, "Saving…", then red "Couldn’t save: READONLY_MSG." Button re-enables (still titled "Approve this category").
3. Expands the row, picks a different "Standard category" and clicks **Choose another** -> same refusal. Clicks **Reject** -> same.
##### Variations
- A row with no proposal shows **Map** instead of Approve; same refusal.
##### Edge Cases
- The 409 "Changed since loaded. Reloading." path can never fire here; the read-only 403 comes first.
- The refusal text says "decisions, views and prompts", not mappings.

##### Merged duplicate: `reconcile-mapping-encode` STORY-011: Read-only visitor tries the mapping buttons

**Type**: short
**Topic**: reconcile-mapping-encode
**Persona**: Analyst on the hosted copy (`LEDGER_READONLY=1`)
**Goal**: Understand how GOOGL "Technical infrastructure" was categorised
**Preconditions**: Header shows "Read-only"; no Signer box
**Ideal path**: 2 — open the row and read the decision card; buttons should be hidden
**Alternate paths**: `#proof/GOOGL` Category mapping stage card (same `mappingDecision` card, no buttons)
###### Steps
1. `#reconcile?scope=GOOGL&cause=asset_types` -> rows with **Approve / Reject / Choose another**
2. Open "Technical infrastructure" -> Proposed Technology Equipment, Company’s own tag "Company-specific tag: goog:TechnicalInfrastructureMember · not every extracted year", Affects "3 figures · $203,679M FY2025"
3. Clicks **Reject** out of curiosity -> "Couldn’t save: this copy … is read-only; …."
###### Edge Cases
- `me` is unset on the read-only copy, so Approve/Choose another are disabled with "Enter a signer name" (misleading there) while Reject is enabled and fails on click.
- The trail card shows the same facts with no buttons — the better read surface for this persona.

#### STORY-062: Check whether v1.9.0 can be signed, and what blocks it
**Type**: medium
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-008; merged with `release-sign` STORY-010 (Read-only visitor presses Sign)
**Persona**: Marcus, wants to know if a new release is imminent before he builds on v1.8.0
**Goal**: Understand v1.9.0's status and the blocking checks
**Preconditions**: Hosted read-only copy; v1.9.0 vs v1.8.0; required lines failing: Proposed, Needs review, Golden test
**Ideal path**: 2 — open Release, read the failing required lines
**Alternate paths**: Proof "Releases" table note "Next release" → `#release`; Proof header "<k> of 6 proven" and each company's "<n> to review"; Known gaps "Release" claims; checklist via `GET /api/v1/release/checklist` (no UI link)
##### Steps
1. Clicks "Release" -> "Release", "v1.9.0 · Compared with v1.8.0 · 6 companies · <k of m> required checks pass".
2. Reads the **Sign v1.9.0** button -> disabled; status "3 required checks failing" (title the same). Read-only plays no part: it is disabled because checks fail.
3. Reads the checklist -> Fail rows: "Proposed", "Needs review", "Golden test" (note "gold unverified 1 of 120: give the verdicts on Proof"); Pass rows G1, G4, G5, Blocks release, Test run, Packet v1.9.0; Info rows "Rows with no value", "Rows changed since v1.8.0", "Known gaps: 0 stub · 3 stale · 37 open findings".
4. Clicks the "Golden test" row -> detail table expands.
5. Clicks its "Fix in" link (Proof) -> `#proof`; Hand check shows "APLD 19/20". Marcus realises the fix is a grader's job he cannot do here (STORY-057).
6. Back; clicks "Fix in" on "Proposed" -> `#reconcile?cause=asset_types`; the mapping rows (STORY-061).
7. Scrolls Release to "Changes since v1.8.0" -> List, Rows, Added, Removed, Changed, Columns.
##### Variations
- `#release?version=v1.8.0` -> the signed release's checklist; Sign button reads "Sign v1.8.0", disabled or not depending on lines.
##### Edge Cases
- If every required line passed on the hosted copy, Sign would be **enabled** with title "Signs and publishes v1.9.0"; clicking shows `confirm("Sign and publish v1.9.0 as Kenny Geiler?")` — a visitor asked to sign as Kenny — then red READONLY_MSG. Broken-flow risk.
- Hosted copy may lag the checkout (findings F6 "not redeployed since v1.8.0", F19), so the checklist a visitor reads may not be the one Kenny signs.
- "To review" counts appear on Proof (per company), Reconcile header, trail summary and Release lines — same numbers, four surfaces.

##### Merged duplicate: `release-sign` STORY-010: Read-only visitor presses Sign

**Type**: short
**Topic**: release-sign
**Persona**: An outside reviewer on the hosted copy (`LEDGER_READONLY=1`)
**Goal**: See whether the release would pass, and (curious) try Sign
**Preconditions**: Hosted copy; header shows "Read-only"; suppose every required line is green there
**Ideal path**: 1 — open Release; a read-only copy should show no Sign button
**Alternate paths**: none found
###### Steps
1. Open **Release** -> checklist renders; "Test run" line reads Info "commit not compared: no git; …" (hosted copy ships no .git) — which is not required-pass, so Sign stays disabled ("1 required check failing").
2. If it were enabled (the `me` variable still holds "Kenny Geiler" from the default even though the Signer box was replaced by "Read-only"), clicking → confirm "…as Kenny Geiler?" → red "this copy of Kenny's Data Emporium is read-only; decisions, views and prompts change in a checkout of the repository".
###### Edge Cases
- The button renders on a read-only copy at all; the status text never says "Read-only".
- On the hosted copy the Test run line can never pass, so the read-only Release page always looks "not signable" — a visitor may read that as a data problem.

#### STORY-063: Verify one AMZN figure all the way to the filing
**Type**: long
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-009
**Persona**: Priya, fact-checking a "$83B capex" claim before publishing
**Goal**: Confirm AMZN's latest capex value, see the exact 10-K cell, and keep the evidence
**Preconditions**: Hosted read-only copy; AMZN in scope; crops located for the cited cell
**Ideal path**: 4 — jump to AMZN, open trail, open the capex item's crop, Open in filing
**Alternate paths**: Proof board row → trail; jump box → Dataset → ticker cell → trail; Dataset Grid cell provenance → "Open in 10-K ↗"; Hand check item crop (if sampled); Reconcile expanded row → "Company trail" / "Open in EDGAR ↗"; Explore click bar → rows → trail; `#evidence/<id>` from a trail item; sec.gov links
##### Steps
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
12. Clicks "Reconcile" in the trail header -> `#reconcile?scope=AMZN`; sees any open AMZN items, does not touch the decision form after STORY-060.
13. Clicks "Dataset" -> `#data?ticker=AMZN`; switches to **Grid**, Field Capex -> the same FY2024 cell with ✓ mark; clicks it -> provenance with "Open in 10-K ↗" (same filing link as step 7).
14. Clicks **Export CSV** -> keeps the numbers alongside the screenshot.
##### Variations
- Crop state "Crop out of date" / "Cell not located" / "Crop file missing": no lightbox; she falls back to "sec.gov ↗"; `/evidence/crops/<f>.png` returns 404 JSON.
- Filing viewer refusals: 409 "the stored copy of this filing differs from its fingerprint" or 410 "…missing" as raw JSON in the new tab.
##### Edge Cases
- The same value + filing link shows on trail, Dataset Grid provenance, Evidence page, Reconcile evidence and Hand check — five surfaces for "where did this number come from".
- The jump box lands on Dataset while the "proof" lives on the trail; one extra hop for a fact-checker.
- Hosted copy's "Data as of" may trail the local run (F6); the scope-line date is the only hint.

#### STORY-064: A day on the hosted copy: evaluate the whole dataset before licensing it
**Type**: long
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-010
**Persona**: Sam, head of data at a buyer, assessing trustworthiness; skeptical, reads everything, clicks every button "to see"
**Goal**: Decide whether the dataset is trustworthy enough to license, leaving with files and a list of caveats
**Preconditions**: Hosted read-only copy; fresh browser; v1.8.0 latest signed; v1.9.0 unsigned
**Ideal path**: 8 — Proof board, one trail, Rules scores, Known gaps, Release, Docs Known limitations, packet download, done
**Alternate paths**: Docs "How it works" flow diagram boxes jump to Proof / Rules / Reconcile / Release / Dataset; Release "Fix in" links into each page; `/docs/<NAME>.md` plain text; read API `/api/v1/...`
##### Steps
1. Opens the hosted root -> Proof; notices "· Read-only" in the scope line and "Read-only" top right.
2. Reads "0 of 6 proven" and each row's "<n> to review" -> frowns; hovers a stage cell for the breakdown (checked · done · explained · open).
3. Reads the Legend and "Verification source" table (SEC XBRL, Other company document, Ties to total, Later actual …, "All").
4. Opens Failure types card -> pareto charts and the Type · Cause class · Origin · Check · Companies seen table.
5. Opens "Regression test" -> Steps Pass/Fail, Differences.
6. Scrolls to Hand check -> "x right · y wrong · z can't say · n unchecked · error rate a% (95% CI …)" per group; picks "MSFT 20/20"; reads a few items.
7. Clicks **Right** on one item "to see" -> red READONLY_MSG under it. Notes: "buttons live, refused after the fact."
8. Clicks the MSFT row in the board -> `#proof/MSFT` trail; opens one crop and "Open" in filing (STORY-063 path).
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
##### Variations
- Reads docs as plain text in a new tab via the footer "Source: docs/<file>.md" link -> `/docs/<NAME>.md`.
- Uses the read API directly (`/api/v1/values?ticker=MSFT`, `/api/v1/proof`) instead of the pages.
##### Edge Cases
- Three refusals in one session (steps 7, 11, 15), each in a different style: plain red text (gold), "Couldn’t save: … Try again." (Reconcile), drawer message (Explore); Delete would add a silent one.
- Staleness of the hosted copy is only discoverable on Known gaps; nothing on Proof or the scope line says "this copy is behind".
- Trust signals repeat across Proof board, trail summary, Rules scores, Release checklist and Known gaps — high redundancy, but each phrased differently ("to review", "Needs review", "open").
- Docs explain the owner's workflow; no page addresses a visitor's "what can I do here".

#### STORY-065: Look up an unknown ticker from the jump box
**Type**: short
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-011
**Persona**: Dana, wants Oracle, assumes it is covered
**Goal**: See ORCL's capex
**Preconditions**: Hosted read-only copy; ORCL not in scope
**Ideal path**: 2 — type ticker, learn it is not covered
**Alternate paths**: Dataset Company select ("Every company" + in-scope list); Proof board (only the 6 proven); Dataset Companies list
##### Steps
1. Types "ORCL" in "Ticker or company…" (no datalist match) and presses Enter -> matches `/^[A-Z.\-]{1,6}$/`, navigates to `#data?ticker=ORCL`.
2. Sees "No rows." (or "0 rows of <m>") -> unsure whether ORCL is missing or filtered; checks Dataset "Companies" list to confirm it is not there.
##### Variations
- Types "Oracle" (a name, not on the list, longer than 6 letters) -> nothing happens at all; the box keeps the text.
- `#proof/ORCL` typed by hand -> trail header with "Not in scope".
##### Edge Cases
- No "not covered" message on Dataset; the trail says "Not in scope" but the jump box never goes there.

#### STORY-066: Read-only copy where the health request fails
**Type**: short
**Topic**: readonly-visitor
**Source**: `readonly-visitor` STORY-012
**Persona**: Leo on a slow hotel connection
**Goal**: Browse, unaware the copy is read-only
**Preconditions**: Hosted read-only copy; `/api/hq` fails or is very slow
**Ideal path**: 1 — the read-only state should come with the page shell (server-rendered), not depend on a second request
**Alternate paths**: none found (`/api/hq` is the only source of `readonly` in the UI)
##### Steps
1. Opens `#proof` -> page renders from `/api/v1/proof`; `/api/hq` errors; the header keeps "Signer [Kenny Geiler]"; no scope line.
2. Edits the Signer box to "Leo" thinking it identifies him -> stored to `localStorage.datahq-me`; buttons stay enabled.
3. Clicks **Right** on a hand-check item -> red READONLY_MSG. The first sign the copy is read-only.
##### Variations
- `/api/hq` succeeds late: the Signer box vanishes mid-session under his cursor and is replaced with "Read-only".
##### Edge Cases
- `.catch(() => {})` swallows the error; no scope line ("<n> companies · Data as of …") either.
- The "Leo" he typed persists in this origin's localStorage and is used as `by` on every refused request.

### Topic: UX paths: operator-onboarding (`operator-onboarding`)

<details><summary>Topic notes (as written by the topic pass)</summary>

Topic: **New operator: Docs, Rules, Known gaps**. The takeover path for someone inheriting Kenny's Data Emporium:
the Docs sidebar and flow diagram (`#docs/<slug>`, `pages/docs.js`, `pages/_markdown.js`, `ledger/web/docs.py`), the
agent charters, scores and runs on Rules (`#rules`, `pages/rules.js`, `/api/v1/rules`, `/api/agents`), and the claims
and open findings on Known gaps (`#gaps`, `pages/gaps.js`, `/api/v1/claims`). Everything in this topic is read-only:
no POST is reachable from these three pages.

Live data at time of writing (GET only, 2026-11-04): 9 Docs pages; Rules shows `Agents · 5` (Reader statements@v2,
AI spend reader aispend@v4, Notes reader notes@v3, Projects reader projects@v1, Mapper mapper@v1, all on
claude-opus-5-5), a Rules table of 74 rows (21 Rule, 5 Guard, 1 Definition, 47 Mapping) and `To review · 45`
(Proposed category 29, Does not tie to total 14, Readings differ 2); Known gaps shows 6 Holds · 38 Partial · 0 Not
built · 3 Out of date · 3 Planned · 37 open issues, `Claims · 50`, `Open issues · 37`, no unregistered claims, issue
log append-only enforced.

</details>

#### STORY-067: First five minutes on the flow diagram
**Type**: short
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-001
**Persona**: Dana, a data engineer handed the repo and the local app URL on her first morning; has never seen the product.
**Goal**: Get the one-picture model of the pipeline and jump to the page that owns the step she cares about (who reads the filings).
**Preconditions**: Local app running on http://localhost:3610; Dana lands on the default route (`#proof`).
**Ideal path**: 3 (Docs tab → read the diagram → click "Read") — the diagram is the first thing on the first Docs page, and each box is a link.
**Alternate paths**: Type `#docs/overview` directly; the nav "Rules" tab goes to the same place as the "Read" box; HANDOFF's "five-minute tour" (Docs → Handoff) lists the same steps as CLI commands; raw text at `/docs/OVERVIEW.md` (no diagram, the mermaid shows as source).
##### Steps
1. Sees the Proof board with six companies all reading "<n> to review" and thinks "too much, where is the manual?" → clicks **Docs** in the navbar → URL `#docs`; no slug, so the page falls back to the first sidebar entry, "How it works" (highlighted, `aria-current="page"`).
2. Reads the flowchart drawn as six boxes in a row: Filings (EDGAR, XBRL) → Read (headless agents) → Check (citations, rules, keys) → Review (open items only) → Release (signed packet) → Database (Postgres, read API) → notices the boxes have no button styling and hovers to discover they are links.
3. Clicks **Read** → navigates to `#rules`; the navbar highlights Rules and the page opens on `Agents · 5`.
##### Variations
- Clicks **Review** instead → `#reconcile`; **Release** → `#release`; **Database** → `#data` (Dataset tab highlighted).
- Reads the table under the diagram (Step · What happens · Page · Package) and clicks its "Rules" link in the Page column: same destination as the box (two links to one route on one screen).
- At phone width (≤700px) the diagram is drawn vertically (boxes stacked); the navbar itself scrolls sideways (finding F-DS1 on Known gaps).
##### Edge Cases
- **Filings** and **Check** both go to `#proof`: Dana clicks Check expecting a list of checks and lands on the same Proof board as Filings. The checks she wanted are on Rules or Docs → Rules and checks. Redundant destination, mismatched expectation.
- The Package column links (`../ledger/ingest/`) open GitHub in a new tab (`REPO_URL`), not the local checkout; offline, they fail.
- The diagram only renders a strictly linear flowchart; if someone adds a branch to OVERVIEW.md's mermaid block, the page silently shows it as a code block instead.

#### STORY-068: Reading the Handoff page start to finish and following its links
**Type**: long
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-002
**Persona**: Dana again, day one afternoon, blocking out two hours to "take the system over" as HANDOFF tells her to.
**Goal**: Read the handoff, understand setup, the objects, and the house rules, opening each referenced doc once, and come out knowing what to run first.
**Preconditions**: On `#docs/overview`. Has a fresh clone but has not run `uv sync`.
**Ideal path**: 6 (Handoff → Map → Operating guide → Glossary → Rules and checks → back to Handoff for setup) — the docs a takeover needs are all in one sidebar; the rest is reading.
**Alternate paths**: The overview's "Where to go next" list links every one of these pages; HANDOFF's first line links Map, Overview and Operations; each page is also at `/docs/<NAME>.md` as plain text; `docs/HANDOFF.md` in the clone itself.
##### Steps
1. Scans the sidebar labelled "Docs pages": How it works, Operating guide, Glossary, Map, States, Rules and checks, Evaluation, Known limitations, Handoff → hesitates: "Handoff" is last but is the one titled "Start here" inside. Clicks **Handoff** → `#docs/handoff`, heading "Start here".
2. Reads the first line: links "docs/MAP.md", "docs/OVERVIEW.md", "docs/OPERATIONS.md" → hovers one; links to sidebar files resolve to `#docs/map`, `#docs/overview`, `#docs/operations` (in-app, same tab).
3. Reads "What this is, in four sentences" → notices "100 companies across the AI supply chain" while the scope line under the nav says "6 companies" → makes a mental note: the proven set (MSFT, GOOGL, AMZN, NVDA, APLD, AMD) is not the full scope.
4. Clicks the inline `docs/COMPANIES.md` reference → it is code text (backticks), not a link; she switches to the sidebar instead and cannot find COMPANIES there (it is served only as raw text).
5. Reads "Setup" (a fenced bash block: `uv sync`, `.env` with `SEC_USER_AGENT`, `claude` then `/login`, `LEDGER_CLAUDE`, `ledger test --fast`) → copies it to her terminal (outside the app).
6. Reads "The five-minute tour" block → notes `ledger app` is what serves this page at port 3610 and that `ledger run --ticker NVDA` runs agents.
7. Reads "The objects, and where each lives" table → sees "prompts | one per agent, versioned the same way | `agents/prompts/`".
8. Clicks **Map** in the sidebar → `#docs/map`; reads "Packages", "Key modules", "To change X, edit Y" → links to `../ledger/...` paths open GitHub in a new tab.
9. Returns with Back → `#docs/handoff` (hash routing keeps history) → page scrolls to top, not where she was.
10. Scrolls to "How to do the common things" → reads "Map a reported asset type" → notes it says Reconcile's "asset types" group and "Approve or Edit".
11. Clicks **Operating guide** → `#docs/operations` → reads "Never" (8 rules: never sign unreviewed, never run agents on the paid API, never edit a prompt in place …).
12. Reads "Daily review": links "[Proof](#proof)" and "[Reconcile](#reconcile)" are app routes; reads the asset-type bullet: "**Approve**, **Edit** or **Reject**".
13. Clicks the inline "Glossary" link (`#docs/glossary`) → the Glossary loads; footer reads "Written from code on every request" instead of a Source link.
14. Uses the browser's find for "Proposed" → finds it in "State words" (machine row, state `wait`) → then the "Terms" table defines Proof, Rules, Reconcile, Dataset, Explore, Release, Known gaps, Docs, Company trail.
15. Clicks **Rules and checks** → `#docs/rules`; reads "Order of checks" (6 steps), "Answer keys, strongest first", the rules table split block/warn/info, and "Release gates" G1/G4/G5/G6.
16. Clicks a rule's File link `rules/jump.yaml` → opens GitHub in a new tab (the rationale and owner live only there).
17. Clicks **Handoff** again → scrolls to "The rules of the house" and "Reading order and invariants" → finishes.
18. Opens **Reconcile** to see the "Edit" button the docs promised → finds a Category mapping row offers **Approve** / **Reject** / **Choose another** (or **Map**), and the group is labelled "Category mapping", not "asset types".
##### Variations
- Reads HANDOFF via its Source footer link `docs/HANDOFF.md` → `/docs/HANDOFF.md` raw text/plain in the same tab; no sidebar, no back link other than the browser's Back.
- Starts from How it works → "Where to go next" → "Taking the system over: Handoff" instead of the sidebar.
##### Edge Cases
- Doc label drift: OPERATIONS and HANDOFF both name an **Edit** mapping action and an "asset types" group; the UI has **Choose another** / **Map** and "Category mapping". A new operator following the docs literally cannot find the button.
- HANDOFF "100 companies" vs scope line "6 companies" with no explanation on the page itself (the Glossary's "Proven set" term explains `config.PROVEN` vs `config.SCOPE`, two clicks away).
- Docs referenced but not served (README.md) render as GitHub links; `/docs/README.md` returns 404 JSON `{"error": "not found"}` if typed.
- Every route change scrolls to the top (`window.scrollTo(0, 0)`), so Back from Map loses her place in a 239-line Handoff.

#### STORY-069: Looking up an unknown word from a Rules card
**Type**: short
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-003
**Persona**: Priya, a finance analyst joining as second reviewer; comfortable with 10-Ks, not with the app's vocabulary.
**Goal**: Find out what "Corroborated" and "Matches SEC XBRL" mean after seeing them on the Reader agent's score.
**Preconditions**: On `#rules`, Reader card visible.
**Ideal path**: 2 (Docs → Glossary) — a single glossary page written from the same state code the cards use.
**Alternate paths**: Docs → States (`#docs/states`, STATES.md, 598 lines, M1 section); Docs → Rules and checks → "Answer keys, strongest first"; the Proof trail's legend shows the colour words without definitions; hover tooltips exist only for some state words elsewhere (e.g. Reconcile decision buttons).
##### Steps
1. Reads Reader's Score datagrid: "Outputs · Statement figures — Checked 80 · Explained 1 · Open 0 · Blocked 0 (of 81)", "SEC XBRL match — Matches SEC XBRL 80 of 81 · 98.8% (95% CI 93.3–99.8%)" → wonders whether "Checked" includes Corroborated. No link from the card.
2. Clicks **Docs** → lands on How it works (not the glossary; the bare `#docs` route always opens the first page) → clicks **Glossary** in the sidebar.
3. Finds "Corroborated" in "State words" (machine row) and "Checked" in Terms: "Agrees with an independent check: an answer key, a verified quote, a located table, or a confirmed mapping." → satisfied.
##### Variations
- Looks up "Twin" (the Score uses "SEC XBRL" in the label, the Glossary's term is "Twin") → finds it under Terms; the word "twin" never appears on the Rules card itself.
##### Edge Cases
- Hovering the "Score" heading shows a long `title` tooltip (sc.note) explaining how outputs are counted; nothing signals the tooltip exists.
- Same definitions live on three surfaces (Glossary, States, Rules and checks), plus STATES.md's machine prose; only the Glossary is generated from code, the others can drift.

#### STORY-070: Auditing one agent before trusting it (charter, score, runs, history)
**Type**: medium
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-004
**Persona**: Marcus, ML engineer taking over the agents; has to decide whether the AI spend reader's v4 prompt is safe to keep.
**Goal**: Understand what the AI spend reader owns, how it is scored, what each company run cost, and how its prompt evolved.
**Preconditions**: On `#rules`. Signer irrelevant (no write controls).
**Ideal path**: 5 (Rules → AI spend reader card → Full charter → read Score → read Prompt and model history) — all on one card.
**Alternate paths**: Docs → Evaluation (`#docs/evals`, "Scores per agent", "Planted errors", "Cost"); Docs → Handoff "The objects" table points to `agents/charters/`, `agents/prompts/`; the raw `/api/agents` JSON; `agents/charters/ai_reader.md` in the clone; Proof's Failure types card mentions checks but not agents.
##### Steps
1. Scrolls past the Reader card to **AI spend reader** → header: job "Reads the MD&A passages of each 10-K that mention AI next to capital or operating spending…", right side "Model claude-opus-5-5", "Prompt aispend@v4".
2. Reads the Charter column: first paragraph only ("The reader of what a company says about AI's part of its spe…") → clicks **Full charter** → headings Owns, Never touches, … expand inline as small paragraphs.
3. Reads Score: "Outputs · AI disclosures — Checked 188 · Explained 39 · Open 0 · Blocked 0 (of 227)", "SEC XBRL match — No SEC XBRL counterpart", "Planted errors — Not measured" → thinks "not measured why?". The page gives no reason.
4. Reads **Runs per company**: rows MSFT, GOOGL, AMZN, NVDA, APLD, AMD with Documents, Calls, Input tokens, Output tokens, Time (s), Attempts, Failed (all 0); footer "All 6 · 186 · 186 · 1,069,738 · 163,566 · 1,584 · 162 · 0".
5. Hesitates: Attempts (162) is lower than Calls (186) in the footer; nothing explains the difference.
6. Reads **Prompt and model history** (When · By · Change): 29 Oct "aispend@v1: first prompt", "aispend@v2 saved, not in use: a sentence with no year gives fiscal_year null…", "switched to aispend@v2", same for v3, 30 Oct "switched to aispend@v4"; note at right "Versions: v1, v2, v3, v4".
7. Notices v4 has a "switched to" line but no "saved, not in use" line with its reason → decides to read `agents/prompts/` in the clone.
8. Opens **Docs → Evaluation** to learn what "Planted errors" means → reads "Planted errors" and "Scores per agent".
##### Variations
- Same audit on **Reader**: Planted errors reads "Caught 1,712 of 1,837 · Missed 1 · No effect 124 · Without the SEC XBRL check: caught 1,705, missed 8"; then expands **Planted errors by kind** (Kind · Planted · Caught · SEC XBRL only · Missed · No effect · Caught without SEC XBRL · Missed without SEC XBRL), sees "omission" with 116 No effect.
- **Notes reader**: "Matches SEC XBRL 204 of 209 · 97.6% (95% CI 94.5–99.0%)", Open 16.
- **Mapper**: Runs per company all zeros, no Score block at all (score null), history one line "mapper@v1" → Marcus wonders whether the mapper ever ran; HANDOFF says mapper runs via `ledger mapper <TICKER>` and its 47 proposals were one batch.
##### Edge Cases
- The API carries `faults_note` ("not measured: `ledger faults` corrupts `extractions` only…") but `scoreBlock` never renders it; "Not measured" has no explanation on the page.
- The Score h3's tooltip is the only place the counting rule lives.
- No write UI: the server has `/api/agents/<id>/prompt|use|model` POST routes, but Rules offers no button; an operator who wants to switch a prompt must use the CLI or edit `agents/agents.json`, which OPERATIONS rule 3 describes as a two-step version switch.
- A retired agent is filtered out of `Agents · <n>`; there is no way on the page to see retired agents' history.

#### STORY-071: Is this rule doing anything? (Rules table vs Docs → Rules and checks)
**Type**: medium
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-005
**Persona**: Priya, second week, seeing "Large year-over-year change" on Reconcile and wanting to know what rule produced it and how often it fires.
**Goal**: Find the rule behind a Reconcile check, its severity, how many times it hit, and its rationale.
**Preconditions**: On `#reconcile`, Check filter shows "Large year-over-year change".
**Ideal path**: 3 (Rules → find `jump` row → read Description/Severity/Hits) — one table, but the rationale needs a 4th step to the yaml.
**Alternate paths**: Docs → Rules and checks (`#docs/rules`): same rules split by block/warn/info with the `check` name and a File link to `rules/<id>.yaml` on GitHub; Release checklist "Fix in → Rules"; `rules/jump.yaml` in the clone.
##### Steps
1. Clicks **Rules** in the navbar → scrolls past five agent cards (several screens) to the "Rules" table.
2. Scans Kind · Rule · Description · Severity · Hits · Failure type → 74 rows, no search box, column headers are not sortable (dtable).
3. Finds "jump" (Rule, "A field does not move more than 3× from one fiscal year to the next.", warn, Hits 5) → hovers the Rule cell; the title shows the raw id `jump`.
4. Wants the rationale → nothing on the Rules page shows it → opens **Docs → Rules and checks** → rules table row `jump` | warn | `check` | description | File link.
5. Clicks the File link → GitHub `rules/jump.yaml` in a new tab → reads rationale and owner.
6. Returns to Rules and looks at Guards: "part_year" Hits 40, Failure type "#68" → "#68" is plain text, not a link; she has no idea where failure type 68 is listed.
##### Variations
- Wants only block-severity rules: Docs → Rules and checks groups them (block first); the Rules page does not.
- Looks for "Restated" (from the Reconcile Check filter): Rules row "restated" info Hits 10 and Guard "restated_between_filings" Hits 5 — two rows with similar names.
##### Edge Cases
- 47 of the 74 Rules-table rows are Kind "Mapping" (each PP&E category of the proven six); real rules are buried among them. Known gaps finding F-RC5 (low) says exactly this: unconfirmed mappings listed under Rules.
- Redundancy: the Rules table (`/api/v1/rules`, with Hits and Guards/Definitions/Mappings) and Docs → Rules and checks (`rules/*.yaml` only, with check names, files and gates) describe the same 21 rules with different columns; neither links to the other.
- "Failure type" numbers correspond to `taxonomy/failures.yaml` / docs/INGESTION.md, neither surfaced in the app.
- If `rules/*.yaml` fails to load the API returns `rules_error`, which `rulesPage` never renders: the table would just be shorter.

#### STORY-072: What's open on the proven set, from Rules "To review"
**Type**: short
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-006
**Persona**: Dana, wanting a one-screen answer to "what is blocking us" without learning Reconcile's filters yet.
**Goal**: See what needs a person, grouped by need.
**Preconditions**: On `#rules`.
**Ideal path**: 2 (Rules → scroll to "To review · 45").
**Alternate paths**: Reconcile header counts and cause cards (live 69 rows, includes items not in this list); Proof board per-company "<n> to review"; company trail summary "<n> to review"; Release checklist lines Needs review / Proposed / Blocks release.
##### Steps
1. Clicks **Rules** → scrolls to the bottom → "To review · 45".
2. Reads three cards: "Proposed category" (29 rows: MSFT mapping "Buildings and improvements: BuildingAndB…, to confirm", …), "Does not tie to total" (14: GOOGL facts "segment_revenue_tie: segment_revenue FY2…"), "Readings differ" (2: APLD "ppe_category Other equipment and fixture…").
3. Wants to act on the GOOGL tie → rows are not clickable; no link to the trail or Reconcile → goes to the navbar **Reconcile** and filters Scope GOOGL by hand.
##### Variations
- With nothing open the section reads "No items to review" in a card.
##### Edge Cases
- Count disagreement across surfaces: Rules says 45, Reconcile shows 69 rows; a new operator cannot tell which is "the" number (Rules' list covers rule findings and mappings on the proven set; Reconcile includes new filings, unconfirmed findings and other causes).
- Same information on four+ surfaces (Rules To review, Reconcile, Proof board, trail, Release) with no cross-links from this one: a dead end.

#### STORY-073: Reading the claims register to decide what not to promise
**Type**: medium
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-007
**Persona**: Leah, the new owner's PM, preparing a call with Arctal and wanting to know which product claims actually hold today.
**Goal**: List the claims that hold, those that are partial, and why the stale ones are stale.
**Preconditions**: On any page; local copy.
**Ideal path**: 4 (Known gaps → sort Status → expand a stale claim → read Gaps column).
**Alternate paths**: Docs → Known limitations (`#docs/claims`, the generated CLAIMS.md: same register as a static table with Declared, Computed, Why, Gaps, Ticket); `/api/v1/claims`; Release page lines that link "Fix in → Known gaps".
##### Steps
1. Clicks **Known gaps** → header "6 Holds · 38 Partial · 0 Not built · 3 Out of date · 3 Planned · 37 open issues", right side "Updated <time>".
2. Sees no "Unregistered claims" alert and no append-only warning → reads that as healthy.
3. Reads "Claims · 50" table (Claim · Where · Status · Gaps): first rows are Out of date (orange): "SEC checked · Next 10-K expected" (Where: Company trail), "Coverage", "Hosted copy".
4. Clicks the **Status** header to sort → Not built → Out of date → Partial → Planned → Holds order (CLAIM_ORDER); clicks again to reverse and see the 6 Holds first: "Calculated: the formula and the arithmetic…", "Verification tile counts", "Answer-key values missing from the dataset = 0", "LIMITATIONS.md in every packet", …
5. Clicks the "Hosted copy" row → a detail row expands with the non-proven reasons as a list (claimWhy) → reads "open findings" / "hosted code checked live only" style phrases.
6. Hovers the "Coverage" status ("Out of date") → tooltip "Declared Partial": the computed status is worse than declared.
7. Reads its Gaps cell: "New filings not yet read are as fresh as the last EDGAR check." → writes "don't promise freshness" in her notes.
8. Opens **Docs → Known limitations** to copy a cleaner table for the call → sees "proven 0 · partial 41 · stale 4 · stub 2 · planned 3 · open findings 37" — different counts from the page she just read.
##### Variations
- Sorts by **Gaps** (count of gaps + facts) to find the claims with the most caveats.
- Filters by Where mentally: "Agent scores with Wilson intervals · planted-error catch rate" → Where "Rules, Proof", Partial, Gaps "Planted faults are nine made-up kinds of error, not the real mix…".
##### Edge Cases
- Redundancy with drift: Known gaps (live, computed per request) and Docs → Known limitations (CLAIMS.md, written by `ledger claims`, excludes clock/commit-dependent checks: "checked live only") show the same 50 claims with different status counts (live 6 Holds vs doc 0 proven, 2 stub vs 0 Not built). CLAIMS.md also calls the page "the Gaps page" while the navbar says "Known gaps". Status words differ too: doc "proven/stub/stale", page "Holds/Not built/Out of date".
- The Where column only names pages (`ledger/web/pages/*.js`); claims backed only by server code ("Late writers never overwrite", "Decisions record person or run", "Point-in-time as_of") show "—".
- Clicking the Claim text expands the row, it is not a link to the page the claim is made on.

#### STORY-074: Triage the high-severity open issues before taking ownership
**Type**: long
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-008
**Persona**: Dana, end of week one, about to tell Kenny she accepts the handoff; wants every high-severity issue understood and mapped to where it shows up in the app.
**Goal**: Read every High open issue, see which claim it caps, and verify two of them in the app itself.
**Preconditions**: On `#gaps`. Has read Handoff and Operating guide (STORY-068).
**Ideal path**: 8 (Known gaps → Open issues → expand each High (≈5 shown) → follow one to Proof, one to Release) — the list has no links, so verification costs extra navigation.
**Alternate paths**: Docs → Known limitations "Open findings" section (same 37, static); `claims/findings.jsonl` in the clone; STATES.md M10 describes the finding lifecycle; Release checklist rows for the same problems.
##### Steps
1. Scrolls to "Open issues · 37" → table Severity · Issue · Claim, pre-sorted High → Medium → Low.
2. Reads the High rows: "The hosted copy has not been redeployed since v1.8.0." (Claim: Hosted copy); "The EDGAR check is not scheduled; it last ran on 28 Oct 2026." (SEC checked · Next 10-K expected); "A company outside the proven set with nothing open reads Proven on its trail…" (Proven); "A decision on an exception (decisions/decisions.jsonl) records no author…" (Decisions record person or run); "A reviewer decision keeps counting on Proof…" (Late writers never overwrite); "The check that every verified or explained row names a record that exists runs only in a test…"; "A note figure whose filing's XBRL instance was never loaded reads as unverified, citation only…"; "The release signature, every reviewer decision, gold verdict and mapping from a page are r…" (Sign); "A release can be signed and published while the hosted copy serves an older release…"; "The Release can be signed with the test suite not run…"; "Nothing says when the local app runs older code than the checkout…" (Item states).
3. Clicks the first High row → detail "Logged 2 Nov 2026 · F6" → now has the id to grep in `claims/findings.jsonl`.
4. Counts 11 High issues across 10 claims; wonders why the Severity column header can be clicked to sort again when it is already sorted.
5. Clicks the **Claim** header to group mentally by claim → "Hosted copy" has F3, F6, F19 together.
6. Wants to verify F7 (EDGAR) in the app → no link → types **MSFT** in the jump box "Ticker or company…" → lands on `#data?ticker=MSFT` (Dataset), not the trail she wanted.
7. Clicks the MSFT ticker cell → `#proof/MSFT` → Coverage tile shows "SEC checked <h>h ago" / "out of date" → confirms the finding.
8. Wants to verify F20 (sign with tests not run) → clicks **Release** → checklist: the test-suite line's State (Pass / Fail / Not run / Stale) → reads the Required/Optional column.
9. Notices the Release header "v1.9.0 · Compared with v1.8.0 · … required checks pass" and the Sign button disabled ("<n> required checks failing").
10. Returns to **Known gaps** → page reloads from the API, sort resets to severity, any expanded rows are collapsed.
11. Reads the Medium list for the reviewer workflow: F1 "A finding that changed after a person resolved it shows as open on Reconcile but stays clo…", F-RC1 "On Reconcile a failing tie or readings that differ now carry their own label…".
12. Reads Low F-DS1 about phone width → resizes her window narrow → the navbar scrolls sideways, as logged.
13. Opens **Docs → Operating guide → "When a Release line is red"** to see if there is a playbook per issue → there is one per Release line, not per finding.
14. Writes her acceptance notes outside the app (nothing on Known gaps can be annotated, acknowledged or assigned; adding a finding is CLI only per docs/BUILD.md).
##### Variations
- Reads the same findings in **Docs → Known limitations**, where each claim row also lists a Ticket column (T82, T53…) that Known gaps does not show.
- Sorts by Issue text alphabetically to find duplicates (F15 and F8 both under "Late writers never overwrite").
##### Edge Cases
- Issue text is truncated nowhere, but long sentences wrap into a very tall table; there is no filter by severity or claim.
- The finding's claim is shown by its human text; if a finding names a claim id not in the register, the raw id is shown.
- If the issue log was edited (not append-only), the header shows red "Issue log edited"; if the check could not run, orange "Issue log append-only: not enforced here". Neither links to what was edited.
- Jump box routes to Dataset, not the trail: one extra hop for every "go check company X" step in this topic.

#### STORY-075: Following Release's "Fix in → Known gaps" and "Fix in → Rules"
**Type**: short
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-009
**Persona**: Dana, looking at why v1.9.0 is not signable.
**Goal**: Understand a red Release line that points to Known gaps or Rules.
**Preconditions**: On `#release`; some checklist lines Fail.
**Ideal path**: 3 (Release → expand line → Fix in link).
**Alternate paths**: Known gaps / Rules navbar tabs directly; Docs → Operating guide → "When a Release line is red".
##### Steps
1. On Release, finds a failing line whose "Fix in" says **Known gaps** → clicks it → `#gaps`, top of the page.
2. Has to find the relevant claim herself: the link carries no anchor or filter → scans 50 claims.
3. Back → Release; a line with "Fix in" **Rules** → `#rules` → lands on the agent cards, the relevant rule table is several screens down.
##### Variations
- Reads the line's expanded detail table first ("No items" when empty) to know what to look for.
##### Edge Cases
- "Fix in" targets are page-level only; neither Rules nor Known gaps accept a query string or anchor (`#agent-<id>` ids exist on agent cards but nothing links to them).

#### STORY-076: Reading docs from the hosted read-only copy and via raw links
**Type**: medium
**Topic**: operator-onboarding
**Source**: `operator-onboarding` STORY-010
**Persona**: Arctal's analyst evaluating the takeover, on the hosted copy (`LEDGER_READONLY=1`), no clone.
**Goal**: Read setup and limitations, and download one doc as text to paste into an internal memo.
**Preconditions**: Hosted copy; header shows "Read-only" instead of the Signer box; scope line ends "· Read-only".
**Ideal path**: 4 (Docs → Handoff → Source link → copy text).
**Alternate paths**: `/docs/<NAME>.md` typed directly for any served file (API, BUILD, COMPANIES, DATA_DICTIONARY, FIELDS, INGESTION, PROOF, TAXONOMY plus sidebar files); GitHub links from docs; Known gaps for live limitations.
##### Steps
1. Clicks **Docs** → How it works → diagram works the same (links are in-app routes, all GETs).
2. Clicks **Known limitations** → the CLAIMS.md register; reads "Hosted copy" stale.
3. Clicks **Handoff** → reads "The hosted copy" section.
4. Scrolls to the footer "Source: docs/HANDOFF.md" → clicks → `/docs/HANDOFF.md` served as text/plain in the same tab.
5. Selects all and copies → presses Back to return to the app at `#docs/handoff`.
6. Clicks a link to `docs/BUILD.md` inside a doc → raw text (served, not on the sidebar).
7. Clicks a code link `../ledger/web/app.py` → GitHub in a new tab (works without a clone).
##### Variations
- On the local copy the same flow is identical; Docs, Rules and Known gaps have no write controls, so read-only mode changes nothing on these three pages.
##### Edge Cases
- `#docs/nonexistent` silently shows How it works (no "not found" message); `/api/v1/docs/nonexistent` returns 404 `{"error": "no such doc"}`.
- Raw docs open in the same tab with no app chrome; a reader who lands there from a shared link has no navigation into the app.
- Docs in `docs/archive/` are never served; links to them go to GitHub.
- Known gaps finding F-EV3 notes the hosted copy has no `data/raw`, so links from docs into Open-in-filing paths will 410 there; Docs pages themselves are unaffected.

## Redundancy Candidates

Ranked by how many surfaces repeat the same thing and how much the copies disagree. Story numbers are where the topic
passes recorded it (Alternate paths, Edge Cases, "Redundancy" notes).

### Duplicate paths (several routes to one destination or action)

| # | Candidate | Surfaces | Stories |
|---|---|---|---|
| P1 | Provenance of one figure: crop + "Open" + "sec.gov ↗" for the same cited cell | Hand check, Company trail, Reconcile evidence row, Dataset Grid drawer, `#evidence/<id>` (five; the richest, `#evidence/<id>`, has no inbound link) | 005, 009, 010, 015, 018, 063 |
| P2 | CSV export of the same rows, three shapes | Rows **CSV** (server, ignores "Find in rows"), Grid **Export CSV** (client blob, other columns), Explore **CSV** (drops category / measure / From-To filters); plus the packet zip | 047, 050, 054, 055, 058 |
| P3 | Landing on a company's rows | Jump box, `#company/<T>`, Rows Company select (all → Rows view); the jump box never goes to the trail, which is where the proof is | 009, 046, 063, 065, 074 |
| P4 | Getting from a company to its Reconcile queue | Trail header "Reconcile" link and summary "Review in Reconcile →" (same URL, one screen); stage "Decide in Reconcile →"; Proof row → trail; Release "Fix in" (unscoped) | 012, 013, 027, 037 |
| P5 | Writing a rule or definition | "Apply everywhere" card in the expanded row and the post-save "Saved. Apply to every company?" panel (same `encodePanel`) | 035, 036 |
| P6 | Confirming a mapping with the proposed member | Row **Approve**, card **Approve**, card **Choose another** with the same member; row "Choose another" only opens the card while the card's writes | 029, 031 |
| P7 | Deciding a run's proposal | Its To confirm row and its own Rule findings row settle the same key | 023, 024 |
| P8 | Keeping a chart | **Save as view** (broken) vs copying the `#explore?…` URL, which already reproduces the chart | 052, 054, 059 |
| P9 | Docs flow diagram | "Filings" and "Check" boxes both go to `#proof`; diagram box and the table's Page link go to the same route | 067 |

### Duplicate information (one number or fact shown in several places)

| # | Candidate | Where it repeats | Stories |
|---|---|---|---|
| I1 | Open-item counts | Proof board "<n> to review", trail header + summary tile + stage tallies, Reconcile header, Release lines (Needs review / Proposed / G6 table), Rules "To review · 45" (Reconcile shows 69 rows); each only consistent after reloading each page | 001, 014, 027, 038, 039, 062, 072 |
| I2 | Hand-check state | Proof header link, Regression test summary, Release "Golden test" (all a CLI snapshot) vs the live Hand check section; plus picker tooltip, card header and group rows for the rate | 002, 006, 008 |
| I3 | Claims register | Known gaps (live) vs Docs → Known limitations (CLAIMS.md): different counts and status words (Holds / Not built / Out of date vs proven / stub / stale) | 073, 074 |
| I4 | Rules | Rules table (Hits, guards, mappings) vs Docs → Rules and checks (check names, files, gates); same 21 rules, different columns, no links between them; 47 of 74 Rules rows are mappings | 071 |
| I5 | Mapping decision card | Same `mappingDecision` card on the trail (no buttons) and in Reconcile (with buttons) | 013, 029, 033 |
| I6 | A saved decision | Row Decision cell, Decision card header, trail / Grid badge | 019 |
| I7 | Restated line | Trail Verification cell, compare header, single evidence header, Hand check | 011 |
| I8 | Cited vs SEC XBRL gap | Gap bar, Difference column, evidence table and a large gap bar on one screen | 025 |
| I9 | State words / definitions | Glossary (generated), States doc (hand-written), Rules and checks, trail and Proof legends | 069 |
| I10 | Packet contents | Release "Packet v1.9.0" line detail and the "Packet v1.9.0" card; downloadable only on Proof Releases | 043 |
| I11 | Release info lines | "Known gaps" line repeats the Known gaps header; "Rows changed" line repeats the "Changes since v1.8.0" card | 045 |
| I12 | Read-only marker | Header span and scope line both say it; neither sits next to a write control | 056 |
| I13 | Setup / tour | Handoff, Operating guide, Overview "Where to go next" | 068 |

### Overlapping features (two features doing nearly the same job)

| # | Candidate | Overlap | Stories |
|---|---|---|---|
| O1 | Five readers of a company's figures | Dataset Rows, Dataset Grid, Explore "Show rows", Company trail, Reconcile evidence | 018, 046, 054 |
| O2 | Hand check vs Company trail | Same crops and figures; only the hand check carries verdicts, only the trail carries verification words; neither links to the other | 005, 007, 018 |
| O3 | Rules "To review" vs Reconcile | A read-only, unlinked list of what Reconcile already shows | 072 |
| O4 | Release "Fix in" vs Proof / trail navigation | Page-level links that land at the top of the target page, so the user re-navigates anyway | 006, 039, 075 |
| O5 | Saved views vs URL hash | Every Explore control already writes the hash; saved views add a name and note | 051, 059 |
| O6 | Accept vs Explain | Same server effect (state explained, word "Unverified"); both need a reason; only the badge differs | 019 |
| O7 | Explore "Measure" | The word names three different controls (list select, taxonomy measure, Grid Kind "Every measure") | 046 |

Top 3 to act on first: **P1** (one evidence view linked from every surface), **I1** (one open-item count, one word, linked
to the filtered Reconcile queue), **P2** (one CSV export that honours the on-screen filters).

## Gaps & Recommendations

Coverage gaps (no story, or code path only):
1. Fixtures for paths with no live data: To confirm rows (023, 024), Blocks release rows (024, 036), unmapped categories
   (034), encodable items (035, 036, 037). Without them the "write it once" and run-confirmation flows cannot be walked.
2. Reconcile causes `new_filing`, `value_missing` and `fact_changed`, and the "Release vs Now" / "Before/After" diff
   tables: write stories once a run produces them.
3. Accessibility: "Skip to content", focus order through the navbar and drawers, and a keyboard-only hand check (there are
   no shortcuts there, 007).
4. Phone width (≤700px): only noted in 067 and 074; no story walks Reconcile, Grid or Release at that width.
5. API `as_of` point-in-time reads and `/api/v1/views/<id>/data` have no UI and no story.
6. Known gaps warning states ("Unregistered claims", "Issue log edited", "not enforced here") never seen with data.
7. A successful Explore save: impossible today (broken), so no story covers views after a save.

Recommendations from the stories:
1. Read-only copy: hide or disable every write control with the reason, render the read-only state with the page shell,
   drop "Try again." from permanent refusals, and stop attributing visitor clicks to Kenny (056, 057, 060, 061, 062, 066).
2. Gold: refresh the header, Regression test and Release "Golden test" from live gold files, or say on the page that a
   CLI run is needed; make "Fix in: Proof" land on `#gold` with the company picked; keep the picker in the URL (002, 006, 007).
3. One Signer rule everywhere: every write disabled live with "Enter a signer name", and every write (including Reject
   and Sign) refusing names off `config.PEOPLE` (004, 023, 026, 042).
4. Deep links: "Fix in", Rules "To review" rows, Known gaps issues and the Release detail `link` column should open the
   filtered item, not the top of a page (039, 072, 074, 075).
5. Keep focus on the next row after a save, and never sweep mapping rows into a bulk selection (020, 022, 033).
6. Show the hidden reasons: encode `why_not`, `faults_note`, `rules_error` (035, 036, 070, 071).
7. Fix doc label drift: "Edit" and "asset types" in OPERATIONS/HANDOFF vs **Choose another** / **Map** and "Category
   mapping" in the UI (068).
8. Jump box: send a ticker to the trail (or offer both), and say "not covered" for out-of-scope tickers (046, 063, 065).

## Known broken flows

| Flow | What happens | Stories |
|---|---|---|
| Explore Save as view / Save changes | POST lacks `Content-Type: application/json`; server answers 403 "a write needs Content-Type: application/json"; nothing can be saved | 052, 053, 059 |
| Explore Delete | Same 403, but no error handling: no message, button stays "Confirm delete" until the timer resets, unhandled rejection in the console | 053, 059 |
| Saved view "What companies state about AI, in dollars" | `chart: null`, falls back to x = `period`, shows "No rows match" for 118 rows | 051 |
| Explore JSON / CSV links | Drop taxonomy Measure, Category, Standard type and From/To; CSV holds all 617 rows instead of the 27 charted | 050, 054 |
| Hand-check verdict → Release | Verdict updates the section only; header, Regression test and Release "Golden test" wait for a CLI `ledger golden --check` / `ledger test` and nothing says so | 002, 006 |
| Release Sign button | Enabled state frozen at render; typing a Signer name does not enable it; clearing it does not disable it | 042 |
| Sign and mapping Reject | Accept any non-empty name, unlike every other write | 026, 042 |
| Signed, not published | No retry in the UI; after reload the Release page shows the next version and forgets the failure; `record_error` never shown | 041 |
| Bulk select in "Grouped by company" / space on a mapping row | Mapping keys sent to `/api/resolve/bulk`; whole batch refused 400 with developer wording | 022, 033 |
| Confirm / Save with an empty Signer | Not disabled; server error "a resolution needs a state … and a name" | 023, 026 |
| Resolution saved against a changed item | No stale check; line written against the old hash, row silently stays open | 025 |
| Fix decision | Cannot be closed from the UI; release stays red until a CLI re-read | 027 |
| `cause=to_confirm` filter with no rows; filter after last row settles | Select shows "Every cause" or its first option, hiding the active filter; "No items to review" misleads | 023, 027 |
| Unknown ticker trail `#proof/ZZZZ` | Reads green "Proven" and "Ready for release" for nothing | 017 |
| `#evidence/<id>` | Richest single-reading view, but no page links to it | 015 |
| Filing viewer refusals | Raw JSON (404 / 409 / 410) in a sandboxed tab with no way back; "Open" on rule findings opens the bare filing | 012, 016 |
| "Fix in: Proof" / page-level Fix in | Lands at the top of the page, not on `#gold` or the item; "Fix in" for Limitations points at Release itself | 006, 039, 045, 075 |
| Read-only copy write controls | Rendered enabled with normal tooltips; refused only after a click; Sign would ask "Sign and publish v1.9.0 as Kenny Geiler?" | 056, 057, 060, 061, 062 |
| `/api/hq` failure on the read-only copy | Signer box stays, no "Read-only" marker anywhere | 066 |
| Hosted copy Test run line | Can never pass (no .git), so the hosted Release page always looks unsignable | 062 |
| Grid "Custom…" | Cannot be reopened while already Custom; an empty selection or an industry with no companies silently means every company | 048, 049 |
| Grid `check=` filter | Supported in the URL only; invisible and dropped on the next control change | 055 |
| Hand-check redraw | Clears draft notes on other rows and drops focus; picker selection lost on reload or Back | 002, 007 |
| Choose another select | Defaults to the first option, not the company's tagged member; one click maps to it with no confirm | 031 |
| Encode panel | `why_not` never shown, so "Apply everywhere" just does not appear; after writing a rule the panel disappears with no sign it was written | 035, 036, 037 |
| Release `?version=` | Recomputes the checklist from today's data with no "as signed" cue | 044 |
| Docs label drift | Docs name an **Edit** mapping action and an "asset types" group that the UI does not have | 068 |
| Jump box | Goes to Dataset, never the trail; a company name not in the list (e.g. "Oracle") does nothing | 046, 063, 065, 074 |
