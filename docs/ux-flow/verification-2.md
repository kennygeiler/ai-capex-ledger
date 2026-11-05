# UX Flow, second batch — verification

Branch `flow-2` (from main 5b22326). Proposals #6, #8, #10, #11, #12, #13, #14 of `docs/ux-flow/report.md`, built on the
first batch (1240ead: #2, #4, #5 and the STORY-027 numbers). Measured 2026-11-05 on a local copy of the app (owner mode
on port 3640, `LEDGER_READONLY=1` on 3641), data as of Nov 1, 2026, at 1600×1000 and 1280×800. "Before" counts come from
the journey files the report cites; "after" counts were taken on the branch. Screens are in `verification-shots/`
(gitignored, not committed). Nothing was signed, published or saved: the save and sign paths were driven up to the
write and are covered by tests on their pure parts.

## Summary

| # | Proposal | Journey | Before | After | Result |
|---|---|---|---|---|---|
| 6 | Rule findings: groups, deliberate Save | STORY-027 | ~38 inputs, Field filter per batch, Accept preselected | 25 inputs, no Field filter, no preselection | pass |
| 8 | Packet download on Release | STORY-045, 055, 064 | Sign → redirect to Proof → find Download among 6 | Sign → Download on the same page | pass |
| 11 | Proof does one job | STORY-006, 045, 064 | ~4 screens: board, verification, failure types, releases, regression card, hand check | 1 screen at 1600×1000: board, hand check, verification folded | pass |
| 10 | Company trail condensed | STORY-014 | 21 steps; 24,181 px with three tallies open; Back → top | ~13 steps; 19,999 px; Back keeps the scroll | pass (after review fix 1) |
| 12 | Docs start at Start here | STORY-068 | 18 steps; Handoff last; 6 dead doc references | 6 steps; Start here first and default; references are links | pass |
| 13 | Dataset: one Verification filter, one export | STORY-055 | 18 steps; verdict in 2 column names; Grid filter hidden and dropped | 6 steps; one control on every list and the Grid; kept across views | pass |
| 14 | Read-only scope line | STORY-064 | "Read-only" only | "Read-only · Serves v1.8.0 · Code c0635f3 · Code differs from …" | pass |

## #6 Rule findings (STORY-027)

Before (journey): per batch Scope, Field, open a sample row, Select all, choose a decision (Accept already chosen), type,
Save, Field again: about 9 inputs, four batches, about 38 inputs. Fix gave no warning that the item stays open.

After, measured on `#reconcile?scope=APLD&cause=finding_unconfirmed` and `?scope=GOOGL`:

| Step | Inputs |
|---|---|
| Release → Needs review → GOOGL (row link from batch 1) | 2 |
| Group "Alphabet · Segment revenue · Does not tie to reported total · 6 rows": tick, decision, reason, Save for 6 | 4 |
| Group "Alphabet · PP&E by category · Does not tie · 1 row": tick, decision, reason, Save | 4 |
| "N left · Release" | 1 |
| Release → APLD | 2 |
| Group "Applied Digital · PP&E by category · Readings differ across filings · 4 rows": tick, decision, Save for 4 (reason prefilled "Later filing's reading used") | 3 |
| Group "Applied Digital · Segment capex · Does not tie · 6 rows" | 4 |
| Group "Applied Digital · Segment revenue · Does not tie · 1 row" | 4 |
| "0 left · Release" | 1 |
| Total | 25 |

| Item | Result |
|---|---|
| Rows grouped by company + field + check, one tick per group | pass: 3 groups on APLD, 2 on GOOGL |
| No decision preselected; Save disabled until one is chosen | pass: bulk bar "Save for 6" disabled, "No decision chosen" |
| "Readings differ" reason prefilled when the dataset uses the newest reading | pass: "Later filing's reading used" for the 4-row group |
| Fix states its consequence | pass: "Item stays open until the next run" (orange) beside the choice |
| "N left · Release" | pass: header "7 left · Release", bold at 0; a save says "Saved · N left · Release" |
| Read-only copy draws no group tick | pass: 0 visible checkboxes besides "Show N settled" on 3641 |

## #8 Packet download on Release (STORY-045, 055, 064)

| Path | Before | After |
|---|---|---|
| Sign → get the packet | Sign, confirm, wait for the redirect to Proof, scroll to Releases, choose among 6 equal Downloads: 2 pages | Sign, confirm, "Download vX.Y.Z" in the status line: 1 page |
| A buyer wants the latest packet | Proof → scroll → Releases → which Download | Release → "Download v1.8.0" (the one outline-primary button in Releases) |
| Packet file → its list | Navbar Dataset → sidebar list: 2 | packet row link (`taxonomy.csv` → `#data?list=taxonomy`): 1 |

| Item | Result |
|---|---|
| After Sign the page stays on Release with "Download vX.Y.Z" | pass (tested on signedNext; no real signature) |
| Releases table on Release | pass: below the checklist |
| One "latest signed" primary | pass: v1.8.0 outline primary, 5 older plain links |
| Packet file names link to Dataset lists | pass: 6 CSVs linked; ai_spend.csv has no list (F-FW1) |

## #11 Proof does one job

| Item | Result |
|---|---|
| Stage board with open buckets, hand check | pass: page fits 1600×1000 with no scroll (was ~4 screens) |
| Failure types → Rules | pass: "Failure types" with both charts at the foot of Rules |
| Releases → Release | pass |
| Repeated Regression test line dropped | pass: the header's "Tables unchanged · date" is the one line; its hover names changed tables |

## #10 Company trail (STORY-014, APLD)

| Measure | Before | After |
|---|---|---|
| Statement figures rows | 23 (flags as duplicate figures) | 15; "Large year-over-year change" folds under Opex FY2026 |
| AI disclosures rows | 35 (7+ rows reading only "Revenue · FY2025 · Actual") | 35, each part-year row showing its own words (they are distinct statements; merging them hid that, review 2) |
| Category mapping | 8 cards ~480 px, "Decide in Reconcile →" ×8 | one row per category, one link in the stage header |
| Links to Reconcile on the page | 10 (header, summary, 8 cards) | 2 (summary, mapping stage) |
| Page height, three tallies open | 24,181 px | 19,999 px (folded: 2,771 px) |
| Complete stages | open when ≤12 rows | folded behind their tally |
| Back from Dataset | scrollY 0 | scrollY kept (656 → 656 measured) |

Steps 21 → about 13 (the duplicate flag rows, the 8 repeated links, the identical-looking rows and the Back round trip are gone).
All items pass. Back restores the scroll, not which tallies were open (F-FW2).

## #12 Docs (STORY-068)

| Step | Before | After |
|---|---|---|
| Where to start | Handoff, 9th of 9; `#docs` opened How it works | Start here, first; `#docs` opens it |
| `docs/COMPANIES.md` and five more in code | code text, dead | links (sidebar doc in-app, served doc as text, others on GitHub) |
| Map then Back | scrollY 0 of a 5,984 px page | the same place |
| Docs vs UI words | "asset types" group, Edit | Category mapping cards, Choose another, Start here |

Steps 18 → 6. Items: Start here first and default (pass), references as links (pass, 1 archive reference goes to
GitHub), wording (pass), anchors keep scroll and land (pass: `#docs/handoff?at=the-hosted-copy` lands on its heading).
Left open: the Handoff page's own length and Known limitations vs Known gaps (F-FW3).

## #13 Dataset (STORY-055)

| Step | Before | After |
|---|---|---|
| Find non-verified rows across lists | open six lists, know the column (`check` vs `check_label`) | one Verification select, same words on every list |
| `values?check=unresolved` | ignored (81 of 81 rows) | 0 rows; facts 5 |
| Rows → Grid | filter and company dropped | kept (`#data?view=grid&list=facts&check=unresolved`) |
| Grid filter | URL only, no control, dropped by any control | a control, kept by every control |
| Export | Rows server CSV + JSON, Grid browser-built CSV | one CSV per view, both from the server |

Steps 18 → 6. All items pass. At 1280×800 the Grid's controls stay on one line with no horizontal scroll.

## #14 Read-only copy

| Item | Result |
|---|---|
| Write controls hidden | pass (F-VT4 and the new group tick) |
| Scope line names the release served | pass: "Serves v1.8.0 · Code c0635f3" |
| Flags an older release than the latest signed | pass (tested; equal today: v1.8.0) |
| Flags different code | pass: "Code differs from <HEAD>" on this checkout; "unknown" (no flag) where no git exists |

The copy reads its own deploy record and the releases it holds; no network call (F-FW4).

## Tests

`tests/test_flow2.py` (one class per proposal), each failing on the code before this batch. Results of
`ledger test` are in `reports/tests.json`.

## Review follow-up

An independent review of 5b22326..fb1d495 found 1 bug and 7 risks; each is fixed with a test that fails on the code it
replaced. Measured again on the branch after the fixes.

| # | Finding | Fix | Commit | Check |
|---|---|---|---|---|
| 1 | Bug: the trail keyed figures on field + period, so a second figure in a period (two segments, two PP&E categories) lost its row and a flag folded into the wrong one. APLD Note figures showed 15 rows for 71 items. | Key field + dimension + period; every figure is kept; a flag folds only into its one matching figure, else stays a row | 7179059 | Database, six proven companies: figure rows equal before and after (MSFT 115, GOOGL 117, AMZN 90, NVDA 166, APLD 252, AMD 135); 14 flags fold; APLD Note figures 71 rows |
| 2 | Rows differing only in what they open (detail, restatement) were merged | Merge only rows identical in the whole card, state, reason and detail; a statement with no figure shows its words | 7179059 | APLD AI disclosures 35 rows, each part-year row with its own text |
| 3 | The "Later filing's reading used" prefill accepted an older filing printing the newest figure | Require the newest filing's own reading | 5161a5f | Repro: used B, newest C → no prefill |
| 4 | Proof's Regression test card held per-step results and per-table differences OPERATIONS.md points to | The Regression test line on Release opens to Steps and Differences | 5c0b777 | Release: 10 steps Pass, "No table differs from the freeze" |
| 5 | After a signature whose publish failed, the releases table still read "Not signed" | Every signature response redraws it | 5c0b777 | Test on the handler text |
| 6 | A signed, unpublished release got the primary Download the post-sign status withholds | latestSigned skips published = false | 5c0b777 | Test |
| 7 | `check` on values and facts changed from no-op to filter without a record | Kept; dated entry in docs/API.md "Changes" (no version mechanism exists) | 62184a9 | Database: check=agree keeps only agree rows on both lists |
| 8 | A folded flag's state showed by colour only | "Large year-over-year change · Unverified" in words | 7179059 | APLD Opex FY2026 |
