# UX paths: operator-onboarding

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

---

## STORY-801: First five minutes on the flow diagram

**Type**: short
**Topic**: operator-onboarding
**Persona**: Dana, a data engineer handed the repo and the local app URL on her first morning; has never seen the product.
**Goal**: Get the one-picture model of the pipeline and jump to the page that owns the step she cares about (who reads the filings).
**Preconditions**: Local app running on http://localhost:3610; Dana lands on the default route (`#proof`).
**Ideal path**: 3 (Docs tab → read the diagram → click "Read") — the diagram is the first thing on the first Docs page, and each box is a link.
**Alternate paths**: Type `#docs/overview` directly; the nav "Rules" tab goes to the same place as the "Read" box; HANDOFF's "five-minute tour" (Docs → Handoff) lists the same steps as CLI commands; raw text at `/docs/OVERVIEW.md` (no diagram, the mermaid shows as source).
### Steps
1. Sees the Proof board with six companies all reading "<n> to review" and thinks "too much, where is the manual?" → clicks **Docs** in the navbar → URL `#docs`; no slug, so the page falls back to the first sidebar entry, "How it works" (highlighted, `aria-current="page"`).
2. Reads the flowchart drawn as six boxes in a row: Filings (EDGAR, XBRL) → Read (headless agents) → Check (citations, rules, keys) → Review (open items only) → Release (signed packet) → Database (Postgres, read API) → notices the boxes have no button styling and hovers to discover they are links.
3. Clicks **Read** → navigates to `#rules`; the navbar highlights Rules and the page opens on `Agents · 5`.
### Variations
- Clicks **Review** instead → `#reconcile`; **Release** → `#release`; **Database** → `#data` (Dataset tab highlighted).
- Reads the table under the diagram (Step · What happens · Page · Package) and clicks its "Rules" link in the Page column: same destination as the box (two links to one route on one screen).
- At phone width (≤700px) the diagram is drawn vertically (boxes stacked); the navbar itself scrolls sideways (finding F-DS1 on Known gaps).
### Edge Cases
- **Filings** and **Check** both go to `#proof`: Dana clicks Check expecting a list of checks and lands on the same Proof board as Filings. The checks she wanted are on Rules or Docs → Rules and checks. Redundant destination, mismatched expectation.
- The Package column links (`../ledger/ingest/`) open GitHub in a new tab (`REPO_URL`), not the local checkout; offline, they fail.
- The diagram only renders a strictly linear flowchart; if someone adds a branch to OVERVIEW.md's mermaid block, the page silently shows it as a code block instead.

---

## STORY-802: Reading the Handoff page start to finish and following its links

**Type**: long
**Topic**: operator-onboarding
**Persona**: Dana again, day one afternoon, blocking out two hours to "take the system over" as HANDOFF tells her to.
**Goal**: Read the handoff, understand setup, the objects, and the house rules, opening each referenced doc once, and come out knowing what to run first.
**Preconditions**: On `#docs/overview`. Has a fresh clone but has not run `uv sync`.
**Ideal path**: 6 (Handoff → Map → Operating guide → Glossary → Rules and checks → back to Handoff for setup) — the docs a takeover needs are all in one sidebar; the rest is reading.
**Alternate paths**: The overview's "Where to go next" list links every one of these pages; HANDOFF's first line links Map, Overview and Operations; each page is also at `/docs/<NAME>.md` as plain text; `docs/HANDOFF.md` in the clone itself.
### Steps
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
### Variations
- Reads HANDOFF via its Source footer link `docs/HANDOFF.md` → `/docs/HANDOFF.md` raw text/plain in the same tab; no sidebar, no back link other than the browser's Back.
- Starts from How it works → "Where to go next" → "Taking the system over: Handoff" instead of the sidebar.
### Edge Cases
- Doc label drift: OPERATIONS and HANDOFF both name an **Edit** mapping action and an "asset types" group; the UI has **Choose another** / **Map** and "Category mapping". A new operator following the docs literally cannot find the button.
- HANDOFF "100 companies" vs scope line "6 companies" with no explanation on the page itself (the Glossary's "Proven set" term explains `config.PROVEN` vs `config.SCOPE`, two clicks away).
- Docs referenced but not served (README.md) render as GitHub links; `/docs/README.md` returns 404 JSON `{"error": "not found"}` if typed.
- Every route change scrolls to the top (`window.scrollTo(0, 0)`), so Back from Map loses her place in a 239-line Handoff.

---

## STORY-803: Looking up an unknown word from a Rules card

**Type**: short
**Topic**: operator-onboarding
**Persona**: Priya, a finance analyst joining as second reviewer; comfortable with 10-Ks, not with the app's vocabulary.
**Goal**: Find out what "Corroborated" and "Matches SEC XBRL" mean after seeing them on the Reader agent's score.
**Preconditions**: On `#rules`, Reader card visible.
**Ideal path**: 2 (Docs → Glossary) — a single glossary page written from the same state code the cards use.
**Alternate paths**: Docs → States (`#docs/states`, STATES.md, 598 lines, M1 section); Docs → Rules and checks → "Answer keys, strongest first"; the Proof trail's legend shows the colour words without definitions; hover tooltips exist only for some state words elsewhere (e.g. Reconcile decision buttons).
### Steps
1. Reads Reader's Score datagrid: "Outputs · Statement figures — Checked 80 · Explained 1 · Open 0 · Blocked 0 (of 81)", "SEC XBRL match — Matches SEC XBRL 80 of 81 · 98.8% (95% CI 93.3–99.8%)" → wonders whether "Checked" includes Corroborated. No link from the card.
2. Clicks **Docs** → lands on How it works (not the glossary; the bare `#docs` route always opens the first page) → clicks **Glossary** in the sidebar.
3. Finds "Corroborated" in "State words" (machine row) and "Checked" in Terms: "Agrees with an independent check: an answer key, a verified quote, a located table, or a confirmed mapping." → satisfied.
### Variations
- Looks up "Twin" (the Score uses "SEC XBRL" in the label, the Glossary's term is "Twin") → finds it under Terms; the word "twin" never appears on the Rules card itself.
### Edge Cases
- Hovering the "Score" heading shows a long `title` tooltip (sc.note) explaining how outputs are counted; nothing signals the tooltip exists.
- Same definitions live on three surfaces (Glossary, States, Rules and checks), plus STATES.md's machine prose; only the Glossary is generated from code, the others can drift.

---

## STORY-804: Auditing one agent before trusting it (charter, score, runs, history)

**Type**: medium
**Topic**: operator-onboarding
**Persona**: Marcus, ML engineer taking over the agents; has to decide whether the AI spend reader's v4 prompt is safe to keep.
**Goal**: Understand what the AI spend reader owns, how it is scored, what each company run cost, and how its prompt evolved.
**Preconditions**: On `#rules`. Signer irrelevant (no write controls).
**Ideal path**: 5 (Rules → AI spend reader card → Full charter → read Score → read Prompt and model history) — all on one card.
**Alternate paths**: Docs → Evaluation (`#docs/evals`, "Scores per agent", "Planted errors", "Cost"); Docs → Handoff "The objects" table points to `agents/charters/`, `agents/prompts/`; the raw `/api/agents` JSON; `agents/charters/ai_reader.md` in the clone; Proof's Failure types card mentions checks but not agents.
### Steps
1. Scrolls past the Reader card to **AI spend reader** → header: job "Reads the MD&A passages of each 10-K that mention AI next to capital or operating spending…", right side "Model claude-opus-5-5", "Prompt aispend@v4".
2. Reads the Charter column: first paragraph only ("The reader of what a company says about AI's part of its spe…") → clicks **Full charter** → headings Owns, Never touches, … expand inline as small paragraphs.
3. Reads Score: "Outputs · AI disclosures — Checked 188 · Explained 39 · Open 0 · Blocked 0 (of 227)", "SEC XBRL match — No SEC XBRL counterpart", "Planted errors — Not measured" → thinks "not measured why?". The page gives no reason.
4. Reads **Runs per company**: rows MSFT, GOOGL, AMZN, NVDA, APLD, AMD with Documents, Calls, Input tokens, Output tokens, Time (s), Attempts, Failed (all 0); footer "All 6 · 186 · 186 · 1,069,738 · 163,566 · 1,584 · 162 · 0".
5. Hesitates: Attempts (162) is lower than Calls (186) in the footer; nothing explains the difference.
6. Reads **Prompt and model history** (When · By · Change): 29 Oct "aispend@v1: first prompt", "aispend@v2 saved, not in use: a sentence with no year gives fiscal_year null…", "switched to aispend@v2", same for v3, 30 Oct "switched to aispend@v4"; note at right "Versions: v1, v2, v3, v4".
7. Notices v4 has a "switched to" line but no "saved, not in use" line with its reason → decides to read `agents/prompts/` in the clone.
8. Opens **Docs → Evaluation** to learn what "Planted errors" means → reads "Planted errors" and "Scores per agent".
### Variations
- Same audit on **Reader**: Planted errors reads "Caught 1,712 of 1,837 · Missed 1 · No effect 124 · Without the SEC XBRL check: caught 1,705, missed 8"; then expands **Planted errors by kind** (Kind · Planted · Caught · SEC XBRL only · Missed · No effect · Caught without SEC XBRL · Missed without SEC XBRL), sees "omission" with 116 No effect.
- **Notes reader**: "Matches SEC XBRL 204 of 209 · 97.6% (95% CI 94.5–99.0%)", Open 16.
- **Mapper**: Runs per company all zeros, no Score block at all (score null), history one line "mapper@v1" → Marcus wonders whether the mapper ever ran; HANDOFF says mapper runs via `ledger mapper <TICKER>` and its 47 proposals were one batch.
### Edge Cases
- The API carries `faults_note` ("not measured: `ledger faults` corrupts `extractions` only…") but `scoreBlock` never renders it; "Not measured" has no explanation on the page.
- The Score h3's tooltip is the only place the counting rule lives.
- No write UI: the server has `/api/agents/<id>/prompt|use|model` POST routes, but Rules offers no button; an operator who wants to switch a prompt must use the CLI or edit `agents/agents.json`, which OPERATIONS rule 3 describes as a two-step version switch.
- A retired agent is filtered out of `Agents · <n>`; there is no way on the page to see retired agents' history.

---

## STORY-805: Is this rule doing anything? (Rules table vs Docs → Rules and checks)

**Type**: medium
**Topic**: operator-onboarding
**Persona**: Priya, second week, seeing "Large year-over-year change" on Reconcile and wanting to know what rule produced it and how often it fires.
**Goal**: Find the rule behind a Reconcile check, its severity, how many times it hit, and its rationale.
**Preconditions**: On `#reconcile`, Check filter shows "Large year-over-year change".
**Ideal path**: 3 (Rules → find `jump` row → read Description/Severity/Hits) — one table, but the rationale needs a 4th step to the yaml.
**Alternate paths**: Docs → Rules and checks (`#docs/rules`): same rules split by block/warn/info with the `check` name and a File link to `rules/<id>.yaml` on GitHub; Release checklist "Fix in → Rules"; `rules/jump.yaml` in the clone.
### Steps
1. Clicks **Rules** in the navbar → scrolls past five agent cards (several screens) to the "Rules" table.
2. Scans Kind · Rule · Description · Severity · Hits · Failure type → 74 rows, no search box, column headers are not sortable (dtable).
3. Finds "jump" (Rule, "A field does not move more than 3× from one fiscal year to the next.", warn, Hits 5) → hovers the Rule cell; the title shows the raw id `jump`.
4. Wants the rationale → nothing on the Rules page shows it → opens **Docs → Rules and checks** → rules table row `jump` | warn | `check` | description | File link.
5. Clicks the File link → GitHub `rules/jump.yaml` in a new tab → reads rationale and owner.
6. Returns to Rules and looks at Guards: "part_year" Hits 40, Failure type "#68" → "#68" is plain text, not a link; she has no idea where failure type 68 is listed.
### Variations
- Wants only block-severity rules: Docs → Rules and checks groups them (block first); the Rules page does not.
- Looks for "Restated" (from the Reconcile Check filter): Rules row "restated" info Hits 10 and Guard "restated_between_filings" Hits 5 — two rows with similar names.
### Edge Cases
- 47 of the 74 Rules-table rows are Kind "Mapping" (each PP&E category of the proven six); real rules are buried among them. Known gaps finding F-RC5 (low) says exactly this: unconfirmed mappings listed under Rules.
- Redundancy: the Rules table (`/api/v1/rules`, with Hits and Guards/Definitions/Mappings) and Docs → Rules and checks (`rules/*.yaml` only, with check names, files and gates) describe the same 21 rules with different columns; neither links to the other.
- "Failure type" numbers correspond to `taxonomy/failures.yaml` / docs/INGESTION.md, neither surfaced in the app.
- If `rules/*.yaml` fails to load the API returns `rules_error`, which `rulesPage` never renders: the table would just be shorter.

---

## STORY-806: What's open on the proven set, from Rules "To review"

**Type**: short
**Topic**: operator-onboarding
**Persona**: Dana, wanting a one-screen answer to "what is blocking us" without learning Reconcile's filters yet.
**Goal**: See what needs a person, grouped by need.
**Preconditions**: On `#rules`.
**Ideal path**: 2 (Rules → scroll to "To review · 45").
**Alternate paths**: Reconcile header counts and cause cards (live 69 rows, includes items not in this list); Proof board per-company "<n> to review"; company trail summary "<n> to review"; Release checklist lines Needs review / Proposed / Blocks release.
### Steps
1. Clicks **Rules** → scrolls to the bottom → "To review · 45".
2. Reads three cards: "Proposed category" (29 rows: MSFT mapping "Buildings and improvements: BuildingAndB…, to confirm", …), "Does not tie to total" (14: GOOGL facts "segment_revenue_tie: segment_revenue FY2…"), "Readings differ" (2: APLD "ppe_category Other equipment and fixture…").
3. Wants to act on the GOOGL tie → rows are not clickable; no link to the trail or Reconcile → goes to the navbar **Reconcile** and filters Scope GOOGL by hand.
### Variations
- With nothing open the section reads "No items to review" in a card.
### Edge Cases
- Count disagreement across surfaces: Rules says 45, Reconcile shows 69 rows; a new operator cannot tell which is "the" number (Rules' list covers rule findings and mappings on the proven set; Reconcile includes new filings, unconfirmed findings and other causes).
- Same information on four+ surfaces (Rules To review, Reconcile, Proof board, trail, Release) with no cross-links from this one: a dead end.

---

## STORY-807: Reading the claims register to decide what not to promise

**Type**: medium
**Topic**: operator-onboarding
**Persona**: Leah, the new owner's PM, preparing a call with Arctal and wanting to know which product claims actually hold today.
**Goal**: List the claims that hold, those that are partial, and why the stale ones are stale.
**Preconditions**: On any page; local copy.
**Ideal path**: 4 (Known gaps → sort Status → expand a stale claim → read Gaps column).
**Alternate paths**: Docs → Known limitations (`#docs/claims`, the generated CLAIMS.md: same register as a static table with Declared, Computed, Why, Gaps, Ticket); `/api/v1/claims`; Release page lines that link "Fix in → Known gaps".
### Steps
1. Clicks **Known gaps** → header "6 Holds · 38 Partial · 0 Not built · 3 Out of date · 3 Planned · 37 open issues", right side "Updated <time>".
2. Sees no "Unregistered claims" alert and no append-only warning → reads that as healthy.
3. Reads "Claims · 50" table (Claim · Where · Status · Gaps): first rows are Out of date (orange): "SEC checked · Next 10-K expected" (Where: Company trail), "Coverage", "Hosted copy".
4. Clicks the **Status** header to sort → Not built → Out of date → Partial → Planned → Holds order (CLAIM_ORDER); clicks again to reverse and see the 6 Holds first: "Calculated: the formula and the arithmetic…", "Verification tile counts", "Answer-key values missing from the dataset = 0", "LIMITATIONS.md in every packet", …
5. Clicks the "Hosted copy" row → a detail row expands with the non-proven reasons as a list (claimWhy) → reads "open findings" / "hosted code checked live only" style phrases.
6. Hovers the "Coverage" status ("Out of date") → tooltip "Declared Partial": the computed status is worse than declared.
7. Reads its Gaps cell: "New filings not yet read are as fresh as the last EDGAR check." → writes "don't promise freshness" in her notes.
8. Opens **Docs → Known limitations** to copy a cleaner table for the call → sees "proven 0 · partial 41 · stale 4 · stub 2 · planned 3 · open findings 37" — different counts from the page she just read.
### Variations
- Sorts by **Gaps** (count of gaps + facts) to find the claims with the most caveats.
- Filters by Where mentally: "Agent scores with Wilson intervals · planted-error catch rate" → Where "Rules, Proof", Partial, Gaps "Planted faults are nine made-up kinds of error, not the real mix…".
### Edge Cases
- Redundancy with drift: Known gaps (live, computed per request) and Docs → Known limitations (CLAIMS.md, written by `ledger claims`, excludes clock/commit-dependent checks: "checked live only") show the same 50 claims with different status counts (live 6 Holds vs doc 0 proven, 2 stub vs 0 Not built). CLAIMS.md also calls the page "the Gaps page" while the navbar says "Known gaps". Status words differ too: doc "proven/stub/stale", page "Holds/Not built/Out of date".
- The Where column only names pages (`ledger/web/pages/*.js`); claims backed only by server code ("Late writers never overwrite", "Decisions record person or run", "Point-in-time as_of") show "—".
- Clicking the Claim text expands the row, it is not a link to the page the claim is made on.

---

## STORY-808: Triage the high-severity open issues before taking ownership

**Type**: long
**Topic**: operator-onboarding
**Persona**: Dana, end of week one, about to tell Kenny she accepts the handoff; wants every high-severity issue understood and mapped to where it shows up in the app.
**Goal**: Read every High open issue, see which claim it caps, and verify two of them in the app itself.
**Preconditions**: On `#gaps`. Has read Handoff and Operating guide (STORY-802).
**Ideal path**: 8 (Known gaps → Open issues → expand each High (≈5 shown) → follow one to Proof, one to Release) — the list has no links, so verification costs extra navigation.
**Alternate paths**: Docs → Known limitations "Open findings" section (same 37, static); `claims/findings.jsonl` in the clone; STATES.md M10 describes the finding lifecycle; Release checklist rows for the same problems.
### Steps
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
### Variations
- Reads the same findings in **Docs → Known limitations**, where each claim row also lists a Ticket column (T82, T53…) that Known gaps does not show.
- Sorts by Issue text alphabetically to find duplicates (F15 and F8 both under "Late writers never overwrite").
### Edge Cases
- Issue text is truncated nowhere, but long sentences wrap into a very tall table; there is no filter by severity or claim.
- The finding's claim is shown by its human text; if a finding names a claim id not in the register, the raw id is shown.
- If the issue log was edited (not append-only), the header shows red "Issue log edited"; if the check could not run, orange "Issue log append-only: not enforced here". Neither links to what was edited.
- Jump box routes to Dataset, not the trail: one extra hop for every "go check company X" step in this topic.

---

## STORY-809: Following Release's "Fix in → Known gaps" and "Fix in → Rules"

**Type**: short
**Topic**: operator-onboarding
**Persona**: Dana, looking at why v1.9.0 is not signable.
**Goal**: Understand a red Release line that points to Known gaps or Rules.
**Preconditions**: On `#release`; some checklist lines Fail.
**Ideal path**: 3 (Release → expand line → Fix in link).
**Alternate paths**: Known gaps / Rules navbar tabs directly; Docs → Operating guide → "When a Release line is red".
### Steps
1. On Release, finds a failing line whose "Fix in" says **Known gaps** → clicks it → `#gaps`, top of the page.
2. Has to find the relevant claim herself: the link carries no anchor or filter → scans 50 claims.
3. Back → Release; a line with "Fix in" **Rules** → `#rules` → lands on the agent cards, the relevant rule table is several screens down.
### Variations
- Reads the line's expanded detail table first ("No items" when empty) to know what to look for.
### Edge Cases
- "Fix in" targets are page-level only; neither Rules nor Known gaps accept a query string or anchor (`#agent-<id>` ids exist on agent cards but nothing links to them).

---

## STORY-810: Reading docs from the hosted read-only copy and via raw links

**Type**: medium
**Topic**: operator-onboarding
**Persona**: Arctal's analyst evaluating the takeover, on the hosted copy (`LEDGER_READONLY=1`), no clone.
**Goal**: Read setup and limitations, and download one doc as text to paste into an internal memo.
**Preconditions**: Hosted copy; header shows "Read-only" instead of the Signer box; scope line ends "· Read-only".
**Ideal path**: 4 (Docs → Handoff → Source link → copy text).
**Alternate paths**: `/docs/<NAME>.md` typed directly for any served file (API, BUILD, COMPANIES, DATA_DICTIONARY, FIELDS, INGESTION, PROOF, TAXONOMY plus sidebar files); GitHub links from docs; Known gaps for live limitations.
### Steps
1. Clicks **Docs** → How it works → diagram works the same (links are in-app routes, all GETs).
2. Clicks **Known limitations** → the CLAIMS.md register; reads "Hosted copy" stale.
3. Clicks **Handoff** → reads "The hosted copy" section.
4. Scrolls to the footer "Source: docs/HANDOFF.md" → clicks → `/docs/HANDOFF.md` served as text/plain in the same tab.
5. Selects all and copies → presses Back to return to the app at `#docs/handoff`.
6. Clicks a link to `docs/BUILD.md` inside a doc → raw text (served, not on the sidebar).
7. Clicks a code link `../ledger/web/app.py` → GitHub in a new tab (works without a clone).
### Variations
- On the local copy the same flow is identical; Docs, Rules and Known gaps have no write controls, so read-only mode changes nothing on these three pages.
### Edge Cases
- `#docs/nonexistent` silently shows How it works (no "not found" message); `/api/v1/docs/nonexistent` returns 404 `{"error": "no such doc"}`.
- Raw docs open in the same tab with no app chrome; a reader who lands there from a shared link has no navigation into the app.
- Docs in `docs/archive/` are never served; links to them go to GitHub.
- Known gaps finding F-EV3 notes the hosted copy has no `data/raw`, so links from docs into Open-in-filing paths will 410 there; Docs pages themselves are unaffected.

---

## Redundancy and broken-flow notes (for ux-flow)

- **Same information, several surfaces**: claims register (Known gaps live vs Docs → Known limitations static, different counts and status words); rules (Rules table vs Docs → Rules and checks, different columns, no cross-links); state words (Glossary generated, States doc hand-written, Proof/trail legends); open items (Rules "To review · 45", Reconcile 69 rows, Proof board, trail, Release); setup/tour (Handoff, Operating guide, Overview "Where to go next").
- **Doc ↔ UI label drift**: OPERATIONS/HANDOFF "Approve, Edit or Reject" and "asset types" group vs UI **Approve / Reject / Choose another / Map** and "Category mapping"; CLAIMS.md "the Gaps page" vs nav "Known gaps".
- **Dead ends**: Rules "To review" rows, Known gaps claims and issues, and Release "Fix in" links carry no deep link to the item; failure type "#NN" is plain text.
- **Hidden reasons**: `faults_note` (why Planted errors is "Not measured") and `rules_error` are in the API but not rendered; the Score counting rule lives only in a heading tooltip.
- **Flow diagram**: Filings and Check boxes both go to `#proof`.
