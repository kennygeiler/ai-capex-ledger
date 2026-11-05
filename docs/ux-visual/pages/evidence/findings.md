I found 31 problems on the Dataset and Explore pages: one misleads (P0), six would make a person stumble (P1), 18 are visibly below excellent (P2) and six are polish (P3). I captured every state at both viewports, ran both audit scripts and interacted with each page read-only; no write requests fired.

**By level:** page 3, layout 3, group 4, component 21.

**Worst 5:**
1. **DE1 (P0, measured):** the Explore chart's FY2026 bar adds up only the 3 companies that have filed (MSFT, NVDA, APLD). It drops from $293B to $125B with nothing marking the year as incomplete, so capex looks like it collapsed. Both the default chart and the saved view show it.
2. **DE2 (P1, measured):** the Rows view draws all 617 rows and 40 columns at once. The page is 19,110 px tall and the table is 5,493 px wide in a 1,069 px pane, so 19% of it is visible. The column headers don't stick.
3. **DE3 (P1, measured):** after Find in rows, the column headers turn into plain grey browser buttons. The Explore "Show rows" table has the same fault. The cause is that the Tabler styling pass (`skin()`) only runs when the page first loads, not when a table is redrawn.
4. **DE6 (P1, observed, cause suspected):** opening an Explore chart link directly can show "Chart unavailable" over a 400 px blank. Plotly loads deferred from a CDN, so the page can draw before it is ready. The same chart draws fine when reached from inside the app.
5. **DE7 (P1, measured):** Explore has 13 controls and none has a visible label. Their options read as fragments ("every asset type", "then", "x: fiscal year"), two are both named "Measure", and they wrap onto 3 ragged lines. At 1280 "From" and "To" land on different lines.

The Grid, the provenance drawer and the chart axis made the "Excellent as is" list, along with Find's live count, the Data table under the chart and dark mode.

Files are in /Users/kennygeiler/ai-capex-ledger/docs/ux-visual/:
- pages/dataset-explore/findings.md
- pages/dataset-explore/audit.json
- pages/dataset-explore/shots/ (10 viewport×state pairs plus about 20 interaction shots)
- tmp/dataset-explore/ (shoot.py, interact.py, proj.py, interact.json)