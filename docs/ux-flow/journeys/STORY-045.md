# STORY-045: Full pre-release pass from Proof to published

Critique of the release-day journey: three failing required checks to a signed v1.9.0 and a downloaded packet.
Evidence: live app at http://localhost:3610, captured 2026-11-04 (read-only, GET only; no write controls clicked).
Screens: `STORY-045-screens/` (`.png` plus `.txt` page text for each).

| Screen | File |
|---|---|
| Proof | `01-proof.png` |
| Release | `02-release.png`, controls and hrefs in `02-release-controls.txt` |
| Reconcile | `04-reconcile.png` |
| Proof, Hand check section | `05-proof-handcheck.png`, `05b-proof-handcheck-apld.png` (APLD picker) |
| APLD trail | `06-proof-apld.png` |
| Known gaps | `07-gaps.png` |
| Dataset, rows without a value | `08-data-novalue.png` |

Live state differs from the catalog: Release reads "10 of 13 required checks pass", not "12 of 15" (`02-release.png`
header). The three failing checks are the same: Proposed 29, Needs review 16, Golden test 1.

Verdict: **convoluted**. Steps: about 55 actual against about 45 ideal (counted, not timed).

## Friction Scorecard

| Measure | Finding | Evidence | Status |
|---|---|---|---|
| Steps, actual vs ideal | About 55 against the Ideal path's 45. The extra steps are 3 round trips back to Release, the scroll down to the Hand check section, the commit and test rerun in the terminal, and the trip to Proof → Releases after signing to download. | Story steps 1–13; `02-release-controls.txt`; `release.js:44` `go('proof')` after publish | Counted |
| Entry detour | Step 1 goes Proof → "Next release". The navbar "Release" link reaches the same page in one click. | `01-proof.png` Releases card; navbar | Measured |
| Decisions a default could carry | 18 of the 29 Proposed mappings read "Matches company's own tag · Same as proposed". Each still needs its own Approve click. The Category mapping list has no "Select all"; the only one on the page is "Select all 16" on Rule findings. | `04-reconcile.png` lower half; `04-reconcile.txt` line 41 | Measured |
| Fix-in targeting | Proposed links to `#reconcile?cause=asset_types` (scoped). Needs review links to bare `#reconcile` (not scoped). Golden test links to `#proof` top, while the unchecked item sits in the Hand check section at the bottom of Proof, below Verification source, Failure types and Releases. | `02-release-controls.txt`; `01-proof.png`; `proof.js:65` | Measured |
| Finding the one unchecked item | Proof → header "Hand check: 119 of 120 checked" (scrolls to `#gold`) → APLD picker (19/20) → item 8 of 20, under "Definition differs". The list does not put the unchecked item first. | `05-proof-handcheck.png`, `05b-proof-handcheck-apld.png` | Measured |
| Re-entry | Release is reopened after each fix (story steps 5, 7, 9) because the fix pages do not show which release checks are still failing. Reconcile's header ("Needs review 16 · Proposed 29 · Unverified 6") is close but adds "Unverified 6", which no release check counts. | `04-reconcile.txt` header; `02-release.png` | Measured |
| Ordering trap | A hand-check verdict writes `gold/*.json`. Committing it moves HEAD, so Test run must be rerun last or it shows "Stale". The page does not show the order. | Story step 9 and Edge Cases; Test run row "on 8199d4e" | Read from code and catalog, not reproduced |
| Confirmations | Sign uses one `confirm("Sign and publish v1.9.0 as …?")`. Signing is irreversible, so the confirmation is justified. | `release.js:37` | Measured |
| Dead ends | "Fix in Release" on Limitations with no mitigation and on Previous releases readable links to the current page. After a publish, the page redirects to Proof after 2.5 s with no Download link, so the packet takes another hunt. | `02-release-controls.txt` (`#release` twice); `release.js:43-44` | Measured |
| Hesitations | Failing rows sit at positions 4, 5 and 14 of 16, mixed in with Pass and Info rows. "Release checks by company" shows "Fail" for all 6 companies with a G6 count. Those counts add up to 29 (Proposed only), so Needs review and Golden test are missing from this per-company view. | `02-release.png` | Measured |

## Take-away Pass

### Release (`02-release.png`)

- **One primary action:** yes. "Sign v1.9.0" is the only primary button, and it stays disabled while 3 checks fail. Correct.
- **Stated twice:** "10 of 13 required checks pass" under the title and "3 required checks failing" under the button. Drop the button caption, or make it the only count.
- **Removable or collapsible:**
  - Fix-in links on Pass rows (11 of 16 rows): a passing check needs no fix.
  - The "Required" column: State already says Pass, Fail or Info, and "Info" always means "Optional".
  - The three Info rows. Rows with no value and Rows changed since v1.8.0 repeat the "Changes since v1.8.0" card. The Known gaps row repeats its own counts in the label ("0 stub · 3 stale · 37 open findings") and the Count (40). Collapse all three into one line or a disclosure below the required checks.
  - "Release checks by company": G1, G4 and G5 are "·" for every company, and G6 duplicates Proposed. Remove the card, or replace it with per-company counts of all three failing checks.
  - "Packet v1.9.0" file table and "Changes since v1.8.0": these help review after the checks pass, not before. Defer them below the fold or behind a disclosure until Sign is enabled.
- **Sort order:** put Fail rows first. Today they are interleaved (positions 4, 5 and 14).

### Proof (`01-proof.png`)

- The journey uses only the "Next release" link and, later, the Hand check section and the Releases Download link.
- For this story, Verification source and Failure types sit between the header and the Releases and Hand check sections. They are deferrable here, but other stories use them, so they are not removable.
- "Tables unchanged · Nov 3" appears in the header and again in the "Regression test" card at the bottom. "Hand check: 119 of 120 checked" also appears in both places. Each fact appears twice.

### Reconcile (`04-reconcile.png`)

- Two lists on one page: Rule findings (16, with "Select all 16") and Category mapping (29, row-by-row Approve, Reject and Choose another). Each mapping row has three equal buttons, so 29 rows show 87 buttons. Approve is styled as primary, which is right.
- The header shows "Unverified 6", which no release check counts. It is stated without a reason this journey needs it.

### Proof, Hand check (`05b-proof-handcheck-apld.png`)

- The Right, Wrong and Can't say buttons and the note field repeat on all 20 items, including the 19 already decided ("Right · Kenny Geiler · Nov 3, 2026" sits under live buttons). Decided items could collapse to their verdict line.
- The summary block lists 5 group lines, each with a confidence interval, above the company picker. They are deferrable for a "check the last item" task.

## The Simpler Version

Target: about 40 steps, none of them navigation hunting.

1. Navbar → Release. Failing checks are listed first: Proposed 29, Needs review 16, Golden test 1.
2. Proposed → "Fix in Reconcile" (already scoped to `cause=asset_types`). Approve the 18 "Matches company's own tag" rows with one "Approve all matching" action. Decide the other 11 one by one.
3. Needs review → "Fix in Reconcile", scoped to Rule findings. Bulk Accept or Explain by company (about 4 saves).
4. Golden test → "Fix in Proof", which deep-links to `#gold`, APLD selected, scrolled to the unchecked item → Right.
5. Terminal: commit and rerun the tests. Release shows this as the last required step before signing.
6. Release → Sign v1.9.0 → OK. The success state stays on Release and shows "Download packet".
7. Download.

Concrete changes:

- Sort Release checks Fail → Info → Pass, and drop Fix-in links on Pass rows.
- Point each Fix-in link at the exact scope:
  - Needs review: `#reconcile` with the Rule findings cause.
  - Golden test: `#proof` with the Hand check anchor and the ticker of the unchecked item.
  - Fix-in links that point at Release itself: remove them, or point Limitations to LIMITATIONS.md under `#docs`.
- Add a bulk "Approve" for Category mapping rows whose proposal matches the company's own tag (18 of 29).
- Sort unchecked hand-check items first, and collapse decided items to their verdict line.
- After publishing, stay on Release with the version's Download link instead of redirecting to Proof after 2.5 s.
- Show the order on Release: "Test run" goes stale after any commit, so mark it as the last step, for example "Rerun after last commit".
- Reconcile: show the release's three failing counts (Proposed, Needs review) in its header so the round trips to Release are not needed. Drop or explain "Unverified 6".

## Clarity Issues

| Issue | Where | Fix |
|---|---|---|
| One concept, four names: "Golden test" (Release), "Regression test" / "Tables unchanged" (Proof), "Hand check" (Proof), "gold" (Details text, `#gold`). Golden test fails because of the Hand check, but the labels do not connect them. | `02-release.png`, `01-proof.png` | Name the check after what fails, "Hand check 119 of 120", and keep "Tables unchanged" as its own row. |
| Contradiction: Test run Details reads "725 tests, 0 failing, golden ok" while Golden test reads Fail. | `02-release.png` rows 14–15 | Say what "golden ok" covers ("tables equal") or drop it from the Test run line. |
| Developer jargon in Details: "decisions/resolutions.jsonl, 'to confirm'", "taxonomy/asset_types.yaml, T63", "golden/stage<N>-handcheck.json", "has_value false", "append-only checked against 9 commits". Details are also truncated with "…". | `02-release.txt` | Use product labels ("29 category mappings to approve"); move file paths to Docs. |
| "G1 · G4 · G5 · G6" column headers with no legend. | Release checks by company | Use check names, or remove the card. |
| "Count" means failures for most rows, but 11 files for "Packet v1.9.0" (Pass) and 0 = pass elsewhere. | `02-release.png` | Use a separate "Files" label, or leave Count blank for Packet. |
| "Answer-key values missing from the dataset": "answer key" is used nowhere else; the app says "SEC XBRL". | Release row 7 | "SEC XBRL values missing from the dataset". |
| "Proposed" as a check name is a status, not a check. | Release row 4 | "Mappings to approve". |
| Row label carries its counts: "Known gaps: 0 stub · 3 stale · 37 open findings", with Count 40 and Details repeating proven, partial, stale and more. | Release row 13 | Label "Known gaps", Count 40, and the breakdown once. |
| The catalog's "12 of 15 required checks" no longer matches the live "10 of 13". | `catalog.md` STORY-045 step 2 | Update the catalog. |
| App-rule check: no gradients or italics seen. Red and orange colored words act as status text, which is acceptable. Every section is a bordered card (Release has 4 stacked cards), which leans toward "bordered boxes everywhere". | All screens | Suspected; flatten the secondary cards (Packet, Changes) into plain tables. |
