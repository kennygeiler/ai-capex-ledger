# Replication run: a Monday morning at Arctal (31 Oct 2026)

A data scientist at Arctal opens DATAHQ cold, works the actionable items, records decisions, and tries to produce
the dataset and the chart a manager would ask for. Done by Claude in the browser at 1600px, light theme, on the state
of the repo at `9ea9e68` (v1.5.0 signed and published, every tab on Tabler). Decisions were saved as
"Replication run (Claude), for Kenny Geiler to confirm" in `data/resolutions.jsonl`; Kenny can revert any of them.

The brief for the morning: make sure the data is clean and exportable, and be equipped to build a dataset or a
visualization on request.

## The verdict first

- **Exportable: yes.** Seven lists as CSV or JSON with filters, grouping and a signed-release switch; every row carries
  its provenance ids, method, basis and layer; the signed release is one table per list in Postgres. A manager's
  dataset request is a URL.
- **Clean: not yet, and the app does not say so loudly enough.** Four dirty values ship in v1.5.0 unflagged in the
  exports: Tesla's $1,000M "AI capex" is a misread of a cash-flow sentence; Applied Digital's AI share of capex is
  203%, 143% and 104%; AT&T's FY2022 opex is a unit error ($74.5M against $74,480M); AMD's AI revenue series mixes two
  scopes across years. Reconcile shows each of them, but nothing in the CSV marks a row as disputed or fix-pending.
- **Equipped for a chart: mostly.** Explore builds the standard asks in under a minute. It cannot plot a share (the
  saved "Hyperscaler AI share of capex" view opens as dollar amounts), truncates layer labels, and has no unit on the
  axis or a table of the plotted numbers.
- **The queue is three places and 182 of 198 items are noise.** Flow, Reconcile and Status each list the same
  findings; the real work is 16 rows.

## Walkthrough, tab by tab

### Flow (home)

Serving:
- One line says where things stand: 198 items, last run, last signed. The four stage cards give the shape of the
  pipeline in ten seconds. "Work through them in Reconcile" is the right first click.
- Dollars at stake sort the queue, so the $91B Alphabet fact and the $18B Alphabet attribution sit on top.

Hindering:
- "17 values differ from the SEC's data" and "53 cited cells not confirmed" have no path to the rows. They are the
  cleanest signal on the page and the only one that is not clickable.
- The Method card lists every model with "edit or rerun" on a Monday when no model needs editing. It should collapse
  to "7 models in use, prompt attribution@v2" with the list behind it.
- The scope select mixes 11 layers and 100 companies in one list of 111 options.
- "new since v1.5.0" sits under almost every row; a tag that is always on carries nothing.
- Three "Moved, $0M" rows (Riot, Talen) are in the queue: an attribution that went from none to words-only.
- Flow's queue and Reconcile's are the same items in a different order (dollars here, cause there). Two orders for
  one list means a person loses their place moving between them.

### Reconcile

Serving:
- Ours, reference, gap bar, delta and decision on one line is enough to triage every row without opening it. The
  seven stated-figure rows took four minutes to read and decide.
- Expand gives the arithmetic: inputs with an SEC badge, the AI amount, the total, the share. The "Every year" table
  is the single most useful thing on the page: Alphabet 34, 44, 56, 68% against a 90% floor and a 60% point tells the
  whole story without the words.
- Keyboard works (j, k, Enter, a, e, f, b, space). Select-all per cause and one reason for many is the right shape
  for the 182 findings.
- Save works. Explain hides the row; Fix keeps it open with a badge and the name; the count and dollars update.

Hindering:
- **What the reference measures is behind the "In words" toggle.** For Alphabet FY2024 the decision rests on one
  sentence ("share of capex going to technical infrastructure, a planning statement, wider than servers"). A fresh
  analyst would not open the toggle and would mark the row wrong. The reference's one-line "what it measures" belongs
  next to the stated figure, always visible.
- **The XBRL tag has no name.** A fact row says "XBRL tag $139,596M" and nothing else. To decide cell vs tag I need the
  concept and member (which us-gaap element, which axis). Iron Mountain's segment capex is $100M under the tag three
  years running: a definition difference, but which definition cannot be told from here.
- **No "add a definition" from Reconcile.** Flow offers it as the action on fact rows; Reconcile links to "The model"
  only. The fix for the Iron Mountain pattern is a definition, and the screen that shows the pattern cannot start it.
- The 182 findings are one group with three sub-kinds (line renamed, unit taken from elsewhere, restated or big
  move). The cause filter cannot split them, so "Select all 182" is the only bulk move and it is too coarse. A sub-kind
  filter would let a person accept all 60 "line renamed" rows in one go.
- Bulk save does not list what is selected. Selecting "every Lumentum row" caught a Lumentum finding (operating
  income) alongside the three revenue regressions, and the bulk reason went on it too. The form should name its rows.
- Moved rows title themselves "null: before and after": the period is not parsed from the key.
- Fix rows stay "open" in the count, which is right, but the decision badge reads "Fix" while the header still says
  "197 open"; a "fix pending" count beside "open" would stop the double-take.
- The row count on the page header (198) and on Flow (198) do not change when Fix is recorded; only Explain and
  Accept reduce it. Expected, but nowhere stated.

Roadblocks:
- **Decisions do not travel with the repo.** `data/resolutions.jsonl` is git-ignored with the rest of `data/`, so the five decisions
  recorded here exist only on this machine; a clone, or Arctal, never sees who judged what. Resolutions are judgement, not pipeline output;
  they belong with `definitions/` and `decisions/`, tracked.
- **A dirty value cannot be corrected from the UI.** AT&T FY2022 opex is $74.5M in the dataset against $74,480M in
  the SEC's data; the Reconcile row says "SEC data can't confirm", not "unit error", and the only action is a link to
  the dataset. Fixing it means a definition or an override from the CLI. For a data-cleaning job this is the wall.
- The stated_amount method can be fed by a misread sentence (Tesla) and nothing upstream catches it; the only guard
  is the gold set, which has one Tesla entry.

### Dataset

Serving:
- The grid is exactly the shape a manager expects: entities down, years across, the share under the amount, a mark
  per cell. Field, group and kind selects and a CSV export in one row. Click a cell for the drawer: value, share,
  method, model, basis, inputs, and for a statement value the cell, its cleaning steps and the screenshot.
- Export CSV carries provenance columns (basis, source_url, provenance ids). URL carries the selection.

Hindering:
- One ✗ glyph means two things: "differs from the SEC's XBRL" on a statement value and "disagrees with a stated
  figure" on an attribution. A manager reads ✗ as "wrong"; for Microsoft FY2025 it means "a journalist's paraphrase
  of a CFO said at most half".
- Shares above 100% (Applied Digital 203%, 143%, 104%) render like any other share. They need a mark, and the CSV a
  column.
- Resolution state is invisible here. Tesla FY2024 was just marked Fix in Reconcile; the grid still shows $1,000M ✗
  with no sign that someone has judged it.
- Amazon has FY2025 only. A gap like that should say why (the category rename, the notes reader) in the cell.
- "Chart" at the bottom is a details toggle to a line chart that Explore does better. It can go.
- "Custom…" opens a checkbox drawer of 100 tickers grouped by layer; fine, but there is no search box in it.

### Attribution

Serving:
- The heat grid by layer with a method badge per cell is the fastest way to see where the amounts are and where the
  thesis says "none". Clicking a badge opens the model; the model drawer has version, edit, dry run, use, rerun.

Hindering:
- Only capex, actual. Revenue exposure and committed amounts are not on this tab at all; a manager asking "who has
  AI revenue" has to know to use Explore.
- Badge letters (PPE, SEG, ST, SH, Q, ALL) have no legend on the page.
- The page title says "AI capex" over the grid and nothing else; the method mix counts live in a sentence.

### Explore

Serving:
- The three standard asks built in under a minute each: AI capex by hyperscaler by year (lines), AI revenue by layer
  (bars), capex plan-vs-actual gap by company (bars). Hover, legend toggle, zoom, click-for-rows all work. Save as
  view keeps the spec and the view is a URL another system can call.

Hindering:
- **No share.** The value for attribution is the dollar amount only. "Hyperscaler AI share of capex", a saved view,
  opens as amounts. Share of capex is the measure Arctal would quote; it must be a value option, and the saved view
  must keep it.
- Layer labels on the x axis truncate ("Chip desi…", "Memory, n…"). Rotate or wrap.
- No axis title or unit note; the $B and $M switch is silent.
- No table of the plotted numbers under the chart (only the raw rows on click, or the CSV of the whole list). A
  manager wants the five numbers the bars show, in a copyable table.
- The plans gap chart shows Equinix at −$10B in FY2025. That is not a chart problem; it is a plan read in the wrong
  unit or over several years, and it sits in `plans` unflagged.

### Status

Serving:
- The stat cards are the right seven numbers. Coverage by layer and field is the honest table: chip design capex is
  "none" for 9 and "not run" for 6 of 15; adopters are mostly "none". Cost per step and per company is the first
  thing a manager asks after "is it right".

Hindering:
- "Reference 13 / 20" here, "13 of 26 references agree" on Flow. Two denominators (with an estimate vs all entries)
  for one number.
- The findings table is the same 182 rows a third time.
- "Not run" in coverage (10 of 19 component suppliers for capex) is a pipeline gap, not a thesis decision, and the
  page does not say which.

### Releases, Agents

- Releases: clear. v1.5.0 signed, packet download, values table behind a toggle. v1.2.0 and v1.0.1 unsigned show
  "a packet needs a signature", which is right.
- Agents: one page of 174,000 characters: five readers, each with its full prompt text and its run table expanded.
  Useful to audit, unusable to skim. Collapse each reader to a card; open one at a time.
- "Add a company" has no nav entry; it is reachable from Flow only when a new filing is in the queue, or by typing
  `#run`.

## Decisions recorded (for Kenny to confirm)

| Item | Decision | Why |
|---|---|---|
| Alphabet AI capex FY2024, ours 56% vs stated ≥ 90% | Explain | Not comparable: the floor covers all technical infrastructure (servers, data centers, networking) and is a plan; ours is growth in the gross server category. Mark the gold entry not comparable. |
| AMD AI revenue FY2024, ours $5,000M vs stated $12,600M | Fix | FY2024 ours is Instinct only (">$5B"), FY2025 ours ($16.6B) is the whole Data Center segment. One scope for the series. |
| Tesla AI capex FY2024, ours $1,000M vs stated ≥ $5,000M | Fix | The $1,000M comes from a sentence about free cash flow and inventory. Misread; drop or re-read. |
| Lumentum revenue FY2023, FY2024, FY2025 attribution moved | Fix (bulk) | The last load regressed from segment amounts to words-only while the segment_revenue facts still exist. |
| Lumentum operating income, line renamed | Fix (bulk, unintended) | Caught by the bulk selection; harmless, but the bulk form should have listed its rows. Kenny can flip it to Accept. |

Not recorded, point of view formed:
- Alphabet FY2025 68% vs 60% and Microsoft FY2025 61% vs ≤ 50%: the growth-in-gross-category method overstates by
  design (software, finance leases, network and data-center assets in the category). Fix at the method, not the row.
- Micron AI revenue FY2025 $13.5B (CMBU segment) vs $10B stated (HBM): the segment is the wider proxy; Explain. But
  the series is broken: FY2022 $13.7B is a different segment than FY2023 $1.9B. Micron reorganized; the segment name
  changed. Fix.
- Applied Digital segment capex > total cash capex every year: accrual vs cash. Explain, and cap or flag the share.
- Iron Mountain segment capex $100M under the tag for three years: a definition difference; needs the tag's name.
- Alphabet FY2024 cell 141,852 vs tag 139,596 (+1.6%): the printed row carries footnote (1); likely a member
  difference. Accept the cell; name the tag.

## Data-quality findings that ship in v1.5.0

1. Tesla FY2024 ai_capex $1,000M, method stated_amount: a misread sentence. In `attribution.csv`.
2. Applied Digital ai_share 2.03, 1.43, 1.04 for FY2024 to FY2026: segment accrual capex over cash capex. In
   `attribution.csv` with no flag.
3. AT&T FY2022 opex $74.5M: unit error, SEC shows $74,480M. In `values.csv`, check_label unresolved, no finding kind
   that says "unit".
4. AMD ai_revenue FY2024 vs FY2025: two scopes in one series. In `attribution.csv`.
5. Micron ai_revenue FY2022 ($13.7B) vs FY2023 ($1.9B): segment definition changed across filings. In `attribution.csv`.
6. Lumentum revenue attribution FY2023 to FY2025: regressed to words-only in the last load; the prior amounts are in
   v1.5.0 (good) but the working database has lost them.
7. Equinix plans FY2025 gap −$10B: a plan in the wrong unit or a multi-year figure read as one year. In `plans.csv`.
8. Amazon AI capex: FY2025 only; the series has no history.

## Export readiness

What a data scientist has today, from the shell, no UI:

```
/api/v1/attribution?field=capex&kind=actual&layer=hyperscaler&format=csv
/api/v1/attribution?field=revenue&group=layer
/api/v1/values?ticker=MSFT,GOOGL&field=capex&release=v1.5.0&format=csv
/api/v1/facts?field=segment_capex&format=csv
/api/v1/plans?format=csv   /api/v1/projects?format=csv   /api/v1/statements?format=csv
/api/v1/views/<id>/data    /api/v1/coverage   /api/v1/cost
```

Missing for a clean handoff:
- A `flag` or `status` column on attribution and values rows: disputed, fix pending, accepted, explained, from
  `data/resolutions.jsonl`. Today the CSV cannot exclude the four dirty rows above without a join by hand.
- A `unit` column (values are integer dollars; nothing in the file says so) and a data dictionary endpoint
  (`/api/v1/fields`: field, definition, unit, kind, source step).
- A wide export (company × year for one field) for the people who live in spreadsheets. Dataset's Export CSV is long
  format with provenance; good for joins, wrong for a pivot.
- `ai_share` capped or accompanied by `share_over_total: true`.
- The XBRL concept name on facts (`xbrl_concept`, `xbrl_member`) beside the tag value.
- `last_run` and `run_id` on values (attribution has them).

## Fix list, ranked by what unblocks the Monday job

1. Track `data/resolutions.jsonl` (move it beside `decisions/`); resolution state into the exports and the Dataset grid (flag column; a mark on the cell).
2. Shares above 100% flagged everywhere; AT&T unit error becomes a "unit" finding with a one-click override.
3. "What it measures" visible beside every stated figure in Reconcile; XBRL concept and member named on fact rows.
4. "Add a definition" as an action in Reconcile, pre-filled from the row.
5. Sub-kind filter for findings (line renamed, unit from elsewhere, restated, big move) and bulk by sub-kind; the bulk
   form lists its rows.
6. Explore: share as a value option; saved share views keep it; axis unit note; a table of the plotted numbers;
   layer labels wrapped.
7. One queue: Flow shows the counts and links into Reconcile; Status drops its copy of the findings.
8. Flow: "17 values differ" and "53 cells not confirmed" link to their rows; Method card collapsed; scope select
   split into layer and company; "new since" shown only when it is not on every row; no $0M moved rows.
9. Fix the moved-row title ("null: before and after"); add a "fix pending" count.
10. Attribution tab: revenue and committed alongside capex; a badge legend.
11. Agents page: one card per reader, prompt and runs behind a toggle.
12. Two denominators for the reference check reconciled (20 vs 26).
13. Data: re-read Tesla, pick one AMD scope, repair Micron's segment series, restore Lumentum, check the Equinix
    plan, explain Amazon's gap in the cell.
