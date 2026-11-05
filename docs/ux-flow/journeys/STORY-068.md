# STORY-068: Reading the Handoff page start to finish and following its links

Verdict: **convoluted**. Steps: 18 actual / 6 ideal.

Evidence: screenshots in `STORY-068-screens/` (01 overview, 02–06 handoff/map/operations/glossary/rules, `-full` variants, 08 handoff after Back, 09–10 reconcile, 11 handoff "How to do the common things"), plus `STORY-068-screens/info.json` (links, headings, scroll position). Captured read-only against http://localhost:3610 on 2026-11-04; all non-GET requests blocked by the capture script.

## Friction Scorecard

| Measure | Result | Evidence |
|---|---|---|
| Steps actual vs ideal | 18 vs 6 (measured: catalog step list, routes confirmed live) | catalog steps 1–18; sidebar order in info.json |
| Extra steps | 12: hover-check of links (2), dead `docs/COMPANIES.md` reference (4), Back round-trip (9), second Handoff visit (17), Reconcile detour to verify a docs claim (18), browser find in Glossary (14), GitHub detour for rule rationale (16) | steps 2, 4, 9, 14, 16, 17, 18 |
| Decisions a default could carry | Where to start. Sidebar lists Handoff last of 9 although its heading is "Start here"; default route `#docs/overview` opens "How it works" | 01-overview.png, 02-handoff.png (heading "Start here") |
| Re-entry | Back from Map returns to Handoff at scrollY 0 (measured: `scroll_after_back: 0` after scrolling to 3000). Handoff full page is 5984 px tall | 08-handoff-after-back.png, info.json |
| Dead ends | `docs/COMPANIES.md`, `docs/PROOF.md`, `docs/TICKETS.md`, `docs/BUILD.md`, `docs/CLAIMS.md`, `docs/TAXONOMY.md` render as code text, not links; COMPANIES.md is served at `/docs/COMPANIES.md` (200) but no sidebar entry; `/docs/README.md` returns 404 JSON (measured) | 02-handoff.png, 11-handoff-common-things.png, info.json |
| Dead end (behavioral) | Docs promise an **Edit** button and an "asset types" group; Reconcile has **Approve** / **Choose another** / **Reject** and a group titled "Category mapping" (measured: button labels on #reconcile) | 11-handoff-common-things.png vs 09/10-reconcile |
| Confirmations guarding nothing | None on this journey (read-only) | — |
| Hesitations | Step 1 (Handoff last), step 3 ("100 companies" vs header "6 companies"), step 4 (code text that looks like a link), step 18 (button not found) | 02-handoff.png header line "6 companies · Data as of Nov 1, 2026" |

## Take-away Pass

**Docs sidebar (all doc pages)**
- 9 entries, flat, no order of reading. Handoff (the entry point) is last. Measured order: How it works, Operating guide, Glossary, Map, States, Rules and checks, Evaluation, Known limitations, Handoff.
- One primary action: none. The likely next step ("Start here") has no weight.

**Handoff (`#docs/handoff`, 02, 11)**
- Sidebar label "Handoff", page heading "Start here", breadcrumb title "Kenny's Data Emporium, Docs": three names for one page.
- First line repeats links that already sit in the sidebar (MAP, OVERVIEW, OPERATIONS). Removable; the sidebar carries them.
- "The hosted copy" (11): one paragraph with ~15 inline code spans covering redeploy, Dockerfile, ignore files and the XBRL restatement guard. Deploy-time detail, deferrable to Operating guide or a "Deploy" section. Wall of text by the app's own rule.
- "How to do the common things" → "Map a reported asset type" (11): one bullet of ~12 lines mixing CLI, file paths, API endpoint, ticket numbers (T33, T63, T100) and UI steps. Collapsible into a short numbered procedure with the reference detail moved to TAXONOMY.
- Ticket numbers (T62, T63, T100, T36) appear inline throughout; a takeover reader has no ticket context. Removable from prose, keep in commit history.
- Setup block is the one actionable section; it sits fourth, below "What a clone contains". Suspected better order: Setup first, inventory later.

**Map (`#docs/map`, 03)**
- Module links open GitHub in a new tab (measured `_blank`); fine. Footer Source link duplicates sidebar. No simplification found beyond scroll restore.

**Operating guide (`#docs/operations`, 04)**
- "Never" list of 8 is the house rules; Handoff also has "The rules of the house". Same concept on two pages (suspected overlap; content not diffed line by line). Pick one canonical home and link from the other.
- Links Handoff and Glossary inline as well as in sidebar (measured: links list). Low cost; keep.

**Glossary (`#docs/glossary`, 05)**
- State words table repeats words with different meanings: "Unverified" for `info` and for group `explained`; "Blocks release" for `blocked` and group `blocked`; "Done" and "Located/Done". Collapse group rows into a column on the state rows.
- Machine and State columns (`row (M1)`, `ok`, `wait`) are code identifiers; useful to engineers, noise to an operator. Deferrable behind States.
- No in-page jump/search; reader used browser find (step 14).

**Rules and checks (`#docs/rules`, 06)**
- Rule rationale and owner live only on GitHub (21 `_blank` file links, measured). Showing one-line rationale inline would remove the step-16 detour.

**Reconcile (09, 10)**
- Not a docs screen; reached only to check a docs claim. The detour exists only because the docs drifted.

## The Simpler Version

Target: 5 steps.

1. Land on `#docs/handoff` (rename "Start here", first in sidebar, default `#docs` route).
2. Run Setup (first section, copy button on the block).
3. Open Map from the sidebar; Back returns to the same Handoff position.
4. Open Operating guide (one canonical "Never" list; Handoff links to it instead of restating).
5. Open Glossary / Rules and checks as reference when a word or rule appears; done.

Concrete changes:
- Reorder sidebar to reading order: Start here, How it works, Operating guide, Map, Glossary, Rules and checks, States, Evaluation, Known limitations. One label per page: sidebar = heading.
- Make `#docs` default to Start here, not How it works.
- Restore scroll position on Back for `#docs/*` routes (replace unconditional `window.scrollTo(0, 0)` with per-hash saved position).
- Turn every `docs/<NAME>.md` reference into a link: served pages to `#docs/<name>`, unserved ones (COMPANIES, PROOF, TICKETS, BUILD, TAXONOMY) to `/docs/<NAME>.md` or GitHub; add COMPANIES to the sidebar or drop the reference.
- Fix doc drift: HANDOFF lines 126–135 and OPERATIONS lines 27 and 67 say "asset types" group and **Edit**; UI says "Category mapping" and **Choose another**. Update the docs to the UI labels (or rename the UI), and add the check to "Keeping the docs true".
- Scope line: next to "6 companies" show "6 proven of 100", or add one line under "What this is" naming the proven set.
- Move "The hosted copy" and ticket numbers out of Handoff into Operating guide / commit history; turn "Map a reported asset type" into ≤5 numbered steps.
- Glossary: one row per state word, groups as a column; add anchors per term.

## Clarity Issues

| Issue | Where | Fix |
|---|---|---|
| One page, three names: "Handoff" / "Start here" / file HANDOFF.md | sidebar vs heading (02) | Use "Start here" everywhere in the UI |
| Same group, three names: "asset types" (HANDOFF, OPERATIONS), "Mapping" (HANDOFF on Proof), "Category mapping" (Reconcile) | 11, 10 | One name: "Category mapping" |
| Action named **Edit** in docs; UI button is **Choose another** | OPERATIONS L27, HANDOFF L127/135 vs 10 | Match UI label |
| "100 companies" vs header "6 companies" with no bridge on the page | 02 | "6 proven of 100" in scope line |
| "47 an agent proposed" in Handoff vs Reconcile "Proposed 29" (suspected: historical count presented as current) | 11 vs 09 | Drop the number or mark it dated |
| Ticket IDs (T33, T36, T62, T63, T100) and gate IDs (G1–G6) used without definition | 11, 06 | Remove from prose or link to definitions |
| "Unverified" means two things; "Blocks release" listed twice | 05 | One meaning per word |
| Engineering identifiers (`row (M1)`, `wait`, `bad`) beside operator words | 05 | Move to States page |
| "How it works" page vs file OVERVIEW.md; "Known limitations" vs `#docs/claims`; "Evaluation" vs `evals` | sidebar hrefs (info.json) | Align route slugs with labels |
| Wall of text: "The hosted copy" paragraph, "Map a reported asset type" bullet | 11 | Numbered steps, detail deferred |
