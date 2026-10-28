# Design review, round 1: independent critiques (2026-10-27)

Reviewers saw Report, Desk and Mirror (Terrain cut). All data is sample.


## CEO

**1. Is this the most useful way to present the data for the persona?**
No, and I'd challenge the persona first. A buy-side analyst already has Bloomberg and FactSet and will not switch to a site built on 10 companies. The realistic users are the hiring manager and the "informed reader" who shares a chart on LinkedIn. The tool should be designed for them, using the analyst's questions as its content.

Measured against that, Mirror is the only direction that states a "so what" (screen 5: "Buyers spend it. Sellers book it."). The trouble is the gap it shows: $134B of capex against $76.5B of seller revenue. That gap is mostly a coverage hole, not a finding. Broadcom, TSMC, Arista, Vertiv and the cost of power and construction are all missing. An analyst would spot that in five seconds.

Report (screens 1–3) gives the right totals but no point of view. "$488B, +42%" is a fact, not an insight.

**2. Is the UI actionable and flexible enough?**
Desk (screen 4) is the only flexible one: the company rail, the finance-lease toggle, and lineage on every fact. It still answers only "what did MSFT file?". The persona needs answers across companies:
- Is spending accelerating?
- Who is the outlier?
- What is funding it?

There is no way to compare two companies, no quarter-on-quarter acceleration, and the lease toggle exists only in Desk. Report and Mirror can't be manipulated at all.

**3. Are the data outcomes actionable?**
Not yet. "Where the risk sits" needs capex against operating cash flow (free cash flow), depreciation, and leases as a share of capex. None of those is in the data contract. The "capex / revenue" column is a weak proxy. CoreWeave at 300% (screen 3) is the most interesting row, and the design hides it: Mirror's slope chart excludes it on screen 6. Tesla is a distraction in a list of AI buyers.

The "Derived" column is the best data-strategist signal in the whole thing, and it sits at the far right with no explanation of why it matters.

**4. Which charts and data experiences are optimal?**
- **Diverging mirror bar** (keep it): is the money flowing through? Add an "unaccounted" band labelled with the missing seller categories, so the gap becomes honest.
- **Capex ÷ operating cash flow per company, as a line or slope chart**: who is funding the buildout from cash, and who from debt or leases. This is the risk question.
- **Quarter-on-quarter growth heatmap** (company × quarter): is spending accelerating or rolling over? Rollovers jump out as colour breaks.
- **Stacked share of combined capex**: concentration, meaning how much of the cycle depends on 2 or 3 firms.
- **Stacked bar of capex split into PP&E and finance leases**: hidden financing.
- **Lineage drawer on any number**: click a figure to see the form, tag, accession and method. This is Desk's table, used as a drawer instead of a screen. It is the hiring proof.

**5. Can the user chat with the data and manipulate it? Should they?**
Manipulation, yes: comparing companies, the lease toggle, a window of 4 or 8 quarters, and a choice of metric.

A free-text chat box, no. It costs money, it can make up numbers, and it undercuts the core claim that every figure is traceable.

Instead, offer **10–15 precomputed question chips**, for example:
- "Who's spending fastest relative to cash flow?"
- "Did any buyer cut capex quarter on quarter?"
- "How much capex is leases?"

Each answer is a deterministic query over the facts table, rendered as a sentence, a mini chart and the accessions it cites. The wording would be written at build time in a Claude Code session, so runtime cost is $0. A local model such as WebLLM is technically possible, but it is a 1–4GB download for visitors and the answers can't be verified. Skip it.

**Top 5 iteration steps (ranked)**
1. **Get real EDGAR data for 3 companies (MSFT, NVDA, CRWV) before any more design work.** A data strategist's portfolio on invented numbers is a design portfolio. Those three cover the hard cases: a June fiscal year, a January fiscal year, and a recent listing. Effort: L.
2. **Merge into a single product: Mirror as the landing page, Desk as the drill-down, and Report's summary table absorbed into Desk.** Cut Report as a standalone direction. Three directions dilute the story. Effort: M.
3. **Add operating cash flow and turn leases on by default.** Show capex ÷ OCF and the lease share. This turns "who spends" into "where the risk sits", the question the persona actually has. Effort: M (tags already exist in companyfacts).
4. **Fix the coverage honesty.** Add Broadcom to the sellers, label Mirror's gap as "not covered: foundry, networking, power, construction", put CoreWeave back with a broken-axis callout, and drop or footnote Tesla. A reviewer's first credibility check will be on coverage. Effort: S.
5. **Add question chips with cited answers, plus a "what to watch next quarter" strip** (acceleration flags and outliers). This gives the actionable "so what" and the shareable screenshot, with no LLM cost. Effort: S–M.

**Verdict:** Carry Mirror forward as the story and Desk as the proof underneath it, and drop Report except for its summary table.


## Chief of Design

**1. Is this the most useful presentation for the persona?**
No. All three directions answer "how big is it?" The analyst's questions are different: is it speeding up, who captures it, and where is the risk.
- Report's hero (screen 1) is a level ($488B). The growth figure (+42%) sits in grey body copy. The one-colour bars hide each company's share until you hover.
- Mirror (screen 5) has the strongest idea. But its caveat ("Totals, not transactions…") is pushed below the fold (top of screen 6), and that caveat is what keeps the chart honest.
- Desk (screen 4) is the only view that shows real data skill, but it opens on Microsoft with no story.
The right structure is Mirror as the thesis, then Desk as the evidence. Report's small multiples should become a ranking view inside Desk.

**2. Is the UI actionable and flexible enough?**
Not yet.
- No time-range control, no compare mode, and no peer-relative view.
- The only state saved in the URL is `?v=`. The Desk company and the finance-lease toggle are not in the URL, so a view can't be shared.
- Desk's fact table has no filter by metric or method. Its accession column is clipped off the right edge (screen 4: "sample-(").
- The three Desk panels each use a different y-scale ($100B / $40B / $20B) but sit side by side, so the eye compares them as if they were equal.
- The shared scale in screen 2 flattens Tesla and CoreWeave into illegible strips. It's fine for showing size, useless for reading their trends. Add a toggle between shared and own scale.
- The 860px breakpoint exists, but a 9-column fact table on a phone will scroll sideways. It needs a stacked-row layout.

**3. Are the data outcomes actionable?**
Partly.
- Capex/revenue is the wrong risk ratio. Capex divided by operating cash flow (a filed tag) says whether spending is self-funded. That, plus finance leases as a share of capex, is the financing-risk signal.
- Screen 3 shows ratios that don't mean anything:
  - capex/revenue for sellers (NVDA 3%);
  - "300%" for CoreWeave, with no flag on it.
- The "Derived" column (16, 10, 6) is good lineage but reads as an unexplained number.
- Nothing points to next quarter. Filing dates from EDGAR could at least drive a "next 10-Q expected" date for each company.

**4. Which charts are optimal?**
- **Top: diverging bars (Mirror, screen 5)**, with seller revenue split by company in tints and the caveat directly under the chart. Answers: how far does spend outrun what suppliers book?
- **Next to it: QoQ and YoY growth-rate line for combined capex.** Answers: accelerating or rolling over? This is the persona's first question and nothing currently answers it.
- **Share-of-spend 100% stacked bars or a ranked bump chart.** Answers: who is concentrating spend. It replaces the hover-only breakdown in screen 1.
- **Replace slope chart (screen 6) with small-multiple lines of capex/OCF across all 8 quarters.** Answers: who is stretching. A first-vs-last slope throws away 6 quarters, and its labels collide (META/ORCL on the left, MSFT/META at 42% on the right). It also uses buyer-blue as the highlight, which breaks "one accent per role."
- **Drill-down: Desk**, with all three panels on one shared scale or explicitly labelled as separate scales, the lease toggle saved in the URL, and the fact table filterable.
- **Lineage drawer:** click any bar to open the facts behind it (form, tag, method, accession linked to EDGAR).

**5. Can they chat with or manipulate the data? Should they?**
They should be able to manipulate it, and to ask in a constrained way. They should not get open chat.
Use a natural-language box that compiles to a visible query spec. The spec is rendered by the same chart code, so every answer carries its lineage. Power options, all with zero API spend:
- precomputed question templates;
- a small grammar parser;
- an in-browser model (WebLLM) that emits only JSON.

```
[ Ask: "meta capex vs ocf since 2025" ............ ⏎ ]
  ↳ chips: [META ×] [capex ÷ op cash flow] [2025Q1–2026Q2] [edit]
┌ chart (same renderer, same tokens) ──────────────┐
│ ▂▃▃▅▆▇  line + zero baseline                       │
└──────────────────────────────────────────────────┘
 12 facts · 9 as filed · 3 YTD difference   [show rows ▾]
 Not in filings: "AI share of capex" → can't answer, here's why.
```

Failure states:
- **Unmapped metric:** say "not in filings" and suggest the nearest filed tag.
- **Partial coverage:** CoreWeave before it listed shows as grey gaps, never zeros.
- **Ambiguous question:** show the chips for the user to confirm before drawing anything.
The chips are the real interface; typing is just a fast way to set them.

**Top 5 iteration steps**
1. **Build the landing page as Mirror plus a growth-rate panel, with the caveat adjacent.** It answers "accelerating?" first and keeps the thesis honest. *M*
2. **Make every view saveable in the URL** (company, metrics, range, leases, scale), with a copy-link button. Shareable views are what analysts actually use. *S*
3. **Replace capex/revenue with capex/OCF and leases as a share of capex**; drop seller capex ratios and flag outliers. This is the real risk signal and it uses only filed tags. *M*
4. **Add a click-to-lineage drawer on every bar, with EDGAR links.** This makes the portfolio's core claim visible everywhere, not only in Desk. *M*
5. **Build a chip-based query bar** (templates first, WebLLM later). It shows data-strategy thinking (spec, lineage, refusal states) with no API spend. *L*

Smaller fixes along the way: fix the clipped accession column and mobile tables, resolve the slope-label collisions, and add the shared/own scale toggle (S).

**Verdict:** Carry Mirror forward as the front door and Desk as the drill-down, and fold Report's ranking table into Desk.


## AI Data Architect

**AI Data Architect, round 1**

**1. Is this the most useful presentation for the persona?**
No. All three views show levels, but the analyst's question is about rates of change and risk. Two framing errors would hurt with a buy-side reader:
- **The hero overclaims.** "$488B … AI buildout spending" is total PP&E cash capex, which includes land, buildings, Tesla factories and Amazon logistics. Label it "capex". Make an AI share an explicit, sourced assumption, not an implied one.
- **Mirror compares unlike things.** Buyer capex is everything; seller revenue is all segments of three chip vendors (Nvidia gaming, AMD client PCs, Micron consumer). It also leaves out Broadcom, TSMC (a foreign filer with no quarterly XBRL), SK Hynix, networking and power. The gap is built into the data, so it can't be read as a finding. The caveat in the footnote doesn't fix that.

The persona hypothesis holds. One addition: credit and lease analysts care about the financing as much as the spend.

**2. Is the UI actionable and flexible enough?**
Not yet. Desk is the only view with flexibility, and it covers one company at a time with a single toggle. An analyst needs to:
- compare companies;
- choose a metric (levels, QoQ, YoY, intensity, trailing four quarters);
- switch between total and data-center segment;
- see each figure as first filed vs latest.

The lease toggle is also wrong. `FinanceLeasePrincipalPayments` is repayment of old leases, so adding it to capex double-counts timing. The new-spend measure is `RightOfUseAssetObtainedInExchangeForFinanceLeaseLiability` (non-cash supplemental), and it should be shown as a separate stacked layer.

**3. Are the data outcomes actionable?**
Only partly. There is lineage, but the schema can't carry a decision-grade answer:
- Values are rounded to USD_B. Store whole dollars.
- No period start/end, filed date, fy/fp, or dimension (segment axis/member).
- A `ytd_diff` or `q4_derived` figure comes from two or more filings but cites one accession. Add `derived_from: [fact_id]`.
- Dedupe by `frame` keeps only the latest value and erases restatements. Keep every vintage (bitemporal).
- Calendar alignment needs one written rule, e.g. the quarter containing the period-end date. Micron's quarters end in Nov/Feb/May/Aug, so they are off by one month.
- `OperatingExpenses` isn't comparable across companies. Amazon's includes COGS and Meta tags `CostsAndExpenses`. Drop opex or define it per company.
- Tesla should come out of the core set, or go behind a flag.
- Excluding CoreWeave hides the strongest risk signal in the data. Show it on its own scale.

**4. Best charts, each tied to a metric**
- **Acceleration strip:** QoQ and YoY capex growth plus its change (Δ of growth), per buyer. Answers "accelerating or rolling over?"
- **Intensity slope or heatmap:** `capex / revenue` and `capex / operating cash flow` (`NetCashProvidedByUsedInOperatingActivities`), with CoreWeave included.
- **FCF-after-capex bars:** OCF − capex − finance-lease ROU additions. This is the funding-risk view.
- **Depreciation overlay:** `DepreciationDepletionAndAmortization` / capex, annotated with useful-life changes. These come from 10-K note text, not XBRL facts, so annotate by hand with citations.
- **Seller-side Mirror, rebuilt:** data-center revenue only (Nvidia via `srt:ProductOrServiceAxis` / market platform; AMD's Data Center segment; Micron's 2025 segment reorg needs a restatement bridge). Add a lag cross-correlation between buyer capex and seller revenue.
- **Backlog panel:** `RevenueRemainingPerformanceObligation` (Oracle's RPO is the story there) and purchase obligations.
- **Concentration:** Nvidia's major-customer `ConcentrationRiskPercentage1`.
- **Financing:** `ProceedsFromIssuanceOfLongTermDebt`. Off-balance-sheet SPVs such as Meta's Hyperion are text-only.

Guidance isn't in XBRL. It is in 8-K EX-99.1 releases (untagged text) and earnings calls (not on EDGAR). Treat it as a separate extracted layer with a human gate and cite each quote.

**5. Chat and manipulation: architecture and cost**
The LLM never emits a number. The flow:
- A metric registry in YAML holds name, SQL, grain, tags and caveats.
- The question is parsed to an intent JSON: `{metric, tickers, period, transform}`. The schema is validated, and it compiles to SQL over DuckDB-WASM in the browser.
- The answer template fills in numbers from the result rows and cites the fact IDs and accessions.
- If the request is out of scope, it refuses.
- Evals: about 50 golden questions with exact-match numbers, plus checks that it refuses when it should and that every number has a citation.

Options:
- **(a) Structured query builder** (dropdowns compile to the same intent): $0. Ship this first.
- **(b) Precomputed Q&A,** generated in a Claude Code session: $0. Static.
- **(c) WebLLM in the browser** (a ~1.5B model doing intent parsing only): $0 server, ~1GB download for the visitor, flaky on phones.
- **(d) Ollama:** $0, but it only runs on Kenny's machine. Fine for a demo video, useless to a recruiter visiting the site.
- **(e) Small hosted model, intent only:** ~$0.0005/query; a $5 hard cap covers about 10k queries. This conflicts with the no-API-spend rule, so it needs Kenny's yes.

**Top 5 iteration steps**
1. **Fix the contract (M).** Whole-dollar values, period dates, filed date, dimensions, vintages, `derived_from`. Every later step depends on it.
2. **Correct the metric definitions (S).** Rename the hero to "capex"; use the ROU-based finance-lease measure; drop or redefine opex; flag Tesla; write the calendar rule. The current versions would get the piece dismissed in an interview.
3. **Build the data-center segment pipeline for sellers (M).** Without it Mirror can't make its argument, and it's the hardest XBRL work, which is exactly the skill on show.
4. **Add the derived signal layer (M).** Acceleration, intensity vs OCF, FCF after capex, depreciation/capex, RPO, concentration. This turns charts into decisions.
5. **Metric registry, DuckDB-WASM and query builder, with the eval set (M→L).** This is the "AI data strategist" proof point at $0 cost; option (c) can come later as a stretch.

**Verdict:** take Desk forward as the core and rebuild it around the metric registry, with a rebuilt Mirror (data-center revenue only) as the landing argument; fold Report's method section into both and drop Report as a standalone view.
