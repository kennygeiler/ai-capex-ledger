# STORY-064 — Evaluate the whole dataset before licensing it

Persona: Sam, head of data at a buyer, on the hosted read-only copy. Goal: a trust verdict, the signed files, a caveat list.
Evidence: local app at http://localhost:3610, captured 2026-11-04 at 1600x1000 (`docs/ux-flow/tmp/s064.py`), screens and page text in `STORY-064-screens/`.
Limit of the evidence: the local app runs in owner mode (Signer box filled, `Sign v1.9.0` button present, 05-release.png). The read-only refusals (catalog steps 7, 11, 15) and the "· Read-only" scope line (step 1) were not reproduced; findings on them cite the catalog only and are marked **suspected**. No write control was clicked; the script logged no non-GET request.

## Friction Scorecard

| Measure | Value | Basis |
|---|---|---|
| Steps, catalog actual | 22 | catalog STORY-064 Steps |
| Steps, Ideal path | 8 | catalog Ideal path |
| Pages visited | 10 distinct, 12 visits (Proof twice, Release twice) | catalog steps 1–21 |
| Decisions a default could carry | 2 | below |
| Re-entry | 2 | below |
| Confirmations guarding nothing | 0 measured; 3 refusals after the fact (suspected) | catalog steps 7, 11, 15 |
| Dead ends | 2 | below |
| Hesitations | 4 | below |

Decisions a default could carry
1. Which trust page to read first. Proof, Rules, Release and Known gaps each carry a summary verdict ("0 of 6 proven", 01-proof.png; "10 of 13 required checks pass", 05-release.png; "6 Holds · 38 Partial …", 04-gaps.png; per-agent "Score", 03-rules.txt). No page says which one answers "can this be licensed". Measured.
2. Which packet. Proof → Releases lists six versions, each with its own `Download` (01-proof-controls.txt: `/packet/v1.8.0.zip` … `/packet/v1.3.0.zip`). The latest signed one is the only one a buyer wants by default. Measured.

Re-entry
1. Release twice: step 16 by nav, step 20 by the "Release" box in Docs → How it works (07-docs-overview.txt lists the box). Same page, no new information. Catalog-measured.
2. Proof twice: step 1 and step 21, because the signed packet `Download` is only on Proof. Release has 0 `Download` links (05-release-controls.txt, grep count 0) and shows only the unsigned "Packet v1.9.0" file list (05-release.png). Measured.

Dead ends
1. Release `FIX IN` column (05-release.png): every row links to Proof / Reconcile / Dataset / Known gaps. For a visitor these lead to owner work queues ("Review in Reconcile →" on the trail, 02-trail-msft.txt). Measured that the links exist; dead end for a visitor is suspected.
2. Reconcile, Explore "Save changes" and gold `Right/Wrong` are live controls that refuse after the click (catalog steps 7, 11, 15, edge case "three refusals … each in a different style"). Suspected (not reproducible in owner mode).

Hesitations
1. "0 of 6 proven" (01-proof.png) next to Release info row "proven 6 · partial 38 · stale 3" (05-release.txt) and Known gaps "6 Holds" (04-gaps.png). Two "proven" numbers, 0 and 6, for different things. Measured.
2. Known gaps header "6 Holds · 38 Partial · 0 Not built · 3 Out of date · 3 Planned · 37 open issues" (04-gaps.txt) vs Docs → Known limitations "proven 0 · partial 41 · stale 4 · stub 2 · planned 3 · open findings 37" (06-docs-claims.png). Same claims register, two vocabularies and different counts on the same day. The doc explains it is the committed snapshot minus live checks, in a 6-line paragraph of code paths. Measured.
3. Staleness: Known gaps row "Hosted copy · Out of date · deployed from c0635f3 … this checkout is at 2bb60b8" (04-gaps.png, row 3) is the only staleness signal; the scope line reads "6 companies · Data as of Nov 1, 2026" on every page (01-proof.png). Measured.
4. Proof stage cells "0 · 5 · 0 · 0" / "15 · 0 · 0" (01-proof.png): unlabeled dot-separated counts with three or four slots depending on column; meaning only from the legend below the table and a hover. Measured.

## Take-away Pass

Proof (01-proof.png, 01-proof-full.png)
- Removable for this journey: Failure types (two pareto charts plus two tables, 72 types; 01-proof.txt). It describes the pipeline's failure taxonomy, not the dataset's trust. Collapse by default.
- Collapsible: Verification source table repeats per-company counts that the trail's VERIFICATION block also shows ("Match SEC XBRL 42 · Tie to totals 31", 02-trail-msft.txt = MSFT row "42 … 31", 01-proof.png).
- Information stated more than once: "Tables unchanged · Nov 3, 2026" and "Hand check: 119 of 120 checked" appear in the header (01-proof.png) and again under Regression test ("Tables unchanged · Nov 3, 4:12 PM · Hand check: 119 of 120 checked", 01-proof.txt). Measured.
- Primary action: none for a visitor. Six `Download` links of equal weight at the bottom of the page; no single "Download latest signed packet". Measured.

Company trail MSFT (02-trail-msft.png)
- Legend of 8 states (Verified, Corroborated, Matches company tag, Done, Unverified, Proposed, Needs review, Blocks release) precedes the content; Proof's legend has 4 (Checked, Located/Done, Unverified, To review). Collapse to the states present.
- Owner actions shown to a visitor: "Review in Reconcile →", "Reconcile", "Dataset" header buttons, "To confirm" on category mapping. Suspected removable in read-only mode.
- Exactly one primary action: no (two header buttons plus "Review in Reconcile →").

Rules (03-rules.txt)
- Keep: Model, Prompt, Score (SEC XBRL match with CI; planted errors caught/missed). This is the strongest trust evidence in the app.
- Removable for a visitor: Charter body with CLI and source paths ("`ledger extract --run`; … ledger/checks/proof.py, `stages["values"]`"); "Runs per company" token/time table. Defer behind "Full charter".

Release (05-release.png)
- Collapsible: Details column truncated with "…" on 10 of 17 rows; full text references internal files ("decisions/resolutions.jsonl", "taxonomy/asset_types.yaml, T63", 05-release.txt).
- Removable for a visitor: `FIX IN` column; disabled `Sign v1.9.0` (rendered disabled in owner mode here; visibility in read-only mode not measured).
- Missing: a `Download` for the last signed packet. The page lists the unsigned packet's files with byte counts instead.
- Information stated more than once: "3 required checks failing" under the button and "10 of 13 required checks pass" in the header. Same fact twice.
- "Release checks by company" G1/G4/G5/G6 columns: every cell "·" except G6 (05-release.png). Three of four columns carry nothing.

Known gaps (04-gaps.png)
- Keep. This is the most direct caveat source. 50 claims in one flat table; filtering to Out of date / Planned first would put the license-relevant rows on top (Hosted copy is row 3 by luck of order).

Docs → Known limitations (06-docs-claims.png)
- Duplicate of Known gaps: same 50-claim register, older snapshot, different column set (WHERE as file paths, DECLARED, COMPUTED, WHY, TICKET). Remove from the sidebar or replace with a link to Known gaps. Measured duplication.

Docs → How it works (07-docs-overview.txt)
- Keep the opening paragraph; it is the only place that states "citation only … more than half the rows in scope". The PACKAGE (MAP) column and CLI names are owner material.

Dataset, Explore, Reconcile
- Not needed for the trust verdict. Steps 11–15 are exploration and failed writes. Reconcile is an owner queue.

## The Simpler Version

Target: 6 steps.
1. Open the hosted root → Proof shows a visitor summary block: latest signed release (v1.8.0, signer, date), hosted copy age ("Hosted copy · Out of date since c0635f3"), "0 of 6 proven", hand-check error rate with CI, and one primary `Download v1.8.0 packet`.
2. Click one company → trail (verification counts, crops, filing links), with owner buttons hidden.
3. Rules → Score per agent (unchanged).
4. Known gaps → filtered by default to Out of date, Planned, Partial with license impact; Hosted copy row first.
5. Release → read the checklist; Details expanded in full, `FIX IN` and G-columns hidden for visitors.
6. Download the signed packet from step 1 (or a `Download v1.8.0` on Release) → caveat list built from Known gaps.

Concrete changes
1. Add `Download v1.8.0 packet` (latest signed) to Release and make it the single primary action on Proof; move older versions behind "Earlier releases". Removes re-entry 2.
2. Put hosted-copy staleness in the scope line ("Data as of Nov 1, 2026 · Hosted copy out of date") instead of only in Known gaps row 3. Removes hesitation 3.
3. Drop "Known limitations" from the Docs sidebar, or render it from the live register so its counts equal Known gaps. Removes hesitation 2 and one page visit.
4. Rename the Release info row's "proven 6" to the Known gaps word ("Holds 6"), so "proven" only means the Proof board's "0 of 6 proven". Removes hesitation 1.
5. In read-only mode, hide or disable every write control (gold Right/Wrong, Reconcile Save, Explore Save changes, Review in Reconcile, `FIX IN`) instead of refusing after the click. Removes dead end 2 and three refusal styles (suspected).
6. Docs How it works "Release" box: link with a visible destination label or drop it; it re-enters Release (step 20).
7. Collapse Failure types and Regression test on Proof by default; drop the repeated "Tables unchanged · Hand check" line under Regression test.

## Clarity Issues

| Label | Where | Problem | Proposed |
|---|---|---|---|
| `0 · 5 · 0 · 0`, `15 · 0 · 0` | Proof stage cells (01-proof.png) | Unlabeled counts; slot count varies by column; meaning only via legend and hover | Show the largest non-zero as "5 done", the rest on hover |
| Checked / Located/Done / Unverified / To review | Proof legend (01-proof.png) | Third vocabulary for item state | One set across Proof, trail, Release |
| Verified / Corroborated / Matches company tag / Done / Unverified / Proposed / Needs review / Blocks release | Trail legend (02-trail-msft.txt) | 8 states vs Proof's 4; "Checked" (Proof) = "Verified + Corroborated + Matches company tag" (trail), only explained in Known gaps row "Item states" (04-gaps.txt) | Same words on both pages |
| checked, explained, open, blocked | Docs How it works "state" (07-docs-overview.txt) | Fourth vocabulary | Use the page words |
| "to review" / "Needs review" / "open issues" / "open findings" | Proof, Release, Known gaps, Docs | Same idea, four names (also noted in catalog edge cases) | "To review" for items, "Open issues" for findings |
| Holds / Partial / Not built / Out of date vs proven / partial / stale / stub | Known gaps (04-gaps.png) vs Release info row and Docs (05-release.txt, 06-docs-claims.png) | Same register, two status vocabularies | Known gaps words everywhere |
| "proven 6" vs "0 of 6 proven" | Release info row vs Proof header | Same word, opposite numbers, different objects | "Holds 6" on Release |
| G1, G4, G5, G6 | Release checks by company (05-release.png) | Codes with no label; three columns empty | Name the gate; drop empty columns |
| Proposed (check name) | Release row (05-release.png) | Check named after a state; reads as a status, not a rule | "Proposals confirmed" |
| Known gaps vs Known limitations | Nav vs Docs sidebar | Two names for one register | One name |
| Signer | Top bar (01-proof.png) | Owner field shown on every page; meaningless to a buyer (read-only behavior not measured) | Hide in read-only mode |
| Charter text with `ledger extract --run`, `ledger/checks/proof.py` | Rules (03-rules.txt) | CLI and source paths in product copy | Move behind "Full charter" |
| Details column text with `decisions/resolutions.jsonl`, `T63` | Release (05-release.txt) | File paths and ticket ids in product copy | Plain labels; paths in Docs |
| "Kenny's Data Emporium" | Top bar | Brand name gives a licensing buyer no signal of the product ("Capex Ledger" in Docs, 07-docs-overview.txt) | One product name |
| Claims register intro paragraph | Docs → Known limitations (06-docs-claims.png) | 6-line wall of text with five code paths | Remove with the page (change 3) |

App-rule check: no gradients, italics or decorative pills seen in the captured screens. Bordered cards wrap every table on Proof, Release and Known gaps (01-proof.png, 05-release.png, 04-gaps.png); borderline against "bordered boxes everywhere", not counted as a finding.
