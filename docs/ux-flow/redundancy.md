# Redundancy and information architecture — Kenny's Data Emporium

Date: 2026-11-04 · App: http://localhost:3610 (local) · Data as of Nov 1, 2026 · Read-only pass (no writes, no POSTs)

Sources: `docs/ux-paths/catalog.md` (76 stories; Redundancy Candidates P1–P9, I1–I13, O1–O7) and screenshots in
`docs/ux-flow/redundancy-screens/` (1600×1000, headless Chrome). Script: `docs/ux-flow/tmp/redundancy_shots.py`,
`redundancy_release.py`, `redundancy_docs.py`.

| Section | Findings |
|---|---|
| Duplicate Paths | 7 |
| Duplicate Information | 9 |
| Overlapping Features | 5 |
| Hierarchy & IA | 7 |

Verdict key: **Keep both** (deliberate shortcut) · **Canonical** (keep one route, the rest link to it) · **Remove** ·
**Merge** · **Differentiate**.

---

## Duplicate Paths

### DP1 — Provenance of one figure: five routes, the richest one unreachable
- Routes: Hand check crop, Company trail "Open · sec.gov ↗", Reconcile evidence row, Dataset Grid drawer, `#evidence/<id>`.
- Evidence: `trail-MSFT.png` (Source column: "Open · sec.gov ↗" per row); catalog P1, stories 005, 009, 010, 015, 018, 063.
  `#evidence/<id>` is the only view with the exact dollar figure and scale, and no page links to it (story 015).
- Verdict: **Canonical.** `#evidence/<id>` becomes the one provenance view. Every other surface keeps its small crop and
  adds one "Evidence" link to it; drop the per-surface "Open" + "sec.gov" pair where the evidence view carries both.

### DP2 — CSV export of the same rows, three shapes plus the packet
- Routes: Dataset Rows **CSV** (server, ignores "Find in rows"), Grid **Export CSV** (client, other columns), Explore
  **CSV** (drops Measure, Category, Standard type, From/To; 617 rows for a 27-row chart), release packet zip.
- Evidence: `explore.png` (JSON · CSV next to "27 rows"); catalog P2, stories 047, 050, 054, 055, 058; Known broken flows
  "Explore JSON / CSV links".
- Verdict: **Canonical.** One export that writes exactly the on-screen filtered rows, same columns everywhere. Packet stays
  (it is the signed artifact, a different job).

### DP3 — Ticker lookup lands on Dataset, not on the company's proof
- Routes to "a company": jump box ("Ticker or company…"), `#company/<T>`, Rows Company select → all go to Dataset Rows.
  The Company trail (`#proof/<T>`) is reached only from the Proof board name link.
- Evidence: `proof.png` header jump box; catalog P3, stories 009, 046, 063, 065, 074.
- Verdict: **Canonical.** Jump box → Company trail; the trail already has a "Dataset" link (`trail-MSFT.png`, top right).

### DP4 — Company → its Reconcile queue: four links, two on one screen
- Routes: trail header "Reconcile", trail summary "Review in Reconcile →" (same URL, same screen), per-stage
  "Decide in Reconcile →", Release "Fix in: Reconcile" (unscoped).
- Evidence: `trail-MSFT.png` — "6 to review · Reconcile · Dataset" at top right and "Review in Reconcile →" 60 px below;
  `trail-MSFT-full.png` "Decide in Reconcile →" under each mapping card; catalog P4, stories 012, 013, 027, 037.
- Verdict: **Remove** the header "Reconcile" link (make "6 to review" itself the link). **Keep** per-item
  "Decide in Reconcile →" as a deep link to that item. Release "Fix in" must scope to the company/item (see DP7).

### DP5 — Two entry points to the same encode panel
- Routes: "Apply everywhere" card in the expanded row, and the post-save "Saved. Apply to every company?" panel; both
  render `encodePanel`.
- Evidence: catalog P5, stories 035, 036 (no live data reaches it today, so no screenshot).
- Verdict: **Keep both** as one component, but only one may be visible at a time; after save, replace the card with the panel.

### DP6 — Confirming the proposed mapping three ways
- Routes: row **Approve**, card **Approve**, card **Choose another** with the proposed member pre-selectable.
- Evidence: `reconcile-full.png` Category mapping rows each show "Approve · Reject · Choose another"; catalog P6,
  stories 029, 031; Known broken flows "Choose another select defaults to the first option".
- Verdict: **Canonical.** Approve is the one confirm. Choose another excludes the proposed member and defaults to the
  company's tagged member.

### DP7 — Keeping a chart: Save as view vs the URL
- Routes: **Save as view** (broken: 403, stories 052, 053, 059) vs copying the `#explore?…` hash, which already
  reproduces the chart.
- Evidence: `explore.png` (Save as view next to JSON / CSV); catalog P8, O5.
- Verdict: **Differentiate or remove.** If saved views stay, their job is name + note + listing; until a save works,
  hide the button and offer "Copy link".

Pass (no change): P7 (To confirm row vs its Rule findings row) — no live rows; recheck with fixtures. P9 (Docs diagram
boxes and the step table both link pages) — a diagram plus its table is a normal double; keep.

---

## Duplicate Information

### DI1 — Open-item count: seven surfaces, two disagree with the rest
- Where: Proof board "<n> to review" (6/11/4/2/17/5 = 45), trail header + Verification tile "To review 6", Reconcile
  header "Needs review 16 · Proposed 29", Release "Proposed 29" + "Needs review 16", Rules "To review · 45", Release
  "Release checks by company" G6 column.
- Disagreement: Release by company shows **GOOGL 4, APLD 8**; Proof shows **GOOGL 11, APLD 17** for the same companies.
  G6 counts mappings only, with no label saying so.
- Evidence: `proof.png`, `trail-MSFT.png`, `reconcile.png`, `release-full.png`, `rules-full.png`; catalog I1,
  stories 001, 014, 027, 038, 039, 062, 072.
- Verdict: **Canonical** = Reconcile. Every other surface shows one number with one word and links to
  `#reconcile?scope=<T>`. Rename G6 to what it counts ("Mappings to confirm") or drop the by-company table.

### DI2 — Hand-check state: snapshot vs live
- Where: Proof header "Hand check: 119 of 120 checked", Regression test "Hand check: 119 of 120 checked", Release
  "Golden test … gold unverified 1 of 120" (all CLI snapshots) vs the live Hand check section; plus per-company 20/20
  tiles.
- Evidence: `proof.png` (header, orange), `proof-full.png` (Regression test line repeats it verbatim), `release-full.png`;
  catalog I2, stories 002, 006, 008.
- Verdict: **Canonical** = live Hand check. Header and Release read the live value or say "as of last CLI run";
  drop the duplicate line under Regression test.

### DI3 — Claims register: three breakdowns, three vocabularies
- Known gaps header: "6 Holds · 38 Partial · 0 Not built · 3 Out of date · 3 Planned · 37 open issues".
- Release info line: "proven 6 · partial 38 · stale 3 · stub 0 · planned 3 · open findings 37" (same numbers, other words).
- Docs → Known limitations: "proven 0 · partial 41 · stale 4 · stub 2 · planned 3 · open findings 37" (other numbers).
- Evidence: `gaps.png`, `release-full.png`, `docs-claims.png`; catalog I3, stories 073, 074.
- Verdict: **Canonical** = Known gaps (live). Release line links to it with the same words; Docs → Known limitations
  either embeds the live table or states "snapshot of <date>" above its counts.

### DI4 — Rules described twice, unlinked
- Where: Rules page rules table (Hits, guards, mappings) vs Docs → Rules and checks ("8 block, 10 warn, 3 info
  (21 in rules/)").
- Evidence: `rules-full.png`, `docs-rules.png`; catalog I4, story 071. 47 of 74 Rules rows are category mappings.
- Verdict: **Canonical** = Rules page for the list; Docs keeps the order-of-checks prose and links each rule id to it.

### DI5 — Mapping decision card on two pages
- Where: identical `mappingDecision` card on the trail (no buttons) and in Reconcile (with buttons).
- Evidence: `trail-MSFT-full.png` (Proposed / Company's own tag / Basis / Alternatives / Affects, then
  "Decide in Reconcile →"); `reconcile-full.png`; catalog I5, stories 013, 029, 033.
- Verdict: **Keep both** only if the trail copy collapses to one line (company line → proposed member · Decide →).
  The full card belongs where the decision is made.

### DI6 — Verification counts per company, twice on Proof and once on the trail
- Where: Proof stage table dot-counts, Proof "Verification source" table (SEC XBRL / Ties to total / Citation only per
  company), trail Verification tile (MSFT: Match SEC XBRL 42, Tie to totals 31).
- Evidence: `proof.png` (both tables on the first screen); `trail-MSFT.png`; catalog story 009 redundancy note.
- Verdict: **Keep** the trail tile (per-company view). On Proof, fold "Verification source" behind the stage table or
  into the trail; one company-level breakdown per screen.

### DI7 — Release info lines restate their own cards
- Where: "Rows changed since v1.8.0 · 174" line vs "Changes since v1.8.0" card below; "Packet v1.9.0 · 11" line vs
  "Packet v1.9.0" card; "Known gaps: …" line vs Known gaps page header.
- Evidence: `release-full.png`; catalog I10, I11, stories 043, 045.
- Verdict: **Remove** the cards' summary duplicates: the checklist line links to its card (anchor) instead.

### DI8 — A saved decision shown three times
- Where: row Decision cell, Decision card header, trail / Grid badge.
- Evidence: catalog I6, story 019 (needs a write to reproduce; not captured in this read-only pass).
- Verdict: **Keep** the badge (trail/Grid) and the card header; drop the row cell's full "Accept · name · date" text
  to just the word.

### DI9 — State words defined in four places
- Where: Docs → Glossary (generated from states), Docs → States (hand-written), Docs → Rules and checks, and the
  in-page legends on Proof and the trail.
- Evidence: `docs-glossary.png`, `docs-states.png`, `proof.png` legend "Checked · Located/Done · Unverified · To review",
  `trail-MSFT.png` legend; catalog I9, story 069.
- Verdict: **Canonical** = Glossary (it is generated). States keeps machines and transitions and links words to the
  Glossary; legends stay (they are in-context keys).

Pass (no change): I7 (Restated line on four surfaces — each is the context the reader is in), I8 (gap shown as bar +
number + table on one screen; recheck when the screen is redesigned), I12 (read-only marker — a placement issue, see
readonly stories, not redundancy), I13 (Handoff / Operating guide / Overview "Where to go next" — three audiences).

---

## Overlapping Features

### OF1 — Five readers of a company's figures
- Dataset Rows, Dataset Grid, Explore "Show rows", Company trail, Reconcile evidence.
- Evidence: `data-full.png` (617-row table, 40 columns), `explore.png` ("Show rows"), `trail-MSFT.png`; catalog O1,
  stories 018, 046, 054.
- Verdict: **Differentiate.** Trail = "is this company's data proven"; Dataset = "get the rows"; Explore = "chart it".
  Explore "Show rows" opens Dataset with the same filters instead of a third table; Grid and Rows become two views of
  one Dataset table.

### OF2 — Hand check vs Company trail
- Same crops and figures; only Hand check has the human verdict, only the trail has the verification words; no link
  between them.
- Evidence: `proof-full.png` Hand check section (per-company 20/20), `trail-MSFT.png`; catalog O2, stories 005, 007, 018.
- Verdict: **Merge** the verdict onto the trail row (a "Hand check: right" chip) and link each hand-check item to its
  trail row; the Hand check section stays as the grading queue.

### OF3 — Rules "To review" duplicates Reconcile, with stale instructions
- Rules "To review · 45" lists the same 45 open items as Reconcile, read-only, unlinked, and tells the user to
  "Approve, Edit or Reject" in "Reconcile, asset types" — the UI has no Edit and no "asset types" group.
- Evidence: `rules-full.png` (rows: "proposed by Claude Fable 5.1; Reconcile, asset types: Approve, Edit or Reject");
  `reconcile.png`; catalog O3, story 072.
- Verdict: **Remove** the list; replace with "45 to review → Reconcile" filtered to rule findings.

### OF4 — Release "Fix in" vs ordinary navigation
- Every checklist row has a page-level "Fix in" (Proof / Reconcile / Dataset / Known gaps / Release) that lands at the
  top of the page; "Limitations with no mitigation" says "Fix in: Release" while on Release.
- Evidence: `release-full.png` FIX IN column; catalog O4, stories 006, 039, 075.
- Verdict: **Differentiate**: each Fix in opens the filtered target (e.g. Golden test → Proof `#gold`, Needs review →
  `#reconcile?state=bad`). Remove self-links.

### OF5 — Accept vs Explain
- Same server effect (state explained, word "Unverified"); both require a reason; only the badge differs.
- Evidence: catalog O6, story 019 (write action, not exercised here).
- Verdict: **Merge** into one action with a reason type, or state on the button what differs.

Pass (no change): O7 (Explore "Measure" naming) is moved to Hierarchy & IA HI3.

---

## Hierarchy & IA

### HI1 — "Rules" page leads with agents
- The nav item **Rules** opens a page whose first section is "Agents · 5" (Reader, AI spend reader, Notes reader,
  Projects reader, Mapper: charter, score, runs, prompt history); the rules table and "To review · 45" come after five
  long agent cards.
- Evidence: `rules.png` (title "Rules", subtitle "Agents · 5", first card "Reader"); Docs → How it works maps the
  "Read" step (agents) to page "Rules" (`docs.png`).
- Fix: rename the page to match its first job ("Agents and rules"), or split: **Agents** (Read step) and **Rules**
  (Check step). One concept, one name.

### HI2 — Category mapping has four names
- UI group: "Category mapping" (Proof column, trail section, Reconcile group). Rules To-review rows and Release
  "Proposed" detail: "asset types", "asset-type mapping". Trail card status: "To confirm"; Reconcile row: "Proposed".
  Docs name an **Edit** action the UI calls **Choose another**.
- Evidence: `proof.png` column "CATEGORY MAPPING"; `rules-full.png` "Reconcile, asset types: Approve, Edit or Reject";
  `release-full.png` "no asset-type mapping without a person's confirmed_by"; `trail-MSFT-full.png` "To confirm";
  `reconcile-full.png` "Proposed"; catalog story 068.
- Fix: one noun ("category mapping"), one state word ("Proposed"), one action set (Approve / Reject / Choose another)
  everywhere, including generated detail strings.

### HI3 — Same filter, different words across pages
- Layer: filters say "Chip design / Hyperscaler / Miner to HPC"; Dataset rows print `layer` = `chip_seller`.
- Measure: Explore has "All measures" (list), "every measure" (taxonomy measure) and Grid Kind "Every measure" — three
  controls, one word.
- Claims status: Holds / Not built / Out of date (Known gaps) vs proven / stub / stale (Release, Docs) — see DI3.
- Evidence: `data-full.png` (row `… xbrl chip_seller yes`), `explore.png` (both "All measures" and "every measure" in
  the control bar), `gaps.png`, `release-full.png`; catalog O7, story 046.
- Fix: show the display label in Dataset (keep the code in the API/CSV); rename the Explore controls "List", "Measure",
  "Kind".

### HI4 — The landing page carries four jobs
- `#proof` stacks: stage table, Verification source, Failure types (two charts + two tables, 72 types), Releases (with
  the only packet Download), Regression test, Hand check (the only grading surface). Hand check, the one place a person
  acts on Proof, is last.
- Evidence: `proof.png` (first screen = stage table + Verification source), `proof-full.png` (Hand check at the bottom);
  catalog stories 001, 008; Known broken flows "Fix in: Proof lands at the top of the page".
- Fix: Proof = stage table + "6 to review" + Hand check progress; move Failure types to Rules (it is a per-check
  breakdown), Releases + Download to Release, and give Hand check its own anchor (`#gold`) reachable from the header
  "Hand check: 119 of 120".

### HI5 — Packet download is on Proof, packet contents are on Release
- Release shows "Packet v1.9.0" (files, rows, bytes) with no download; Proof → Releases has "Download" per signed version.
- Evidence: `release-full.png` (Packet card, no link), `proof-full.png` Releases table (Download column); catalog I10,
  story 043.
- Fix: Releases table and downloads live on Release; Proof links "Last release v1.8.0" there (the trail already shows
  "Last release v1.8.0").

### HI6 — Two primary-looking links on the trail header
- "6 to review" (orange), "Reconcile", "Dataset" sit together at top right, with "Review in Reconcile →" directly
  below in the Before release card.
- Evidence: `trail-MSFT.png`.
- Fix: covered by DP4 — one link, the count itself.

### HI7 — Docs and Known gaps split one topic
- Nav has **Known gaps** (live claims + open issues) and **Docs → Known limitations** (`#docs/claims`, a snapshot with
  other counts). Docs also lists nine pages in the nav dropdown (How it works, Operating guide, Glossary, Map, States,
  Rules and checks, Evaluation, Known limitations, Handoff).
- Evidence: nav links captured in `docs/ux-flow/tmp/texts.json` (`_nav`), `gaps.png`, `docs-claims.png`.
- Fix: drop Known limitations from Docs (link to Known gaps). Map vs How it works overlap not checked in this pass.

---

Not checked here (needs data or a write): P7 To confirm rows, DP5 encode panel, DI8 saved-decision display, OF5
Accept vs Explain. Each is backed by catalog stories only.
