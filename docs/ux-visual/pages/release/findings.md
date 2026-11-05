I audited Reconcile and found 33 problems, 0 of them P0. Every viewport × state was screenshotted and measured, nothing was written, and no non-GET request was attempted.

**By severity:** P0 0 · P1 4 · P2 20 · P3 9
**By level:** component 15 · group 10 · page 4 · layout 4

**5 worst:**
1. **F01 (P1, layout):** Grouped by company at 1280×800, the Cause and Item columns shrink to about 90 px and wrap to four lines, so rows are 105 px tall. Meanwhile four value columns showing only "—" keep about 650 px (`1280-by-company.png`).
2. **F02 (P1, component):** With filters on, the header still shows global counts: "Needs review 16" sits above 7 rows (`1600-filtered.png`).
3. **F03 (P1, group):** Ticking the first checkbox inserts a 73 px bulk bar above the table, so the row you just clicked jumps 101 px down (`1600-selected.png`).
4. **F04 (P1, layout):** The page scrolls 4,719 px at 1600×1000 and up to 6,790 px grouped by company at 1280×800. Table headers and filters don't stay on screen, so deep in Category mapping no column names are visible.
5. **F06 (P2, component):** The Accept / Explain / Fix / Block release control is a cramped 20 px group ("Fix" is 27 px wide). The selected option uses the same blue as the Save button next to it (`1600-rule-open-zoom-decision.png`).

**Notes:**
- **Category mapping click:** the first run's scripted click on a Category mapping row didn't open it. A second script (`mapping.py`) opened it and replaced both the mapping-open shots and their audit entries.
- **Signer contrast:** the layout audit flags the "Signer" label at 1.43:1 in every state. The screenshots show it readable on the dark navbar, so I treated it as an audit false positive and filed nothing.
- **Earlier flow decisions:** where a finding overlaps a decision already made in the flow report (empty value columns, the many Approve buttons, Accept selected by default), it covers only the visual layer and names that decision.

The findings file also has a verdict for each viewport × state and an "Excellent as is" list. The filtered view at 1600×1000 is the best state and the model for the rest of the page.

Files are in /Users/kennygeiler/ai-capex-ledger/docs/ux-visual/:
- pages/reconcile/findings.md
- pages/reconcile/audit.json
- pages/reconcile/shots/ (23 screenshots)
- tmp/reconcile/ (scripts: run.py, mapping.py, probe.py; extra.json)